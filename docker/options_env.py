#!/usr/bin/env python3
"""Convert Home Assistant add-on options to shell exports."""

import json
import shlex
import sys
from pathlib import Path


MAPPING = {
    "MYTECHCONNECT_URL": "mytechconnect_url",
    "MQTT_HOST": "mqtt_host",
    "MQTT_PORT": "mqtt_port",
    "MQTT_USERNAME": "mqtt_username",
    "MQTT_PASSWORD": "mqtt_password",
    "MQTT_DISCOVERY_PREFIX": "mqtt_discovery_prefix",
    "POLL_INTERVAL_SECONDS": "poll_interval_seconds",
    "RESOURCE_METRICS": "resource_metrics",
    "NICE_LEVEL": "nice_level",
}


def main():
    options = json.loads(Path(sys.argv[1]).read_text())
    for environment_name, option_name in MAPPING.items():
        value = options.get(option_name)
        if value is not None:
            print(f"export {environment_name}={shlex.quote(str(value))}")


if __name__ == "__main__":
    main()
