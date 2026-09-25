FROM python:3.12-slim-bookworm

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION} \
    APP_NAME=web-demo \
    HOST=0.0.0.0 \
    PORT=18080 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY --chown=app:app app.py ./
COPY --chown=app:app templates/ ./templates/

USER app
EXPOSE 18080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:18080/healthz', timeout=2)"]

CMD ["python", "app.py"]
