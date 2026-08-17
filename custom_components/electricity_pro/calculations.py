"""Calculation helpers for Electricity Pro."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from homeassistant.const import UnitOfEnergy

from .pricing import PriceComponent, PricingMetadata

_KWH_PER_WH = Decimal("0.001")


def calculate_current_cost_rate(
    power_w: Decimal | None,
    price_per_kwh: Decimal | None,
) -> Decimal | None:
    """Calculate the current electricity cost per hour.

    Power is supplied in watts and price in currency per kilowatt-hour.
    The returned value is currency per hour.
    """
    if power_w is None or price_per_kwh is None:
        return None

    if power_w < 0 or price_per_kwh < 0:
        return None

    power_kw = power_w / Decimal(1000)

    return power_kw * price_per_kwh


def calculate_normalized_effective_price(
    base_price: Decimal | None,
    metadata: PricingMetadata,
    adjustments: Mapping[PriceComponent, Decimal] | None = None,
) -> Decimal | None:
    """Calculate an effective price without double-counting components.

    Every configured live price source reaches this calculation with explicit
    component semantics.
    """
    if base_price is None or not base_price.is_finite() or base_price < 0:
        return None

    additions = adjustments or {}
    if metadata.is_complete and additions:
        return None

    for component, value in additions.items():
        if (
            not isinstance(component, PriceComponent)
            or metadata.scope.includes(component)
            or not value.is_finite()
            or value < 0
        ):
            return None

    return base_price + sum(additions.values(), start=Decimal(0))


def calculate_declared_effective_price(
    base_price: Decimal | None,
    metadata: PricingMetadata | None,
    grid_fee_per_kwh: Decimal | None = None,
) -> Decimal | None:
    """Calculate live Effective Price from explicitly declared semantics."""
    if metadata is None:
        return None
    adjustments = (
        {PriceComponent.VARIABLE_GRID_FEE: grid_fee_per_kwh}
        if grid_fee_per_kwh is not None
        else None
    )
    return calculate_normalized_effective_price(
        base_price,
        metadata,
        adjustments,
    )


def calculate_consumption_weighted_average_price(
    cost_today: Decimal | None,
    energy_today: Decimal | None,
    energy_unit: str | None,
    grid_fee_per_kwh: Decimal | None = None,
) -> Decimal | None:
    """Calculate today's achieved average effective price per kWh."""
    if (
        cost_today is None
        or not cost_today.is_finite()
        or cost_today < 0
        or energy_today is None
        or not energy_today.is_finite()
    ):
        return None

    if energy_unit == UnitOfEnergy.KILO_WATT_HOUR:
        energy_kwh = energy_today
    elif energy_unit == UnitOfEnergy.WATT_HOUR:
        energy_kwh = energy_today * _KWH_PER_WH
    else:
        return None

    if energy_kwh <= 0:
        return None

    if grid_fee_per_kwh is not None and (
        not grid_fee_per_kwh.is_finite() or grid_fee_per_kwh < 0
    ):
        return None

    return (cost_today / energy_kwh) + (grid_fee_per_kwh or Decimal(0))
