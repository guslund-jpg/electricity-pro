"""Forecast interval models for Electricity Pro."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from .pricing import (
    PriceCompleteness,
    PriceComponent,
    PriceComponentScope,
    PricingMetadata,
    PricingStrategy,
    VatTreatment,
)


NORDPOOL_MARKET_PRICE_METADATA = PricingMetadata(
    strategy=PricingStrategy.MARKET_PRICE_PLUS_TARIFF,
    scope=PriceComponentScope(
        included=frozenset({PriceComponent.MARKET_ENERGY}),
        vat=VatTreatment.UNKNOWN,
    ),
    completeness=PriceCompleteness.PARTIAL,
)


@dataclass(frozen=True, slots=True)
class ForecastInterval:
    """Normalized future electricity price interval."""

    start: datetime
    end: datetime
    market_price: Decimal
    currency: str
    area: str
    published_at: datetime | None = None
    pricing_metadata: PricingMetadata = NORDPOOL_MARKET_PRICE_METADATA

    def __post_init__(self) -> None:
        """Validate the normalized interval."""
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Forecast interval datetimes must be timezone-aware")

        if self.start >= self.end:
            raise ValueError("Forecast interval start must be before end")

        if not self.market_price.is_finite():
            raise ValueError("Forecast interval market price must be finite")

        if not self.currency:
            raise ValueError("Forecast interval currency is required")

        if not self.area:
            raise ValueError("Forecast interval area is required")

        if self.published_at is not None and self.published_at.tzinfo is None:
            raise ValueError("Forecast interval published_at must be timezone-aware")

    @property
    def duration(self) -> timedelta:
        """Return the interval duration."""
        return self.end - self.start

    @property
    def resolution_minutes(self) -> int:
        """Return the interval resolution in minutes."""
        return int(self.duration.total_seconds() // 60)


@dataclass(frozen=True, slots=True)
class DailyAverageMarketPriceResult:
    """Represent one complete local day's time-weighted market average."""

    average_market_price: Decimal
    period_start: datetime
    period_end: datetime
    interval_count: int
    currency: str
    area: str
    pricing_metadata: PricingMetadata


def validate_forecast_series(
    intervals: Iterable[ForecastInterval],
) -> list[ForecastInterval]:
    """Return one ordered, deduplicated provider-independent price series."""
    ordered = sorted(intervals, key=lambda interval: (interval.start, interval.end))
    if not ordered:
        return []

    first = ordered[0]
    by_boundary: dict[tuple[datetime, datetime], ForecastInterval] = {}
    for interval in ordered:
        if (
            interval.currency != first.currency
            or interval.area != first.area
            or interval.pricing_metadata != first.pricing_metadata
        ):
            raise ValueError("Forecast series contains mixed metadata")

        boundary = (interval.start, interval.end)
        existing = by_boundary.get(boundary)
        if existing is not None:
            if existing.market_price != interval.market_price:
                raise ValueError("Forecast series contains conflicting duplicates")
            continue
        by_boundary[boundary] = interval

    deduplicated = sorted(
        by_boundary.values(),
        key=lambda interval: (interval.start, interval.end),
    )
    for previous, current in zip(deduplicated, deduplicated[1:]):
        if previous.end > current.start:
            raise ValueError("Forecast series contains overlapping intervals")

    return deduplicated


def current_market_price_interval(
    intervals: Iterable[ForecastInterval],
    *,
    now: datetime,
) -> ForecastInterval | None:
    """Return the unique validated market-price interval covering now."""
    if now.tzinfo is None:
        raise ValueError("Current market-price timestamp must be timezone-aware")

    matches = [interval for interval in intervals if interval.start <= now < interval.end]
    return matches[0] if len(matches) == 1 else None


def daily_average_market_price(
    intervals: Iterable[ForecastInterval],
    *,
    period_start: datetime,
    period_end: datetime,
) -> DailyAverageMarketPriceResult | None:
    """Return a duration-weighted average only for one completely covered day."""
    if period_start.tzinfo is None or period_end.tzinfo is None:
        raise ValueError("Daily market-price boundaries must be timezone-aware")
    if period_start >= period_end:
        raise ValueError("Daily market-price period start must be before end")

    validated = validate_forecast_series(intervals)
    relevant = [
        interval
        for interval in validated
        if interval.end > period_start and interval.start < period_end
    ]
    if not relevant:
        return None

    cursor = period_start
    weighted_price_seconds = Decimal(0)
    covered_seconds = Decimal(0)
    interval_count = 0
    for interval in relevant:
        clipped_start = max(interval.start, period_start)
        clipped_end = min(interval.end, period_end)
        if clipped_start != cursor:
            return None

        duration_seconds = Decimal(str((clipped_end - clipped_start).total_seconds()))
        weighted_price_seconds += interval.market_price * duration_seconds
        covered_seconds += duration_seconds
        interval_count += 1
        cursor = clipped_end
        if cursor == period_end:
            break

    if cursor != period_end or covered_seconds <= 0:
        return None

    first = relevant[0]
    return DailyAverageMarketPriceResult(
        average_market_price=weighted_price_seconds / covered_seconds,
        period_start=period_start,
        period_end=period_end,
        interval_count=interval_count,
        currency=first.currency,
        area=first.area,
        pricing_metadata=first.pricing_metadata,
    )


def serialize_market_price_forecast(
    intervals: Iterable[ForecastInterval],
) -> dict[str, Any]:
    """Serialize one validated market-price series for Home Assistant."""
    validated = validate_forecast_series(intervals)
    if not validated:
        raise ValueError("Market-price forecast is unavailable")

    first = validated[0]
    publication_times = [
        interval.published_at
        for interval in validated
        if interval.published_at is not None
    ]
    published_at = max(publication_times) if publication_times else None
    return {
        "currency": first.currency,
        "area": first.area,
        "price_components": sorted(
            component.value
            for component in first.pricing_metadata.scope.included
        ),
        "vat_treatment": first.pricing_metadata.scope.vat.value,
        "price_completeness": first.pricing_metadata.completeness.value,
        "published_at": (
            published_at.isoformat() if published_at is not None else None
        ),
        "intervals": [
            {
                "start": interval.start.isoformat(),
                "end": interval.end.isoformat(),
                "price": float(interval.market_price),
            }
            for interval in validated
        ],
    }
