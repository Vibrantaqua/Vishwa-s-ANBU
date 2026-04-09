from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    APP_NAME: str = "Tamil Emotional Conversational AI"
    DEBUG: bool = True
    
    # LLM Settings - Qwen2.5-3B-Instruct
    MODEL_PATH: str = os.path.join(os.path.dirname(__file__), "models", "qwen2.5-3b-instruct-q8_0gguf")
    LLM_N_GPU_LAYERS: int = -1
    LLM_N_THREADS: int = 6
    LLM_N_CTX: int = 2048
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 256
    
    # Whisper Settings (GPU mode)
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cuda"
    WHISPER_COMPUTE_TYPE: str = "float16"
    
    # XTTS Settings (GPU mode)
    XTTS_MODEL_PATH: Optional[str] = None
    XTTS_DEVICE: str = "cuda"
    XTTS_SPEAKER_WAV: str = os.path.join(os.path.dirname(__file__), "models", "tamil_speaker.wav")
    USE_XTTS: bool = False
    
    # VRAM Guard
    VRAM_THRESHOLD_GB: float = 3.8
    IDLE_VRAM_TARGET_GB: float = 3.2
    
    # Memory Settings
    DB_PATH: str = os.path.join(os.path.dirname(__file__), "data", "conversations.db")
    SUMMARY_INTERVAL: int = 5
    
    # System Prompt
    SYSTEM_PROMPT: str = """You are Anbu. You MUST respond ONLY in Tamil script (தமிழ்).
INPUT: I understand Tanglish, English, and Tamil.
OUTPUT: Always output in Tamil script only. No English letters in response.

JSON format:
{"response": "Tamil text only", "emotion": "happy", "filler_intensity": 0.0}

Examples:
- Input: "hello" -> Output: {"response": "வணக்கம்!", "emotion": "happy", "filler_intensity": 0.1}
- Input: "nalla irukka" -> Output: {"response": "நல்லா இருக்கேன்!", "emotion": "happy", "filler_intensity": 0.2}
- Input: "epadi irukka" -> Output: {"response": "எப்படி இருக்கேன்?", "emotion": "neutral", "filler_intensity": 0.3}"""

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
os.makedirs(os.path.dirname(settings.MODEL_PATH.replace(settings.MODEL_PATH.split("/")[-1], "")), exist_ok=True)
