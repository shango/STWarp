# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for better layer caching.
COPY web/requirements.txt /app/web/requirements.txt
RUN pip install -r /app/web/requirements.txt

# Copy shared core package + web app.
COPY stwarp /app/stwarp
COPY web /app/web

# Run as an unprivileged user so an exploit of the app doesn't land on
# root inside the container.
RUN adduser --disabled-password --gecos "" --uid 10001 appuser \
    && chown -R appuser /app
USER appuser

EXPOSE 8000
# Railway injects $PORT; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn web.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
