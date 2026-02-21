FROM python:3.12-slim AS base

WORKDIR /cv

RUN apt-get update && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/cv

FROM base AS production

COPY requirements.txt requirements-rag.txt .
RUN pip install --no-cache-dir -r requirements.txt -r requirements-rag.txt

COPY app ./app

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

FROM production AS development

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt


# NEW: generation stage (offline pipeline)
FROM base AS generation

# System deps for WeasyPrint (HTML -> PDF)
# Note: This is intentionally NOT in production.
RUN apt-get update && apt-get install -y \
    build-essential \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libffi-dev \
    libjpeg62-turbo \
    libopenjp2-7 \
    libtiff6 \
    zlib1g \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-generation.txt .
RUN pip install --no-cache-dir -r requirements-generation.txt

# We mount the repo as volume, so no COPY here.
WORKDIR /cv


# RAG: search deps shared with production; index deps only for this stage.
FROM base AS rag

COPY requirements-rag.txt requirements-rag-index.txt .
RUN pip install --no-cache-dir -r requirements-rag.txt -r requirements-rag-index.txt

WORKDIR /cv
