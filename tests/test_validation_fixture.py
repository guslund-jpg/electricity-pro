"""Exercise the shipped synthetic package with real HA helpers and templates."""

from decimal import Decimal
from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.electricity_pro.const import DOMAIN

PACKAGE = Path(__file__).parents[1] / "examples/testing/ep_lab.yaml"


@pytest.fixture
async def lab(hass):
    package = yaml.safe_load(PACKAGE.read_text())
    for domain in ("input_number", "input_boolean", "script", "template", "automation"):
        assert await async_setup_component(hass, domain, {domain: package[domain]})
    await hass.async_start()
    await hass.async_block_till_done()
    await hass.services.async_call("script", "ep_lab_initialize", blocking=True)
    await hass.async_block_till_done()
    yield package
    await hass.services.async_call("automation", "turn_off", {
        "entity_id": "automation.ep_lab_heartbeat",
    }, blocking=True)
    await hass.async_block_till_done()


async def publish(hass, channel="all"):
    hass.bus.async_fire("ep_lab_publish", {"channel": channel})
    await hass.async_block_till_done()


async def set_number(hass, name, value):
    await hass.services.async_call("input_number", "set_value", {
        "entity_id": f"input_number.ep_lab_{name}", "value": value,
    }, blocking=True)
    await hass.async_block_till_done()


@pytest.fixture
async def integration(hass, lab):
    data = {"power_entity": "sensor.ep_lab_import_power"}
    for channel in ("production", "grid_export", "household"):
        for quantity in ("power", "energy"):
            data[f"{channel}_{quantity}_entity"] = f"sensor.ep_lab_{channel}_{quantity}"
    data.update({
        "flow_compatibility_enabled": True,
        "flow_generation_presence": "present", "flow_storage_presence": "absent",
        **{f"{channel}_power_phase_convention": "net_across_phases"
           for channel in ("production", "grid_export", "household")},
    })
    entry = MockConfigEntry(domain=DOMAIN, title="Electricity Pro", data=data)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_package_publishes_declared_units_and_independent_totals(hass, integration):
    assert hass.states.get("input_boolean.ep_lab_heartbeat").state == "off"
    assert hass.states.get("sensor.ep_lab_production_power").attributes["unit_of_measurement"] == "kW"
    assert hass.states.get("sensor.ep_lab_production_energy").attributes["unit_of_measurement"] == "Wh"
    assert Decimal(hass.states.get("sensor.electricity_pro_production_power").state) == 1200
    assert hass.states.get("sensor.electricity_pro_flow_power_compatibility").state == "aligned"
    for value in (101000, 97000, 100000, 101000, 102000):
        await set_number(hass, "production_energy", value)
        await publish(hass)
    state = hass.states.get("sensor.electricity_pro_production_today")
    assert Decimal(state.state) == 2
    assert state.attributes["coverage"] == "partial"
    assert Decimal(hass.states.get("sensor.electricity_pro_grid_export_today").state) == 0
    assert Decimal(hass.states.get("sensor.electricity_pro_household_energy_today").state) == 0
    assert hass.states.get("sensor.electricity_pro_current_power").state == "800.0"


async def test_package_zero_negative_and_outage_inputs(hass, integration):
    await set_number(hass, "production_power", 0)
    await publish(hass)
    entity = "sensor.electricity_pro_production_power"
    assert Decimal(hass.states.get(entity).state) == 0
    await set_number(hass, "production_power", -1)
    await publish(hass)
    assert hass.states.get(entity).state == "unavailable"
    await set_number(hass, "production_power", 1.2)
    await hass.services.async_call("input_boolean", "turn_off", {
        "entity_id": "input_boolean.ep_lab_production_available",
    }, blocking=True)
    await publish(hass)
    assert hass.states.get("sensor.ep_lab_production_power").state == "unavailable"
    assert hass.states.get(entity).state == "unavailable"
    assert Decimal(hass.states.get("sensor.electricity_pro_grid_export_power").state) == 200
    await hass.services.async_call("input_boolean", "turn_on", {
        "entity_id": "input_boolean.ep_lab_production_available",
    }, blocking=True)
    await publish(hass)
    assert Decimal(hass.states.get(entity).state) == 1200


async def test_package_skew_staleness_and_recovery(hass, integration, freezer):
    freezer.tick(timedelta(seconds=45))
    await publish(hass, "production")
    await set_number(hass, "import_power", 801)
    diagnostic = "sensor.electricity_pro_flow_power_compatibility"
    assert hass.states.get(diagnostic).state == "time_skew"
    await publish(hass)
    await set_number(hass, "import_power", 802)
    assert hass.states.get(diagnostic).state == "aligned"
    freezer.tick(timedelta(minutes=6))
    await set_number(hass, "import_power", 803)
    assert hass.states.get("sensor.electricity_pro_production_power").state == "unavailable"
    assert hass.states.get(diagnostic).state == "stale_source"
    await publish(hass)
    await set_number(hass, "import_power", 804)
    assert hass.states.get(diagnostic).state == "aligned"


async def test_heartbeat_republishes_only_when_enabled(hass, integration, freezer):
    await set_number(hass, "production_power", 2)
    assert Decimal(hass.states.get("sensor.ep_lab_production_power").state) == Decimal("1.2")
    await hass.services.async_call("input_boolean", "turn_on", {
        "entity_id": "input_boolean.ep_lab_heartbeat",
    }, blocking=True)
    freezer.tick(timedelta(seconds=11))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert Decimal(hass.states.get("sensor.electricity_pro_production_power").state) == 2000


async def test_fixture_reload_during_dip_preserves_high_water(hass, integration, freezer, hass_storage):
    await set_number(hass, "production_energy", 101000)
    await publish(hass)
    await set_number(hass, "production_energy", 97000)
    await publish(hass)
    assert await hass.config_entries.async_unload(integration.entry_id)
    # Let the unload callback's scheduled final save run before loading again.
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert f"{DOMAIN}.{integration.entry_id}.statistics" in hass_storage
    assert await hass.config_entries.async_setup(integration.entry_id)
    await hass.async_block_till_done()
    for value in (100000, 101000, 102000):
        await set_number(hass, "production_energy", value)
        await publish(hass)
    assert Decimal(hass.states.get("sensor.electricity_pro_production_today").state) == 2
    assert Decimal(hass.states.get("sensor.electricity_pro_grid_export_today").state) == 0


async def test_fixture_cross_midnight_gap_is_not_counted(hass, integration, freezer):
    await set_number(hass, "production_energy", 101000)
    await publish(hass)
    local_now = dt_util.now()
    next_day = local_now.replace(hour=0, minute=0, second=1, microsecond=0) + timedelta(days=1)
    freezer.move_to(next_day)
    await set_number(hass, "production_energy", 104000)
    await publish(hass)
    assert Decimal(hass.states.get("sensor.electricity_pro_production_today").state) == 0
    expected_month = 0 if next_day.month != local_now.month else 1
    assert Decimal(hass.states.get("sensor.electricity_pro_production_this_month").state) == expected_month
    await set_number(hass, "production_energy", 105000)
    await publish(hass)
    assert Decimal(hass.states.get("sensor.electricity_pro_production_today").state) == 1
    assert Decimal(hass.states.get("sensor.electricity_pro_production_this_month").state) == expected_month + 1


async def test_fixture_unsupported_unit_is_rejected_and_publish_restores(hass, integration):
    hass.states.async_set("sensor.ep_lab_production_power", "1.2", {
        "device_class": "power", "unit_of_measurement": "VA",
    })
    await hass.async_block_till_done()
    state = hass.states.get("sensor.electricity_pro_production_power")
    assert state.state == "unavailable"
    assert integration.runtime_data.flow_values["production_power"][1]["reason"] == "unsupported_unit"
    await publish(hass)
    assert Decimal(hass.states.get("sensor.electricity_pro_production_power").state) == 1200
