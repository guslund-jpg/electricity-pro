"""Synthetic AC production/export contracts; no hardware validation implied."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN, CONF_POWER_ENTITY
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.energy_flows import FlowCounter
from custom_components.electricity_pro.flow_sources import FlowSources


def test_lifetime_dips_restart_and_same_day_gap():
    now = datetime(2026, 9, 16, 12, tzinfo=UTC)
    counter = FlowCounter()
    for reading in ("100", "101", "97"):
        counter.update(Decimal(reading), now)
    assert counter.reason == "backward_reading"
    counter = FlowCounter.from_dict(counter.as_dict())
    assert not counter.update(None, now)
    for reading in ("99", "101", "102"):
        counter.update(Decimal(reading), now)
    assert counter.today == counter.this_month == Decimal(2)
    assert counter.high_water == Decimal(102)
    assert len(counter.as_dict()) == 8


@pytest.mark.parametrize("start", [
    "2026-09-16", "2026-09-30", "2026-03-28", "2026-10-24",
    "2026-12-31", "2028-02-28",
])
def test_boundary_gap_never_assigned_to_new_day(start):
    now = datetime.fromisoformat(start).replace(hour=23, tzinfo=ZoneInfo("Europe/Stockholm"))
    counter = FlowCounter()
    counter.update(Decimal(100), now)
    counter.update(Decimal(102), now)
    tomorrow = now + timedelta(days=1)
    assert not counter.update(None, tomorrow)
    assert not counter.update(Decimal(97), tomorrow)
    counter = FlowCounter.from_dict(counter.as_dict())
    assert counter.update(Decimal(105), tomorrow)
    assert counter.today == 0
    counter.update(Decimal(106), tomorrow)
    assert counter.today == 1
    assert counter.this_month == (1 if tomorrow.month != now.month else 3)
    assert not counter.update(Decimal(110), now)
    assert counter.high_water == 106


def test_explicit_replacement_preserves_totals_and_rejects_invalid():
    now = datetime(2026, 9, 16, 12, tzinfo=UTC)
    counter = FlowCounter()
    counter.update(Decimal(100), now)
    counter.update(Decimal(103), now)
    counter.confirm_reset(Decimal(1), now)
    counter.update(Decimal(2), now)
    assert counter.today == counter.this_month == 4
    assert counter.generation == 1
    for bad in ("NaN", "Infinity", "-1"):
        assert not counter.update(Decimal(bad), now)
        with pytest.raises(ValueError):
            counter.confirm_reset(Decimal(bad), now)


@pytest.mark.parametrize("field,value", [
    ("high_water", "NaN"), ("today", "-1"), ("this_month", "Infinity"),
    ("month", "2026-08"), ("pending_boundary", "false"), ("generation", -1),
    ("started", "2026-09-16T12:00:00"),
])
def test_corrupt_counter_state_rejected(field, value):
    counter = FlowCounter()
    counter.update(Decimal(100), datetime(2026, 9, 16, tzinfo=UTC))
    state = counter.as_dict()
    state[field] = value
    with pytest.raises(ValueError):
        FlowCounter.from_dict(state)


@pytest.mark.parametrize("quantity,unit,value,expected,reason", [
    ("power", "kW", "1.5", "1500", "measured"),
    ("power", "W", "0", "0", "measured"),
    ("energy", "Wh", "102500", "102.5", "measured"),
    ("energy", "kWh", "0", "0", "measured"),
    ("power", "W", "-100", None, "invalid"),
    ("energy", "kWh", "NaN", None, "invalid"),
    ("energy", "kWh", "unavailable", None, "unavailable"),
    ("power", "MW", "1", None, "unsupported_unit"),
])
async def test_source_normalization(hass, quantity, unit, value, expected, reason):
    hass.states.async_set("sensor.source", value, {"unit_of_measurement": unit})
    sources = FlowSources(hass, {f"production_{quantity}_entity": "sensor.source"})
    reading = sources.read("production", quantity, dt_util.utcnow())
    assert reading.value == (Decimal(expected) if expected is not None else None)
    assert reading.reason == reason
    assert reading.observed_at is not None


async def test_source_missing_stale_and_future_are_not_zero(hass):
    sources = FlowSources(hass, {"production_power_entity": "sensor.power"})
    assert sources.read("grid_export", "power", dt_util.utcnow()).reason == "not_configured"
    assert sources.read("production", "power", dt_util.utcnow()).reason == "unavailable"
    hass.states.async_set("sensor.power", "100", {"unit_of_measurement": "W"})
    at = hass.states.get("sensor.power").last_reported
    for now in (at - timedelta(seconds=1), at + timedelta(seconds=301)):
        reading = sources.read("production", "power", now)
        assert reading.value is None
        assert reading.reason == "stale"


def flow_entry(**overrides):
    return MockConfigEntry(domain=DOMAIN, title="Electricity Pro", data={
        CONF_POWER_ENTITY: "sensor.import_power",
        "production_energy_entity": "sensor.production",
        "grid_export_energy_entity": "sensor.export",
        **overrides,
    })


async def test_independent_channels_restore_and_source_change(hass, freezer):
    freezer.move_to("2026-09-16T12:00:00+00:00")
    hass.config.time_zone = "UTC"
    c = ElectricityProCoordinator(hass, flow_entry())
    for prod, export in ((100, 50), (103, 51), (90, 52)):
        hass.states.async_set("sensor.production", str(prod), {"unit_of_measurement": "kWh"})
        hass.states.async_set("sensor.export", str(export), {"unit_of_measurement": "kWh"})
        c._read_flows(dt_util.utcnow())
    assert c.flow_values["production_today"][0] is None
    assert c.flow_values["grid_export_today"][0] == 2
    stored = c._statistics_data()
    restored = ElectricityProCoordinator(hass, flow_entry())
    with patch.object(restored._store, "async_load", return_value=stored):
        await restored._async_restore_statistics()
    hass.states.async_set("sensor.production", "104", {"unit_of_measurement": "kWh"})
    restored._read_flows(dt_util.utcnow())
    assert restored.flow_values["production_today"][0] == 4
    changed = ElectricityProCoordinator(hass, flow_entry(production_energy_entity="sensor.other"))
    with patch.object(changed._store, "async_load", return_value=stored):
        await changed._async_restore_statistics()
    assert changed._flow_counters["production"].high_water is None
    assert changed._flow_counters["grid_export"].this_month == 2


@pytest.mark.parametrize("saved", [None, [], {"production": []}, {"production": {"counter": {}}}])
async def test_malformed_optional_storage_does_not_block_import(hass, saved):
    c = ElectricityProCoordinator(hass, flow_entry())
    with patch.object(c._store, "async_load", return_value={"directional_flows": saved}):
        await c._async_restore_statistics()
    assert c._flow_counters["production"].high_water is None


async def test_reset_scoped_to_one_fresh_source(hass, freezer):
    freezer.move_to("2026-09-16T12:00:00+00:00")
    c = ElectricityProCoordinator(hass, flow_entry())
    for prod, export in ((100, 50), (103, 52)):
        hass.states.async_set("sensor.production", str(prod), {"unit_of_measurement": "kWh"})
        hass.states.async_set("sensor.export", str(export), {"unit_of_measurement": "kWh"})
        c._read_flows(dt_util.now().astimezone(c._local_timezone))
    export_before = c._flow_counters["grid_export"].as_dict()
    hass.states.async_set("sensor.production", "1", {"unit_of_measurement": "kWh"})
    with patch.object(c._store, "async_save"), patch.object(c._store, "async_delay_save"):
        with pytest.raises(ValueError):
            await c.async_confirm_flow_meter_reset("production", "sensor.export")
        await c.async_confirm_flow_meter_reset("production", "sensor.production")
    assert c._flow_counters["production"].today == 3
    assert c._flow_counters["production"].generation == 1
    assert c._flow_counters["grid_export"].as_dict() == export_before


async def test_midnight_rejects_old_receipt_then_rebaselines(hass, freezer):
    freezer.move_to("2026-09-16T23:59:00+00:00")
    hass.config.time_zone = "UTC"
    c = ElectricityProCoordinator(hass, flow_entry())
    hass.states.async_set("sensor.production", "100", {"unit_of_measurement": "kWh"})
    c._read_flows(dt_util.utcnow())
    freezer.move_to("2026-09-17T00:01:00+00:00")
    c._read_flows(dt_util.utcnow())
    assert c.flow_values["production_today"][0] is None
    assert c.flow_values["production_today"][1]["reason"] == "previous_day_reading"
    with pytest.raises(ValueError, match="valid fresh"):
        await c.async_confirm_flow_meter_reset("production", "sensor.production")
    hass.states.async_set("sensor.production", "101", {"unit_of_measurement": "kWh"})
    c._read_flows(dt_util.utcnow())
    assert c.flow_values["production_today"][0] == 0
    hass.states.async_set("sensor.production", "102", {"unit_of_measurement": "kWh"})
    c._read_flows(dt_util.utcnow())
    assert c.flow_values["production_today"][0] == 1


async def test_timezone_change_does_not_restore_incompatible_periods(hass):
    hass.config.time_zone = "UTC"
    c = ElectricityProCoordinator(hass, flow_entry())
    counter = c._flow_counters["production"]
    counter.update(Decimal(100), datetime(2026, 9, 16, tzinfo=UTC))
    counter.update(Decimal(101), datetime(2026, 9, 16, tzinfo=UTC))
    stored = c._statistics_data()
    hass.config.time_zone = "Europe/Stockholm"
    restored = ElectricityProCoordinator(hass, flow_entry())
    with patch.object(restored._store, "async_load", return_value=stored):
        await restored._async_restore_statistics()
    assert restored._flow_counters["production"].high_water is None
