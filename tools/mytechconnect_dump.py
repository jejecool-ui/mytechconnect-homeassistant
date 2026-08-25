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
        sanitize_error,
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
        sanitize_error,
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
            try:
                page = open_page(browser, url)
                open_device(page)
                raw = extract_main_values(page)
                values = normalize_sensor_values(raw)

                LOGGER.info(
                    "Intermediate result: heat pump state=%s, water flow=%s",
                    values["binary_sensor.pool_heat_pump"],
                    values["binary_sensor.pool_water_flow"],
                )

                flow_is_on = values["binary_sensor.pool_water_flow"] == "ON"
                if flow_is_on:
                    LOGGER.info("Starting water temperature precision retrieval (water flow is ON)")
                    try:
                        point = precise_water_temperature(page)
                        values["sensor.pool_water_temperature"] = (
                            point["value"] if point and point["value"] is not None else None
                        )
                    except Exception as exc:
                        LOGGER.warning(
                            "Water temperature precision retrieval failed; publishing "
                            "water temperature as unavailable (%s: %s)",
                            type(exc).__name__,
                            sanitize_error(exc),
                        )
                        values["sensor.pool_water_temperature"] = None
                else:
                    LOGGER.info("Water flow is OFF; skipping water chart retrieval")
                    values["sensor.pool_water_temperature"] = None

                LOGGER.info("MyTechConnect data request completed")
                return values
            finally:
                try:
                    browser.close()
                    LOGGER.info("Chromium browser closed")
                except Exception as exc:
                    LOGGER.warning("Failed to close Chromium browser (%s: %s)", type(exc).__name__, exc)
    except Exception as exc:  # JSON output remains machine-readable on failure.
        raise RuntimeError(sanitize_error(exc)) from exc


def main():
    url = os.environ.get("MYTECHCONNECT_URL")
    try:
        values = collect_values(url)
    except Exception as exc:
        LOGGER.error("MyTechConnect data request failed: %s", sanitize_error(exc))
        return 1

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "values": values,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
