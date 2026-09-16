"""Measured non-storage load is independent of net grid and optional flows."""

from decimal import Decimal
from unittest.mock import patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator


def set_source(hass, entity, value, unit, device_class):
    hass.states.async_set(entity, str(value), {
        "unit_of_measurement": unit, "device_class": device_class,
    })


def make_entry(**options):
    return MockConfigEntry(domain=DOMAIN, title="Electricity Pro", data={
        "power_entity": "sensor.net", "energy_entity": "sensor.import_energy",
        "household_power_entity": "sensor.load_power",
        "household_energy_entity": "sensor.load_energy",
        "production_energy_entity": "sensor.production",
    }, options=options)


@pytest.mark.parametrize("mode", ["power", "energy", "both", "neither"])
async def test_measured_entities_without_topology_or_solar_sources(hass, freezer, mode):
    freezer.move_to("2026-09-16T12:00:00+00:00")
    set_source(hass, "sensor.net", -500, "W", "power")
    set_source(hass, "sensor.import_energy", 10, "kWh", "energy")
    set_source(hass, "sensor.load_power", 1.5, "kW", "power")
    set_source(hass, "sensor.load_energy", 100000, "Wh", "energy")
    entry = make_entry(
        household_power_entity="sensor.load_power" if mode in ("power", "both") else None,
        household_energy_entity="sensor.load_energy" if mode in ("energy", "both") else None,
        production_energy_entity=None,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.electricity_pro_current_power").state == "-500"
    assert hass.states.get("sensor.electricity_pro_energy_today").state == "10"
    power = hass.states.get("sensor.electricity_pro_household_demand_power")
    today = hass.states.get("sensor.electricity_pro_household_energy_today")
    month = hass.states.get("sensor.electricity_pro_household_energy_this_month")
    assert (power is not None) == (mode in ("power", "both"))
    assert (today is not None) == (month is not None) == (mode in ("energy", "both"))
    if power:
        assert power.state == "1500.0"
        assert power.attributes["origin"] == "measured"
        assert power.attributes["state_class"] == "measurement"
    if today:
        assert Decimal(today.state) == 0
        assert today.attributes["coverage"] == "partial"
        assert today.attributes["source_entity"] == "sensor.load_energy"
        assert today.attributes["state_class"] == "total_increasing"
        set_source(hass, "sensor.load_energy", 101250, "Wh", "energy")
        await hass.async_block_till_done()
        assert Decimal(hass.states.get(today.entity_id).state) == Decimal("1.25")
        assert hass.states.get("sensor.electricity_pro_energy_today").state == "10"


async def test_dips_restart_and_reset_never_change_other_channels(hass, freezer):
    freezer.move_to("2026-09-16T12:00:00+00:00")
    hass.config.time_zone = "UTC"
    set_source(hass, "sensor.net", 800, "W", "power")
    set_source(hass, "sensor.import_energy", 10, "kWh", "energy")
    set_source(hass, "sensor.production", 200, "kWh", "energy")
    c = ElectricityProCoordinator(hass, make_entry())
    with patch.object(c._store, "async_delay_save"):
        for reading in (100, 101, 97):
            set_source(hass, "sensor.load_energy", reading, "kWh", "energy")
            original_import_data = c._read()
    assert c.flow_values["household_today"][0] is None
    stored = c._statistics_data()
    restored = ElectricityProCoordinator(hass, make_entry())
    with patch.object(restored._store, "async_load", return_value=stored):
        await restored._async_restore_statistics()
    set_source(hass, "sensor.load_energy", 102, "kWh", "energy")
    with patch.object(restored._store, "async_delay_save"):
        assert restored._read() == original_import_data
    assert restored.flow_values["household_today"][0] == 2
    production_before = restored._flow_counters["production"].as_dict()
    set_source(hass, "sensor.load_energy", 1, "kWh", "energy")
    with patch.object(restored._store, "async_save"), patch.object(restored._store, "async_delay_save"):
        await restored.async_confirm_flow_meter_reset("household", "sensor.load_energy")
    assert restored._flow_counters["household"].today == 2
    assert restored._flow_counters["household"].generation == 1
    assert restored._flow_counters["production"].as_dict() == production_before
    assert restored.data == original_import_data


@pytest.mark.parametrize("state,expected", [
    ("0", Decimal(0)), ("-1", None), ("NaN", None), ("unavailable", None),
])
async def test_household_invalid_or_missing_never_falls_back_to_grid(hass, state, expected):
    set_source(hass, "sensor.net", 800, "W", "power")
    set_source(hass, "sensor.load_power", state, "W", "power")
    c = ElectricityProCoordinator(hass, make_entry())
    c._read_flows(dt_util.now().astimezone(c._local_timezone))
    assert c.flow_values["household_power"][0] == expected


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_options_confirm_preserve_and_clear_household_bindings(hass, profile):
    entry = MockConfigEntry(domain=DOMAIN, data={"power_entity": "sensor.net", "source_profile": profile})
    entry.add_to_hass(hass)
    set_source(hass, "sensor.load_power", 100, "W", "power")
    submission = {"power_entity": "sensor.net"} if profile == "custom" else {}
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        **submission, "configure_energy_flows": True,
    })
    keys = {key.schema for key in result["data_schema"].schema}
    assert {"household_power_entity", "household_energy_entity"} <= keys
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "household_power_entity": "sensor.load_power",
    })
    assert result["errors"]["base"] == "confirm_flow_semantics"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "household_power_entity": "sensor.load_power", "confirm_flow_semantics": True,
    })
    assert result["type"] == FlowResultType.CREATE_ENTRY
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], submission)
    assert result["data"]["household_power_entity"] == "sensor.load_power"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        **submission, "configure_energy_flows": True,
    })
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["data"]["household_power_entity"] is None


async def test_household_cannot_reuse_import_or_production_source(hass):
    from custom_components.electricity_pro.config_flow import _source_input_errors
    for other in ("power_entity", "production_power_entity", "grid_export_power_entity"):
        errors = _source_input_errors(hass, {
            "household_power_entity": "sensor.same", other: "sensor.same",
        })
        assert errors["base"] == "invalid_flow_source"


async def test_public_reset_action_accepts_household_channel(hass, freezer):
    freezer.move_to("2026-09-16T12:00:00+00:00")
    set_source(hass, "sensor.net", 800, "W", "power")
    set_source(hass, "sensor.load_energy", 100, "kWh", "energy")
    entry = make_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    with patch.object(entry.runtime_data._store, "async_save"):
        await hass.services.async_call(DOMAIN, "confirm_flow_meter_reset", {
            "config_entry_id": entry.entry_id, "channel": "household",
            "source_entity": "sensor.load_energy", "confirm_reset": True,
        }, blocking=True)
    assert entry.runtime_data._flow_counters["household"].generation == 1
    assert entry.runtime_data._flow_counters["production"].generation == 0
