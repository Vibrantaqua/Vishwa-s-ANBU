import numpy as np
import torch
from typing import Optional, Union
from faster_whisper import WhisperModel
from loguru import logger
from config import settings


class SpeechToText:
    def __init__(
        self,
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Optional[WhisperModel] = None
        self._is_initialized = False

    def load_model(self) -> None:
        if self._is_initialized:
            return
        
        logger.info(f"Loading Whisper {self.model_size} on {self.device}...")
        
        try:
            # Ensure CUDA is available if GPU device is requested
            if self.device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA not available, falling back to CPU")
                self.device = "cpu"
                self.compute_type = "int8"
            
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=None,
                num_workers=4 if self.device == "cuda" else 1
            )
            self._is_initialized = True
            logger.info(f"Whisper model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def _is_gibberish(self, text: str) -> bool:
        if not text or len(text.strip()) < 3:
            return True
        
        text_lower = text.lower()
        
        gibberish_patterns = [
            "le steel", "leel steel", "leel steal",
            "silence", "noise", "background",
            "uh uh", "um um", "ah ah"
        ]
        
        for pattern in gibberish_patterns:
            if pattern in text_lower:
                return True
        
        english_letters = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        total_letters = sum(1 for c in text if c.isalpha())
        
        if total_letters > 0 and english_letters / total_letters > 0.9:
            words = text.split()
            if len(words) <= 3 and all(len(w) <= 4 for w in words):
                return True
        
        return False

    def transcribe(
        self,
        audio_data: Union[np.ndarray, list],
        sample_rate: int = 16000,
        language: Optional[str] = "ta",
        task: str = "transcribe"
    ) -> dict:
        if not self._is_initialized:
            self.load_model()
        
        if isinstance(audio_data, list):
            audio_data = np.array(audio_data, dtype=np.float32)
        
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        if audio_data.max() > 1.0:
            audio_data = audio_data / 32768.0
        
        audio_data = np.squeeze(audio_data)
        
        try:
            segments, info = self._model.transcribe(
                audio_data,
                language="ta",
                task=task,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=400
                ),
                initial_prompt="Tamil, Tanglish, Anbu, Josh.",
                no_speech_threshold=0.6
            )
            
            full_text = ""
            segment_list = []
            
            for segment in segments:
                full_text += segment.text
                segment_list.append({
                    "text": segment.text,
                    "start": segment.start,
                    "end": segment.end
                })
            
            full_text = full_text.strip()
            
            if self._is_gibberish(full_text):
                logger.debug(f"Gibberish detected, filtering: {full_text}")
                full_text = ""
            
            return {
                "text": full_text,
                "segments": segment_list,
                "language": info.language,
                "language_probability": info.language_probability
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {
                "text": "",
                "segments": [],
                "language": "ta",
                "language_probability": 0.0,
                "error": str(e)
            }

    def transcribe_from_file(self, file_path: str) -> dict:
        if not self._is_initialized:
            self.load_model()
        
        try:
            segments, info = self._model.transcribe(
                file_path,
                language="ta",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=400),
                initial_prompt="Tamil, Tanglish, Anbu, Josh.",
                no_speech_threshold=0.6
            )
            
            full_text = "".join([segment.text for segment in segments])
            full_text = full_text.strip()
            
            if self._is_gibberish(full_text):
                full_text = ""
            
            return {
                "text": full_text,
                "language": info.language,
                "language_probability": info.language_probability
            }
        except Exception as e:
            logger.error(f"File transcription error: {e}")
            return {"text": "", "error": str(e)}

    def is_initialized(self) -> bool:
        return self._is_initialized

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            self._is_initialized = False
            logger.info("Whisper model unloaded")


stt = SpeechToText(
    model_size=settings.WHISPER_MODEL,
    device=settings.WHISPER_DEVICE,
    compute_type=settings.WHISPER_COMPUTE_TYPE
)
