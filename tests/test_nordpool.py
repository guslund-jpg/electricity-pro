"""Tests for Nord Pool forecast normalization."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from custom_components.electricity_pro.nordpool import (
    normalize_nordpool_forecast_intervals,
)


def test_normalize_nordpool_forecast_intervals() -> None:
    """Nord Pool action intervals should normalize to forecast intervals."""
    intervals = [
        {
            "start": "2026-08-13T10:00:00+00:00",
            "end": "2026-08-13T10:15:00+00:00",
            "price": 591.04,
        },
        {
            "start": "2026-08-13T10:15:00+00:00",
            "end": "2026-08-13T10:30:00+00:00",
            "price": 539.67,
        },
    ]

    forecast_intervals = normalize_nordpool_forecast_intervals(
        area="SE3",
        intervals=intervals,
        currency="SEK",
        published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
    )

    assert len(forecast_intervals) == 2
    assert forecast_intervals[0].market_price == Decimal("0.59104")
    assert forecast_intervals[0].currency == "SEK"
    assert forecast_intervals[0].area == "SE3"
    assert forecast_intervals[0].published_at == datetime(
        2026,
        8,
        12,
        11,
        0,
        tzinfo=UTC,
    )
    assert forecast_intervals[0].resolution_minutes == 15


@pytest.mark.parametrize(
    ("area", "currency", "intervals", "message"),
    [
        ("", "SEK", [], "area is required"),
        ("SE3", "", [], "currency is required"),
        (
            "SE3",
            "SEK",
            [{"end": "2026-08-13T10:15:00+00:00", "price": 591.04}],
            "string start and end",
        ),
        (
            "SE3",
            "SEK",
            [{"start": "2026-08-13T10:00:00+00:00", "price": 591.04}],
            "string start and end",
        ),
        (
            "SE3",
            "SEK",
            [
                {
                    "start": "2026-08-13T10:00:00+00:00",
                    "end": "2026-08-13T10:15:00+00:00",
                    "price": "591.04",
                }
            ],
            "numeric price",
        ),
        (
            "SE3",
            "SEK",
            [
                {
                    "start": "not-a-date",
                    "end": "2026-08-13T10:15:00+00:00",
                    "price": 591.04,
                }
            ],
            "valid ISO datetimes",
        ),
    ],
)
def test_normalize_nordpool_forecast_intervals_rejects_invalid_values(
    area: str,
    currency: str,
    intervals: list[dict[str, str | int | float]],
    message: str,
) -> None:
    """Nord Pool forecast normalization should reject invalid values."""
    with pytest.raises(ValueError, match=message):
        normalize_nordpool_forecast_intervals(
            area=area,
            intervals=intervals,
            currency=currency,
        )
