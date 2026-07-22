"""Shared fixtures for Electricity Pro tests."""

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_POWER_ENTITY,
    DOMAIN,
)

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable custom integrations for every test."""

@pytest.fixture
def setup_electricity_pro(hass):
    """Set up Electricity Pro with a configurable power source."""

    async def _setup(
        value: str = "1234",
        unit: str = "W",
    ) -> MockConfigEntry:
        hass.states.async_set(
            "sensor.test_power",
            value,
            {
                "unit_of_measurement": unit,
                "device_class": "power",
            },
        )

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Electricity Pro",
            data={
                CONF_POWER_ENTITY: "sensor.test_power",
            },
        )

        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        return entry

    return _setup
