# Use Python 3.11 - IMPORTANT for Gradio 5.x compatibility
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 docuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

RUN python -c "import easyocr; reader = easyocr.Reader(['en'], gpu=False, download_enabled=True)" || true

COPY --chown=docuser:docuser . .

COPY --chown=docuser:docuser docker-entrypoint.sh /app/
COPY --chown=docuser:docuser run_services.sh /app/
RUN chmod +x /app/docker-entrypoint.sh /app/run_services.sh

RUN mkdir -p uploads cache test_docs logs app && \
    touch app/__init__.py && \
    chown -R docuser:docuser /app

USER docuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT=7860
ENV GRADIO_ROOT_PATH=""
ENV GRADIO_SHARE=False

EXPOSE 8000 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]

CMD ["/app/run_services.sh"]