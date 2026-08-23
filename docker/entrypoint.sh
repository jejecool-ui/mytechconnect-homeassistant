#!/usr/bin/env bash
set -euo pipefail

load_home_assistant_options() {
    if [[ ! -f /data/options.json ]]; then
        return
    fi

    options_exports=$(python /app/options_env.py /data/options.json)
    eval "$options_exports"
}

load_home_assistant_options

: "${MYTECHCONNECT_URL:?MYTECHCONNECT_URL is required}"
: "${MQTT_HOST:?MQTT_HOST is required}"
: "${MQTT_USERNAME:?MQTT_USERNAME is required}"
: "${MQTT_PASSWORD:?MQTT_PASSWORD is required}"

poll_interval="${POLL_INTERVAL_SECONDS:-900}"

if ! [[ "$poll_interval" =~ ^[1-9][0-9]*$ ]]; then
    echo "POLL_INTERVAL_SECONDS must be a positive integer" >&2
    exit 2
fi

while true; do
    echo "Starting MyTechConnect poll"
    if ! python /app/tools/mytechconnect_mqtt.py; then
        echo "MyTechConnect poll failed; retrying on next interval" >&2
    fi
    sleep "$poll_interval"
done
