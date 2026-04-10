from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    APP_NAME: str = "Tamil Emotional Conversational AI"
    DEBUG: bool = True
    
    # Ollama LLM Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2:7b-instruct-q4_K_M"
    OLLAMA_TEMPERATURE: float = 0.75
    OLLAMA_MAX_TOKENS: int = 384
    OLLAMA_TOP_P: float = 0.95
    OLLAMA_REPEAT_PENALTY: float = 1.15
    
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

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
