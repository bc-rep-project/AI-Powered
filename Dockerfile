FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src /app/src

ENV PORT=8000
ENV PYTHONPATH=/app

CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} 