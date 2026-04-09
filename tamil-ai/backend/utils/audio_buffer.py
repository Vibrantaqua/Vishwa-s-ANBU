import numpy as np
import queue
import threading
import sounddevice as sd
from typing import Optional, Callable
from loguru import logger


class AudioBuffer:
    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration: float = 0.5,
        silence_threshold: float = 0.02,
        silence_duration: float = 1.5,
        max_duration: float = 30.0
    ):
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_duration = max_duration
        
        self._buffer: list = []
        self._is_recording = False
        self._silence_frames = 0
        self._total_frames = 0
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._callback: Optional[Callable] = None

    def _audio_callback(self, indata, frames, time, status):
        if status:
            logger.warning(f"Audio input status: {status}")
        
        audio_chunk = indata[:, 0].copy()
        self._buffer.append(audio_chunk)
        
        self._total_frames += frames
        
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        
        if rms < self.silence_threshold:
            self._silence_frames += frames
        else:
            self._silence_frames = 0
        
        max_frames = int(self.sample_rate * self.max_duration)
        if self._total_frames >= max_frames:
            logger.warning("Max recording duration reached")
            self.stop()
        
        silence_limit_frames = int(self.sample_rate * self.silence_duration / self.chunk_duration)
        if self._silence_frames >= silence_limit_frames and len(self._buffer) > 5:
            logger.debug("Silence detected, stopping recording")
            self.stop()

    def start(self) -> bool:
        if self._is_recording:
            return True
        
        try:
            self._buffer = []
            self._silence_frames = 0
            self._total_frames = 0
            
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                blocksize=int(self.sample_rate * self.chunk_duration),
                callback=self._audio_callback
            )
            
            self._stream.start()
            self._is_recording = True
            logger.info("Audio recording started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio recording: {e}")
            return False

    def stop(self) -> Optional[np.ndarray]:
        if not self._is_recording:
            return None
        
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            
            self._is_recording = False
            
            if self._buffer:
                audio_data = np.concatenate(self._buffer)
                self._buffer = []
                
                audio_data = self._normalize_audio(audio_data)
                
                logger.debug(f"Audio recorded: {len(audio_data)} samples, {len(audio_data)/self.sample_rate:.2f}s")
                return audio_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return None

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        if len(audio) == 0:
            return audio
        
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val
        
        return audio

    def get_audio(self) -> Optional[np.ndarray]:
        with self._lock:
            if not self._buffer:
                return None
            audio = np.concatenate(self._buffer)
            return self._normalize_audio(audio)

    def is_recording(self) -> bool:
        return self._is_recording

    def clear(self) -> None:
        with self._lock:
            self._buffer = []
            self._silence_frames = 0
            self._total_frames = 0

    def add_chunk(self, chunk: np.ndarray) -> None:
        """Add audio chunk from WebSocket stream with proper processing."""
        with self._lock:
            self._buffer.append(chunk.copy())
            
            self._total_frames += len(chunk)
            
            rms = np.sqrt(np.mean(chunk ** 2))
            
            if rms < self.silence_threshold:
                self._silence_frames += len(chunk)
            else:
                self._silence_frames = 0
            
            max_frames = int(self.sample_rate * self.max_duration)
            if self._total_frames >= max_frames:
                logger.warning("Max recording duration reached")


def get_available_devices() -> list:
    try:
        devices = sd.query_devices()
        return devices if isinstance(devices, list) else [devices]
    except Exception as e:
        logger.error(f"Failed to query audio devices: {e}")
        return []


def get_default_input_device() -> Optional[dict]:
    try:
        return sd.query_devices(kind='input')
    except Exception:
        return None
