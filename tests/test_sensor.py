"""Tests for Electricity Pro sensors."""

from decimal import Decimal

from homeassistant.core import HomeAssistant

from custom_components.electricity_pro.const import DOMAIN

ENTITY_ID = f"sensor.{DOMAIN}_current_power"
SOURCE_ENTITY_ID = "sensor.test_power"


async def test_current_power_initial_value(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Current power should use the initial source value."""

    await setup_electricity_pro(power_value="1234", power_unit="W")

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "1234"
    assert state.attributes["unit_of_measurement"] == "W"
    assert state.attributes["device_class"] == "power"


async def test_current_power_updates_when_source_changes(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Current power should update when the source changes."""

    await setup_electricity_pro(power_value="1000", power_unit="W")

    hass.states.async_set(
        SOURCE_ENTITY_ID,
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
    setup_electricity_pro,
) -> None:
    """Current power should convert kilowatts to watts."""

    await setup_electricity_pro(power_value="1.5", power_unit="kW")

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("1500")
    assert state.attributes["unit_of_measurement"] == "W"


async def test_current_power_becomes_unavailable(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Current power should become unavailable for an unknown source."""

    await setup_electricity_pro(power_value="1000", power_unit="W")

    hass.states.async_set(
        SOURCE_ENTITY_ID,
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

async def test_current_power_becomes_unavailable_for_invalid_value(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Current power should become unavailable for a non-numeric source."""

    await setup_electricity_pro(power_value="1000", power_unit="W")

    hass.states.async_set(
        SOURCE_ENTITY_ID,
        "not-a-number",
        {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"

PRICE_ENTITY_ID = f"sensor.{DOMAIN}_current_price"


async def test_current_price_initial_value(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Current price should use the configured price source."""

    await setup_electricity_pro(
        power_value="1000",
        power_unit="W",
        price_value="1.25",
        price_unit="SEK/kWh",
    )

    state = hass.states.get(PRICE_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("1.25")
    assert state.attributes["unit_of_measurement"] == "SEK/kWh"

async def test_current_price_updates_when_source_changes(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Current price should update when the source changes."""

    await setup_electricity_pro(
        power_value="1000",
        power_unit="W",
        price_value="1.25",
        price_unit="SEK/kWh",
    )

    hass.states.async_set(
        "sensor.test_price",
        "0.85",
        {
            "unit_of_measurement": "SEK/kWh",
            "device_class": "monetary",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(PRICE_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("0.85")
    assert state.attributes["unit_of_measurement"] == "SEK/kWh"
