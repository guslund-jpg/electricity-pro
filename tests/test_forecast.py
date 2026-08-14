"""Tests for forecast interval models."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from custom_components.electricity_pro.forecast import ForecastInterval


def test_forecast_interval_valid() -> None:
    """A valid forecast interval should preserve its normalized values."""
    interval = ForecastInterval(
        start=datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
        end=datetime(2026, 8, 13, 10, 15, tzinfo=UTC),
        market_price=Decimal("0.59104"),
        currency="SEK",
        area="SE3",
        published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
    )

    assert interval.market_price == Decimal("0.59104")
    assert interval.currency == "SEK"
    assert interval.area == "SE3"
    assert interval.duration == timedelta(minutes=15)
    assert interval.resolution_minutes == 15


@pytest.mark.parametrize(
    ("start", "end", "published_at"),
    [
        (
            datetime(2026, 8, 13, 10, 0),
            datetime(2026, 8, 13, 10, 15, tzinfo=UTC),
            None,
        ),
        (
            datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
            datetime(2026, 8, 13, 10, 15),
            None,
        ),
        (
            datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
            datetime(2026, 8, 13, 10, 15, tzinfo=UTC),
            datetime(2026, 8, 12, 11, 0),
        ),
    ],
)
def test_forecast_interval_requires_timezone_aware_datetimes(
    start: datetime,
    end: datetime,
    published_at: datetime | None,
) -> None:
    """Forecast intervals should reject naive datetimes."""
    with pytest.raises(ValueError, match="timezone-aware"):
        ForecastInterval(
            start=start,
            end=end,
            market_price=Decimal("1.25"),
            currency="SEK",
            area="SE3",
            published_at=published_at,
        )


@pytest.mark.parametrize(
    ("start", "end", "market_price", "currency", "area"),
    [
        (datetime(2026, 8, 13, 10, 0, tzinfo=UTC), datetime(2026, 8, 13, 10, 0, tzinfo=UTC), Decimal("1.25"), "SEK", "SE3"),
        (datetime(2026, 8, 13, 10, 15, tzinfo=UTC), datetime(2026, 8, 13, 10, 0, tzinfo=UTC), Decimal("1.25"), "SEK", "SE3"),
        (datetime(2026, 8, 13, 10, 0, tzinfo=UTC), datetime(2026, 8, 13, 10, 15, tzinfo=UTC), Decimal("NaN"), "SEK", "SE3"),
        (datetime(2026, 8, 13, 10, 0, tzinfo=UTC), datetime(2026, 8, 13, 10, 15, tzinfo=UTC), Decimal("1.25"), "", "SE3"),
        (datetime(2026, 8, 13, 10, 0, tzinfo=UTC), datetime(2026, 8, 13, 10, 15, tzinfo=UTC), Decimal("1.25"), "SEK", ""),
    ],
)
def test_forecast_interval_rejects_invalid_values(
    start: datetime,
    end: datetime,
    market_price: Decimal,
    currency: str,
    area: str,
) -> None:
    """Forecast intervals should reject invalid normalized values."""
    with pytest.raises(ValueError):
        ForecastInterval(
            start=start,
            end=end,
            market_price=market_price,
            currency=currency,
            area=area,
        )


def test_forecast_interval_accepts_negative_market_price() -> None:
    """Negative Nord Pool spot prices are valid forecast data."""
    interval = ForecastInterval(
        start=datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
        end=datetime(2026, 8, 13, 10, 15, tzinfo=UTC),
        market_price=Decimal("-0.01"),
        currency="SEK",
        area="SE3",
    )

    assert interval.market_price == Decimal("-0.01")
