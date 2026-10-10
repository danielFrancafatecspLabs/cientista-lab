# App web
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Backend + app compilado
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml README.md ./
COPY metaexp/ metaexp/
RUN pip install --no-cache-dir .
COPY data/corpus/sintetico/ data/corpus/sintetico/
COPY --from=web /web/dist web/dist
ENV METAEXP_FRONTEND_DIR=/app/web/dist METAEXP_SESSIONS_DIR=/app/data/sessions
EXPOSE 8000
CMD ["python", "-m", "metaexp", "servir", "--host", "0.0.0.0", "--port", "8000"]
