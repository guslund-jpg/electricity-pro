"""Tests for normalized pricing models."""

from dataclasses import FrozenInstanceError

import pytest

from custom_components.electricity_pro.pricing import (
    CostProvenance,
    PriceComponent,
    PriceComponentScope,
    PriceCompleteness,
    PricingMetadata,
    PricingStrategy,
    VatTreatment,
)


def test_pricing_strategy_values_are_storage_safe() -> None:
    """Strategy values should remain stable for future configuration storage."""
    assert PricingStrategy.SUPPLIER_CONTRACTED_PRICE == "supplier_contracted_price"
    assert PricingStrategy.MARKET_PRICE_PLUS_TARIFF == "market_price_plus_tariff"
    assert PricingStrategy.EXTERNAL_COMPLETE_PRICE == "external_complete_price"


def test_price_component_scope_normalizes_and_queries_components() -> None:
    """A scope should be immutable and expose explicit inclusion semantics."""
    scope = PriceComponentScope(
        included={PriceComponent.MARKET_ENERGY, PriceComponent.SUPPLIER_MARKUP},
        vat=VatTreatment.INCLUDED,
    )

    assert scope.included == frozenset(
        {PriceComponent.MARKET_ENERGY, PriceComponent.SUPPLIER_MARKUP}
    )
    assert scope.includes(PriceComponent.MARKET_ENERGY)
    assert not scope.includes(PriceComponent.ENERGY_TAX)
    assert scope.vat is VatTreatment.INCLUDED

    with pytest.raises(FrozenInstanceError):
        scope.vat = VatTreatment.EXCLUDED  # type: ignore[misc]


def test_price_component_scope_detects_overlap() -> None:
    """Overlapping scopes identify a potential double-counted component."""
    supplier = PriceComponentScope(
        frozenset({PriceComponent.MARKET_ENERGY, PriceComponent.SUPPLIER_MARKUP})
    )
    tax = PriceComponentScope(frozenset({PriceComponent.ENERGY_TAX}))
    complete = PriceComponentScope(
        frozenset({PriceComponent.MARKET_ENERGY, PriceComponent.ENERGY_TAX})
    )

    assert not supplier.overlaps(tax)
    assert supplier.overlaps(complete)
    assert tax.overlaps(complete)


def test_price_component_scope_rejects_unknown_components() -> None:
    """Unrecognized component strings must not silently enter the model."""
    with pytest.raises(ValueError, match="unsupported component"):
        PriceComponentScope(frozenset({"market_energy"}))  # type: ignore[arg-type]


def test_cost_provenance_values_are_storage_safe() -> None:
    """Cost provenance should distinguish source and local calculation."""
    assert CostProvenance.AUTHORITATIVE_SOURCE == "authoritative_source"
    assert CostProvenance.LOCALLY_CALCULATED == "locally_calculated"


def test_pricing_metadata_defaults_to_unknown_completeness() -> None:
    """Completeness must remain unknown until an adapter or user declares it."""
    metadata = PricingMetadata(
        strategy=PricingStrategy.SUPPLIER_CONTRACTED_PRICE,
        scope=PriceComponentScope(frozenset({PriceComponent.MARKET_ENERGY})),
    )

    assert metadata.completeness is PriceCompleteness.UNKNOWN
    assert not metadata.is_complete


def test_pricing_metadata_exposes_declared_completeness() -> None:
    """Complete metadata should be explicit and remain immutable."""
    metadata = PricingMetadata(
        strategy=PricingStrategy.MARKET_PRICE_PLUS_TARIFF,
        scope=PriceComponentScope(
            frozenset(
                {
                    PriceComponent.MARKET_ENERGY,
                    PriceComponent.SUPPLIER_MARKUP,
                    PriceComponent.ENERGY_TAX,
                    PriceComponent.VARIABLE_GRID_FEE,
                }
            ),
            vat=VatTreatment.INCLUDED,
        ),
        completeness=PriceCompleteness.COMPLETE,
    )

    assert metadata.is_complete

    with pytest.raises(FrozenInstanceError):
        metadata.completeness = PriceCompleteness.PARTIAL  # type: ignore[misc]
