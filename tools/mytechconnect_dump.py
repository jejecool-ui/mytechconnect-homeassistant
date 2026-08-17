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

try:
    from mytechconnect_client import (
        extract_main_values,
        launch_kwargs,
        normalize_sensor_values,
        open_device,
        open_page,
        precise_water_temperature,
        validate_url,
    )
except ModuleNotFoundError:  # Import also works as tools.mytechconnect_dump.
    from tools.mytechconnect_client import (
        extract_main_values,
        launch_kwargs,
        normalize_sensor_values,
        open_device,
        open_page,
        precise_water_temperature,
        validate_url,
    )


def collect_values(url):
    if not validate_url(url):
        raise ValueError("MYTECHCONNECT_URL must be a MyTechConnect user-app URL")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_kwargs())
            page = open_page(browser, url)
            open_device(page)
            raw = extract_main_values(page)
            values = normalize_sensor_values(raw)

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
            return values
    except Exception as exc:  # JSON output remains machine-readable on failure.
        raise RuntimeError(str(exc)) from exc


def main():
    url = os.environ.get("MYTECHCONNECT_URL")
    try:
        values = collect_values(url)
    except Exception as exc:
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
