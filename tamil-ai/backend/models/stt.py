import numpy as np
import torch
from typing import Optional, Union
from transformers import pipeline, AutoModelForSpeechSeq2Seq, AutoProcessor
from loguru import logger
from config import settings


class SpeechToText:
    def __init__(
        self,
        model_id: str = "vasista22/whisper-tamil-medium",
        device: str = "cuda",
        compute_type: str = "float16"
    ):
        self.model_id = model_id
        self.device = device
        self.compute_type = compute_type
        self._pipe = None
        self._is_initialized = False

    def load_model(self) -> None:
        if self._is_initialized:
            return
        
        logger.info(f"Loading {self.model_id} on {self.device}...")
        
        try:
            if self.device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA not available, falling back to CPU")
                self.device = "cpu"
                self.compute_type = "float32"
            
            torch_dtype = torch.float16 if self.device == "cuda" else torch.float32
            
            model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.model_id,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True
            )
            processor = AutoProcessor.from_pretrained(self.model_id)
            
            self._pipe = pipeline(
                "automatic-speech-recognition",
                model=model,
                tokenizer=processor.tokenizer,
                feature_extractor=processor.feature_extractor,
                device=self.device,
                torch_dtype=torch_dtype
            )
            
            if hasattr(self._pipe.model, 'config') and hasattr(self._pipe.tokenizer, 'get_decoder_prompt_ids'):
                self._pipe.model.config.forced_decoder_ids = self._pipe.tokenizer.get_decoder_prompt_ids(
                    language="ta", task="transcribe"
                )
                logger.info("Forced Tamil language decoding")
            
            self._is_initialized = True
            logger.info(f"HuggingFace Tamil Whisper model loaded successfully on {self.device}")
        except Exception as e:
            error_msg = str(e).lower()
            if "cublas" in error_msg or "cudart" in error_msg or "cuda" in error_msg or "out of memory" in error_msg:
                logger.warning(f"CUDA error ({e}), falling back to CPU...")
                self.device = "cpu"
                self.compute_type = "float32"
                try:
                    torch_dtype = torch.float32
                    model = AutoModelForSpeechSeq2Seq.from_pretrained(
                        self.model_id,
                        torch_dtype=torch_dtype,
                        low_cpu_mem_usage=True
                    )
                    processor = AutoProcessor.from_pretrained(self.model_id)
                    
                    self._pipe = pipeline(
                        "automatic-speech-recognition",
                        model=model,
                        tokenizer=processor.tokenizer,
                        feature_extractor=processor.feature_extractor,
                        device="cpu",
                        torch_dtype=torch_dtype
                    )
                    
                    if hasattr(self._pipe.model, 'config') and hasattr(self._pipe.tokenizer, 'get_decoder_prompt_ids'):
                        self._pipe.model.config.forced_decoder_ids = self._pipe.tokenizer.get_decoder_prompt_ids(
                            language="ta", task="transcribe"
                        )
                    
                    self._is_initialized = True
                    logger.info("Tamil Whisper model loaded successfully on CPU (fallback)")
                except Exception as e2:
                    logger.error(f"Failed to load Tamil Whisper on CPU: {e2}")
                    raise
            else:
                logger.error(f"Failed to load Tamil Whisper model: {e}")
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
        
        if total_letters > 0 and english_letters / total_letters > 0.95:
            words = text.split()
            if len(words) <= 2 and all(len(w) <= 3 for w in words):
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
            result = self._pipe(
                audio_data,
                return_timestamps=False,
                generate_kwargs={
                    "language": "ta",
                    "task": "transcribe"
                }
            )
            
            full_text = result.get("text", "")
            full_text = full_text.strip()
            
            if self._is_gibberish(full_text):
                logger.debug(f"Gibberish detected, filtering: {full_text}")
                full_text = ""
            
            segment_list = []
            if full_text:
                segment_list.append({
                    "text": full_text,
                    "start": 0.0,
                    "end": 0.0
                })
            
            return {
                "text": full_text,
                "segments": segment_list,
                "language": "ta",
                "language_probability": 0.0
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
            result = self._pipe(
                file_path,
                return_timestamps=False,
                generate_kwargs={
                    "language": "ta",
                    "task": "transcribe"
                }
            )
            
            full_text = result.get("text", "")
            full_text = full_text.strip()
            
            if self._is_gibberish(full_text):
                full_text = ""
            
            return {
                "text": full_text,
                "language": "ta",
                "language_probability": 0.0
            }
        except Exception as e:
            logger.error(f"File transcription error: {e}")
            return {"text": "", "error": str(e)}

    def is_initialized(self) -> bool:
        return self._is_initialized

    def unload(self) -> None:
        if self._pipe is not None:
            del self._pipe
            self._pipe = None
            self._is_initialized = False
            logger.info("Tamil Whisper model unloaded")
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()


stt = SpeechToText(
    model_id=settings.HF_STT_MODEL,
    device=settings.HF_STT_DEVICE,
    compute_type=settings.HF_STT_COMPUTE_TYPE
)
