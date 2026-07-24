"""Calculation helpers for Electricity Pro."""

from __future__ import annotations


def calculate_current_cost_rate(
    power_w: float | None,
    price_per_kwh: float | None,
) -> float | None:
    """Calculate the current electricity cost per hour.

    Power is supplied in watts and price in currency per kilowatt-hour.
    The returned value is currency per hour.

    Return None when either input is unavailable.
    """
    if power_w is None or price_per_kwh is None:
        return None

    if power_w < 0 or price_per_kwh < 0:
        return None

    power_kw = power_w / 1000

    return power_kw * price_per_kwh
