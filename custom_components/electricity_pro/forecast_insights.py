"""Pure forecast insight calculations for Electricity Pro."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .forecast import ForecastInterval


@dataclass(frozen=True, slots=True)
class NextInexpensive1hWindowInsight:
    """The earliest upcoming 1-hour window whose average effective price is at or below threshold."""

    start: datetime
    end: datetime
    duration_minutes: int
    interval_count: int
    average_market_price: Decimal
    average_effective_price: Decimal
    threshold: Decimal
    currency: str
    area: str
    published_at: datetime | None


@dataclass(frozen=True, slots=True)
class ForecastWindowInsight:
    """A selected continuous future price window."""

    start: datetime
    end: datetime
    duration_minutes: int
    interval_count: int
    average_market_price: Decimal
    average_effective_price: Decimal
    currency: str
    area: str
    published_at: datetime | None


@dataclass(frozen=True, slots=True)
class ForecastDirectionInsight:
    """A comparison between two nearby forecast intervals."""

    direction: str
    current_start: datetime
    current_end: datetime
    next_start: datetime
    next_end: datetime
    current_effective_price: Decimal
    next_effective_price: Decimal
    delta: Decimal
    currency: str
    area: str
    published_at: datetime | None


def find_cheapest_continuous_window(
    intervals: list[ForecastInterval],
    *,
    now: datetime,
    duration_minutes: int,
    grid_fee_per_kwh: Decimal | None = None,
    tax_per_kwh: Decimal | None = None,
) -> ForecastWindowInsight | None:
    """Return the cheapest upcoming continuous window with the exact duration."""
    upcoming = [interval for interval in intervals if interval.start >= now]
    best_window: ForecastWindowInsight | None = None

    for start_index, start_interval in enumerate(upcoming):
        window = [start_interval]
        total_minutes = start_interval.resolution_minutes

        for interval in upcoming[start_index + 1 :]:
            previous = window[-1]
            if interval.start < previous.end:
                return None
            if interval.start != previous.end or total_minutes >= duration_minutes:
                break
            window.append(interval)
            total_minutes += interval.resolution_minutes

        if total_minutes != duration_minutes:
            continue

        if any(
            interval.currency != start_interval.currency or interval.area != start_interval.area
            for interval in window[1:]
        ):
            continue

        average_market_price = _average_market_price(window)
        average_effective_price = _average_effective_price(
            window,
            grid_fee_per_kwh=grid_fee_per_kwh,
            tax_per_kwh=tax_per_kwh,
        )
        candidate = ForecastWindowInsight(
            start=window[0].start,
            end=window[-1].end,
            duration_minutes=duration_minutes,
            interval_count=len(window),
            average_market_price=average_market_price,
            average_effective_price=average_effective_price,
            currency=window[0].currency,
            area=window[0].area,
            published_at=window[0].published_at,
        )
        if best_window is None or (candidate.average_effective_price, candidate.start, candidate.average_market_price) < (
            best_window.average_effective_price,
            best_window.start,
            best_window.average_market_price,
        ):
            best_window = candidate

    return best_window


def find_price_direction(
    intervals: list[ForecastInterval],
    *,
    now: datetime,
    grid_fee_per_kwh: Decimal | None = None,
    tax_per_kwh: Decimal | None = None,
) -> ForecastDirectionInsight | None:
    """Return the near-term price direction from the normalized forecast."""
    sorted_intervals = sorted(intervals, key=lambda interval: interval.start)

    for index in range(len(sorted_intervals) - 1):
        current = sorted_intervals[index]
        following = sorted_intervals[index + 1]
        if following.start < current.end:
            return None
        if current.start <= now < current.end or current.start >= now:
            if current.currency != following.currency or current.area != following.area:
                return None
            current_effective_price = _effective_price(
                current.market_price,
                grid_fee_per_kwh=grid_fee_per_kwh,
                tax_per_kwh=tax_per_kwh,
            )
            next_effective_price = _effective_price(
                following.market_price,
                grid_fee_per_kwh=grid_fee_per_kwh,
                tax_per_kwh=tax_per_kwh,
            )
            delta = next_effective_price - current_effective_price
            direction = "stable" if delta == 0 else "rising" if delta > 0 else "falling"
            return ForecastDirectionInsight(
                direction=direction,
                current_start=current.start,
                current_end=current.end,
                next_start=following.start,
                next_end=following.end,
                current_effective_price=current_effective_price,
                next_effective_price=next_effective_price,
                delta=delta,
                currency=current.currency,
                area=current.area,
                published_at=current.published_at,
            )

    return None


def _effective_price(
    market_price: Decimal,
    *,
    grid_fee_per_kwh: Decimal | None,
    tax_per_kwh: Decimal | None,
) -> Decimal:
    """Return the effective price including configured adjustments."""
    return market_price + (grid_fee_per_kwh or Decimal("0")) + (tax_per_kwh or Decimal("0"))


def _average_market_price(window: list[ForecastInterval]) -> Decimal:
    """Return the duration-weighted average market price for a window."""
    total_minutes = sum(interval.resolution_minutes for interval in window)
    weighted_sum = sum(
        interval.market_price * interval.resolution_minutes for interval in window
    )
    return weighted_sum / Decimal(total_minutes)


def _average_effective_price(
    window: list[ForecastInterval],
    *,
    grid_fee_per_kwh: Decimal | None,
    tax_per_kwh: Decimal | None,
) -> Decimal:
    """Return the duration-weighted average effective price for a window."""
    total_minutes = sum(interval.resolution_minutes for interval in window)
    weighted_sum = sum(
        _effective_price(
            interval.market_price,
            grid_fee_per_kwh=grid_fee_per_kwh,
            tax_per_kwh=tax_per_kwh,
        )
        * interval.resolution_minutes
        for interval in window
    )
    return weighted_sum / Decimal(total_minutes)


def find_next_inexpensive_1h_window(
    intervals: list[ForecastInterval],
    *,
    now: datetime,
    threshold: Decimal,
    grid_fee_per_kwh: Decimal | None = None,
    tax_per_kwh: Decimal | None = None,
) -> NextInexpensive1hWindowInsight | None:
    """Return the earliest upcoming 1-hour window whose average effective price is at or below threshold."""
    upcoming = [interval for interval in intervals if interval.start >= now]

    for start_index, start_interval in enumerate(upcoming):
        window = [start_interval]
        total_minutes = start_interval.resolution_minutes

        for interval in upcoming[start_index + 1 :]:
            previous = window[-1]
            if interval.start < previous.end:
                return None
            if interval.start != previous.end or total_minutes >= 60:
                break
            window.append(interval)
            total_minutes += interval.resolution_minutes

        if total_minutes != 60:
            continue

        if any(
            interval.currency != start_interval.currency or interval.area != start_interval.area
            for interval in window[1:]
        ):
            continue

        average_effective_price = _average_effective_price(
            window,
            grid_fee_per_kwh=grid_fee_per_kwh,
            tax_per_kwh=tax_per_kwh,
        )
        if average_effective_price > threshold:
            continue

        return NextInexpensive1hWindowInsight(
            start=window[0].start,
            end=window[-1].end,
            duration_minutes=60,
            interval_count=len(window),
            average_market_price=_average_market_price(window),
            average_effective_price=average_effective_price,
            threshold=threshold,
            currency=window[0].currency,
            area=window[0].area,
            published_at=window[0].published_at,
        )

    return None
