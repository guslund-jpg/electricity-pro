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
        "sensor.electricity_pro_current_price",
        "sensor.electricity_pro_effective_price",
    ):
        assert series_by_entity[entity_id]["float_precision"] == 2
