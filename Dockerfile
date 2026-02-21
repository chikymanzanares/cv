FROM python:3.12-slim AS base

WORKDIR /cv

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/cv

FROM base AS production

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

FROM production AS development

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
