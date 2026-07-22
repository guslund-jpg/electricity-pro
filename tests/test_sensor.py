"""Tests for Electricity Pro sensors."""

from decimal import Decimal

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_POWER_ENTITY,
    DOMAIN,
)

ENTITY_ID = "sensor.electricity_pro_current_power"


async def test_current_power_initial_value(
    hass: HomeAssistant,
) -> None:
    """Current power should reflect the configured source sensor."""

    hass.states.async_set(
        "sensor.test_power",
        "1234",
        {
            "unit_of_measurement": "W",
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

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "1234"
    assert state.attributes["unit_of_measurement"] == "W"
    assert state.attributes["device_class"] == "power"

async def test_current_power_updates_when_source_changes(
    hass: HomeAssistant,
) -> None:
    """Current power should update when the source sensor changes."""

    hass.states.async_set(
        "sensor.test_power",
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
            CONF_POWER_ENTITY: "sensor.test_power",
        },
    )

    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "1000"

    hass.states.async_set(
        "sensor.test_power",
        "850",
        {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
    )

    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "850"

async def test_current_power_converts_kw_to_w(
    hass: HomeAssistant,
) -> None:
    """Current power should convert kilowatts to watts."""

    hass.states.async_set(
        "sensor.test_power",
        "1.5",
        {
            "unit_of_measurement": "kW",
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

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("1500")
    assert state.attributes["unit_of_measurement"] == "W"

async def test_current_power_becomes_unavailable(
    hass: HomeAssistant,
) -> None:
    """Current power should become unavailable when the source is unknown."""

    hass.states.async_set(
        "sensor.test_power",
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
            CONF_POWER_ENTITY: "sensor.test_power",
        },
    )

    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    hass.states.async_set(
        "sensor.test_power",
        "unknown",
        {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
    )

    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"
