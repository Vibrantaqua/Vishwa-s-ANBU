import asyncio
import base64
import uuid
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger
import torch
import numpy as np

from config import settings
from models.llm import llm
from models.stt import stt
from models.tts import tts
from models import stt as stt_module
from utils.audio_buffer import AudioBuffer, get_available_devices, get_default_input_device
from memory.conversation_memory import summary_memory, memory


class AudioInput(BaseModel):
    audio_data: str
    session_id: Optional[str] = None


class TextInput(BaseModel):
    text: str
    session_id: Optional[str] = None


class ConversationResponse(BaseModel):
    response: str
    emotion: str
    filler_intensity: float
    audio_base64: Optional[str] = None
    session_id: str
    new_summary: Optional[str] = None
    transcription: Optional[str] = None


class StatusResponse(BaseModel):
    status: str
    vram_usage_gb: float
    models_loaded: bool
    session_id: Optional[str] = None


connections: dict[str, WebSocket] = {}
audio_buffers: dict[str, AudioBuffer] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Tamil Emotional AI Server...")
    
    try:
        llm.load_model()
        logger.info(f"LLM ready (Ollama: {settings.OLLAMA_MODEL})")
    except Exception as e:
        logger.error(f"LLM init failed: {e}")
    
    try:
        stt.load_model()
        logger.info("STT ready")
    except Exception as e:
        logger.error(f"STT load failed: {e}")
    
    try:
        tts.load_model()
        logger.info("TTS ready")
    except Exception as e:
        logger.warning(f"TTS load failed, fallback enabled: {e}")
    
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    
    yield
    
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=StatusResponse)
async def root():
    return StatusResponse(
        status="online",
        vram_usage_gb=0.0,
        models_loaded=llm.is_initialized() and stt.is_initialized()
    )


@app.get("/status", response_model=StatusResponse)
async def get_status():
    return StatusResponse(
        status="ready",
        vram_usage_gb=0.0,
        models_loaded=llm.is_initialized() and stt.is_initialized()
    )


@app.get("/audio/devices")
async def list_audio_devices():
    devices = get_available_devices()
    default = get_default_input_device()
    return {
        "devices": devices,
        "default_input": default
    }


@app.post("/conversation/text", response_model=ConversationResponse)
async def text_conversation(input_data: TextInput):
    session_id = input_data.session_id or str(uuid.uuid4())
    
    try:
        history_context = await summary_memory.get_context_for_prompt(session_id)
        
        llm_response = llm.generate_response(
            user_input=input_data.text,
            history_context=history_context
        )
        
        new_summary = await summary_memory.add_turn_and_check_summary(
            session_id=session_id,
            user_input=input_data.text,
            bot_response=llm_response["response"],
            emotion=llm_response["emotion"],
            filler_intensity=llm_response["filler_intensity"]
        )
        
        audio_base64 = tts.synthesize_to_base64(llm_response["response"])
        
        return ConversationResponse(
            response=llm_response["response"],
            emotion=llm_response["emotion"],
            filler_intensity=llm_response["filler_intensity"],
            audio_base64=audio_base64,
            session_id=session_id,
            new_summary=new_summary
        )
        
    except Exception as e:
        logger.error(f"Conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/conversation/audio", response_model=ConversationResponse)
async def audio_conversation(input_data: AudioInput):
    session_id = input_data.session_id or str(uuid.uuid4())
    
    try:
        from pydub import AudioSegment
        import numpy as np
        from io import BytesIO
        
        audio_bytes = base64.b64decode(input_data.audio_data)
        buffer = BytesIO(audio_bytes)
        
        try:
            buffer.seek(0)
            audio_segment = AudioSegment.from_file(buffer)
        except Exception:
            try:
                buffer.seek(0)
                audio_segment = AudioSegment.from_file(buffer, format="webm")
            except Exception as e:
                logger.error(f"Audio parsing failed: {e}")
                return ConversationResponse(
                    response="mm, audio ah parchingala?",
                    emotion="confused",
                    filler_intensity=0.3,
                    session_id=session_id
                )
        
        audio_segment = audio_segment.set_frame_rate(16000).set_channels(1)
        audio_data = np.array(audio_segment.get_array_of_samples(), dtype=np.float32) / 32768.0
        sample_rate = 16000
        
        transcription = stt.transcribe(audio_data, sample_rate=16000)
        
        if not transcription["text"] or len(transcription["text"]) < 2:
            return ConversationResponse(
                response="mm, enna?",
                emotion="confused",
                filler_intensity=0.3,
                session_id=session_id
            )
        
        history_context = await summary_memory.get_context_for_prompt(session_id)
        
        llm_response = llm.generate_response(
            user_input=transcription["text"],
            history_context=history_context
        )
        
        new_summary = await summary_memory.add_turn_and_check_summary(
            session_id=session_id,
            user_input=transcription["text"],
            bot_response=llm_response["response"],
            emotion=llm_response["emotion"],
            filler_intensity=llm_response["filler_intensity"]
        )
        
        audio_base64 = tts.synthesize_to_base64(llm_response["response"])
        
        return ConversationResponse(
            response=llm_response["response"],
            emotion=llm_response["emotion"],
            filler_intensity=llm_response["filler_intensity"],
            audio_base64=audio_base64,
            session_id=session_id,
            new_summary=new_summary,
            transcription=transcription["text"]
        )
        
    except Exception as e:
        logger.error(f"Audio conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/stream/{session_id}")
async def websocket_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    connections[session_id] = websocket
    
    audio_buffer = AudioBuffer()
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "start":
                audio_buffer.start()
                
            elif data.get("type") == "stop":
                audio_data = audio_buffer.stop()
                
                if audio_data is not None and len(audio_data) > 1600:
                    transcription = stt.transcribe(audio_data)
                    
                    if transcription["text"] and len(transcription["text"]) > 2:
                        history_context = await summary_memory.get_context_for_prompt(session_id)
                        
                        llm_response = llm.generate_response(
                            user_input=transcription["text"],
                            history_context=history_context
                        )
                        
                        await summary_memory.add_turn_and_check_summary(
                            session_id=session_id,
                            user_input=transcription["text"],
                            bot_response=llm_response["response"],
                            emotion=llm_response["emotion"],
                            filler_intensity=llm_response["filler_intensity"]
                        )
                        
                        audio_base64 = tts.synthesize_to_base64(llm_response["response"])
                        
                        await websocket.send_json({
                            "type": "response",
                            "transcription": transcription["text"],
                            "response": llm_response["response"],
                            "emotion": llm_response["emotion"],
                            "filler_intensity": llm_response["filler_intensity"],
                            "audio": audio_base64
                        })
                    else:
                        await websocket.send_json({
                            "type": "response",
                            "response": "mm?",
                            "emotion": "neutral",
                            "filler_intensity": 0.3
                        })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No audio detected"
                    })
                    
            elif data.get("type") == "audio_chunk":
                if data.get("chunk"):
                    chunk_bytes = base64.b64decode(data["chunk"])
                    audio_buffer._buffer.append(
                        np.frombuffer(chunk_bytes, dtype=np.float32)
                    )
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        audio_buffer.stop()
        connections.pop(session_id, None)


@app.get("/conversation/history/{session_id}")
async def get_conversation_history(session_id: str, limit: int = 20):
    turns = await memory.get_recent_turns(session_id, limit)
    summary = await memory.get_latest_summary(session_id)
    return {
        "session_id": session_id,
        "turns": turns,
        "summary": summary,
        "turn_count": len(turns)
    }


@app.delete("/conversation/history/{session_id}")
async def clear_conversation(session_id: str):
    await summary_memory.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.post("/vram/cleanup")
async def force_vram_cleanup():
    return {
        "status": "cleaned",
        "vram_usage_gb": 0.0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
