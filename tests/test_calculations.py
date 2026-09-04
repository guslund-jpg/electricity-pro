"""Tests for Electricity Pro calculations."""

from decimal import Decimal

import pytest

from custom_components.electricity_pro.calculations import (
    calculate_consumption_weighted_average_price,
    calculate_current_cost_rate,
    calculate_declared_effective_price,
    calculate_normalized_effective_price,
    effective_price_metadata,
)
from custom_components.electricity_pro.pricing import (
    PriceComponent,
    PriceComponentScope,
    PriceCompleteness,
    PricingMetadata,
    PricingStrategy,
    VatTreatment,
)


def test_calculate_normalized_effective_price_adds_missing_components() -> None:
    """The normalized path should add only declared missing components."""
    metadata = PricingMetadata(
        strategy=PricingStrategy.MARKET_PRICE_PLUS_TARIFF,
        scope=PriceComponentScope(frozenset({PriceComponent.MARKET_ENERGY})),
        completeness=PriceCompleteness.PARTIAL,
    )

    assert calculate_normalized_effective_price(
        Decimal("0.80"),
        metadata,
        {
            PriceComponent.SUPPLIER_MARKUP: Decimal("0.05"),
            PriceComponent.ENERGY_TAX: Decimal("0.45"),
        },
    ) == Decimal("1.30")


def test_calculate_normalized_effective_price_rejects_overlap() -> None:
    """A component already in the source must not be counted twice."""
    metadata = PricingMetadata(
        strategy=PricingStrategy.SUPPLIER_CONTRACTED_PRICE,
        scope=PriceComponentScope(
            frozenset(
                {PriceComponent.MARKET_ENERGY, PriceComponent.SUPPLIER_MARKUP}
            )
        ),
        completeness=PriceCompleteness.PARTIAL,
    )

    assert (
        calculate_normalized_effective_price(
            Decimal("0.85"),
            metadata,
            {PriceComponent.SUPPLIER_MARKUP: Decimal("0.05")},
        )
        is None
    )


def test_calculate_normalized_effective_price_respects_complete_source() -> None:
    """A complete external price must not receive extra components."""
    metadata = PricingMetadata(
        strategy=PricingStrategy.EXTERNAL_COMPLETE_PRICE,
        scope=PriceComponentScope(
            frozenset(
                {
                    PriceComponent.MARKET_ENERGY,
                    PriceComponent.SUPPLIER_MARKUP,
                    PriceComponent.ENERGY_TAX,
                    PriceComponent.VARIABLE_GRID_FEE,
                }
            )
        ),
        completeness=PriceCompleteness.COMPLETE,
    )

    assert calculate_normalized_effective_price(Decimal("1.50"), metadata) == Decimal(
        "1.50"
    )
    assert (
        calculate_normalized_effective_price(
            Decimal("1.50"),
            metadata,
            {PriceComponent.ENERGY_TAX: Decimal("0.45")},
        )
        is None
    )


@pytest.mark.parametrize(
    ("base_price", "adjustments"),
    [
        (None, {}),
        (Decimal("NaN"), {}),
        (Decimal("0.80"), {PriceComponent.ENERGY_TAX: Decimal("NaN")}),
        (Decimal("0.80"), {PriceComponent.ENERGY_TAX: Decimal("-0.01")}),
    ],
)
def test_calculate_normalized_effective_price_rejects_invalid_values(
    base_price: Decimal | None,
    adjustments: dict[PriceComponent, Decimal],
) -> None:
    """Invalid prices and adjustments should produce no result."""
    metadata = PricingMetadata(
        strategy=PricingStrategy.MARKET_PRICE_PLUS_TARIFF,
        scope=PriceComponentScope(frozenset({PriceComponent.MARKET_ENERGY})),
    )

    assert calculate_normalized_effective_price(
        base_price, metadata, adjustments
    ) is None


def test_calculate_normalized_effective_price_accepts_negative_base() -> None:
    """Non-negative tariff components should be added to a signed base price."""
    metadata = PricingMetadata(
        strategy=PricingStrategy.MARKET_PRICE_PLUS_TARIFF,
        scope=PriceComponentScope(frozenset({PriceComponent.MARKET_ENERGY})),
    )

    assert calculate_normalized_effective_price(
        Decimal("-0.50"),
        metadata,
        {PriceComponent.ENERGY_TAX: Decimal("0.20")},
    ) == Decimal("-0.30")


def test_calculate_consumption_weighted_average_price() -> None:
    """Calculate achieved average price with adjustments applied once."""
    assert calculate_consumption_weighted_average_price(
        Decimal("12"),
        Decimal("10"),
        "kWh",
        Decimal("0.25"),
    ) == Decimal("1.45")


def test_explicit_energy_tax_is_added_to_effective_prices() -> None:
    """Grid-side energy tax should be added exactly once."""
    metadata = PricingMetadata(
        strategy=PricingStrategy.SUPPLIER_CONTRACTED_PRICE,
        scope=PriceComponentScope(
            frozenset(
                {PriceComponent.MARKET_ENERGY, PriceComponent.SUPPLIER_MARKUP}
            )
        ),
        completeness=PriceCompleteness.PARTIAL,
    )
    assert calculate_declared_effective_price(
        Decimal("1.00"), metadata, Decimal("0.10"), Decimal("0.45")
    ) == Decimal("1.55")


def test_supplier_markup_is_added_only_when_missing_from_source() -> None:
    """Configured supplier markup should enrich raw market prices only once."""
    market_metadata = PricingMetadata(
        strategy=PricingStrategy.MARKET_PRICE_PLUS_TARIFF,
        scope=PriceComponentScope(frozenset({PriceComponent.MARKET_ENERGY})),
        completeness=PriceCompleteness.PARTIAL,
    )
    contracted_metadata = PricingMetadata(
        strategy=PricingStrategy.SUPPLIER_CONTRACTED_PRICE,
        scope=PriceComponentScope(
            frozenset(
                {PriceComponent.MARKET_ENERGY, PriceComponent.SUPPLIER_MARKUP}
            )
        ),
        completeness=PriceCompleteness.PARTIAL,
    )

    assert calculate_declared_effective_price(
        Decimal("0.80"),
        market_metadata,
        supplier_markup_per_kwh=Decimal("0.08"),
    ) == Decimal("0.88")
    assert calculate_declared_effective_price(
        Decimal("0.88"),
        contracted_metadata,
        supplier_markup_per_kwh=Decimal("0.08"),
    ) == Decimal("0.88")
    assert calculate_consumption_weighted_average_price(
        Decimal("10"), Decimal("10"), "kWh", Decimal("0.10"), Decimal("0.45")
    ) == Decimal("1.55")


def test_effective_price_metadata_becomes_complete_after_composition() -> None:
    """Configured missing components should complete the Effective Price scope."""
    metadata = PricingMetadata(
        strategy=PricingStrategy.SUPPLIER_CONTRACTED_PRICE,
        scope=PriceComponentScope(
            frozenset(
                {PriceComponent.MARKET_ENERGY, PriceComponent.SUPPLIER_MARKUP}
            ),
            vat=VatTreatment.INCLUDED,
        ),
        completeness=PriceCompleteness.PARTIAL,
    )

    result = effective_price_metadata(
        metadata,
        grid_fee_per_kwh=Decimal("0.10"),
        energy_tax_per_kwh=Decimal("0.45"),
    )

    assert result.completeness is PriceCompleteness.COMPLETE
    assert result.scope.included == frozenset(PriceComponent)


def test_effective_price_metadata_keeps_incomplete_unknown_vat() -> None:
    """Configured components cannot make unknown VAT semantics comparable."""
    metadata = PricingMetadata(
        strategy=PricingStrategy.MARKET_PRICE_PLUS_TARIFF,
        scope=PriceComponentScope(
            frozenset({PriceComponent.MARKET_ENERGY}),
            vat=VatTreatment.UNKNOWN,
        ),
        completeness=PriceCompleteness.PARTIAL,
    )

    result = effective_price_metadata(
        metadata,
        grid_fee_per_kwh=Decimal("0.10"),
        energy_tax_per_kwh=Decimal("0.45"),
        supplier_markup_per_kwh=Decimal("0.08"),
    )

    assert result.completeness is PriceCompleteness.PARTIAL


def test_calculate_consumption_weighted_average_price_accepts_wh() -> None:
    """Normalize watt-hours before calculating the average price."""
    assert calculate_consumption_weighted_average_price(
        Decimal("3"),
        Decimal("2500"),
        "Wh",
    ) == Decimal("1.2")


@pytest.mark.parametrize(
    ("cost", "energy", "unit", "grid_fee"),
    [
        (None, Decimal("1"), "kWh", None),
        (Decimal("1"), None, "kWh", None),
        (Decimal("1"), Decimal("0"), "kWh", None),
        (Decimal("1"), Decimal("1"), "J", None),
        (Decimal("-1"), Decimal("1"), "kWh", None),
        (Decimal("1"), Decimal("1"), "kWh", Decimal("-1")),
    ],
)
def test_calculate_consumption_weighted_average_price_rejects_invalid_inputs(
    cost: Decimal | None,
    energy: Decimal | None,
    unit: str,
    grid_fee: Decimal | None,
) -> None:
    """Return unavailable for incomplete or incompatible daily inputs."""
    assert (
        calculate_consumption_weighted_average_price(
            cost,
            energy,
            unit,
            grid_fee,
        )
        is None
    )


def test_calculate_current_cost_rate() -> None:
    """Current cost rate should use power and price."""
    result = calculate_current_cost_rate(
        power_w=Decimal(2400),
        price_per_kwh=Decimal("1.80"),
    )

    assert result == Decimal("4.320")


def test_calculate_current_cost_rate_with_zero_power() -> None:
    """Zero power should result in zero cost."""
    result = calculate_current_cost_rate(
        power_w=Decimal(0),
        price_per_kwh=Decimal("1.80"),
    )

    assert result == Decimal("0.00")


def test_calculate_current_cost_rate_with_zero_price() -> None:
    """Zero price should result in zero cost."""
    result = calculate_current_cost_rate(
        power_w=Decimal(2400),
        price_per_kwh=Decimal(0),
    )

    assert result == Decimal("0.0")


def test_calculate_current_cost_rate_without_power() -> None:
    """Unavailable power should result in an unavailable calculation."""
    result = calculate_current_cost_rate(
        power_w=None,
        price_per_kwh=Decimal("1.80"),
    )

    assert result is None


def test_calculate_current_cost_rate_without_price() -> None:
    """Unavailable price should result in an unavailable calculation."""
    result = calculate_current_cost_rate(
        power_w=Decimal(2400),
        price_per_kwh=None,
    )

    assert result is None


def test_calculate_current_cost_rate_rejects_negative_power() -> None:
    """Negative power should not produce a cost rate."""
    result = calculate_current_cost_rate(
        power_w=Decimal(-100),
        price_per_kwh=Decimal("1.80"),
    )

    assert result is None


def test_calculate_current_cost_rate_accepts_negative_import_price() -> None:
    """Imported power at a negative price should produce a negative rate."""
    result = calculate_current_cost_rate(
        power_w=Decimal(2400),
        price_per_kwh=Decimal("-0.25"),
    )

    assert result == Decimal("-0.600")
