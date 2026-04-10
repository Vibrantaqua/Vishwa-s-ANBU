import json
import re
import requests
from typing import Optional, Dict, Any, List
from collections import OrderedDict
from loguru import logger
from config import settings


def detect_user_language(text: str) -> str:
    """Detect if user is speaking Tanglish, Tamil, or English"""
    tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    total = len(text.replace(' ', ''))
    
    if total == 0:
        return "tanglish"
    
    tamil_ratio = tamil_chars / total if total > 0 else 0
    
    tamil_words = ['en', 'naan', 'nee', 'epadi', 'enga', 'enna', 'un', 'nan', 'irukka', 'iruken', 'irukku', 'sollu', 'pannu', 'thaan', 'da', 'di', 'la', 'nu', 'vanakkam', 'nalla', 'sellam', 'semma', 'kandippa', 'paathu', 'mudiyathu', 'apparam', 'thangiyow']
    english_words = ['hi', 'hello', 'hey', 'how', 'what', 'where', 'why', 'bro', 'friend', 'help', 'please', 'thanks', 'thank', 'you', 'are', 'doing', 'good', 'nice', 'great']
    
    text_lower = text.lower()
    tamil_word_count = sum(1 for word in tamil_words if word in text_lower)
    english_word_count = sum(1 for word in english_words if word in text_lower)
    
    if tamil_ratio > 0.4:
        return "tamil"
    elif tamil_word_count >= 1 or english_word_count >= 1:
        return "tanglish"
    else:
        return "tanglish"


class ConversationHistory:
    """Simple in-memory conversation history per session"""
    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self._history: OrderedDict[str, List[Dict]] = OrderedDict()
    
    def add_turn(self, session_id: str, user: str, assistant: str) -> None:
        if session_id not in self._history:
            self._history[session_id] = []
        
        self._history[session_id].append({
            "user": user,
            "assistant": assistant
        })
        
        if len(self._history[session_id]) > self.max_turns:
            self._history[session_id].pop(0)
        
        self._history.move_to_end(session_id)
    
    def get_history(self, session_id: str) -> str:
        if session_id not in self._history:
            return ""
        
        history_text = ""
        for turn in self._history[session_id]:
            history_text += f"User: {turn['user']}\nAnbu: {turn['assistant']}\n"
        
        return history_text.strip()
    
    def clear(self, session_id: str) -> None:
        if session_id in self._history:
            del self._history[session_id]


conversation_history = ConversationHistory(max_turns=5)


class EmotionalLLM:
    def __init__(
        self,
        model: str = "qwen2:7b-instruct-q4_K_M",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.75,
        max_tokens: int = 384
    ):
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._is_initialized = False
        
        self.system_prompt = """You are Anbu. You MUST follow these rules:

1. RESPOND IN TAMILGLISH ONLY (NOT PURE ENGLISH)
2. TamilGLISH = Tamil words + English words mixed together
3. Examples of WRONG responses (pure English - DON'T DO THIS):
   - "Hey! How are you doing?"
   - "That's great! Let me know if you need anything."
   - "I can help you with your studies."

4. Examples of CORRECT responses (TamilGLISH):
   - "Semma! Epadi iruka?"
   - "Kandippa, help pannuren"
   - "Nanba, studies la erpudi?"
   - "Haan bro, kandippa"

5. Common TamilGLISH phrases to use:
   - "Semma", "Kandippa", "Nanba", "Bro", "Haan", "Aama"
   - "Epadi", "Enna", "Venna", "Pannuren"
   - "Help", "Studies", "Work", "Time"

6. Keep responses SHORT - 1 sentence max

7. If you don't understand, say: "Nanba, athu theriyathu"

Start every response with Tamil word: Semma, Kandippa, Haan, Nanba, etc."""

    def load_model(self) -> None:
        self._is_initialized = True
        logger.info(f"Ollama LLM ready: {self.model}")

    def generate_response(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        history_context: str = "",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self._is_initialized:
            self.load_model()
        
        user_lang = detect_user_language(user_input)
        logger.info(f"User language: {user_lang}")
        
        history_text = ""
        if session_id:
            history_text = conversation_history.get_history(session_id)
        
        system_content = self.system_prompt
        if history_text:
            system_content += f"\n\nCONVERSATION HISTORY:\n{history_text}"
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_input}
        ]
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                        "top_p": 0.95,
                        "repeat_penalty": 1.15,
                    },
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("message", {}).get("content", "").strip()
            
            logger.debug(f"LLM raw: {content[:300]}")
            
            formatted_response = self._format_response(content, user_lang)
            
            if session_id:
                conversation_history.add_turn(session_id, user_input, formatted_response["response"])
            
            return formatted_response
            
        except requests.exceptions.Timeout:
            logger.error("LLM request timed out after 60 seconds")
            return self._get_fallback_response(user_lang)
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return self._get_fallback_response(user_lang)

    def _format_response(self, content: str, user_lang: str) -> Dict[str, Any]:
        content = content.strip()
        
        content = self._fix_tanglish(content)
        
        emotion = self._detect_emotion(content)
        filler = self._detect_filler(content)
        
        return {
            "response": content,
            "emotion": emotion,
            "filler_intensity": filler
        }
    
    def _fix_tanglish(self, text: str) -> str:
        """Convert pure English sentences to Tanglish if needed"""
        pure_english_phrases = [
            ("how are you", "epadi iruka"),
            ("how's it going", "epadi iruka"),
            ("how are you doing", "epadi iruka"),
            ("that's great", "semma"),
            ("that's good", "semma"),
            ("let me know", "sollu"),
            ("i can help", "help pannuren"),
            ("no problem", "no issues"),
            ("no worries", "no problem bro"),
        ]
        
        text_lower = text.lower()
        
        tamil_words = ['semma', 'kandippa', 'nanba', 'bro', 'haan', 'aama', 'appidiya', 'thangiyow', 'enna', 'epadi', 'nalla', 'iruka', 'iruken', 'pannu', 'sollu', 'theriyathu', 'vellam', 'po', 'va']
        has_tamil = any(word in text_lower for word in tamil_words)
        
        if not has_tamil and len(text) > 30:
            for eng, taml in pure_english_phrases:
                if eng in text_lower:
                    text = text.replace(eng, taml)
                    text = text.replace(eng.title(), taml.title())
        
        return text

    def _detect_emotion(self, text: str) -> str:
        text_lower = text.lower()
        
        if any(w in text_lower for w in ['semma', 'kandippa', 'thaangiyow', 'appidiya', 'wow', 'super', 'semmaa']):
            return "excited"
        elif any(w in text_lower for w in ['sorry', 'sad', 'paathu', 'konjam', 'nanu', 'heavy']):
            return "empathetic"
        elif any(w in text_lower for w in ['?', 'theriyathu', 'enna', 'enh', 'how', 'what', 'why']):
            return "confused"
        elif any(w in text_lower for w in ['okay', 'ok', 'haan', 'aama', 'aa', 'yeah', 'ha']):
            return "happy"
        
        return "happy"

    def _detect_filler(self, text: str) -> float:
        filler_words = ['mm', 'mmm', 'aama', 'aam', 'kandippa', 'semma', 'etho', 'nanu', 'paathu', 'konjam']
        text_lower = text.lower()
        count = sum(1 for w in filler_words if w in text_lower)
        return min(1.0, count * 0.15)

    def _get_fallback_response(self, user_lang: str = "tanglish") -> Dict[str, Any]:
        return {"response": "Nanba, athu theriyathu.enna help venna?", "emotion": "neutral", "filler_intensity": 0.4}

    def is_initialized(self) -> bool:
        return self._is_initialized

    def clear_cache(self) -> None:
        logger.info("Ollama LLM cache cleared")
    
    def clear_history(self, session_id: str) -> None:
        conversation_history.clear(session_id)
        logger.info(f"Cleared conversation history for session: {session_id}")


llm = EmotionalLLM(
    model=settings.OLLAMA_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
    temperature=settings.OLLAMA_TEMPERATURE,
    max_tokens=settings.OLLAMA_MAX_TOKENS
)
