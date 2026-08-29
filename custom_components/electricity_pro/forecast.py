"""Forecast interval models for Electricity Pro."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

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
