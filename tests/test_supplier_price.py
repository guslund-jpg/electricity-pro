"""Supplier price excludes grid charges and preserves source-price history."""

from dataclasses import replace
from decimal import Decimal

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.calculations import calculate_supplier_price
from custom_components.electricity_pro.forecast import NORDPOOL_MARKET_PRICE_METADATA
from custom_components.electricity_pro.pricing import (
    PriceComponent, PricingStrategy, VatTreatment,
)


@pytest.mark.parametrize("price,markup,expected", [
    ("2.99", "0.18", "3.9175"),
    ("2", "0", "2.50"),
    ("-1", "0.18", "-1.07"),
])
def test_market_supplier_price(price, markup, expected):
    metadata = replace(NORDPOOL_MARKET_PRICE_METADATA, vat_rate=Decimal(25))
    assert calculate_supplier_price(
        Decimal(price), metadata, Decimal(markup)
    ) == Decimal(expected)


def test_included_supplier_price_is_not_taxed_or_marked_up_again():
    metadata = replace(
        NORDPOOL_MARKET_PRICE_METADATA,
        strategy=PricingStrategy.SUPPLIER_CONTRACTED_PRICE,
        scope=replace(
            NORDPOOL_MARKET_PRICE_METADATA.scope,
            included=frozenset({PriceComponent.MARKET_ENERGY, PriceComponent.SUPPLIER_MARKUP}),
            vat=VatTreatment.INCLUDED,
        ),
        vat_rate=Decimal(25),
    )
    assert calculate_supplier_price(Decimal("3.92"), metadata, Decimal("0.18")) == Decimal("3.92")


@pytest.mark.parametrize("component", [PriceComponent.ENERGY_TAX, PriceComponent.VARIABLE_GRID_FEE])
def test_cannot_extract_supplier_price_from_combined_source(component):
    metadata = replace(
        NORDPOOL_MARKET_PRICE_METADATA,
        scope=replace(
            NORDPOOL_MARKET_PRICE_METADATA.scope,
            included=frozenset({PriceComponent.MARKET_ENERGY, component}),
        ),
        vat_rate=Decimal(25),
    )
    assert calculate_supplier_price(Decimal("2"), metadata, Decimal("0.18")) is None


def test_unknown_markup_or_vat_is_not_assumed():
    metadata = replace(NORDPOOL_MARKET_PRICE_METADATA, vat_rate=Decimal(25))
    assert calculate_supplier_price(Decimal("2"), metadata) is None
    assert calculate_supplier_price(Decimal("2"), NORDPOOL_MARKET_PRICE_METADATA, Decimal("0.18")) is None
    complete = replace(metadata, strategy=PricingStrategy.EXTERNAL_COMPLETE_PRICE)
    assert calculate_supplier_price(Decimal("2"), complete, Decimal("0.18")) is None


async def test_supplier_entity_updates_without_changing_source_or_effective_price(hass):
    hass.states.async_set("sensor.power", "1000", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.price", "2.99", {"unit_of_measurement": "SEK/kWh"})
    entry = MockConfigEntry(domain="electricity_pro", data={
        "power_entity": "sensor.power",
        "price_entity": "sensor.price",
        "pricing_strategy": "market_price_plus_tariff",
        "price_included_components": ["market_energy"],
        "price_vat_treatment": "excluded",
        "price_completeness": "partial",
        "price_vat_rate": 25,
        "supplier_markup_per_kwh": 0.18,
        "grid_fee_per_kwh": 0.5,
    })
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    supplier_id = "sensor.electricity_pro_current_supplier_price"
    source_id = "sensor.electricity_pro_current_price"
    effective_id = "sensor.electricity_pro_effective_price"
    assert Decimal(hass.states.get(supplier_id).state) == Decimal("3.9175")
    assert hass.states.get(supplier_id).attributes["vat_treatment"] == "included"
    assert Decimal(hass.states.get(source_id).state) == Decimal("2.99")
    assert Decimal(hass.states.get(effective_id).state) == Decimal("4.4175")

    hass.states.async_set("sensor.price", "2", {"unit_of_measurement": "SEK/kWh"})
    await hass.async_block_till_done()
    assert Decimal(hass.states.get(supplier_id).state) == Decimal("2.68")
    hass.states.async_set("sensor.price", "unavailable")
    await hass.async_block_till_done()
    assert hass.states.get(supplier_id).state == "unavailable"
