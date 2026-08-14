"""Forecast interval models for Electricity Pro."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ForecastInterval:
    """Normalized future electricity price interval."""

    start: datetime
    end: datetime
    market_price: Decimal
    currency: str
    area: str
    published_at: datetime | None = None

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
