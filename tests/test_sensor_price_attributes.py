"""Characterize the public live-price attributes before and after extraction."""

from dataclasses import replace
from decimal import Decimal

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.pricing import (
    PriceComponent,
    PriceComponentScope,
    PriceCompleteness,
    PricingMetadata,
    PricingStrategy,
    VatTreatment,
)
from custom_components.electricity_pro.provider import ElectricityProEntityProvider
from custom_components.electricity_pro.sensor import (
    SENSOR_DESCRIPTIONS,
    ElectricityProSensor,
)

_METADATA = PricingMetadata(
    strategy=PricingStrategy.MARKET_PRICE_PLUS_TARIFF,
    scope=PriceComponentScope(
        included=frozenset({PriceComponent.MARKET_ENERGY}),
        vat=VatTreatment.EXCLUDED,
    ),
    completeness=PriceCompleteness.PARTIAL,
    vat_rate=Decimal("25.00"),
)
_SUPPLIER_ATTRIBUTES = {
    "price_components": ["market_energy", "supplier_markup"],
    "vat_treatment": "included",
    "price_completeness": "partial",
}


@pytest.fixture
def price_sensor(hass):
    """Build real sensor entities over an explicitly controlled snapshot."""
    entry = MockConfigEntry(domain=DOMAIN, data={"power_entity": "sensor.power"})
    coordinator = ElectricityProCoordinator(hass, entry)
    data = replace(
        ElectricityProEntityProvider(hass, entry).read(),
        current_price=Decimal("2"),
        current_price_unit="SEK/kWh",
        pricing_metadata=_METADATA,
        supplier_markup_per_kwh=Decimal("0.18"),
        grid_fee_per_kwh=Decimal("0.50"),
        energy_tax_per_kwh=Decimal("0.10"),
    )

    def create(key, **updates):
        coordinator.async_set_updated_data(replace(data, **updates))
        description = next(item for item in SENSOR_DESCRIPTIONS if item.key == key)
        return ElectricityProSensor(coordinator, entry, description)

    return create


@pytest.mark.parametrize(
    "updates,expected",
    [
        pytest.param({}, "2.6800", id="excluded-vat"),
        pytest.param({"current_price": Decimal("-1")}, "-1.0700", id="negative"),
        pytest.param(
            {"current_price": Decimal(0), "supplier_markup_per_kwh": Decimal(0)},
            "0",
            id="zero",
        ),
        pytest.param(
            {
                "pricing_metadata": replace(
                    _METADATA,
                    scope=PriceComponentScope(
                        included=frozenset(
                            {
                                PriceComponent.MARKET_ENERGY,
                                PriceComponent.SUPPLIER_MARKUP,
                            }
                        ),
                        vat=VatTreatment.INCLUDED,
                    ),
                )
            },
            "2",
            id="markup-already-included",
        ),
        pytest.param({"pricing_metadata": None}, None, id="missing-metadata"),
        pytest.param({"current_price": None}, None, id="missing-price"),
        pytest.param({"supplier_markup_per_kwh": None}, None, id="unknown-markup"),
        pytest.param(
            {"pricing_metadata": replace(_METADATA, vat_rate=None)},
            None,
            id="missing-vat-rate",
        ),
        pytest.param(
            {
                "pricing_metadata": replace(
                    _METADATA, strategy=PricingStrategy.EXTERNAL_COMPLETE_PRICE
                )
            },
            None,
            id="external-complete-price",
        ),
        *[
            pytest.param(
                {
                    "pricing_metadata": replace(
                        _METADATA,
                        scope=replace(
                            _METADATA.scope,
                            included=frozenset(
                                {PriceComponent.MARKET_ENERGY, component}
                            ),
                        ),
                    )
                },
                None,
                id=f"includes-{component.value}",
            )
            for component in (
                PriceComponent.VARIABLE_GRID_FEE,
                PriceComponent.ENERGY_TAX,
            )
        ],
    ],
)
def test_supplier_price_attributes_follow_identifiable_supplier_value(
    price_sensor, updates, expected
):
    """Publish the exact known/unknown payload, including while unavailable."""
    sensor = price_sensor("current_supplier_price", **updates)
    value = None if expected is None else Decimal(expected)
    assert sensor.native_value == value
    assert value is None or isinstance(sensor.native_value, Decimal)
    assert sensor.available is (value is not None)
    assert sensor.extra_state_attributes == (
        {"price_completeness": "unknown"} if value is None else _SUPPLIER_ATTRIBUTES
    )


@pytest.mark.parametrize(
    "metadata,price,expected,source_vat,rate,required",
    [
        pytest.param(
            _METADATA, "2", "3.2800", "excluded", "25.00", False, id="excluded"
        ),
        pytest.param(
            replace(
                _METADATA, scope=replace(_METADATA.scope, vat=VatTreatment.INCLUDED)
            ),
            "2",
            "2.78",
            "included",
            "25.00",
            False,
            id="included",
        ),
        pytest.param(
            replace(_METADATA, vat_rate=Decimal(0)),
            "0",
            "0.78",
            "excluded",
            "0",
            False,
            id="zero-rate",
        ),
        pytest.param(
            _METADATA, "-1", "-0.4700", "excluded", "25.00", False, id="negative"
        ),
        pytest.param(
            _METADATA, None, None, "excluded", "25.00", False, id="missing-price"
        ),
        pytest.param(
            replace(
                _METADATA, scope=replace(_METADATA.scope, vat=VatTreatment.UNKNOWN)
            ),
            "2",
            None,
            "unknown",
            "25.00",
            True,
            id="unknown-vat",
        ),
        pytest.param(
            replace(_METADATA, vat_rate=None),
            "2",
            None,
            "excluded",
            None,
            True,
            id="missing-rate",
        ),
        pytest.param(
            replace(_METADATA, vat_rate=Decimal(101)),
            "2",
            None,
            "excluded",
            "101",
            False,
            id="invalid-rate",
        ),
    ],
)
def test_effective_price_attributes_preserve_vat_explanations(
    price_sensor, metadata, price, expected, source_vat, rate, required
):
    """Keep serialized rates and configuration hints distinct from availability."""
    sensor = price_sensor(
        "effective_price",
        pricing_metadata=metadata,
        current_price=None if price is None else Decimal(price),
    )
    value = None if expected is None else Decimal(expected)
    assert sensor.native_value == value
    assert value is None or isinstance(sensor.native_value, Decimal)
    assert sensor.available is (value is not None)
    assert sensor.extra_state_attributes == {
        "source_vat_treatment": source_vat,
        "vat_rate_percent": rate,
        "vat_treatment": "unknown" if value is None else "included",
        "vat_configuration_required": required,
    }


def test_effective_price_without_metadata_has_no_attributes(price_sensor):
    sensor = price_sensor("effective_price", pricing_metadata=None)
    assert sensor.native_value is None
    assert sensor.available is False
    assert sensor.extra_state_attributes is None


@pytest.mark.parametrize("key", ["current_supplier_price", "effective_price"])
def test_price_attributes_do_not_depend_on_unit_or_coordinator_availability(
    price_sensor, key
):
    """Availability guards must not silently alter otherwise known attributes."""
    sensor = price_sensor(key)
    expected = sensor.extra_state_attributes
    value = sensor.native_value
    sensor.coordinator.data = replace(sensor.coordinator.data, current_price_unit=None)
    assert sensor.available is False
    assert sensor.native_value == value
    assert sensor.extra_state_attributes == expected
    sensor.coordinator.data = replace(
        sensor.coordinator.data, current_price_unit="SEK/kWh"
    )
    sensor.coordinator.last_update_success = False
    assert sensor.available is False
    assert sensor.extra_state_attributes == expected


def test_supplier_attribute_containers_are_fresh(price_sensor):
    sensor = price_sensor("current_supplier_price")
    attributes = sensor.extra_state_attributes
    attributes["price_components"].append("unexpected")
    assert sensor.extra_state_attributes == _SUPPLIER_ATTRIBUTES


async def test_published_price_attributes_and_identity_survive_updates_and_reload(
    hass, setup_electricity_pro
):
    """Exercise HA publication, missing input, recovery and registry continuity."""
    entry = await setup_electricity_pro(
        price_value="1.23456789012345",
        supplier_markup_per_kwh=0.18,
        grid_fee_per_kwh=0.5,
    )
    expected_attributes = {
        "current_supplier_price": _SUPPLIER_ATTRIBUTES,
        "effective_price": {
            "source_vat_treatment": "included",
            "vat_rate_percent": None,
            "vat_treatment": "included",
            "vat_configuration_required": False,
        },
    }
    registry = er.async_get(hass)
    saved_settings = (dict(entry.data), dict(entry.options))

    def assert_prices(supplier, effective):
        for key, expected in (
            ("current_supplier_price", supplier),
            ("effective_price", effective),
        ):
            entity_id = f"sensor.{DOMAIN}_{key}"
            assert registry.async_get(entity_id).unique_id == f"{entry.entry_id}_{key}"
            state = hass.states.get(entity_id)
            assert Decimal(state.state) == Decimal(expected)
            assert state.attributes["unit_of_measurement"] == "SEK/kWh"
            assert {
                name: state.attributes[name] for name in expected_attributes[key]
            } == expected_attributes[key]

    assert_prices("1.41456789012345", "1.91456789012345")
    hass.states.async_set("sensor.test_price", "unavailable")
    await hass.async_block_till_done()
    for key in expected_attributes:
        assert hass.states.get(f"sensor.{DOMAIN}_{key}").state == "unavailable"

    hass.states.async_set("sensor.test_price", "-1", {"unit_of_measurement": "SEK/kWh"})
    await hass.async_block_till_done()
    assert_prices("-0.82", "-0.32")
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert_prices("-0.82", "-0.32")
    assert (dict(entry.data), dict(entry.options)) == saved_settings
