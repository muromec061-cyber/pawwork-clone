#!/bin/bash
# Setup Ollama in Codespace

set -e

echo "🦙 Installing Ollama..."

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama in background
echo "🚀 Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for server to be ready
echo "⏳ Waiting for Ollama to start..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama is ready!"
        break
    fi
    sleep 1
done

# Pull your models
echo "📦 Pulling models..."

# qwen2:0.5b (352 MB) - fast, lightweight
echo "  → qwen2:0.5b"
ollama pull qwen2:0.5b

# Moonlight-16B-A3B-Instruct (8.3 GB) - needs HF token
if [ -n "$HF_TOKEN" ]; then
    echo "  → Moonlight-16B-A3B-Instruct (Q3_K_M)"
    ollama pull hf.co/mmnga/Moonlight-16B-A3B-Instruct-gguf:Q3_K_M
else
    echo "  ⚠️ Moonlight-16B skipped (set HF_TOKEN secret)"
fi

# kimi-vl-a3b-thinking (10 GB) - needs HF token
if [ -n "$HF_TOKEN" ]; then
    echo "  → kimi-vl-a3b-thinking"
    ollama pull hf.co/richardyoung/kimi-vl-a3b-thinking:latest
else
    echo "  ⚠️ kimi-vl skipped (set HF_TOKEN secret)"
fi

echo "✅ Setup complete!"
echo "Ollama API: http://localhost:11434"
echo "Available models:"
ollama list

# Keep running
wait $OLLAMA_PID