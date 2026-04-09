# Tamil Emotional Conversational AI - அன்பு (Anbu)

A real-time Tamil emotional conversational AI system with speech-to-speech capabilities, optimized to run on laptops with 4GB+ VRAM NVIDIA GPUs.

## Features

- **Speech-to-Speech**: Voice-based conversation with Tamil/English (Tanglish) input
- **Emotion Detection**: Analyzes user emotion and responds with appropriate tone
- **Tamil Fillers**: Natural Tamil conversational fillers (mm, ah, aama, sari, ipo)
- **Memory**: SQLite-based conversation storage with summarization
- **VRAM Guard**: Automatic GPU memory management to stay within limits
- **Modern UI**: Real-time visualization of AI states with emotion indicators

## Hardware Requirements

- NVIDIA GPU with 4GB+ VRAM (RTX 3060 or similar)
- 8GB+ System RAM
- Microphone for voice input

## Software Requirements

- Python 3.10
- CUDA 12.1+
- Node.js 18+
- ffmpeg (for audio processing)

## Project Structure

```
tamil-ai/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration settings
│   ├── models/
│   │   ├── llm.py             # Qwen2.5 LLM with llama-cpp-python
│   │   ├── stt.py             # Faster-Whisper STT
│   │   └── tts.py             # gTTS / Coqui XTTS v2 TTS
│   ├── memory/
│   │   └── conversation_memory.py  # SQLite + summarization
│   └── utils/
│       ├── vram_guard.py       # VRAM management
│       └── audio_buffer.py    # Audio capture
├── frontend/
│   ├── src/
│   │   ├── components/         # React + MUI components
│   │   ├── hooks/             # Custom React hooks
│   │   └── App.tsx            # Main app
│   └── package.json
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Install Backend Dependencies

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install additional audio dependencies
pip install TTS gtts pydub

# Install ffmpeg (system level)
# Ubuntu: sudo apt install ffmpeg
# Mac: brew install ffmpeg
# Windows: winget install ffmpeg
```

### 2. Download LLM Model

```bash
# Create models directory
mkdir -p backend/models

# Download Qwen2.5-3B-Instruct Q8_0 GGUF
# From: https://huggingface.co/QuantFactory/Mergekit-Qwen2.5-3B-Instruct-GGUF
# File: qwen2.5-3b-instruct-q8_0.gguf (~2GB)
# Save to: backend/models/
```

### 3. Start Backend

```bash
cd backend
source venv/bin/activate
python main.py
```

Server runs at: http://localhost:8000

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Access UI at: http://localhost:5173

## Configuration

Edit `backend/config.py` or create `.env`:

```env
# LLM Settings
MODEL_PATH=./models/qwen2.5-3b-instruct-q8_0.gguf
LLM_N_GPU_LAYERS=35
LLM_N_THREADS=6
LLM_N_CTX=2048
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=150

# STT Settings (Whisper)
WHISPER_MODEL=tiny
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

# TTS Settings
# Currently uses gTTS (Google TTS) - no additional setup needed
# For XTTS v2: XTTS_SPEAKER_WAV=./models/tamil_speaker.wav

# VRAM Settings
VRAM_THRESHOLD_GB=3.8
IDLE_VRAM_TARGET_GB=3.2
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | System status |
| `/status` | GET | Detailed status with VRAM usage |
| `/audio/devices` | GET | List available audio devices |
| `/conversation/text` | POST | Text conversation |
| `/conversation/audio` | POST | Audio conversation (returns transcription + response) |
| `/ws/stream/{session_id}` | WS | WebSocket streaming |
| `/conversation/history/{session_id}` | GET | Get conversation history |
| `/conversation/history/{session_id}` | DELETE | Clear conversation |
| `/vram/cleanup` | POST | Force VRAM cleanup |

### Text Conversation

```bash
curl -X POST http://localhost:8000/conversation/text \
  -H "Content-Type: application/json" \
  -d '{"text": "நம்ம கைபேசி என்ன", "session_id": "test123"}'
```

### Audio Conversation

```bash
curl -X POST http://localhost:8000/conversation/audio \
  -H "Content-Type: application/json" \
  -d '{"audio_data": "<base64_audio>", "session_id": "test123"}'
```

## Memory System

- **SQLite Storage**: All conversation turns stored in `backend/data/conversations.db`
- **Summarization**: Every 5 turns, older messages are summarized to save context
- **Context Injection**: Summaries are injected into the system prompt for continuity

## Troubleshooting

### LLM not responding in Tamil
- Ensure system prompt is being loaded correctly
- Try lowering temperature to 0.3 in config
- Check if model file is complete (should be ~2GB)

### Whisper not transcribing
- Ensure microphone permissions are granted
- Check browser/system audio settings
- Try speaking closer to microphone
- Use text input as alternative

### TTS not working
- **gTTS** requires internet connection
- For offline TTS, provide XTTS speaker wav file
- Check audio playback in system

### Out of Memory / VRAM issues
- Reduce `LLM_N_GPU_LAYERS` in config (try 25 instead of 35)
- Lower context window `LLM_N_CTX`
- Use smaller Whisper model (tiny.en instead of tiny)

### Common Error: "No module named 'pydub'"
```bash
pip install pydub gtts
```

### Common Error: "Format not recognised"
- Install ffmpeg: `sudo apt install ffmpeg` (Linux)
- Or: `brew install ffmpeg` (Mac)

## Model Downloads

### Primary: Qwen2.5-3B-Instruct Q8_0 GGUF
- URL: https://huggingface.co/QuantFactory/Mergekit-Qwen2.5-3B-Instruct-GGUF
- File: `qwen2.5-3b-instruct-q8_0.gguf`
- Size: ~2GB
- Save to: `backend/models/`

### Optional: XTTS Speaker Reference
For better offline Tamil TTS:
- 10-30 second clear Tamil voice recording
- Format: WAV, 16kHz, mono
- Save as: `backend/models/tamil_speaker.wav`

## Tech Stack

- **Backend**: FastAPI, llama-cpp-python, faster-whisper, gTTS
- **Frontend**: React, TypeScript, Material-UI
- **Database**: SQLite
- **LLM**: Qwen2.5-3B-Instruct (GGUF)
- **STT**: Faster-Whisper (tiny model)
- **TTS**: gTTS (default), XTTS v2 (optional)

## License

MIT License

## Contributing

Pull requests welcome! Please test changes locally before submitting.
