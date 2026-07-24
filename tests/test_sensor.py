"""Tests for Electricity Pro sensors."""

from decimal import Decimal

from homeassistant.core import HomeAssistant

from custom_components.electricity_pro.const import DOMAIN

ENTITY_ID = f"sensor.{DOMAIN}_current_power"
SOURCE_ENTITY_ID = "sensor.test_power"

ENERGY_ENTITY_ID = f"sensor.{DOMAIN}_energy"
ENERGY_SOURCE_ENTITY_ID = "sensor.test_energy"


async def test_current_energy_initial_value(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Current energy should use the configured energy source."""

    await setup_electricity_pro(
        energy_value="12.5",
        energy_unit="kWh",
    )

    state = hass.states.get(ENERGY_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("12.5")
    assert state.attributes["unit_of_measurement"] == "kWh"
    assert state.attributes["device_class"] == "energy"
    assert state.attributes["state_class"] == "total_increasing"


async def test_current_energy_updates_when_source_changes(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Current energy should update when its source changes."""

    await setup_electricity_pro(
        energy_value="12.5",
        energy_unit="kWh",
    )

    hass.states.async_set(
        ENERGY_SOURCE_ENTITY_ID,
        "13.25",
        {
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENERGY_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("13.25")
    assert state.attributes["unit_of_measurement"] == "kWh"


async def test_current_energy_accepts_wh(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Current energy should accept watt-hours."""

    await setup_electricity_pro(
        energy_value="1250",
        energy_unit="Wh",
    )

    state = hass.states.get(ENERGY_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("1250")
    assert state.attributes["unit_of_measurement"] == "Wh"


async def test_current_energy_becomes_unavailable(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Current energy should become unavailable for an unknown source."""

    await setup_electricity_pro(
        energy_value="12.5",
        energy_unit="kWh",
    )

    hass.states.async_set(
        ENERGY_SOURCE_ENTITY_ID,
        "unknown",
        {
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENERGY_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_current_energy_rejects_invalid_unit(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Current energy should reject unsupported units."""

    await setup_electricity_pro(
        energy_value="12.5",
        energy_unit="kWh",
    )

    hass.states.async_set(
        ENERGY_SOURCE_ENTITY_ID,
        "12.6",
        {
            "unit_of_measurement": "J",
            "device_class": "energy",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENERGY_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"

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


async def test_current_price_becomes_unavailable(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Current price becomes unavailable when source is unknown."""

    await setup_electricity_pro(
        power_value="1000",
        power_unit="W",
        price_value="1.25",
        price_unit="SEK/kWh",
    )

    hass.states.async_set(
        "sensor.test_price",
        "unknown",
        {
            "unit_of_measurement": "SEK/kWh",
        },
    )

    await hass.async_block_till_done()

    state = hass.states.get(PRICE_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_current_price_invalid_value(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Invalid price should become unavailable."""

    await setup_electricity_pro(
        power_value="1000",
        power_unit="W",
        price_value="1.25",
        price_unit="SEK/kWh",
    )

    hass.states.async_set(
        "sensor.test_price",
        "banana",
        {
            "unit_of_measurement": "SEK/kWh",
        },
    )

    await hass.async_block_till_done()

    state = hass.states.get(PRICE_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_current_price_requires_unit(
    hass: HomeAssistant,
    setup_electricity_pro,
) -> None:
    """Price requires a unit of measurement."""

    await setup_electricity_pro(
        power_value="1000",
        power_unit="W",
        price_value="1.25",
        price_unit="SEK/kWh",
    )

    hass.states.async_set(
        "sensor.test_price",
        "0.85",
        {},
    )

    await hass.async_block_till_done()

    state = hass.states.get(PRICE_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"
