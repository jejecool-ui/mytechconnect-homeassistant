#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
chromium_path="/home/servane/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome"

if [[ -z "${MYTECHCONNECT_URL:-}" ]]; then
    read -r -s -p "URL de session MyTechConnect : " MYTECHCONNECT_URL
    printf '\n'
    export MYTECHCONNECT_URL
fi

export PLAYWRIGHT_CHROMIUM="$chromium_path"

cleanup() {
    unset MYTECHCONNECT_URL PLAYWRIGHT_CHROMIUM
}
trap cleanup EXIT

cd "$project_dir"
exec /tmp/mytechconnect-venv/bin/python tools/mytechconnect_mqtt.py
