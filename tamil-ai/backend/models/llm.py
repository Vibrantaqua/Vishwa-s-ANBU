import json
import re
import gc
from typing import Optional, Dict, Any, List, Tuple
from llama_cpp import Llama
from loguru import logger
from config import settings


class EmotionalLLM:
    def __init__(
        self,
        model_path: str,
        n_gpu_layers: int = 35,
        n_threads: int = 6,
        n_ctx: int = 2048,
        temperature: float = 0.7,
        max_tokens: int = 256
    ):
        self.model_path = model_path
        self.n_gpu_layers = n_gpu_layers
        self.n_threads = n_threads
        self.n_ctx = n_ctx
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._model: Optional[Llama] = None
        self._is_initialized = False

    def load_model(self) -> None:
        if self._is_initialized:
            return
        
        import os
        if not os.path.exists(self.model_path):
            logger.warning(f"Model not found at {self.model_path}")
            logger.info("Please download Qwen2.5-3B-Instruct Q4_K_M GGUF model")
            logger.info("Expected: qwen2.5-3b-instruct-q4_k_m.gguf")
        
        logger.info(f"Loading LLM from {self.model_path}...")
        logger.info(f"GPU layers: all, Context: {self.n_ctx}")
        
        try:
            self._model = Llama(
                model_path=self.model_path,
                n_gpu_layers=-1,
                n_threads=self.n_threads,
                n_ctx=self.n_ctx,
                n_batch=512,
                use_mlock=True,
                use_mmap=True,
                verbose=False,
                chat_format="chatml",
                flash_attention=True,
            )
            self._is_initialized = True
            logger.info("LLM loaded successfully (GPU mode)")
        except Exception as e:
            logger.error(f"Failed to load LLM: {e}")
            raise

    def _format_messages(self, system_prompt: str, history_context: str, user_input: str) -> str:
        prompt = f"""<|im_start|>system
You are Anbu. Never call yourself Anubhav or any other name. Chill, casual Tanglish vibes only.

### VIBE:
- No formality. Just friendly, emotional, and relatable.
- Use "bro", "friend", "Kandippa", "Serious-ah", "Semma", "Appidiya?"
- Tanglish = Tamil + English mix. Chennai street talk style.

### USER:
- Call them "friend" or "bro" until they say their name.
- If they say their name (e.g. "My name is Vishwa"), remember it.

### STYLE:
- Match their energy. Tamil speaker = more Tamil. English speaker = more English.
- Keep it short. Don't lecture. Just vibe and connect.
- Never repeat their question back.

### JSON (MUST):
{{"response": "...", "emotion": "happy/supportive/excited/calm/empathetic", "filler_intensity": 0.3}}
<|im_end|>
<|im_start|>user
{user_input}
<|im_end|>
<|im_start|>assistant
"""
        return prompt

    def generate_response(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        history_context: str = ""
    ) -> Dict[str, Any]:
        if not self._is_initialized:
            self.load_model()
        
        if system_prompt is None:
            system_prompt = settings.SYSTEM_PROMPT
        
        prompt = self._format_messages(system_prompt, history_context, user_input)
        
        try:
            response = self._model(
                prompt,
                max_tokens=512,
                temperature=0.7,
                top_p=0.95,
                repeat_penalty=1.2,
                stop=["<|im_end|>", "<|endoftext|>"],
                echo=False,
            )
            
            content = response["choices"][0]["text"]
            
            if '"Anbu"' in content:
                content = content.replace('"Anbu"', '"response"')
            
            if not content.strip().endswith('}'):
                if content.count('{') > content.count('}'):
                    content = content.rstrip() + '}'
            
            logger.debug(f"LLM raw response: {content[:500]}")
            
            return self._parse_json_response(content)
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            gc.collect()
            return self._get_fallback_response()

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        import re
        
        if content and not content.strip().endswith('}'):
            content = content.rstrip() + '}'
        
        json_patterns = [
            r'```(?:json)?\s*(\{.*?\})\s*```',
            r'\{.*"response".*"emotion".*"filler_intensity".*\}',
        ]
        
        for pattern in json_patterns:
            code_match = re.search(pattern, content, re.DOTALL)
            if code_match:
                try:
                    parsed = json.loads(code_match.group(1) if code_match.lastindex else code_match.group())
                    return self._validate_response(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    parsed = json.loads(line)
                    return self._validate_response(parsed)
                except json.JSONDecodeError:
                    continue
        
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                potential_json = content[start_idx:end_idx+1]
                parsed = json.loads(potential_json)
                if "response" in parsed:
                    return self._validate_response(parsed)
            except json.JSONDecodeError:
                pass
        
        if start_idx != -1:
            try:
                potential_json = content[start_idx:]
                if not potential_json.endswith('}'):
                    potential_json += '}'
                parsed = json.loads(potential_json)
                if "response" in parsed:
                    return self._validate_response(parsed)
            except json.JSONDecodeError:
                pass
        
        logger.warning(f"Could not parse JSON from: {content[:300]}")
        import re
        tamil_text = re.sub(r'[^\u0B80-\u0BFF\s]', '', content)
        tamil_text = ' '.join(tamil_text.split())
        if tamil_text and len(tamil_text) > 5:
            return {
                "response": tamil_text.strip(),
                "emotion": "neutral",
                "filler_intensity": 0.3
            }
        return self._get_fallback_response()

    def _validate_response(self, parsed: dict) -> Dict[str, Any]:
        valid_emotions = ["happy", "sad", "excited", "calm", "confused", "empathetic", "neutral"]
        
        return {
            "response": str(parsed.get("response", "")).strip(),
            "emotion": parsed.get("emotion", "neutral") if parsed.get("emotion") in valid_emotions else "neutral",
            "filler_intensity": max(0.0, min(1.0, float(parsed.get("filler_intensity", 0.5))))
        }

    def _get_fallback_response(self, raw_content: str = "") -> Dict[str, Any]:
        if raw_content and len(raw_content) > 10:
            return {
                "response": "mm, nee enna solluva? athu Tamil-la sollunga",
                "emotion": "confused",
                "filler_intensity": 0.6
            }
        return {
            "response": "mm, nee enna solluva?",
            "emotion": "neutral",
            "filler_intensity": 0.5
        }

    def is_initialized(self) -> bool:
        return self._is_initialized

    def clear_cache(self) -> None:
        if self._model is not None:
            gc.collect()
            logger.info("LLM cache cleared")


llm = EmotionalLLM(
    model_path=settings.MODEL_PATH,
    n_gpu_layers=settings.LLM_N_GPU_LAYERS,
    n_threads=settings.LLM_N_THREADS,
    n_ctx=settings.LLM_N_CTX,
    temperature=settings.LLM_TEMPERATURE,
    max_tokens=settings.LLM_MAX_TOKENS
)
