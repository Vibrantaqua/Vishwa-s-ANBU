FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_PATH=/usr/local/cuda

WORKDIR /app

RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    libsndfile1 \
    libasound2-dev \
    portaudio19-dev \
    ffmpeg \
    wget \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.11 /usr/bin/python

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cu121

RUN pip install llama-cpp-python==0.2.90 --force-reinstall --no-cache-dir \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121

RUN pip install --no-cache-dir \
    faster-whisper==1.0.3 \
    TTS==0.22.0 \
    fastapi==0.110.0 \
    uvicorn[standard]==0.27.1 \
    python-multipart==0.0.9 \
    sounddevice==0.4.6 \
    scipy>=1.11.0 \
    aiosqlite==0.20.0 \
    pydantic==2.6.3 \
    pydantic-settings==2.2.1 \
    python-dotenv==1.0.1 \
    httpx==0.27.0 \
    loguru==0.7.2 \
    psutil

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY scripts/ ./scripts/

RUN mkdir -p backend/models backend/data

RUN mkdir -p frontend/node_modules
WORKDIR /app/frontend
RUN npm install && npm run build
WORKDIR /app

ENV PYTHONPATH=/app
ENV DEBUG=False

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
