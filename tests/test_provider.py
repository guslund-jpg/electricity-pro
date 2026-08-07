"""Tests for the Electricity Pro entity provider."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_CURRENT_L1_ENTITY,
    CONF_CURRENT_L2_ENTITY,
    CONF_CURRENT_L3_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
    CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
    CONF_PEAK_POWER_TODAY_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
    CONF_VOLTAGE_L1_ENTITY,
    CONF_VOLTAGE_L2_ENTITY,
    CONF_VOLTAGE_L3_ENTITY,
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
    include_peak_power_today: bool = False,
    include_phase_currents: bool = False,
    include_phase_voltages: bool = False,
    include_monthly_peak_hour_consumption: bool = False,
    include_monthly_peak_hour_time: bool = False,
) -> ElectricityProEntityProvider:
    "Create a provider with configurable source entities."
    entry_data = {
        CONF_POWER_ENTITY: "sensor.test_power",
    }

    if include_price:
        entry_data[CONF_PRICE_ENTITY] = "sensor.test_price"

    if include_energy:
        entry_data[CONF_ENERGY_ENTITY] = "sensor.test_energy"

    if include_peak_power_today:
        entry_data[CONF_PEAK_POWER_TODAY_ENTITY] = "sensor.test_peak_power_today"

    if include_phase_currents:
        entry_data[CONF_CURRENT_L1_ENTITY] = "sensor.test_current_l1"
        entry_data[CONF_CURRENT_L2_ENTITY] = "sensor.test_current_l2"
        entry_data[CONF_CURRENT_L3_ENTITY] = "sensor.test_current_l3"
    if include_phase_voltages:
        entry_data[CONF_VOLTAGE_L1_ENTITY] = "sensor.test_voltage_l1"
        entry_data[CONF_VOLTAGE_L2_ENTITY] = "sensor.test_voltage_l2"
        entry_data[CONF_VOLTAGE_L3_ENTITY] = "sensor.test_voltage_l3"
    if include_monthly_peak_hour_consumption:
        entry_data[CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY] = (
            "sensor.test_monthly_peak_hour_consumption"
        )
    if include_monthly_peak_hour_time:
        entry_data[CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY] = (
            "sensor.test_monthly_peak_hour_time"
        )

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

    assert data.current_power == Decimal(1500)
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


def test_peak_power_today_source_entity_id(
    hass: HomeAssistant,
) -> None:
    """Provider should expose the configured peak-power source."""
    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_peak_power_today=True,
    )

    assert provider.source_entity_ids == (
        "sensor.test_power",
        "sensor.test_peak_power_today",
    )


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        ("4200", "W", Decimal(4200)),
        ("4.2", "kW", Decimal(4200)),
    ],
)
def test_valid_peak_power_today_values(
    hass: HomeAssistant,
    value: str,
    unit: str,
    expected: Decimal,
) -> None:
    """Provider should normalize daily peak power to watts."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_peak_power_today",
        value,
        {"unit_of_measurement": unit},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_peak_power_today=True,
    )

    assert provider.read().peak_power_today == expected


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        ("unknown", "W"),
        ("unavailable", "W"),
        ("not-a-number", "W"),
        ("-1", "W"),
        ("4200", "V"),
        ("NaN", "W"),
        ("Infinity", "W"),
    ],
)
def test_invalid_peak_power_today_returns_none(
    hass: HomeAssistant,
    value: str,
    unit: str,
) -> None:
    """Invalid daily peak-power values should normalize to None."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_peak_power_today",
        value,
        {"unit_of_measurement": unit},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_peak_power_today=True,
    )

    assert provider.read().peak_power_today is None


def test_phase_current_source_entity_ids(
    hass: HomeAssistant,
) -> None:
    """Provider should expose all configured phase-current sources."""
    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_phase_currents=True,
    )

    assert provider.source_entity_ids == (
        "sensor.test_power",
        "sensor.test_current_l1",
        "sensor.test_current_l2",
        "sensor.test_current_l3",
    )


def test_read_valid_phase_currents(
    hass: HomeAssistant,
) -> None:
    """Provider should normalize all configured phase currents."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_current_l1",
        "4.5",
        {"unit_of_measurement": "A"},
    )
    hass.states.async_set(
        "sensor.test_current_l2",
        "5.25",
        {"unit_of_measurement": "A"},
    )
    hass.states.async_set(
        "sensor.test_current_l3",
        "6.75",
        {"unit_of_measurement": "A"},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_phase_currents=True,
    )
    data = provider.read()

    assert data.current_l1 == Decimal("4.5")
    assert data.current_l2 == Decimal("5.25")
    assert data.current_l3 == Decimal("6.75")


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        ("12.5", "A", Decimal("12.5")),
        ("12500", "mA", Decimal("12.5")),
    ],
)
def test_valid_phase_current_units(
    hass: HomeAssistant,
    value: str,
    unit: str,
    expected: Decimal,
) -> None:
    """Provider should normalize amperes and milliamperes to amperes."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_current_l1",
        value,
        {"unit_of_measurement": unit},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_phase_currents=True,
    )

    assert provider.read().current_l1 == expected


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        ("unknown", "A"),
        ("unavailable", "A"),
        ("not-a-number", "A"),
        ("-1", "A"),
        ("12.5", "V"),
        ("12.5", ""),
        ("NaN", "A"),
        ("Infinity", "A"),
    ],
)
def test_invalid_phase_current_returns_none(
    hass: HomeAssistant,
    value: str,
    unit: str,
) -> None:
    """Invalid phase-current values should normalize to None."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_current_l1",
        value,
        {"unit_of_measurement": unit},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_phase_currents=True,
    )

    assert provider.read().current_l1 is None


def test_unconfigured_phase_currents_are_none(
    hass: HomeAssistant,
) -> None:
    """Unconfigured phase-current values should remain unavailable."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
    )
    data = provider.read()

    assert data.current_l1 is None
    assert data.current_l2 is None
    assert data.current_l3 is None


def test_phase_voltage_source_entity_ids(
    hass: HomeAssistant,
) -> None:
    """Provider should expose all configured phase-voltage sources."""
    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_phase_voltages=True,
    )

    assert provider.source_entity_ids == (
        "sensor.test_power",
        "sensor.test_voltage_l1",
        "sensor.test_voltage_l2",
        "sensor.test_voltage_l3",
    )


def test_read_valid_phase_voltages(
    hass: HomeAssistant,
) -> None:
    """Provider should normalize all configured phase voltages."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_voltage_l1",
        "231.4",
        {"unit_of_measurement": "V"},
    )
    hass.states.async_set(
        "sensor.test_voltage_l2",
        "232.1",
        {"unit_of_measurement": "V"},
    )
    hass.states.async_set(
        "sensor.test_voltage_l3",
        "230.8",
        {"unit_of_measurement": "V"},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_phase_voltages=True,
    )
    data = provider.read()

    assert data.voltage_l1 == Decimal("231.4")
    assert data.voltage_l2 == Decimal("232.1")
    assert data.voltage_l3 == Decimal("230.8")


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        ("236.2", "V", Decimal("236.2")),
        ("236200", "mV", Decimal("236.2")),
    ],
)
def test_valid_phase_voltage_units(
    hass: HomeAssistant,
    value: str,
    unit: str,
    expected: Decimal,
) -> None:
    """Provider should normalize volts and millivolts to volts."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_voltage_l1",
        value,
        {"unit_of_measurement": unit},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_phase_voltages=True,
    )

    assert provider.read().voltage_l1 == expected


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        ("unknown", "V"),
        ("unavailable", "V"),
        ("not-a-number", "V"),
        ("-1", "V"),
        ("230", "A"),
        ("230", ""),
        ("NaN", "V"),
        ("Infinity", "V"),
    ],
)
def test_invalid_phase_voltage_returns_none(
    hass: HomeAssistant,
    value: str,
    unit: str,
) -> None:
    """Invalid phase-voltage values should normalize to None."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_voltage_l1",
        value,
        {"unit_of_measurement": unit},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_phase_voltages=True,
    )

    assert provider.read().voltage_l1 is None


def test_unconfigured_phase_voltages_are_none(
    hass: HomeAssistant,
) -> None:
    """Unconfigured phase-voltage values should remain unavailable."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
    )
    data = provider.read()

    assert data.voltage_l1 is None
    assert data.voltage_l2 is None
    assert data.voltage_l3 is None


def test_monthly_peak_hour_consumption_source_entity_id(
    hass: HomeAssistant,
) -> None:
    """Provider should expose the configured monthly peak-hour source."""
    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_monthly_peak_hour_consumption=True,
    )

    assert provider.source_entity_ids == (
        "sensor.test_power",
        "sensor.test_monthly_peak_hour_consumption",
    )


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        ("2450", "Wh"),
        ("2.45", "kWh"),
    ],
)
def test_valid_monthly_peak_hour_consumption(
    hass: HomeAssistant,
    value: str,
    unit: str,
) -> None:
    """Provider should accept supported monthly peak-hour energy units."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_monthly_peak_hour_consumption",
        value,
        {"unit_of_measurement": unit},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_monthly_peak_hour_consumption=True,
    )
    data = provider.read()

    assert data.monthly_peak_hour_consumption == Decimal(value)
    assert data.monthly_peak_hour_consumption_unit == unit


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        ("unknown", "kWh"),
        ("unavailable", "kWh"),
        ("banana", "kWh"),
        ("-1", "kWh"),
        ("2.45", "W"),
        ("2.45", ""),
        ("NaN", "kWh"),
        ("Infinity", "kWh"),
    ],
)
def test_invalid_monthly_peak_hour_consumption_returns_none(
    hass: HomeAssistant,
    value: str,
    unit: str,
) -> None:
    """Invalid monthly peak-hour values should normalize to None."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_monthly_peak_hour_consumption",
        value,
        {"unit_of_measurement": unit},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_monthly_peak_hour_consumption=True,
    )
    data = provider.read()

    assert data.monthly_peak_hour_consumption is None
    assert data.monthly_peak_hour_consumption_unit is None


def test_unconfigured_monthly_peak_hour_consumption_is_none(
    hass: HomeAssistant,
) -> None:
    """Unconfigured monthly peak-hour consumption should remain unavailable."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
    )
    data = provider.read()

    assert data.monthly_peak_hour_consumption is None
    assert data.monthly_peak_hour_consumption_unit is None


def test_valid_monthly_peak_hour_time(hass: HomeAssistant) -> None:
    """Provider should normalize a configured monthly peak-hour timestamp."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_monthly_peak_hour_time",
        "2026-08-03T17:00:00+02:00",
        {"device_class": "timestamp"},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_monthly_peak_hour_time=True,
    )

    assert provider.source_entity_ids == (
        "sensor.test_power",
        "sensor.test_monthly_peak_hour_time",
    )
    assert provider.read().monthly_peak_hour_time == datetime(
        2026, 8, 3, 15, tzinfo=UTC
    )


@pytest.mark.parametrize(
    "value",
    ["unknown", "unavailable", "not-a-timestamp", "2026-08-03T17:00:00"],
)
def test_invalid_monthly_peak_hour_time_returns_none(
    hass: HomeAssistant,
    value: str,
) -> None:
    """Provider should reject missing, invalid, and timezone-naive timestamps."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    hass.states.async_set(
        "sensor.test_monthly_peak_hour_time",
        value,
        {"device_class": "timestamp"},
    )

    provider = _create_provider(
        hass,
        include_price=False,
        include_energy=False,
        include_monthly_peak_hour_time=True,
    )

    assert provider.read().monthly_peak_hour_time is None
