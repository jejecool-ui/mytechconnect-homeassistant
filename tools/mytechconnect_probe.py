#!/usr/bin/env python3
"""Probe the rendered MyTechConnect Blazor page.

Usage:
  MYTECHCONNECT_URL='https://.../from-native/...' python3 tools/mytechconnect_probe.py

The URL is intentionally read from the environment and never printed.
This first pass only reads the rendered page and writes local diagnostics.
"""

import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from mytechconnect_client import (
    all_chart_data,
    extract_main_values,
    launch_kwargs,
    open_chart,
    open_device,
    open_page,
    PLAYWRIGHT_CONNECTION_TIMEOUT_MS,
    PLAYWRIGHT_TIMEOUT_MS,
    validate_url,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "mytechconnect-6.2" / "browser-probe"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    url = os.environ.get("MYTECHCONNECT_URL")
    if not url:
        print("MYTECHCONNECT_URL is required", file=sys.stderr)
        return 2
    if not validate_url(url):
        print("Refusing URL outside the MyTechConnect user-app host", file=sys.stderr)
        return 2

    with sync_playwright() as pw:
        browser = pw.chromium.launch(**launch_kwargs())
        page = open_page(browser, url)
        try:
            page.wait_for_function(
                "document.querySelector('#user-app') && document.querySelector('#user-app').innerText.trim().length > 0",
                timeout=PLAYWRIGHT_CONNECTION_TIMEOUT_MS,
            )
        except PlaywrightTimeoutError:
            print("Blazor content did not render before timeout", file=sys.stderr)

        page.wait_for_timeout(3_000)
        text = page.locator("body").inner_text()
        html = page.content()
        page.screenshot(path=str(OUT / "page.png"), full_page=True)
        (OUT / "visible-text.txt").write_text(text, encoding="utf-8")
        (OUT / "rendered.html").write_text(html, encoding="utf-8")

        # Follow the same read-only navigation as the mobile UI so that the
        # chart page can be inspected in the authenticated browser context.
        open_device(page)
        page.wait_for_timeout(500)
        (OUT / "device-text.txt").write_text(page.locator("body").inner_text(), encoding="utf-8")
        (OUT / "device.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(OUT / "device.png"), full_page=True)

        import json
        main_values = extract_main_values(page)
        (OUT / "main-values.json").write_text(json.dumps(main_values, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Main values:", json.dumps(main_values, ensure_ascii=False))

        if os.environ.get("MYTECHCONNECT_SKIP_CHART") == "1" or not main_values["water_temperature"]:
            browser.close()
            return 0

        page.locator(".navbar-container button").nth(1).click(timeout=PLAYWRIGHT_TIMEOUT_MS)
        page.wait_for_timeout(500)
        (OUT / "menu-text.txt").write_text(page.locator("body").inner_text(), encoding="utf-8")
        (OUT / "menu.html").write_text(page.content(), encoding="utf-8")

        page.get_by_text("Informations", exact=True).last.click(timeout=PLAYWRIGHT_TIMEOUT_MS)
        page.wait_for_timeout(1_500)
        (OUT / "info-text.txt").write_text(page.locator("body").inner_text(), encoding="utf-8")
        (OUT / "info.html").write_text(page.content(), encoding="utf-8")

        open_chart(page, menu_open=True)
        page.wait_for_timeout(500)
        (OUT / "chart-text.txt").write_text(page.locator("body").inner_text(), encoding="utf-8")
        (OUT / "chart.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(OUT / "chart.png"), full_page=True)
        chart_data = all_chart_data(page)
        (OUT / "chart-data.json").write_text(json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Chart URL:", page.url)
        print("Chart data saved to", OUT / "chart-data.json")

        print("Rendered text saved to", OUT / "visible-text.txt")
        print("Rendered HTML saved to", OUT / "rendered.html")
        print("Screenshot saved to", OUT / "page.png")
        print("Temperature-like values found:")
        matches = sorted(set(re.findall(r"(?i)(?:temp(?:érature|erature)?|eau|water)[^\n]{0,80}", text)))
        for match in matches[:50]:
            print(match)
        print("Device text saved to", OUT / "device-text.txt")
        print("Menu text saved to", OUT / "menu-text.txt")
        print("Chart text saved to", OUT / "chart-text.txt")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
