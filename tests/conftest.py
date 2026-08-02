"""Shared fixtures for Electricity Pro tests."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
    CONF_CURRENT_L1_ENTITY,
    CONF_CURRENT_L2_ENTITY,
    CONF_CURRENT_L3_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_PEAK_POWER_TODAY_ENTITY,
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
        accumulated_cost_today_value: str | None = None,
        accumulated_cost_today_unit: str = "SEK",
        peak_power_today_value: str | None = None,
        peak_power_today_unit: str = "W",
        current_l1_value: str | None = None,
        current_l2_value: str | None = None,
        current_l3_value: str | None = None,
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

        if accumulated_cost_today_value is not None:
            hass.states.async_set(
                "sensor.test_accumulated_cost_today",
                accumulated_cost_today_value,
                {
                    "unit_of_measurement": accumulated_cost_today_unit,
                    "device_class": "monetary",
                    "state_class": "total",
                },
            )
            entry_data[CONF_ACCUMULATED_COST_TODAY_ENTITY] = (
                "sensor.test_accumulated_cost_today"
            )

        if peak_power_today_value is not None:
            hass.states.async_set(
                "sensor.test_peak_power_today",
                peak_power_today_value,
                {
                    "unit_of_measurement": peak_power_today_unit,
                    "device_class": "power",
                },
            )
            entry_data[CONF_PEAK_POWER_TODAY_ENTITY] = "sensor.test_peak_power_today"

        if current_l1_value is not None:
            hass.states.async_set(
                "sensor.test_current_l1",
                current_l1_value,
                {
                    "unit_of_measurement": "A",
                    "device_class": "current",
                },
            )
            entry_data[CONF_CURRENT_L1_ENTITY] = "sensor.test_current_l1"

        if current_l2_value is not None:
            hass.states.async_set(
                "sensor.test_current_l2",
                current_l2_value,
                {
                    "unit_of_measurement": "A",
                    "device_class": "current",
                },
            )
            entry_data[CONF_CURRENT_L2_ENTITY] = "sensor.test_current_l2"

        if current_l3_value is not None:
            hass.states.async_set(
                "sensor.test_current_l3",
                current_l3_value,
                {
                    "unit_of_measurement": "A",
                    "device_class": "current",
                },
            )
            entry_data[CONF_CURRENT_L3_ENTITY] = "sensor.test_current_l3"

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
