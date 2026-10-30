"""Characterize device metadata and registry identity across entity families."""

import pytest
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.binary_sensor import GoodTimeToUseElectricityBinarySensor
from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.device import device_info_for_entry
from custom_components.electricity_pro.sensor import (
    SENSOR_DESCRIPTIONS,
    ElectricityProAveragePowerTodaySensor,
    ElectricityProConsumptionTimingScoreSensor,
    ElectricityProEstimatedBaseLoadSensor,
    ElectricityProFlowCompatibilitySensor,
    ElectricityProFlowSensor,
    ElectricityProForecastInsightSensor,
    ElectricityProSensor,
)


@pytest.mark.parametrize("kind", [
    "ordinary", "forecast", "timing", "base_load", "average_power",
    "flow", "compatibility", "good_time",
])
def test_all_entity_families_preserve_device_metadata(hass, kind):
    """Every metadata-owning class uses the same entry-scoped device contract."""
    entry = MockConfigEntry(domain=DOMAIN, data={"power_entity": "sensor.power"})
    coordinator = ElectricityProCoordinator(hass, entry)
    entry.runtime_data = coordinator
    if kind == "ordinary":
        description = SENSOR_DESCRIPTIONS[0]
        entity = ElectricityProSensor(coordinator, entry, description)
        suffix = description.key
    elif kind == "forecast":
        entity = ElectricityProForecastInsightSensor(
            coordinator, entry, key="test_forecast", name="Test forecast",
        )
        suffix = "test_forecast"
    elif kind == "flow":
        entity = ElectricityProFlowSensor(coordinator, entry, "production", "power")
        suffix = "production_power"
    elif kind == "good_time":
        entity = GoodTimeToUseElectricityBinarySensor(entry)
        suffix = "good_time_to_use_electricity"
    else:
        entity_class, suffix = {
            "timing": (ElectricityProConsumptionTimingScoreSensor, "consumption_timing_score_yesterday"),
            "base_load": (ElectricityProEstimatedBaseLoadSensor, "estimated_base_load"),
            "average_power": (ElectricityProAveragePowerTodaySensor, "average_power_today"),
            "compatibility": (ElectricityProFlowCompatibilitySensor, "flow_power_compatibility"),
        }[kind]
        entity = entity_class(coordinator, entry)
    assert entity.unique_id == f"{entry.entry_id}_{suffix}"
    assert entity.device_info == {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": "Electricity Pro",
        "manufacturer": "Electricity Pro",
        "model": "Electricity monitor",
    }


async def test_registry_devices_stay_separate_and_survive_reload(hass):
    """Reload retains entity/device IDs and user names without combining entries."""
    entries = []
    for index in range(2):
        entry = MockConfigEntry(domain=DOMAIN, title=f"Installation {index}", data={
            "power_entity": f"sensor.power_{index}",
            "good_price_threshold": 1,
            "production_power_entity": f"sensor.production_{index}",
            "flow_compatibility_enabled": True,
        })
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entries.append(entry)

    devices = dr.async_get(hass)
    registry = er.async_get(hass)
    device_ids = []
    identities = {}
    for entry in entries:
        entry_devices = dr.async_entries_for_config_entry(devices, entry.entry_id)
        assert len(entry_devices) == 1
        device = entry_devices[0]
        assert device.identifiers == {(DOMAIN, entry.entry_id)}
        assert device.config_entry_id == entry.entry_id
        assert (device.name, device.manufacturer, device.model) == (
            "Electricity Pro", "Electricity Pro", "Electricity monitor",
        )
        device_ids.append(device.id)
        entities = er.async_entries_for_config_entry(registry, entry.entry_id)
        assert entities
        assert {entity.device_id for entity in entities} == {device.id}
        identities[entry.entry_id] = {
            (entity.entity_id, entity.unique_id, entity.device_id) for entity in entities
        }
    assert len(set(device_ids)) == 2
    devices.async_update_device(device_ids[0], name_by_user="My household")

    for entry in entries:
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert {
            (entity.entity_id, entity.unique_id, entity.device_id)
            for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        } == identities[entry.entry_id]
        assert len(dr.async_entries_for_config_entry(devices, entry.entry_id)) == 1
    assert devices.async_get(device_ids[0]).name_by_user == "My household"


def test_metadata_and_identifiers_are_not_shared_between_calls():
    """Mutating one entity's metadata cannot affect another entity or entry."""
    first = device_info_for_entry("entry-a")
    second = device_info_for_entry("entry-a")
    other = device_info_for_entry("entry-b")
    assert first == second
    assert first is not second
    assert first["identifiers"] is not second["identifiers"]
    first["name"] = "Changed locally"
    first["identifiers"].add((DOMAIN, "unexpected"))
    assert second == device_info_for_entry("entry-a")
    assert other["identifiers"] == {(DOMAIN, "entry-b")}
    assert other["name"] == "Electricity Pro"
