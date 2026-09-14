"""Configuration serialization for normalized pricing metadata."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from decimal import Decimal, InvalidOperation

from .const import (
    CONF_PRICE_VAT_RATE,
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICING_STRATEGY,
)
from .pricing import (
    PriceComponent,
    PriceComponentScope,
    PriceCompleteness,
    PricingMetadata,
    PricingStrategy,
    VatTreatment,
)


def pricing_metadata_from_mapping(
    settings: Mapping[str, Any],
) -> PricingMetadata | None:
    """Deserialize explicitly configured pricing metadata.

    Missing, partial, or invalid metadata returns ``None``. Integration setup
    rejects that result when a price source is configured; provider semantics
    are never inferred.
    """
    required = (
        CONF_PRICING_STRATEGY,
        CONF_PRICE_INCLUDED_COMPONENTS,
        CONF_PRICE_VAT_TREATMENT,
        CONF_PRICE_COMPLETENESS,
    )
    if any(key not in settings for key in required):
        return None

    raw_components = settings[CONF_PRICE_INCLUDED_COMPONENTS]
    if not isinstance(raw_components, (list, tuple, set, frozenset)):
        return None

    try:
        strategy = PricingStrategy(settings[CONF_PRICING_STRATEGY])
        components = frozenset(
            PriceComponent(component) for component in raw_components
        )
        vat = VatTreatment(settings[CONF_PRICE_VAT_TREATMENT])
        completeness = PriceCompleteness(settings[CONF_PRICE_COMPLETENESS])
    except (TypeError, ValueError):
        return None

    return PricingMetadata(
        strategy=strategy,
        scope=PriceComponentScope(components, vat=vat),
        completeness=completeness,
        vat_rate=vat_rate_from_mapping(settings),
    )


def resolve_pricing_metadata(
    data: Mapping[str, Any],
    options: Mapping[str, Any],
) -> PricingMetadata | None:
    """Resolve pricing metadata with options taking precedence over entry data."""
    settings = {**data, **options}
    return pricing_metadata_from_mapping(settings)


def vat_rate_from_mapping(settings: Mapping[str, Any]) -> Decimal | None:
    """Read an explicitly configured percentage; never infer a tax rate."""
    raw = settings.get(CONF_PRICE_VAT_RATE)
    if raw is None or isinstance(raw, bool):
        return None
    try:
        rate = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None
    return rate if rate.is_finite() and Decimal(0) <= rate <= Decimal(100) else None
