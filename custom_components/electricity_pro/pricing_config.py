"""Configuration serialization for normalized pricing metadata."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from .const import (
    CONF_PRICE_VAT_RATE,
    CONF_PRICE_ENTITY,
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
from .settings import resolve_settings


def pricing_metadata_from_mapping(
    settings: Mapping[str, object],
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

    raw_strategy = settings[CONF_PRICING_STRATEGY]
    raw_vat = settings[CONF_PRICE_VAT_TREATMENT]
    raw_completeness = settings[CONF_PRICE_COMPLETENESS]
    if (
        not isinstance(raw_strategy, str)
        or not isinstance(raw_vat, str)
        or not isinstance(raw_completeness, str)
    ):
        return None

    try:
        strategy = PricingStrategy(raw_strategy)
        components = frozenset(
            PriceComponent(component) for component in raw_components
        )
        vat = VatTreatment(raw_vat)
        completeness = PriceCompleteness(raw_completeness)
    except TypeError, ValueError:
        return None

    return PricingMetadata(
        strategy=strategy,
        scope=PriceComponentScope(components, vat=vat),
        completeness=completeness,
        vat_rate=vat_rate_from_mapping(settings),
    )


def resolve_pricing_metadata(
    data: Mapping[str, object],
    options: Mapping[str, object],
) -> PricingMetadata | None:
    """Resolve pricing metadata with options taking precedence over entry data."""
    settings = resolve_settings(data, options)
    return pricing_metadata_from_mapping(settings)


def vat_rate_from_mapping(settings: Mapping[str, object]) -> Decimal | None:
    """Read an explicitly configured percentage; never infer a tax rate."""
    raw = settings.get(CONF_PRICE_VAT_RATE)
    if raw is None or isinstance(raw, bool):
        return None
    try:
        rate = Decimal(str(raw))
    except InvalidOperation, ValueError:
        return None
    return rate if rate.is_finite() and Decimal(0) <= rate <= Decimal(100) else None


def prepare_pricing_metadata(user_input: dict[str, Any]) -> bool:
    """Validate and normalize explicit price semantics in submitted data."""
    metadata_keys = (
        CONF_PRICING_STRATEGY,
        CONF_PRICE_INCLUDED_COMPONENTS,
        CONF_PRICE_VAT_TREATMENT,
        CONF_PRICE_COMPLETENESS,
    )
    if not user_input.get(CONF_PRICE_ENTITY):
        for key in metadata_keys:
            user_input.pop(key, None)
        return True

    raw_strategy = user_input.get(CONF_PRICING_STRATEGY)
    raw_components = user_input.get(CONF_PRICE_INCLUDED_COMPONENTS)
    raw_vat = user_input.get(CONF_PRICE_VAT_TREATMENT)
    if (
        not isinstance(raw_components, list)
        or not isinstance(raw_strategy, str)
        or not isinstance(raw_vat, str)
    ):
        return False

    try:
        strategy = PricingStrategy(raw_strategy)
        components = frozenset(PriceComponent(value) for value in raw_components)
        vat = VatTreatment(raw_vat)
    except TypeError, ValueError:
        return False

    if PriceComponent.MARKET_ENERGY not in components:
        return False

    all_components = frozenset(PriceComponent)
    completeness = (
        PriceCompleteness.COMPLETE
        if strategy is PricingStrategy.EXTERNAL_COMPLETE_PRICE
        or components == all_components
        else PriceCompleteness.PARTIAL
    )
    user_input[CONF_PRICING_STRATEGY] = strategy.value
    user_input[CONF_PRICE_INCLUDED_COMPONENTS] = sorted(
        component.value for component in components
    )
    user_input[CONF_PRICE_VAT_TREATMENT] = vat.value
    user_input[CONF_PRICE_COMPLETENESS] = completeness.value
    return True
