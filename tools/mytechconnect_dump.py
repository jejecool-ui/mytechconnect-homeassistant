#!/usr/bin/env python3
"""Dump current MyTechConnect pool sensors as JSON.

The authenticated URL is read from MYTECHCONNECT_URL and is never printed.
The chart is opened only when the main PAC page exposes a water temperature.

Example:
  MYTECHCONNECT_URL='https://.../from-native/...' \
    PLAYWRIGHT_CHROMIUM='/path/to/chrome' \
    python tools/mytechconnect_dump.py
"""

import json
import os
import sys
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

from mytechconnect_client import (
    HOST_PREFIX,
    extract_main_values,
    launch_kwargs,
    open_device,
    open_page,
    precise_water_temperature,
    validate_url,
)


def main():
    url = os.environ.get("MYTECHCONNECT_URL")
    if not validate_url(url):
        print("MYTECHCONNECT_URL must be a MyTechConnect user-app URL", file=sys.stderr)
        return 2

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_kwargs())
            page = open_page(browser, url)
            open_device(page)
            raw = extract_main_values(page)
            values = {
                "binary_sensor.pool_heat_pump": raw["heat_pump_state"],
                "binary_sensor.pool_water_flow": raw["water_flow"],
                "sensor.pool_water_temperature": raw["water_temperature"],
                "sensor.pool_outdoor_temperature": raw["outdoor_temperature"],
                "sensor.pool_heat_pump_operation_mode": raw["operation_mode"],
                "sensor.pool_heat_pump_regulation_mode": raw["regulation_mode"],
                "sensor.pool_heat_pump_temperature_setpoint": raw["setpoint"],
            }

            # A missing main-page temperature means no reliable water reading.
            # Do not consult the estimated chart in that case.
            if values["sensor.pool_water_temperature"]:
                try:
                    point = precise_water_temperature(page)
                    if point and point["value"] is not None:
                        values["sensor.pool_water_temperature"] = point["value"]
                except Exception:
                    pass

            browser.close()
    except Exception as exc:  # JSON output remains machine-readable on failure.
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stdout)
        return 1

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "values": values,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
