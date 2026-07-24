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
