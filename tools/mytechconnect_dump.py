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
import resource
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

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


def resource_metrics_enabled():
    return os.environ.get("RESOURCE_METRICS", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class ResourceMonitor:
    """Sample this process and its Chromium descendants while enabled."""

    def __init__(self):
        self.max_processes = 0
        self.max_memory_kb = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="resource-monitor")

    @staticmethod
    def _children(pid):
        try:
            children_file = Path(f"/proc/{pid}/task/{pid}/children")
            children = [int(value) for value in children_file.read_text().split()]
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
            return []

        result = []
        for child in children:
            result.append(child)
            result.extend(ResourceMonitor._children(child))
        return result

    @staticmethod
    def _memory_kb(pid):
        try:
            # PSS accounts for shared Chromium pages proportionally, unlike
            # RSS which would count the same shared pages for every process.
            for line in Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines():
                if line.startswith("Pss:"):
                    return int(line.split()[1])
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
            pass
        try:
            for line in Path(f"/proc/{pid}/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
            pass
        return 0

    def sample(self):
        pids = [os.getpid(), *self._children(os.getpid())]
        self.max_processes = max(self.max_processes, len(set(pids)))
        self.max_memory_kb = max(
            self.max_memory_kb, sum(self._memory_kb(pid) for pid in pids)
        )

    def _run(self):
        while not self._stop.wait(0.25):
            self.sample()

    def start(self):
        self.sample()
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)
        self.sample()
        children_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        return {
            "max_processes": self.max_processes,
            "max_memory_mb": round(self.max_memory_kb / 1024, 1),
            "child_cpu_seconds": round(
                children_usage.ru_utime + children_usage.ru_stime, 2
            ),
        }


def collect_values(url):
    if not validate_url(url):
        raise ValueError("MYTECHCONNECT_URL must be a MyTechConnect user-app URL")
    LOGGER.info("Starting MyTechConnect data request")
    monitor = ResourceMonitor() if resource_metrics_enabled() else None
    if monitor:
        LOGGER.info("Resource metrics enabled")
        monitor.start()
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
    finally:
        if monitor:
            metrics = monitor.stop()
            LOGGER.info(
                "Resource metrics: max_processes=%d, max_memory_mb=%.1f (PSS), child_cpu_seconds=%.2f",
                metrics["max_processes"],
                metrics["max_memory_mb"],
                metrics["child_cpu_seconds"],
            )


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
