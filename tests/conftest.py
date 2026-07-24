"""Shared fixtures for Electricity Pro tests."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_ENERGY_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable custom integrations for every test."""


@pytest.fixture
def setup_electricity_pro(hass):
    """Set up Electricity Pro with configurable source sensors."""

    async def _setup(
        power_value: str = "1234",
        power_unit: str = "W",
        price_value: str | None = None,
        price_unit: str = "SEK/kWh",
        energy_value: str | None = None,
        energy_unit: str = "kWh",
    ) -> MockConfigEntry:
        """Create and set up an Electricity Pro config entry."""

        hass.states.async_set(
            "sensor.test_power",
            power_value,
            {
                "unit_of_measurement": power_unit,
                "device_class": "power",
            },
        )

        entry_data = {
            CONF_POWER_ENTITY: "sensor.test_power",
        }

        if price_value is not None:
            hass.states.async_set(
                "sensor.test_price",
                price_value,
                {
                    "unit_of_measurement": price_unit,
                    "device_class": "monetary",
                },
            )
            entry_data[CONF_PRICE_ENTITY] = "sensor.test_price"

        if energy_value is not None:
            hass.states.async_set(
                "sensor.test_energy",
                energy_value,
                {
                    "unit_of_measurement": energy_unit,
                    "device_class": "energy",
                    "state_class": "total_increasing",
                },
            )
            entry_data[CONF_ENERGY_ENTITY] = "sensor.test_energy"

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Electricity Pro",
            data=entry_data,
        )

        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        return entry

    return _setup
