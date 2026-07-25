"""Statistics helpers for Electricity Pro."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal

_SECONDS_PER_HOUR = Decimal(3600)


def remaining_cost_today(
    current_cost_rate: Decimal | None,
    now: datetime,
) -> Decimal | None:
    """Calculate the projected electricity cost until local midnight.

    The calculation assumes that the current cost rate remains unchanged
    from the supplied time until midnight.

    Args:
        current_cost_rate: Current electricity cost per hour.
        now: Current local date and time.

    Returns:
        The projected remaining cost for today, or None when the current
        cost rate is unavailable.
    """
    if current_cost_rate is None:
        return None

    if current_cost_rate < 0:
        return None

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("remaining_cost_today requires a timezone-aware datetime")

    tomorrow = now.date() + timedelta(days=1)
    midnight = datetime.combine(tomorrow, time.min, tzinfo=now.tzinfo)

    seconds_remaining = Decimal(str((midnight - now).total_seconds()))
    hours_remaining = seconds_remaining / _SECONDS_PER_HOUR

    return current_cost_rate * hours_remaining
