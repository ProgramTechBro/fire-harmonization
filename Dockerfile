FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
RUN test -f backend/precomputed/meta.json || (echo "backend/precomputed is missing. On your computer run: cd backend && python -m app.precompute, then commit backend/precomputed" && exit 1)
COPY --from=web /web/dist frontend/dist
ENV PRECOMPUTED_DIR=/app/backend/precomputed \
    DATA_DIR=/app/web_data \
    FRONTEND_DIST=/app/frontend/dist \
    PORT=10000 \
    MALLOC_ARENA_MAX=2 \
    PYTHONUNBUFFERED=1
EXPOSE 10000
WORKDIR /app/backend
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1
