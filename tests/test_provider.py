"""Tests for the Electricity Pro entity provider."""

from decimal import Decimal

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_ENERGY_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
    DOMAIN,
)
from custom_components.electricity_pro.provider import (
    ElectricityProEntityProvider,
)


def _create_provider(
    hass: HomeAssistant,
    *,
    include_price: bool = True,
    include_energy: bool = True,
) -> ElectricityProEntityProvider:
    """Create a provider with configurable source entities."""
    entry_data = {
        CONF_POWER_ENTITY: "sensor.test_power",
    }

    if include_price:
        entry_data[CONF_PRICE_ENTITY] = "sensor.test_price"

    if include_energy:
        entry_data[CONF_ENERGY_ENTITY] = "sensor.test_energy"

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data=entry_data,
    )

    return ElectricityProEntityProvider(hass, entry)


def test_source_entity_ids(
    hass: HomeAssistant,
) -> None:
    """Provider should expose all configured source entity IDs."""
    provider = _create_provider(hass)

    assert provider.source_entity_ids == (
        "sensor.test_power",
        "sensor.test_price",
        "sensor.test_energy",
    )


def test_optional_source_entity_ids(
    hass: HomeAssistant,
) -> None:
    """Provider should omit unconfigured optional sources."""
    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
    )

    assert provider.source_entity_ids == ("sensor.test_power",)


def test_read_valid_sources(
    hass: HomeAssistant,
) -> None:
    """Provider should normalize configured source values."""
    hass.states.async_set(
        "sensor.test_power",
        "1.5",
        {"unit_of_measurement": "kW"},
    )
    hass.states.async_set(
        "sensor.test_price",
        "1.25",
        {"unit_of_measurement": "SEK/kWh"},
    )
    hass.states.async_set(
        "sensor.test_energy",
        "12.5",
        {"unit_of_measurement": "kWh"},
    )

    provider = _create_provider(hass)
    data = provider.read()

    assert data.current_power == Decimal("1500")
    assert data.current_price == Decimal("1.25")
    assert data.current_price_unit == "SEK/kWh"
    assert data.current_energy == Decimal("12.5")
    assert data.current_energy_unit == "kWh"


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        ("unknown", "W"),
        ("unavailable", "W"),
        ("not-a-number", "W"),
        ("-1", "W"),
        ("1000", "V"),
        ("NaN", "W"),
        ("Infinity", "W"),
    ],
)
def test_invalid_power_returns_none(
    hass: HomeAssistant,
    value: str,
    unit: str,
) -> None:
    """Invalid power values should normalize to None."""
    hass.states.async_set(
        "sensor.test_power",
        value,
        {"unit_of_measurement": unit},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
    )

    assert provider.read().current_power is None


@pytest.mark.parametrize(
    ("value", "attributes"),
    [
        ("unknown", {"unit_of_measurement": "SEK/kWh"}),
        ("unavailable", {"unit_of_measurement": "SEK/kWh"}),
        ("banana", {"unit_of_measurement": "SEK/kWh"}),
        ("-1", {"unit_of_measurement": "SEK/kWh"}),
        ("1.25", {}),
        ("NaN", {"unit_of_measurement": "SEK/kWh"}),
        ("Infinity", {"unit_of_measurement": "SEK/kWh"}),
    ],
)
def test_invalid_price_returns_none(
    hass: HomeAssistant,
    value: str,
    attributes: dict[str, str],
) -> None:
    """Invalid price values should normalize to None."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_price",
        value,
        attributes,
    )

    provider = _create_provider(
        hass,
        include_energy=False,
    )
    data = provider.read()

    assert data.current_price is None
    assert data.current_price_unit is None


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        ("unknown", "kWh"),
        ("unavailable", "kWh"),
        ("banana", "kWh"),
        ("-1", "kWh"),
        ("1.5", "J"),
        ("1.5", ""),
        ("NaN", "kWh"),
        ("Infinity", "kWh"),
    ],
)
def test_invalid_energy_returns_none(
    hass: HomeAssistant,
    value: str,
    unit: str,
) -> None:
    """Invalid energy values should normalize to None."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_energy",
        value,
        {"unit_of_measurement": unit},
    )

    provider = _create_provider(
        hass,
        include_price=False,
    )
    data = provider.read()

    assert data.current_energy is None
    assert data.current_energy_unit is None


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        ("1250", "Wh"),
        ("1.25", "kWh"),
    ],
)
def test_valid_energy_units(
    hass: HomeAssistant,
    value: str,
    unit: str,
) -> None:
    """Provider should accept watt-hours and kilowatt-hours."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_energy",
        value,
        {"unit_of_measurement": unit},
    )

    provider = _create_provider(
        hass,
        include_price=False,
    )
    data = provider.read()

    assert data.current_energy == Decimal(value)
    assert data.current_energy_unit == unit
