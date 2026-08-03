"""Calculation helpers for Electricity Pro."""

from __future__ import annotations

from decimal import Decimal


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


def calculate_effective_price(
    current_price: Decimal | None,
    grid_fee_per_kwh: Decimal | None = None,
    tax_per_kwh: Decimal | None = None,
) -> Decimal | None:
    """Calculate price including optional variable per-kWh adjustments."""
    if current_price is None or current_price < 0:
        return None

    adjustments = (grid_fee_per_kwh, tax_per_kwh)
    if any(value is not None and value < 0 for value in adjustments):
        return None

    return current_price + sum(
        (value for value in adjustments if value is not None),
        start=Decimal(0),
    )
