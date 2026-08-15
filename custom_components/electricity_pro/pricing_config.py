"""Configuration serialization for normalized pricing metadata."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .const import (
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

    Existing entries without all metadata fields intentionally return ``None``
    so callers can preserve the legacy calculation path. No provider semantics
    are inferred during migration.
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
    )


def resolve_pricing_metadata(
    data: Mapping[str, Any],
    options: Mapping[str, Any],
) -> PricingMetadata | None:
    """Resolve pricing metadata with options taking precedence over entry data."""
    settings = {**data, **options}
    return pricing_metadata_from_mapping(settings)
