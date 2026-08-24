#!/usr/bin/env bash
set -euo pipefail

log() {
    printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S,%3N')" "$*"
}

load_home_assistant_options() {
    if [[ ! -f /data/options.json ]]; then
        return
    fi

    options_exports=$(python /app/options_env.py /data/options.json)
    eval "$options_exports"
}

load_home_assistant_options

for required_var in MYTECHCONNECT_URL MQTT_HOST MQTT_USERNAME MQTT_PASSWORD; do
    if [[ -z "${!required_var:-}" ]]; then
        log "ERROR ${required_var} is required" >&2
        exit 2
    fi
done

poll_interval="${POLL_INTERVAL_SECONDS:-900}"

if ! [[ "$poll_interval" =~ ^[1-9][0-9]*$ ]]; then
    log "ERROR POLL_INTERVAL_SECONDS must be a positive integer" >&2
    exit 2
fi

while true; do
    log "INFO Starting MyTechConnect poll"
    if ! python /app/tools/mytechconnect_mqtt.py; then
        log "ERROR MyTechConnect poll failed; retrying on next interval" >&2
    fi
    sleep "$poll_interval"
done
