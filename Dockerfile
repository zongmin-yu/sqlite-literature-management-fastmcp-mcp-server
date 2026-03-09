FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SQLITE_DB_PATH=/data/sources.db

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --upgrade pip \
    && pip install .

VOLUME ["/data"]

CMD ["sh", "-c", "mkdir -p \"$(dirname \"$SQLITE_DB_PATH\")\" && if [ ! -f \"$SQLITE_DB_PATH\" ]; then sqlite3 \"$SQLITE_DB_PATH\" < /app/create_sources_db.sql; fi && exec python3 /app/sqlite-paper-fastmcp-server.py"]
