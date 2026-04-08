import torch
import gc
import psutil
from loguru import logger
from typing import Optional, Callable
from functools import wraps
from config import settings


class VRAMGuard:
    def __init__(self, threshold_gb: float = 3.8, idle_target_gb: float = 3.2):
        self.threshold_gb = threshold_gb
        self.idle_target_gb = idle_target_gb
        self._enabled = torch.cuda.is_available()
        self._check_count = 0
        self._max_checkes_before_cleanup = 10

    def get_vram_usage_gb(self) -> float:
        if not self._enabled or not torch.cuda.is_available():
            return 0.0
        
        try:
            allocated = torch.cuda.memory_allocated() / (1024 ** 3)
            reserved = torch.cuda.memory_reserved() / (1024 ** 3)
            return max(allocated, reserved)
        except Exception as e:
            logger.warning(f"Failed to get VRAM usage: {e}")
            return 0.0

    def get_system_memory_gb(self) -> float:
        return psutil.virtual_memory().used / (1024 ** 3)

    def enforce_threshold(self) -> bool:
        if not self._enabled:
            return True

        current_vram = self.get_vram_usage_gb()
        logger.debug(f"VRAM usage: {current_vram:.2f}GB / {self.threshold_gb}GB threshold")
        
        self._check_count += 1
        
        if current_vram > self.threshold_gb:
            logger.warning(f"VRAM threshold exceeded: {current_vram:.2f}GB > {self.threshold_gb}GB. Clearing cache...")
            self.clear_cuda_cache()
            return False
        
        if self._check_count >= self._max_checkes_before_cleanup:
            self._check_count = 0
            torch.cuda.synchronize()
        
        return True

    def clear_cuda_cache(self) -> None:
        if self._enabled and torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                gc.collect()
                logger.info("CUDA cache cleared successfully")
            except Exception as e:
                logger.error(f"Failed to clear CUDA cache: {e}")

    def get_idle_vram_gb(self) -> float:
        return self.get_vram_usage_gb()

    def is_safe_for_inference(self) -> bool:
        return self.enforce_threshold()

    def monitor_operation(self, operation_name: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.is_safe_for_inference():
                    logger.warning(f"Proceeding with {operation_name} despite high VRAM usage")
                try:
                    result = func(*args, **kwargs)
                    self.enforce_threshold()
                    return result
                except RuntimeError as e:
                    if "out of memory" in str(e).lower():
                        logger.error("OOM during operation, clearing cache and retrying...")
                        self.clear_cuda_cache()
                        gc.collect()
                        raise
                    raise
            return wrapper
        return decorator


vram_guard = VRAMGuard(
    threshold_gb=settings.VRAM_THRESHOLD_GB,
    idle_target_gb=settings.IDLE_VRAM_TARGET_GB
)
