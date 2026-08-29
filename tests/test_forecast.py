"""Tests for forecast interval models."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from custom_components.electricity_pro.forecast import (
    ForecastInterval,
    current_market_price_interval,
    daily_average_market_price,
    serialize_market_price_forecast,
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


def test_daily_average_market_price_is_duration_weighted_for_complete_local_day(
) -> None:
    """A complete local day should produce one duration-weighted market mean."""
    timezone = ZoneInfo("Europe/Stockholm")
    period_start = datetime(2026, 8, 13, tzinfo=timezone)
    midpoint = period_start + timedelta(hours=6)
    period_end = period_start + timedelta(days=1)
    intervals = [
        ForecastInterval(
            start=period_start,
            end=midpoint,
            market_price=Decimal("1"),
            currency="SEK",
            area="SE3",
        ),
        ForecastInterval(
            start=midpoint,
            end=period_end,
            market_price=Decimal("3"),
            currency="SEK",
            area="SE3",
        ),
    ]

    result = daily_average_market_price(
        intervals,
        period_start=period_start,
        period_end=period_end,
    )

    assert result is not None
    assert result.average_market_price == Decimal("2.5")
    assert result.interval_count == 2
    assert result.currency == "SEK"
    assert result.area == "SE3"


def test_daily_average_market_price_rejects_partial_day() -> None:
    """A partial series must not be published as a daily market average."""
    timezone = ZoneInfo("Europe/Stockholm")
    period_start = datetime(2026, 8, 13, tzinfo=timezone)
    period_end = period_start + timedelta(days=1)

    assert (
        daily_average_market_price(
            [
                ForecastInterval(
                    start=period_start,
                    end=period_end - timedelta(minutes=15),
                    market_price=Decimal("1.5"),
                    currency="SEK",
                    area="SE3",
                )
            ],
            period_start=period_start,
            period_end=period_end,
        )
        is None
    )


@pytest.mark.parametrize(
    ("local_day", "expected_intervals"),
    [
        ((2026, 3, 29), 92),
        ((2026, 10, 25), 100),
    ],
)
def test_daily_average_market_price_handles_daylight_saving_days(
    local_day: tuple[int, int, int],
    expected_intervals: int,
) -> None:
    """Complete 23- and 25-hour local days should both be accepted."""
    timezone = ZoneInfo("Europe/Stockholm")
    period_start = datetime(*local_day, tzinfo=timezone)
    period_end = datetime(
        *(period_start.date() + timedelta(days=1)).timetuple()[:3],
        tzinfo=timezone,
    )
    utc_start = period_start.astimezone(UTC)
    utc_end = period_end.astimezone(UTC)
    intervals = []
    cursor = utc_start
    while cursor < utc_end:
        intervals.append(
            ForecastInterval(
                start=cursor,
                end=cursor + timedelta(minutes=15),
                market_price=Decimal("1.25"),
                currency="SEK",
                area="SE3",
            )
        )
        cursor += timedelta(minutes=15)

    result = daily_average_market_price(
        intervals,
        period_start=period_start,
        period_end=period_end,
    )

    assert result is not None
    assert result.average_market_price == Decimal("1.25")
    assert result.interval_count == expected_intervals


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


def test_serialize_market_price_forecast_returns_json_safe_series() -> None:
    """Forecast responses should carry shared metadata and numeric prices."""
    first = ForecastInterval(
        start=datetime(2026, 8, 13, 10, tzinfo=UTC),
        end=datetime(2026, 8, 13, 11, tzinfo=UTC),
        market_price=Decimal("-0.05000"),
        currency="SEK",
        area="SE3",
        published_at=datetime(2026, 8, 12, 11, tzinfo=UTC),
    )
    second = ForecastInterval(
        start=datetime(2026, 8, 13, 11, tzinfo=UTC),
        end=datetime(2026, 8, 13, 12, tzinfo=UTC),
        market_price=Decimal("0.30000"),
        currency="SEK",
        area="SE3",
        published_at=datetime(2026, 8, 12, 11, tzinfo=UTC),
    )

    assert serialize_market_price_forecast([second, first]) == {
        "currency": "SEK",
        "area": "SE3",
        "price_components": ["market_energy"],
        "vat_treatment": "unknown",
        "price_completeness": "partial",
        "published_at": "2026-08-12T11:00:00+00:00",
        "intervals": [
            {
                "start": "2026-08-13T10:00:00+00:00",
                "end": "2026-08-13T11:00:00+00:00",
                "price": -0.05,
            },
            {
                "start": "2026-08-13T11:00:00+00:00",
                "end": "2026-08-13T12:00:00+00:00",
                "price": 0.3,
            },
        ],
    }


def test_serialize_market_price_forecast_rejects_empty_series() -> None:
    """The action contract should reject an unavailable forecast."""
    with pytest.raises(ValueError, match="unavailable"):
        serialize_market_price_forecast([])
