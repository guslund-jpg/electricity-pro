"""Validation tests for the published dashboard examples."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml


DASHBOARD_EXAMPLES = Path(__file__).parents[1] / "examples" / "dashboards"


def _walk(value: Any) -> Iterator[Any]:
    """Yield every nested value from a YAML document."""
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_dashboard_condition_state_not_is_scalar() -> None:
    """Home Assistant conditional cards require one state_not value."""
    for dashboard_path in DASHBOARD_EXAMPLES.glob("*.yaml"):
        dashboard = yaml.safe_load(dashboard_path.read_text(encoding="utf-8"))
        invalid = [
            item
            for item in _walk(dashboard)
            if isinstance(item, dict)
            and "state_not" in item
            and not isinstance(item["state_not"], str)
        ]
        assert not invalid, f"{dashboard_path.name} contains invalid state_not values"


def test_standard_dashboard_covers_core_measurements_and_insights() -> None:
    """Standard dashboard should cover the core product without custom cards."""
    dashboard = yaml.safe_load(
        (DASHBOARD_EXAMPLES / "electricity-pro.yaml").read_text(encoding="utf-8")
    )
    entity_ids = {
        item["entity"]
        for item in _walk(dashboard)
        if isinstance(item, dict) and isinstance(item.get("entity"), str)
    }

    assert {
        "sensor.electricity_pro_current_power",
        "sensor.electricity_pro_current_market_price",
        "sensor.electricity_pro_current_price",
        "sensor.electricity_pro_effective_price",
        "sensor.electricity_pro_current_cost_rate",
        "sensor.electricity_pro_energy_today",
        "sensor.electricity_pro_cost_today",
        "sensor.electricity_pro_consumption_weighted_average_price_today",
        "sensor.electricity_pro_average_power_today",
        "sensor.electricity_pro_peak_power_today",
        "sensor.electricity_pro_peak_power_time_today",
        "sensor.electricity_pro_energy_this_month",
        "sensor.electricity_pro_cost_this_month",
        "sensor.electricity_pro_consumption_timing_score_yesterday",
        "binary_sensor.electricity_pro_good_time_to_use_electricity",
    } <= entity_ids

    assert not {
        str(item.get("type"))
        for item in _walk(dashboard)
        if isinstance(item, dict)
    } & {"custom:mushroom-template-card", "custom:apexcharts-card"}

    views_by_title = {view["title"]: view for view in dashboard["views"]}
    assert set(views_by_title) == {"Overview", "Live", "Statistics", "Forecast"}
    overview_entity_ids = {
        item["entity"]
        for item in _walk(views_by_title["Overview"])
        if isinstance(item, dict) and isinstance(item.get("entity"), str)
    }
    assert not {
        "sensor.electricity_pro_energy_this_month",
        "sensor.electricity_pro_cost_this_month",
    } & overview_entity_ids
    statistics_headings = {
        card["heading"]
        for card in views_by_title["Statistics"]["cards"]
        if card.get("type") == "heading"
    }
    assert statistics_headings == {"Today’s totals", "This month"}

    advice_tiles = {
        item["card"]["name"]: item
        for item in _walk(dashboard)
        if isinstance(item, dict)
        and item.get("type") == "conditional"
        and isinstance(item.get("card"), dict)
        and item["card"].get("name")
        in {"Good time to use electricity", "Wait for a better price"}
    }
    assert set(advice_tiles) == {
        "Good time to use electricity",
        "Wait for a better price",
    }
    for tile in advice_tiles.values():
        assert tile["card"]["entity"] == "sensor.electricity_pro_effective_price"
    assert advice_tiles["Good time to use electricity"]["conditions"][0]["state"] == "on"
    assert advice_tiles["Wait for a better price"]["conditions"][0]["state"] == "off"


def test_enhanced_dashboard_live_header_precision() -> None:
    """Enhanced live charts use readable power and price precision."""
    dashboard = yaml.safe_load(
        (DASHBOARD_EXAMPLES / "electricity-pro-enhanced.yaml").read_text(
            encoding="utf-8"
        )
    )
    series_by_entity = {
        series["entity"]: series
        for item in _walk(dashboard)
        if isinstance(item, dict) and isinstance(item.get("series"), list)
        for series in item["series"]
        if isinstance(series, dict) and "entity" in series
    }

    assert (
        series_by_entity["sensor.electricity_pro_current_power"]["float_precision"]
        == 0
    )
    for entity_id in (
        "sensor.electricity_pro_current_market_price",
        "sensor.electricity_pro_current_price",
        "sensor.electricity_pro_effective_price",
    ):
        assert series_by_entity[entity_id]["float_precision"] == 2


def test_enhanced_dashboard_advice_formats_effective_price_to_two_decimals() -> None:
    """Enhanced advice card should not expose raw effective-price precision."""
    dashboard = yaml.safe_load(
        (DASHBOARD_EXAMPLES / "electricity-pro-enhanced.yaml").read_text(
            encoding="utf-8"
        )
    )
    advice_card = next(
        item
        for item in _walk(dashboard)
        if isinstance(item, dict)
        and item.get("type") == "custom:mushroom-template-card"
        and item.get("entity")
        == "binary_sensor.electricity_pro_good_time_to_use_electricity"
    )

    assert "'%.2f' | format" in advice_card["secondary"]


def test_enhanced_dashboard_market_price_presentation() -> None:
    """Enhanced dashboard compares and previews provider-independent prices."""
    dashboard = yaml.safe_load(
        (DASHBOARD_EXAMPLES / "electricity-pro-enhanced.yaml").read_text(
            encoding="utf-8"
        )
    )
    charts = [
        item
        for item in _walk(dashboard)
        if isinstance(item, dict) and item.get("type") == "custom:apexcharts-card"
    ]

    comparison = next(
        chart
        for chart in charts
        if chart.get("header", {}).get("title")
        == "Market, supplier, and effective price"
    )
    assert comparison["yaxis"][0]["min"] == "~0"
    assert [series["entity"] for series in comparison["series"]] == [
        "sensor.electricity_pro_current_market_price",
        "sensor.electricity_pro_current_price",
        "sensor.electricity_pro_effective_price",
    ]

    forecast = next(
        chart
        for chart in charts
        if chart.get("header", {}).get("title") == "Market price forecast"
    )
    assert forecast["graph_span"] == "50h"
    assert forecast["span"] == {"start": "day"}
    assert forecast["yaxis"][0]["min"] == "~0"
    assert forecast["update_delay"] == "3s"
    assert forecast["update_interval"] == "1min"
    assert forecast["now"]["show"] is True
    assert forecast["apex_config"]["chart"] == {
        "animations": {"enabled": False},
        "redrawOnParentResize": True,
        "redrawOnWindowResize": True,
    }
    assert forecast["series"][0]["curve"] == "stepline"
    assert forecast["series"][0]["show"]["in_header"] == "before_now"
    assert "entity.attributes.forecast" in forecast["series"][0]["data_generator"]


def test_enhanced_dashboard_phase_current_gauges_share_20a_scale() -> None:
    """Phase-current gauges should use one comparable example scale."""
    dashboard = yaml.safe_load(
        (DASHBOARD_EXAMPLES / "electricity-pro-enhanced.yaml").read_text(
            encoding="utf-8"
        )
    )
    cards_by_entity = {
        item["entity"]: item
        for item in _walk(dashboard)
        if isinstance(item, dict)
        and item.get("type") == "gauge"
        and str(item.get("entity", "")).startswith(
            "sensor.electricity_pro_current_l"
        )
    }

    expected_entities = {
        "sensor.electricity_pro_current_l1",
        "sensor.electricity_pro_current_l2",
        "sensor.electricity_pro_current_l3",
    }
    assert cards_by_entity.keys() == expected_entities
    for card in cards_by_entity.values():
        assert card["min"] == 0
        assert card["max"] == 20
        assert card["needle"] is True
        assert card["severity"] == {"green": 0, "yellow": 14, "red": 18}
