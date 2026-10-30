"""Characterize optional entity creation independently of provider internals."""

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.sensor import async_setup_entry as setup_sensors


@pytest.mark.parametrize("channel", ["production", "grid_export", "household"])
@pytest.mark.parametrize("quantity", ["power", "energy"])
@pytest.mark.parametrize("configuration", ["data", "options", "cleared", "empty", "absent"])
async def test_optional_source_entity_creation_contract(
    hass, channel, quantity, configuration,
):
    """Only configured quantities create entities, even when readings are absent."""
    key = f"{channel}_{quantity}_entity"
    data = {"power_entity": "sensor.import_power"}
    options = {}
    if configuration in {"data", "cleared", "empty"}:
        data[key] = "sensor.optional_source"
    if configuration == "options":
        options[key] = "sensor.optional_source"
    elif configuration == "cleared":
        options[key] = None
    elif configuration == "empty":
        options[key] = ""
    entry = MockConfigEntry(domain=DOMAIN, title="Electricity Pro", data=data, options=options)
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.import_power", "800", {"unit_of_measurement": "W"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    for candidate in ("production", "grid_export", "household"):
        for period in ("power", "today", "this_month"):
            expected = (
                configuration in {"data", "options"}
                and candidate == channel
                and (period == "power") == (quantity == "power")
            )
            unique_id = f"{entry.entry_id}_{candidate}_{period}"
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            assert (entity_id is not None) is expected
            if expected:
                registered = registry.async_get(entity_id)
                assert registered.config_entry_id == entry.entry_id
                state = hass.states.get(entity_id)
                assert state is not None
                assert state.state == "unavailable"
    assert hass.states.get("sensor.electricity_pro_current_power").state == "800"


@pytest.mark.parametrize("enabled", [True, False, None, 1, "true"])
async def test_diagnostic_requires_explicit_true_option(hass, enabled):
    """Only literal True opts in; other option values override saved True."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={"power_entity": "sensor.import_power", "flow_compatibility_enabled": True},
        options={"flow_compatibility_enabled": enabled},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_flow_power_compatibility",
    )
    assert (entity_id is not None) is (enabled is True)


def test_public_flow_configuration_is_separate_from_readings(hass):
    """Expose only boolean configuration answers, including options clearing."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "power_entity": "sensor.import_power",
            "production_power_entity": "sensor.missing",
            "production_energy_entity": "sensor.old",
            "flow_compatibility_enabled": True,
        },
        options={"production_energy_entity": None, "flow_compatibility_enabled": False},
    )
    coordinator = ElectricityProCoordinator(hass, entry)
    for channel in ("production", "grid_export", "household"):
        for quantity in ("power", "energy"):
            assert coordinator.is_flow_source_configured(channel, quantity) is (
                channel == "production" and quantity == "power"
            )
    assert coordinator.flow_compatibility_enabled is False
    with pytest.raises(KeyError):
        coordinator.is_flow_source_configured("unsupported", "energy")
    with pytest.raises(KeyError):
        coordinator.is_flow_source_configured("production", "unsupported")


async def test_sensor_setup_needs_no_private_coordinator_access(hass):
    """The platform can create flow entities using only the public interface."""
    entry = MockConfigEntry(domain=DOMAIN, data={
        "power_entity": "sensor.import_power",
        "production_power_entity": "sensor.missing_power",
        "household_energy_entity": "sensor.missing_energy",
        "flow_compatibility_enabled": True,
    })
    coordinator = ElectricityProCoordinator(hass, entry)

    class PublicCoordinator:
        """Forward public attributes but reject all private entity-layer access."""

        def __getattr__(self, name):
            assert not name.startswith("_"), f"Private coordinator access: {name}"
            return getattr(coordinator, name)

    entry.runtime_data = PublicCoordinator()
    entities = []
    await setup_sensors(hass, entry, entities.extend)
    unique_ids = {entity.unique_id for entity in entities}
    for suffix in (
        "production_power", "household_today", "household_this_month",
        "flow_power_compatibility",
    ):
        assert f"{entry.entry_id}_{suffix}" in unique_ids
    for suffix in ("production_today", "household_power", "grid_export_power"):
        assert f"{entry.entry_id}_{suffix}" not in unique_ids
