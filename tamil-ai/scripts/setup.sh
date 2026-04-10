#!/bin/bash

set -e

echo "=============================================="
echo "Tamil Emotional AI - Anbu Setup Script"
echo "=============================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

check_cuda() {
    if command -v nvidia-smi &> /dev/null; then
        echo "[✓] NVIDIA GPU detected"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    else
        echo "[!] No NVIDIA GPU detected. CPU-only mode will be used."
    fi
}

install_python_deps() {
    echo ""
    echo "[*] Installing Python dependencies..."
    
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    echo "[*] Python version: $python_version"
    
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    pip install --upgrade pip setuptools wheel
    
    echo "[*] Installing PyTorch with CUDA 12.1 support..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    
    echo "[*] Installing llama-cpp-python..."
    pip install llama-cpp-python
    
    echo "[*] Installing other Python dependencies..."
    pip install \
        faster-whisper \
        fastapi \
        uvicorn[standard] \
        python-multipart \
        sounddevice \
        scipy \
        soundfile \
        aiosqlite \
        pydantic \
        pydantic-settings \
        python-dotenv \
        httpx \
        loguru \
        psutil \
        edge-tts \
        gTTS \
        pyttsx3 \
        pydub
    
    echo "[*] Verifying CUDA availability..."
    python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
}

install_npm_deps() {
    echo ""
    echo "[*] Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
}

download_models() {
    echo ""
    echo "[*] Model files..."
    
    mkdir -p backend/models
    
    echo "[*] Qwen2.5-3B-Instruct Q8_0 GGUF model (~3.6GB)"
    MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q8_0.gguf"
    MODEL_PATH="backend/models/qwen2.5-3b-instruct-q8_0.gguf"
    
    if [ -f "$MODEL_PATH" ]; then
        echo "[✓] Q8_0 model already exists"
    else
        echo "[*] Downloading model (this may take a while)..."
        curl -L -o "$MODEL_PATH" "$MODEL_URL" --progress-bar || echo "[!] Download failed, please download manually"
    fi
    
    echo "[*] Optional: Tamil speaker reference for TTS:"
    echo "[*] Record a 15-30 sec Tamil voice sample"
    echo "[*] Save as: backend/models/tamil_speaker.wav"
}

setup_env() {
    echo ""
    echo "[*] Creating .env file..."
    
    cat > backend/.env << 'EOF'
DEBUG=True
MODEL_PATH=./models/qwen2.5-3b-instruct-q8_0.gguf
LLM_N_GPU_LAYERS=-1
LLM_N_THREADS=6
LLM_N_CTX=2048
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=256

WHISPER_MODEL=base
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16

USE_XTTS=False
XTTS_DEVICE=cuda

VRAM_THRESHOLD_GB=3.8
IDLE_VRAM_TARGET_GB=3.2
SUMMARY_INTERVAL=5
EOF
    
    echo "[✓] .env file created"
}

main() {
    echo ""
    echo "[*] System check..."
    check_cuda
    
    echo ""
    read -p "Proceed with installation? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "[*] Installation cancelled"
        exit 0
    fi
    
    install_python_deps
    install_npm_deps
    download_models
    setup_env
    
    echo ""
    echo "=============================================="
    echo "Setup complete!"
    echo "=============================================="
    echo ""
    echo "To start the backend:"
    echo "  cd backend && source ../venv/bin/activate && python main.py"
    echo ""
    echo "To start the frontend:"
    echo "  cd frontend && npm run dev"
    echo ""
    echo "Open http://localhost:5173 in your browser"
    echo ""
}

main "$@"
