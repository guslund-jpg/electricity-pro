"""Tests for Electricity Pro integration setup."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_POWER_ENTITY,
    DOMAIN,
)

ENTITY_ID = "sensor.electricity_pro_current_power"


async def test_setup_and_unload_entry(
    hass: HomeAssistant,
) -> None:
    """Test setting up and unloading Electricity Pro."""
    source_entity_id = "sensor.test_power"

    hass.states.async_set(
        source_entity_id,
        "1000",
        {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: source_entity_id,
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(ENTITY_ID) is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED

    state = hass.states.get(ENTITY_ID)

    if state is not None:
        assert state.state == "unavailable"
        assert state.attributes.get("restored") is True
