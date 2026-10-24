FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system bot \
    && useradd --system --gid bot --home-dir /nonexistent --shell /usr/sbin/nologin bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY assets ./assets

USER bot
STOPSIGNAL SIGTERM

CMD ["python", "-m", "app.main"]
