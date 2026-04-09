import aiosqlite
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from loguru import logger
from config import settings


class ConversationMemory:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._conn: Optional[aiosqlite.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        async def _setup():
            conn = await aiosqlite.connect(self.db_path)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    user_input TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    emotion TEXT,
                    filler_intensity REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    summary_text TEXT NOT NULL,
                    turn_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session 
                ON conversations(session_id, turn_number)
            """)
            await conn.commit()
            await conn.close()
        
        asyncio.run(_setup())
        logger.info(f"Database initialized at {self.db_path}")

    async def _get_connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
        return self._conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def add_turn(
        self,
        session_id: str,
        user_input: str,
        bot_response: str,
        emotion: str,
        filler_intensity: float
    ) -> int:
        async with self._lock:
            conn = await self._get_connection()
            async with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COALESCE(MAX(turn_number), 0) + 1 as next_turn
                    FROM conversations WHERE session_id = ?
                """, (session_id,))
                next_turn = cursor.fetchone()["next_turn"]
                
                cursor.execute("""
                    INSERT INTO conversations 
                    (session_id, turn_number, user_input, bot_response, emotion, filler_intensity)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, next_turn, user_input, bot_response, emotion, filler_intensity))
                conn.commit()
                return next_turn

    async def get_recent_turns(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        async with self._lock:
            conn = await self._get_connection()
            async with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE session_id = ?
                    ORDER BY turn_number DESC
                    LIMIT ?
                """, (session_id, limit))
                rows = cursor.fetchall()
                return [dict(row) for row in reversed(rows)]

    async def get_turn_count(self, session_id: str) -> int:
        async with self._lock:
            conn = await self._get_connection()
            async with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as count FROM conversations WHERE session_id = ?
                """, (session_id,))
                return cursor.fetchone()["count"]

    async def save_summary(self, session_id: str, summary: str, turn_count: int) -> None:
        async with self._lock:
            conn = await self._get_connection()
            async with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO summaries (session_id, summary_text, turn_count)
                    VALUES (?, ?, ?)
                """, (session_id, summary, turn_count))
                conn.commit()
                logger.info(f"Summary saved for session {session_id}")

    async def get_latest_summary(self, session_id: str) -> Optional[str]:
        async with self._lock:
            conn = await self._get_connection()
            async with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT summary_text FROM summaries
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (session_id,))
                row = cursor.fetchone()
                return row["summary_text"] if row else None

    async def should_summarize(self, session_id: str, interval: int = 5) -> bool:
        count = await self.get_turn_count(session_id)
        return count > 0 and count % interval == 0


class ConversationSummaryMemory:
    def __init__(
        self,
        memory: ConversationMemory,
        summary_interval: int = 5,
        max_history_turns: int = 3
    ):
        self.memory = memory
        self.summary_interval = summary_interval
        self.max_history_turns = max_history_turns

    async def add_turn_and_check_summary(
        self,
        session_id: str,
        user_input: str,
        bot_response: str,
        emotion: str,
        filler_intensity: float
    ) -> Optional[str]:
        await self.memory.add_turn(
            session_id, user_input, bot_response, emotion, filler_intensity
        )
        
        if await self.memory.should_summarize(session_id, self.summary_interval):
            return await self.generate_and_save_summary(session_id)
        
        return None

    async def generate_and_save_summary(self, session_id: str) -> str:
        turns = await self.memory.get_recent_turns(
            session_id, 
            limit=self.summary_interval * 2
        )
        
        if not turns:
            return ""
        
        summary_parts = []
        for turn in turns[-self.summary_interval:]:
            summary_parts.append(
                f"User: {turn['user_input'][:100]}... | "
                f"Anbu: {turn['bot_response'][:100]}... ({turn['emotion']})"
            )
        
        summary = "முந்தைய உரையாடல்: " + " | ".join(summary_parts)
        
        turn_count = await self.memory.get_turn_count(session_id)
        await self.memory.save_summary(session_id, summary, turn_count)
        
        logger.info(f"Generated summary for session {session_id}")
        return summary

    async def get_context_for_prompt(self, session_id: str) -> str:
        recent_summary = await self.memory.get_latest_summary(session_id)
        
        if recent_summary:
            context = f"[முந்தைய உரையாடல் சுருக்கம்]: {recent_summary}\n\n"
        else:
            context = ""
        
        recent_turns = await self.memory.get_recent_turns(
            session_id, 
            limit=self.max_history_turns
        )
        
        if recent_turns:
            context += "[சமீபத்திய உரையாடல்]:\n"
            for turn in recent_turns:
                context += f"User: {turn['user_input']}\nAnbu: {turn['bot_response']}\n"
        
        return context

    async def clear_session(self, session_id: str) -> None:
        async with self.memory._lock:
            conn = await self.memory._get_connection()
            async with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM conversations WHERE session_id = ?", 
                    (session_id,)
                )
                cursor.execute(
                    "DELETE FROM summaries WHERE session_id = ?", 
                    (session_id,)
                )
                conn.commit()
                logger.info(f"Cleared session {session_id}")


memory = ConversationMemory(settings.DB_PATH)
summary_memory = ConversationSummaryMemory(memory, settings.SUMMARY_INTERVAL)
