"""Tests for pricing metadata configuration serialization."""

from custom_components.electricity_pro.const import (
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICING_STRATEGY,
)
from custom_components.electricity_pro.pricing import (
    PriceComponent,
    PriceCompleteness,
    PricingStrategy,
    VatTreatment,
)
from custom_components.electricity_pro.pricing_config import (
    pricing_metadata_from_mapping,
    resolve_pricing_metadata,
)


def _complete_settings() -> dict[str, object]:
    """Return a complete serialized pricing configuration."""
    return {
        CONF_PRICING_STRATEGY: PricingStrategy.MARKET_PRICE_PLUS_TARIFF.value,
        CONF_PRICE_INCLUDED_COMPONENTS: [PriceComponent.MARKET_ENERGY.value],
        CONF_PRICE_VAT_TREATMENT: VatTreatment.EXCLUDED.value,
        CONF_PRICE_COMPLETENESS: PriceCompleteness.PARTIAL.value,
    }


def test_pricing_metadata_from_mapping_deserializes_explicit_settings() -> None:
    """Explicit persisted values should produce normalized metadata."""
    metadata = pricing_metadata_from_mapping(_complete_settings())

    assert metadata is not None
    assert metadata.strategy is PricingStrategy.MARKET_PRICE_PLUS_TARIFF
    assert metadata.scope.included == frozenset({PriceComponent.MARKET_ENERGY})
    assert metadata.scope.vat is VatTreatment.EXCLUDED
    assert metadata.completeness is PriceCompleteness.PARTIAL


def test_pricing_metadata_from_mapping_rejects_missing_metadata() -> None:
    """An entry without explicit metadata must not acquire guessed semantics."""
    assert pricing_metadata_from_mapping({"price_entity": "sensor.price"}) is None


def test_pricing_metadata_from_mapping_rejects_partial_metadata() -> None:
    """Partly stored metadata must not be guessed or silently defaulted."""
    settings = _complete_settings()
    settings.pop(CONF_PRICE_VAT_TREATMENT)

    assert pricing_metadata_from_mapping(settings) is None


def test_pricing_metadata_from_mapping_rejects_invalid_values() -> None:
    """Unknown serialized values should be rejected."""
    settings = _complete_settings()
    settings[CONF_PRICE_INCLUDED_COMPONENTS] = ["unsupported"]

    assert pricing_metadata_from_mapping(settings) is None


def test_resolve_pricing_metadata_prefers_options() -> None:
    """User-confirmed options should override entry data."""
    data = _complete_settings()
    options = {
        CONF_PRICE_VAT_TREATMENT: VatTreatment.INCLUDED.value,
        CONF_PRICE_COMPLETENESS: PriceCompleteness.COMPLETE.value,
    }

    metadata = resolve_pricing_metadata(data, options)

    assert metadata is not None
    assert metadata.scope.vat is VatTreatment.INCLUDED
    assert metadata.completeness is PriceCompleteness.COMPLETE
