"""Tests for forecast interval models."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from custom_components.electricity_pro.forecast import (
    ForecastInterval,
    current_market_price_interval,
    validate_forecast_series,
)
from custom_components.electricity_pro.pricing import (
    PriceCompleteness,
    PriceComponent,
    VatTreatment,
)


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
    assert interval.pricing_metadata.scope.included == frozenset(
        {PriceComponent.MARKET_ENERGY}
    )
    assert interval.pricing_metadata.scope.vat is VatTreatment.UNKNOWN
    assert interval.pricing_metadata.completeness is PriceCompleteness.PARTIAL


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


def _interval(
    start_hour: int,
    end_hour: int,
    price: str,
    *,
    currency: str = "SEK",
) -> ForecastInterval:
    """Create one UTC market-price interval for series tests."""
    return ForecastInterval(
        start=datetime(2026, 8, 13, start_hour, tzinfo=UTC),
        end=datetime(2026, 8, 13, end_hour, tzinfo=UTC),
        market_price=Decimal(price),
        currency=currency,
        area="SE3",
    )


def test_validate_forecast_series_sorts_and_deduplicates() -> None:
    """A valid series should be ordered and ignore identical duplicates."""
    first = _interval(10, 11, "0.20")
    second = _interval(11, 12, "0.30")

    assert validate_forecast_series([second, first, first]) == [first, second]


@pytest.mark.parametrize(
    "intervals",
    [
        [_interval(10, 11, "0.20"), _interval(10, 11, "0.25")],
        [_interval(10, 12, "0.20"), _interval(11, 13, "0.25")],
        [
            _interval(10, 11, "0.20", currency="SEK"),
            _interval(11, 12, "0.25", currency="EUR"),
        ],
    ],
)
def test_validate_forecast_series_rejects_ambiguous_data(
    intervals: list[ForecastInterval],
) -> None:
    """Conflicts, overlaps, and mixed metadata should reject the series."""
    with pytest.raises(ValueError):
        validate_forecast_series(intervals)


def test_current_market_price_interval_uses_start_inclusive_end_exclusive() -> None:
    """The active interval should switch exactly at its boundary."""
    first = _interval(10, 11, "-0.05")
    second = _interval(11, 12, "0.30")
    intervals = validate_forecast_series([second, first])

    assert current_market_price_interval(
        intervals,
        now=datetime(2026, 8, 13, 10, tzinfo=UTC),
    ) == first
    assert current_market_price_interval(
        intervals,
        now=datetime(2026, 8, 13, 11, tzinfo=UTC),
    ) == second
    assert (
        current_market_price_interval(
            intervals,
            now=datetime(2026, 8, 13, 12, tzinfo=UTC),
        )
        is None
    )


def test_current_market_price_interval_requires_aware_now() -> None:
    """Current interval selection must not compare ambiguous local datetimes."""
    with pytest.raises(ValueError, match="timezone-aware"):
        current_market_price_interval(
            [_interval(10, 11, "0.20")],
            now=datetime(2026, 8, 13, 10),
        )
