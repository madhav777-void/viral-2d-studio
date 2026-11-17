FROM python:3.11-slim

# Install system dependencies: FFmpeg, Git, Fonts, Graphic libraries for Skia
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ffmpeg \
    git \
    fontconfig \
    fonts-dejavu-core \
    libfontconfig1 \
    libfreetype6 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy application files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    requests \
    numpy \
    scipy \
    pillow \
    skia-python \
    kokoro-onnx \
    onnxruntime \
    pydantic

# Pre-download Kokoro TTS models so voice works offline instantly
ENV OMNI_HOME=/app/.omni-shorts
RUN mkdir -p /app/.omni-shorts/kokoro && \
    wget -q -O /app/.omni-shorts/kokoro/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx && \
    wget -q -O /app/.omni-shorts/kokoro/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

EXPOSE 7860

ENV APP_DIR=/app
ENV PYTHONPATH=/app/studio:/app/cinematic-skill/skills/cinematic-film/scripts

# Dynamically binds to $PORT (Render.com uses 10000, Hugging Face uses 7860, default 8000)
CMD sh -c "python -m uvicorn server:app --app-dir studio --host 0.0.0.0 --port \${PORT:-8000}"
