"""Pure forecast insight calculations for Electricity Pro."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable

from .forecast import ForecastInterval

GridFeeAt = Callable[[datetime], Decimal | None]


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
    grid_fee_at: GridFeeAt | None = None,
) -> ForecastWindowInsight | None:
    """Return the cheapest upcoming continuous window with the exact duration."""
    upcoming = sorted(
        (interval for interval in intervals if interval.start >= now),
        key=lambda interval: interval.start,
    )
    best_window: ForecastWindowInsight | None = None

    for start_index, start_interval in enumerate(upcoming):
        window = [start_interval]
        total_minutes = start_interval.resolution_minutes

        for interval in upcoming[start_index + 1 :]:
            previous = window[-1]
            if interval.start < previous.end:
                break
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
            grid_fee_at=grid_fee_at,
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
    grid_fee_at: GridFeeAt | None = None,
) -> ForecastDirectionInsight | None:
    """Return the near-term price direction from the normalized forecast."""
    sorted_intervals = sorted(intervals, key=lambda interval: interval.start)

    for index in range(len(sorted_intervals) - 1):
        current = sorted_intervals[index]
        following = sorted_intervals[index + 1]
        if following.start < current.end:
            continue
        if current.start <= now < current.end or current.start >= now:
            if current.currency != following.currency or current.area != following.area:
                return None
            current_effective_price = _effective_price(
                current.market_price,
                at=current.start,
                grid_fee_per_kwh=grid_fee_per_kwh,
                grid_fee_at=grid_fee_at,
            )
            next_effective_price = _effective_price(
                following.market_price,
                at=following.start,
                grid_fee_per_kwh=grid_fee_per_kwh,
                grid_fee_at=grid_fee_at,
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
    at: datetime,
    grid_fee_per_kwh: Decimal | None,
    grid_fee_at: GridFeeAt | None,
) -> Decimal:
    """Return the effective price including configured adjustments."""
    grid_fee = grid_fee_at(at) if grid_fee_at is not None else grid_fee_per_kwh
    return market_price + (grid_fee or Decimal("0"))


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
    grid_fee_at: GridFeeAt | None,
) -> Decimal:
    """Return the duration-weighted average effective price for a window."""
    total_minutes = sum(interval.resolution_minutes for interval in window)
    weighted_sum = sum(
        _effective_price(
            interval.market_price,
            at=interval.start,
            grid_fee_per_kwh=grid_fee_per_kwh,
            grid_fee_at=grid_fee_at,
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
    grid_fee_at: GridFeeAt | None = None,
) -> NextInexpensive1hWindowInsight | None:
    """Return the earliest upcoming 1-hour window whose average effective price is at or below threshold."""
    upcoming = sorted(
        (interval for interval in intervals if interval.start >= now),
        key=lambda interval: interval.start,
    )

    for start_index, start_interval in enumerate(upcoming):
        window = [start_interval]
        total_minutes = start_interval.resolution_minutes

        for interval in upcoming[start_index + 1 :]:
            previous = window[-1]
            if interval.start < previous.end:
                break
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
            grid_fee_at=grid_fee_at,
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
