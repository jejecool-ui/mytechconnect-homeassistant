FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=0 \
    PLAYWRIGHT_CHROMIUM=/usr/bin/chromium

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        chromium \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY tools/requirements-browser.txt /app/tools/requirements-browser.txt
COPY tools/requirements-mqtt.txt /app/tools/requirements-mqtt.txt
RUN pip install --no-cache-dir \
        -r /app/tools/requirements-browser.txt \
        -r /app/tools/requirements-mqtt.txt

COPY tools/mytechconnect_client.py /app/tools/mytechconnect_client.py
COPY tools/mytechconnect_dump.py /app/tools/mytechconnect_dump.py
COPY tools/mytechconnect_mqtt.py /app/tools/mytechconnect_mqtt.py
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
