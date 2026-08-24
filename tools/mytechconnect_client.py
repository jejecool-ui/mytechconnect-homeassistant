"""Shared read-only MyTechConnect browser client."""

import os
import re
import logging

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


HOST_PREFIX = "https://mytech-connect.user-app.pool.mytech-connect.io/"
LOGGER = logging.getLogger(__name__)


def validate_url(url):
    return bool(url and url.startswith(HOST_PREFIX))


def launch_kwargs():
    kwargs = {
        "headless": True,
        "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    }
    chromium_path = os.environ.get("PLAYWRIGHT_CHROMIUM")
    if chromium_path:
        kwargs["executable_path"] = chromium_path
    return kwargs


def open_page(browser, url):
    LOGGER.info("Opening MyTechConnect page (URL prefix, 50 chars): %s", url[:50])
    page = browser.new_page(viewport={"width": 1440, "height": 1200})
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    LOGGER.info("MyTechConnect page loaded; waiting for rendered application")
    try:
        page.wait_for_function(
            "document.querySelector('#user-app') && document.querySelector('#user-app').innerText.trim().length > 0",
            timeout=60_000,
        )
    except PlaywrightTimeoutError:
        # Let callers inspect the rendered error page or handle the exception
        # from the next navigation step.
        LOGGER.warning("Rendered MyTechConnect application did not appear within 60 seconds")
    else:
        LOGGER.info("Rendered MyTechConnect application detected")
    return page


def open_device(page):
    devices = page.locator(".device-summary-item")
    LOGGER.info("Looking for MyTechConnect devices")
    device_count = devices.count()
    LOGGER.info("MyTechConnect device entries found: %d", device_count)
    if not device_count:
        LOGGER.error("No MyTechConnect device entry found on the rendered page")
    LOGGER.info("Opening first MyTechConnect device")
    devices.first.click(timeout=15_000)
    page.wait_for_timeout(1_500)
    LOGGER.info("MyTechConnect device page opened")


def text_or_none(page, selector):
    locator = page.locator(selector).first
    if not locator.count():
        return None
    value = locator.inner_text().strip()
    return value or None


def mode_from_class(page, selector):
    locator = page.locator(selector).first
    if not locator.count():
        return None
    classes = locator.get_attribute("class") or ""
    for token in classes.split():
        if token.startswith("heat-pump-mode-"):
            return token.removeprefix("heat-pump-mode-").removeprefix("power-")
    return None


def extract_main_values(page):
    LOGGER.info("Extracting values from the main MyTechConnect page")
    body = page.locator("body").inner_text()
    state = text_or_none(page, "#heat-pump-on-off")
    state = state.upper() if state else None
    values = {
        "heat_pump_state": state if state in {"ON", "OFF"} else None,
        "water_flow": None if not body else "OFF" if "PAS DE DÉBIT D’EAU" in body or "PAS DE DEBIT D'EAU" in body else "ON",
        "water_temperature": text_or_none(page, ".order-and-value-heatpump .order-and-value-value-number"),
        "outdoor_temperature": text_or_none(page, ".topbar-weather"),
        "operation_mode": mode_from_class(page, "#heat-pump-power-mode .state-button-container:nth-child(1) .state-button-value .istd-co-icon"),
        "regulation_mode": mode_from_class(page, "#heat-pump-power-mode .state-button-container:nth-child(2) .state-button-value .istd-co-icon"),
        "setpoint": text_or_none(page, ".order-and-value-heatpump .order-and-value-set .order-and-value-order-number"),
    }
    LOGGER.info("Main MyTechConnect values extracted")
    return values


def number_from_display(value):
    """Convert a display value such as ``26.8°C`` to a JSON number."""
    if value is None:
        return None
    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", value)
    if not match:
        return None
    number = float(match.group(0).replace(",", "."))
    return int(number) if number.is_integer() else number


def normalize_sensor_values(raw):
    return {
        "binary_sensor.pool_heat_pump": raw["heat_pump_state"],
        "binary_sensor.pool_water_flow": raw["water_flow"],
        "sensor.pool_water_temperature": number_from_display(raw["water_temperature"]),
        "sensor.pool_outdoor_temperature": number_from_display(raw["outdoor_temperature"]),
        "sensor.pool_heat_pump_operation_mode": raw["operation_mode"],
        "sensor.pool_heat_pump_regulation_mode": raw["regulation_mode"],
        "sensor.pool_heat_pump_temperature_setpoint": number_from_display(raw["setpoint"]),
    }


def open_chart(page, menu_open=False):
    LOGGER.info("Opening MyTechConnect data chart")
    if not menu_open:
        LOGGER.info("Opening MyTechConnect navigation menu")
        page.locator(".navbar-container button").nth(1).click(timeout=15_000)
        page.wait_for_timeout(300)
        LOGGER.info("MyTechConnect navigation menu opened")
    LOGGER.info("Opening MyTechConnect Information section")
    page.get_by_text("Informations", exact=True).last.click(timeout=15_000)
    page.wait_for_timeout(500)
    LOGGER.info("MyTechConnect Information section opened")
    LOGGER.info("Selecting MyTechConnect data charts")
    page.get_by_text("Graphiques de données", exact=True).last.click(timeout=15_000)
    LOGGER.info("MyTechConnect data charts selected; waiting for Highcharts data")
    page.wait_for_function(
        """() => (window.Highcharts?.charts || []).some(chart =>
            chart && chart.series.some(series =>
                series.name === \"Température d'eau (calculée)\" && series.points.length > 0))""",
        timeout=30_000,
    )
    LOGGER.info("MyTechConnect data chart loaded")


def precise_water_temperature(page):
    open_chart(page)
    LOGGER.info("Reading last calculated water temperature point from Highcharts")
    point = page.evaluate(
        """() => {
            const chart = (window.Highcharts?.charts || []).find(chart => chart &&
                chart.series.some(series => series.name === "Température d'eau (calculée)"));
            const series = chart?.series.find(series => series.name === "Température d'eau (calculée)");
            const point = series?.points[series.points.length - 1];
            return point ? {value: point.y, timestamp_ms: point.x} : null;
        }"""
    )
    if point:
        LOGGER.info(
            "Last calculated water temperature point read: value=%s, timestamp_ms=%s",
            point["value"],
            point["timestamp_ms"],
        )
    else:
        LOGGER.warning("No calculated water temperature point found in Highcharts")
    return point


def all_chart_data(page):
    return page.evaluate("""
        () => (window.Highcharts?.charts || []).filter(Boolean).map(chart => ({
            container: chart.renderTo?.id,
            series: chart.series.map(series => ({
                name: series.name,
                points: series.points.map(point => ({timestamp_ms: point.x, value: point.y}))
            }))
        }))
    """)
