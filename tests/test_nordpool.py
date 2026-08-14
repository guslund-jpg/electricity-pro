"""Tests for Nord Pool forecast normalization."""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.electricity_pro.nordpool import (
    async_get_nordpool_forecast_intervals_for_date,
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


def test_normalize_nordpool_forecast_intervals_sorts_and_accepts_negative_prices() -> None:
    """Normalization should order intervals and preserve valid negative prices."""
    intervals = [
        {
            "start": "2026-08-13T10:15:00+00:00",
            "end": "2026-08-13T10:30:00+00:00",
            "price": 100,
        },
        {
            "start": "2026-08-13T10:00:00+00:00",
            "end": "2026-08-13T10:15:00+00:00",
            "price": -50,
        },
    ]

    forecast_intervals = normalize_nordpool_forecast_intervals(
        area="SE3",
        intervals=intervals,
        currency="SEK",
    )

    assert forecast_intervals[0].start == datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    assert forecast_intervals[0].market_price == Decimal("-0.050")


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


async def test_async_get_nordpool_forecast_intervals_for_date() -> None:
    """The Nord Pool action helper should retrieve and normalize one area."""
    async_call = AsyncMock(
        return_value={
            "SE3": [
                {
                    "start": "2026-08-13T10:00:00+00:00",
                    "end": "2026-08-13T10:15:00+00:00",
                    "price": 591.04,
                }
            ]
        }
    )
    hass = SimpleNamespace(services=SimpleNamespace(async_call=async_call))

    forecast_intervals = await async_get_nordpool_forecast_intervals_for_date(
        hass,
        config_entry_id="test-entry-id",
        target_date=date(2026, 8, 13),
        area="SE3",
        currency="SEK",
        published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
    )

    async_call.assert_awaited_once_with(
        "nordpool",
        "get_prices_for_date",
        {
            "config_entry": "test-entry-id",
            "date": "2026-08-13",
            "areas": ["SE3"],
        },
        blocking=True,
        return_response=True,
    )
    assert len(forecast_intervals) == 1
    assert forecast_intervals[0].market_price == Decimal("0.59104")


async def test_forecast_retrieval_inherits_nordpool_area_and_currency() -> None:
    """Forecast retrieval should use the selected native entry's settings."""
    async_call = AsyncMock(
        return_value={
            "SE3": [
                {
                    "start": "2026-08-13T10:00:00+00:00",
                    "end": "2026-08-13T11:00:00+00:00",
                    "price": 500.0,
                }
            ]
        }
    )
    nordpool_entry = SimpleNamespace(
        data={"areas": ["SE3"], "currency": "SEK"}
    )
    hass = SimpleNamespace(
        services=SimpleNamespace(async_call=async_call),
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: nordpool_entry
        ),
    )

    intervals = await async_get_nordpool_forecast_intervals_for_date(
        hass,
        config_entry_id="test-entry-id",
        target_date=date(2026, 8, 13),
    )

    async_call.assert_awaited_once_with(
        "nordpool",
        "get_prices_for_date",
        {
            "config_entry": "test-entry-id",
            "date": "2026-08-13",
            "areas": ["SE3"],
        },
        blocking=True,
        return_response=True,
    )
    assert intervals[0].area == "SE3"
    assert intervals[0].currency == "SEK"


@pytest.mark.parametrize(
    "response",
    [
        None,
        [],
        {"SE4": []},
        {"SE3": None},
        {"SE3": ["not-a-mapping"]},
    ],
)
async def test_async_get_nordpool_forecast_intervals_for_date_rejects_invalid_response(
    response: object,
) -> None:
    """The Nord Pool action helper should reject malformed responses."""
    async_call = AsyncMock(return_value=response)
    hass = SimpleNamespace(services=SimpleNamespace(async_call=async_call))

    with pytest.raises(ValueError):
        await async_get_nordpool_forecast_intervals_for_date(
            hass,
            config_entry_id="test-entry-id",
            target_date=date(2026, 8, 13),
            area="SE3",
            currency="SEK",
        )
