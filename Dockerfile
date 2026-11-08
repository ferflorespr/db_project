FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY schema ./schema
COPY ETL ./ETL
COPY data ./data
COPY config ./config
COPY dao ./dao
COPY handler ./handler
COPY main.py .

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data
ENV SCHEMA_DIR=/app/schema
ENV PORT=8765

EXPOSE 8765

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8765}"]
