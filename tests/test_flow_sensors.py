"""End-to-end optional flow sensor and recovery action tests."""

from unittest.mock import patch

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN, CONF_POWER_ENTITY


async def setup_flows(hass, configured=True):
    hass.states.async_set("sensor.import_power", "800", {
        "device_class": "power", "unit_of_measurement": "W",
    })
    hass.states.async_set("sensor.production", "100", {
        "device_class": "energy", "unit_of_measurement": "kWh",
    })
    hass.states.async_set("sensor.solar_power", "1.2", {
        "device_class": "power", "unit_of_measurement": "kW",
    })
    entry = MockConfigEntry(domain=DOMAIN, title="Electricity Pro", data={
        CONF_POWER_ENTITY: "sensor.import_power",
        **({
            "production_energy_entity": "sensor.production",
            "production_power_entity": "sensor.solar_power",
        } if configured else {}),
    })
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.mark.parametrize("configured", [False, True])
async def test_only_configured_entities_and_existing_import_unchanged(hass, freezer, configured):
    freezer.move_to("2026-09-16T12:00:00+00:00")
    await setup_flows(hass, configured)
    assert hass.states.get("sensor.electricity_pro_current_power").state == "800"
    assert hass.states.get("sensor.electricity_pro_grid_export_today") is None
    production = hass.states.get("sensor.electricity_pro_production_today")
    if not configured:
        assert production is None
        return
    assert production.state == "0"
    assert production.attributes["coverage"] == "partial"
    assert production.attributes["state_class"] == "total_increasing"
    assert hass.states.get("sensor.electricity_pro_production_power").state == "1200.0"
    hass.states.async_set("sensor.production", "101", {
        "device_class": "energy", "unit_of_measurement": "kWh",
    })
    await hass.async_block_till_done()
    assert hass.states.get("sensor.electricity_pro_production_today").state == "1"
    hass.states.async_set("sensor.production", "98", {
        "device_class": "energy", "unit_of_measurement": "kWh",
    })
    await hass.async_block_till_done()
    assert hass.states.get("sensor.electricity_pro_production_today").state == "unavailable"
    assert hass.states.get("sensor.electricity_pro_current_power").state == "800"


async def test_action_requires_confirmation_loaded_entry_and_matching_source(hass, freezer):
    freezer.move_to("2026-09-16T12:00:00+00:00")
    entry = await setup_flows(hass)
    base = {
        "config_entry_id": entry.entry_id, "source_entity": "sensor.production",
        "channel": "production", "confirm_reset": True,
    }
    for changes in (
        {"config_entry_id": "missing"}, {"source_entity": "sensor.other"},
        {"channel": "grid_export"},
    ):
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(DOMAIN, "confirm_flow_meter_reset", {**base, **changes}, blocking=True)
    import voluptuous as vol
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(DOMAIN, "confirm_flow_meter_reset", {**base, "confirm_reset": False}, blocking=True)
    c = entry.runtime_data
    with patch.object(c._store, "async_save") as save:
        await hass.services.async_call(DOMAIN, "confirm_flow_meter_reset", base, blocking=True)
    save.assert_awaited_once()
    assert c._flow_counters["production"].generation == 1
    assert c._flow_counters["grid_export"].generation == 0


async def test_unrelated_updates_do_not_duplicate_energy_or_change_attributes(hass, freezer):
    freezer.move_to("2026-09-16T12:00:00+00:00")
    entry = await setup_flows(hass)
    c = entry.runtime_data
    before = c._flow_counters["production"].as_dict()
    attrs = dict(c.flow_values["production_today"][1])
    for power in (801, 802, 803):
        hass.states.async_set("sensor.import_power", str(power), {"unit_of_measurement": "W"})
        await hass.async_block_till_done()
    assert c._flow_counters["production"].as_dict() == before
    assert c.flow_values["production_today"][1] == attrs
    c._async_daily_rollover(dt_util.now())
