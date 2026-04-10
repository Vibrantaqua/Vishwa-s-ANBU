import json
import re
import requests
from typing import Optional, Dict, Any
from loguru import logger
from config import settings


class EmotionalLLM:
    def __init__(
        self,
        model: str = "qwen2.5-3b-q6k",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.75,
        max_tokens: int = 384,
        top_p: float = 0.95,
        repeat_penalty: float = 1.15
    ):
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.repeat_penalty = repeat_penalty
        self._is_initialized = False

    def load_model(self) -> None:
        self._is_initialized = True
        logger.info(f"Ollama LLM ready: {self.model}")

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

    def _format_messages(self, system_prompt: str, history_context: str, user_input: str) -> str:
        return user_input

    def generate_response(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        history_context: str = ""
    ) -> Dict[str, Any]:
        if not self._is_initialized:
            self.load_model()
        
        messages = [
            {
                "role": "system",
                "content": """You are Anbu - a warm, supportive Tamil AI companion.

## YOUR PERSONALITY:
- Casual Chennai street style. Think Marina Beach evening vibes.
- Use Tanglish naturally (Tamil + English mix)
- Say things like: "Kandippa", "Semma", "Appidiya", "Thangiyow", "Nanba"
- Be conversational, not robotic. Like talking to a supportive friend.

## WHAT YOU UNDERSTAND:
- Tanglish (Tamil + English mix)
- Pure Tamil
- Pure English

## HOW YOU RESPOND:
- Match their energy. English speaker = more English. Tamil speaker = more Tanglish.
- Keep responses SHORT - 1-3 sentences max
- Be empathetic and supportive
- If you don't know something, say "Nanba, athu theriyathu, but..." (I don't know, but...)
- NEVER make up facts. If unsure, say so clearly.

## RESPONSE FORMAT (JSON only):
{"response": "Your response in Tanglish", "emotion": "happy", "filler_intensity": 0.0}

## EMOTIONS: happy, excited, calm, empathetic, sad, confused, neutral
## FILLER_INTENSITY: 0.0-1.0 (0 = confident, 1 = lots of "mm", "aama", "kandippa")"""
            },
            {
                "role": "user", 
                "content": user_input
            }
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
                        "top_p": self.top_p,
                        "repeat_penalty": self.repeat_penalty,
                    },
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("message", {}).get("content", "").strip()
            
            if '"Anbu"' in content:
                content = content.replace('"Anbu"', '"response"')
            
            if content and not content.endswith('}'):
                if content.count('{') > content.count('}'):
                    content = content.rstrip() + '}'
            
            logger.debug(f"LLM raw response: {content[:500]}")
            
            return self._parse_json_response(content)
            
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return self._get_fallback_response()
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return self._get_fallback_response()

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        if not content:
            return self._get_fallback_response()
        
        if not content.endswith('}'):
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
        logger.info("Ollama LLM cache cleared")


llm = EmotionalLLM(
    model=settings.OLLAMA_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
    temperature=settings.OLLAMA_TEMPERATURE,
    max_tokens=settings.OLLAMA_MAX_TOKENS,
    top_p=settings.OLLAMA_TOP_P,
    repeat_penalty=settings.OLLAMA_REPEAT_PENALTY
)
