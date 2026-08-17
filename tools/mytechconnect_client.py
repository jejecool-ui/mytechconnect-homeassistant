"""Shared read-only MyTechConnect browser client."""

import os

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


HOST_PREFIX = "https://mytech-connect.user-app.pool.mytech-connect.io/"


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
    page = browser.new_page(viewport={"width": 1440, "height": 1200})
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    try:
        page.wait_for_function(
            "document.querySelector('#user-app') && document.querySelector('#user-app').innerText.trim().length > 0",
            timeout=60_000,
        )
    except PlaywrightTimeoutError:
        # Let callers inspect the rendered error page or handle the exception
        # from the next navigation step.
        pass
    return page


def open_device(page):
    page.locator(".device-summary-item").first.click(timeout=15_000)
    page.wait_for_timeout(1_500)


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
    body = page.locator("body").inner_text()
    state = text_or_none(page, "#heat-pump-on-off")
    state = state.upper() if state else None
    return {
        "heat_pump_state": state if state in {"ON", "OFF"} else None,
        "water_flow": None if not body else "OFF" if "PAS DE DÉBIT D’EAU" in body or "PAS DE DEBIT D'EAU" in body else "ON",
        "water_temperature": text_or_none(page, ".order-and-value-heatpump .order-and-value-value-number"),
        "outdoor_temperature": text_or_none(page, ".topbar-weather"),
        "operation_mode": mode_from_class(page, "#heat-pump-power-mode .state-button-container:nth-child(1) .state-button-value .istd-co-icon"),
        "regulation_mode": mode_from_class(page, "#heat-pump-power-mode .state-button-container:nth-child(2) .state-button-value .istd-co-icon"),
        "setpoint": text_or_none(page, ".order-and-value-heatpump .order-and-value-set .order-and-value-order-number"),
    }


def open_chart(page, menu_open=False):
    if not menu_open:
        page.locator(".navbar-container button").nth(1).click(timeout=15_000)
        page.wait_for_timeout(300)
    page.get_by_text("Informations", exact=True).last.click(timeout=15_000)
    page.wait_for_timeout(500)
    page.get_by_text("Graphiques de données", exact=True).last.click(timeout=15_000)
    page.wait_for_function(
        """() => (window.Highcharts?.charts || []).some(chart =>
            chart && chart.series.some(series =>
                series.name === \"Température d'eau (calculée)\" && series.points.length > 0))""",
        timeout=30_000,
    )


def precise_water_temperature(page):
    open_chart(page)
    return page.evaluate(
        """() => {
            const chart = (window.Highcharts?.charts || []).find(chart => chart &&
                chart.series.some(series => series.name === "Température d'eau (calculée)"));
            const series = chart?.series.find(series => series.name === "Température d'eau (calculée)");
            const point = series?.points[series.points.length - 1];
            return point ? {value: point.y, timestamp_ms: point.x} : null;
        }"""
    )


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
