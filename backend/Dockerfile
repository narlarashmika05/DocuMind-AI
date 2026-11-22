# DocuMind AI backend: FastAPI + ML models (CPU)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models

# Tesseract OCR with English and Telugu language data; libglib for OpenCV
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-tel libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the CPU-only PyTorch build first: on Linux the default PyPI wheel pulls in ~2.5 GB of CUDA libraries.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Never run as root inside the container
RUN useradd --create-home --uid 1000 documind \
    && mkdir -p /app/storage /models \
    && chown -R documind:documind /app /models
USER documind

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health').status == 200 else 1)"

# Apply database migrations, then start the API
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
