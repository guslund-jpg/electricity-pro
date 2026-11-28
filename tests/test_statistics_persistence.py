"""Preserve saved sections and independent recovery at the storage boundary."""

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
import json
from unittest.mock import patch

import pytest

from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.statistics_storage import (
    StatisticsComponent,
    dump_components,
    restore_components,
)
from custom_components.electricity_pro.variable_cost_statistics import (
    VariableCostHistory,
)
from tests.test_monthly_energy_recovery import make_entry


@pytest.mark.parametrize(
    "key,invalid",
    [
        ("local_costs", {}),
        ("local_costs", None),
        ("monthly_variable_cost_archive", None),
        ("variable_cost_statistics", []),
        ("energy_today_from_total", None),
        ("cost_this_month", None),
        ("peak_power_today", None),
        ("consumption_timing_buckets", None),
        ("consumption_timing_score_yesterday", {"period_start": "bad", "result": {}}),
        ("base_load_buckets", None),
        ("base_load_daily_summaries", [{}]),
        ("base_load_daily_summaries", [None]),
        ("adaptive_price_history", None),
    ],
)
async def test_invalid_section_does_not_erase_valid_monthly_balance(
    hass, freezer, key, invalid, caplog
):
    await hass.config.async_set_time_zone("UTC")
    now = datetime(2026, 11, 19, 12, tzinfo=UTC)
    freezer.move_to(now)
    entry = make_entry(mode="lifetime")
    original = ElectricityProCoordinator(hass, entry)
    original._energy_this_month.update(Decimal(100), now)
    original._energy_this_month.update(Decimal("103.125"), now)
    original._monthly_energy_started = now.isoformat()
    original._monthly_energy_legacy = False
    stored = json.loads(json.dumps(original._statistics_data()))
    stored.update(
        {
            "energy_today_source_entity": "sensor.energy",
            "cost_this_month_unit": "SEK",
            key: invalid,
        }
    )
    restored = ElectricityProCoordinator(hass, entry)
    restored._variable_cost_history = VariableCostHistory()
    with patch.object(restored._store, "async_load", return_value=deepcopy(stored)):
        await restored._async_restore_statistics()
    result = json.loads(json.dumps(restored._statistics_data()))
    for field in (
        "energy_this_month",
        "monthly_energy_source",
        "monthly_energy_started",
        "monthly_energy_legacy",
    ):
        assert result[field] == stored[field]
    assert restored._energy_this_month.value == Decimal("3.125")
    assert "invalid" in caplog.text.lower()
    if key == "variable_cost_statistics":
        assert restored._variable_cost_history is None
        assert result[key] == invalid


@pytest.mark.parametrize("stored", [{}, {"unrecognized_future_section": {"value": 1}}])
async def test_missing_sections_keep_existing_dump_omission_rules(hass, stored):
    coordinator = ElectricityProCoordinator(hass, make_entry())
    before = json.loads(json.dumps(coordinator._statistics_data()))
    with patch.object(coordinator._store, "async_load", return_value=stored):
        await coordinator._async_restore_statistics()
    assert coordinator._statistics_data() == before


async def test_legacy_balances_and_lifetime_metadata_survive_two_restores(
    hass, freezer
):
    await hass.config.async_set_time_zone("UTC")
    freezer.move_to("2026-11-19T12:00:00+00:00")
    # Original version-1 format, before monthly source/coverage metadata existed.
    stored = {
        "energy_this_month": {
            "period_start": "2026-11-01",
            "last_value": "100",
            "value": "13.125",
        },
        "cost_this_month": {
            "period_start": "2026-11-01",
            "last_value": "20",
            "value": "4.750",
        },
        "cost_this_month_unit": "SEK",
        "energy_today_from_total": {
            "period_start": "2026-11-19",
            "last_value": "100",
            "value": "1.125",
        },
        "energy_today_source_entity": "sensor.energy",
        "energy_today_period_complete": False,
    }
    first = ElectricityProCoordinator(hass, make_entry(mode="lifetime"))
    with patch.object(first._store, "async_load", return_value=deepcopy(stored)):
        await first._async_restore_statistics()
    checkpoint = json.loads(json.dumps(first._statistics_data()))
    for key, value in stored.items():
        assert checkpoint[key] == value
    assert checkpoint["monthly_energy_legacy"] is True
    assert checkpoint["monthly_energy_started"] is None
    second = ElectricityProCoordinator(hass, make_entry(mode="lifetime"))
    with patch.object(second._store, "async_load", return_value=checkpoint):
        await second._async_restore_statistics()
    assert second._statistics_data() == checkpoint


@pytest.mark.parametrize("error", [RuntimeError, AssertionError, AttributeError])
def test_unexpected_loader_errors_are_not_reported_as_invalid_checkpoints(error):
    calls = []

    def broken(_stored):
        raise error("programming failure")

    components = (
        StatisticsComponent(
            ("broken",),
            broken,
            warning="invalid checkpoint",
            recover=lambda _: calls.append("recover"),
        ),
    )
    with pytest.raises(error, match="programming failure"):
        restore_components({"broken": {}}, components, calls.append)
    assert calls == []


def test_dump_failure_cannot_return_a_partial_checkpoint():
    def broken():
        raise RuntimeError("serialization failure")

    components = (
        StatisticsComponent(("kept",), lambda _: None, lambda: {"kept": "balance"}),
        StatisticsComponent(("broken",), lambda _: None, broken),
    )
    with pytest.raises(RuntimeError, match="serialization failure"):
        dump_components(components)
