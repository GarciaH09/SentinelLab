FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SENTINELLAB_READ_ONLY=1 \
    HOST=0.0.0.0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN gcc c_engine/hashfile.c -o c_engine/hashfile -lcrypto \
    && python python/inventory.py \
    && chmod 0555 c_engine/hashfile \
    && chmod -R a-w data \
    && useradd --system --no-create-home --shell /usr/sbin/nologin sentinellab \
    && chmod -R a-w /app

USER sentinellab

CMD ["python", "python/web_app.py"]
