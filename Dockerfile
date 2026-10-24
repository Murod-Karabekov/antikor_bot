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

# COPY keeps host permission bits. Normalize them so the unprivileged runtime user can
# read all code and assets whatever the developer's umask was, while files stay
# root-owned and non-writable by the bot. Directories 0755, files 0644 (no 777).
RUN find /app/app /app/assets -type d -exec chmod 0755 {} + \
    && find /app/app /app/assets -type f -exec chmod 0644 {} +

USER bot
STOPSIGNAL SIGTERM

CMD ["python", "-m", "app.main"]
