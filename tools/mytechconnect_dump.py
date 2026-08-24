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
import logging
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


LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)


def collect_values(url):
    if not validate_url(url):
        raise ValueError("MYTECHCONNECT_URL must be a MyTechConnect user-app URL")
    LOGGER.info("Starting MyTechConnect data request")
    try:
        with sync_playwright() as playwright:
            LOGGER.info("Starting Chromium browser")
            browser = playwright.chromium.launch(**launch_kwargs())
            page = open_page(browser, url)
            open_device(page)
            raw = extract_main_values(page)
            values = normalize_sensor_values(raw)

            LOGGER.info(
                "Intermediate result: heat pump state=%s, water flow=%s",
                values["binary_sensor.pool_heat_pump"],
                values["binary_sensor.pool_water_flow"],
            )

            # A missing main-page temperature means no reliable water reading.
            # Do not consult the estimated chart in that case.
            if values["sensor.pool_water_temperature"] is not None:
                LOGGER.info(
                    "Starting water temperature precision retrieval "
                    "(main-page temperature is available)"
                )
                try:
                    point = precise_water_temperature(page)
                    if point and point["value"] is not None:
                        values["sensor.pool_water_temperature"] = point["value"]
                        LOGGER.info(
                            "Water temperature precision retrieved: %.1f °C",
                            point["value"],
                        )
                    else:
                        LOGGER.warning(
                            "Water temperature precision unavailable; keeping "
                            "the main-page value"
                        )
                except Exception:
                    LOGGER.warning(
                        "Water temperature precision retrieval failed; keeping "
                        "the main-page value"
                    )
            else:
                LOGGER.info(
                    "Water temperature unavailable on the main page; "
                    "skipping chart retrieval"
                )

            browser.close()
            LOGGER.info("MyTechConnect data request completed")
            return values
    except Exception as exc:  # JSON output remains machine-readable on failure.
        raise RuntimeError(str(exc)) from exc


def main():
    url = os.environ.get("MYTECHCONNECT_URL")
    try:
        values = collect_values(url)
    except Exception as exc:
        LOGGER.error("MyTechConnect data request failed: %s", exc)
        return 1

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "values": values,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
