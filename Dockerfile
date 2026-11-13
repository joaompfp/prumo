FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY static/ ./static/
COPY ingest/ ./ingest/
COPY registry/ ./registry/
COPY entrypoint.sh ./
RUN chmod +x ./entrypoint.sh
ENV PRUMO_DB_PATH=/data/prumo.sqlite3
ENV PRUMO_RAW_DIR=/data/raw
EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --start-period=15s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)" || exit 1
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
