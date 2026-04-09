import os
import numpy as np
import torch
import base64
import threading
import atexit
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple
from io import BytesIO
from scipy.io import wavfile
from loguru import logger
from config import settings

# Global executor for running TTS operations
_tts_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tts_worker")

def _cleanup_executor():
    _tts_executor.shutdown(wait=False)

atexit.register(_cleanup_executor)


class TextToSpeech:
    def __init__(
        self,
        device: str = "cpu",
        speaker_wav: Optional[str] = None
    ):
        self.device = device
        self.speaker_wav = speaker_wav or settings.XTTS_SPEAKER_WAV
        self._tts = None
        self._synthesizer = None
        self._is_initialized = False
        self._fallback_enabled = True

    def load_model(self) -> bool:
        if self._is_initialized:
            return True
        
        # Skip XTTS, use offline TTS
        logger.info("Using pyttsx3 for offline Tamil TTS...")
        self._fallback_enabled = True
        self._is_initialized = True
        logger.info("TTS ready (offline mode)")
        return True

    def synthesize_speech(
        self,
        text: str,
        language: str = "ta"
    ) -> Tuple[Optional[bytes], bool]:
        if not self._is_initialized:
            self.load_model()
        
        return self._generate_fallback_audio(text)

    def _generate_fallback_audio(self, text: str) -> Tuple[bytes, bool]:
        # Try edge-tts (best quality, needs internet)
        try:
            import edge_tts
            import asyncio
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                temp_path = f.name
            asyncio.run(edge_tts.aget_audio(text[:500], temp_path))
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(temp_path)
            audio = audio.set_frame_rate(24000).set_channels(1)
            os.unlink(temp_path)
            buffer = BytesIO()
            audio.export(buffer, format='wav')
            return buffer.getvalue(), False
        except Exception as e:
            logger.warning(f"edge-tts failed: {e}, trying gTTS...")
        
        # Try gTTS (online)
        try:
            from gtts import gTTS
            import tempfile
            tts = gTTS(text=text[:500], lang='ta', slow=False)
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                temp_path = f.name
            tts.save(temp_path)
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(temp_path)
            audio = audio.set_frame_rate(24000).set_channels(1)
            os.unlink(temp_path)
            buffer = BytesIO()
            audio.export(buffer, format='wav')
            return buffer.getvalue(), False
        except Exception as e:
            logger.warning(f"gTTS failed: {e}, trying pyttsx3...")
        
        # Try pyttsx3 (offline) - run in dedicated thread to avoid threading conflicts
        try:
            import pyttsx3
            import tempfile
            
            def _run_pyttsx3(txt):
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    temp_path = f.name
                engine.save_to_file(txt[:500], temp_path)
                engine.runAndWait()
                engine.stop()
                import soundfile as sf
                audio_data, sr = sf.read(temp_path)
                if len(audio_data.shape) > 1:
                    audio_data = audio_data[:, 0]
                buffer = BytesIO()
                wavfile.write(buffer, int(sr), (audio_data * 32767).astype(np.int16))
                os.unlink(temp_path)
                return buffer.getvalue()
            
            audio_bytes = _tts_executor.submit(_run_pyttsx3, text).result(timeout=10)
            return audio_bytes, False
        except Exception as e:
            logger.warning(f"pyttsx3 failed: {e}, using beep")
        
        # Last resort: beep
        try:
            import scipy.signal as signal
            duration = min(len(text) * 0.08, 3.0)
            sample_rate = 22050
            t = np.linspace(0, duration, int(sample_rate * duration))
            freq_mod = 150 + 50 * np.sin(2 * np.pi * 2 * t)
            audio = 0.3 * signal.chirp(t, f0=120, f1=freq_mod[-1], t1=duration, method='linear')
            envelope = np.ones_like(audio)
            fade_samples = int(0.05 * sample_rate)
            envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
            envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
            audio = audio * envelope * 0.3
            audio_int16 = (audio * 32767).astype(np.int16)
            buffer = BytesIO()
            wavfile.write(buffer, sample_rate, audio_int16)
            return buffer.getvalue(), True  # Fallback to emergency beep
        except Exception as e:
            logger.error(f"Fallback audio generation failed: {e}")
            return b"", True

    def synthesize_to_base64(
        self,
        text: str,
        language: str = "ta"
    ) -> Optional[str]:
        audio_bytes, success = self.synthesize_speech(text, language)
        
        if audio_bytes:
            return base64.b64encode(audio_bytes).decode('utf-8')
        return None

    def is_initialized(self) -> bool:
        return self._is_initialized

    def is_fallback_mode(self) -> bool:
        return self._fallback_enabled

    def unload(self) -> None:
        if self._tts is not None:
            del self._tts
            self._tts = None
            self._is_initialized = False
            logger.info("TTS model unloaded")


tts = TextToSpeech(
    device=settings.XTTS_DEVICE,
    speaker_wav=settings.XTTS_SPEAKER_WAV
)
