"""Tests for Electricity Pro statistics helpers."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from custom_components.electricity_pro.statistics import remaining_cost_today


def dt(hour: int, minute: int = 0, second: int = 0) -> datetime:
    """Create a timezone-aware UTC datetime for tests."""
    return datetime(
        2026,
        7,
        25,
        hour,
        minute,
        second,
        tzinfo=UTC,
    )


def naive_dt(hour: int, minute: int = 0, second: int = 0) -> datetime:
    """Create a timezone-naive datetime for validation tests."""
    return datetime(  # pyright: ignore[reportCallIssue]
        2026,
        7,
        25,
        hour,
        minute,
        second,
    )


@pytest.mark.parametrize(
    ("current_cost_rate", "now", "expected"),
    [
        (
            Decimal("4.32"),
            dt(15),
            Decimal("38.88"),
        ),
        (
            Decimal("2.00"),
            dt(18, 30),
            Decimal("11.00"),
        ),
        (
            Decimal("1.50"),
            dt(23),
            Decimal("1.50"),
        ),
        (
            Decimal(0),
            dt(12),
            Decimal(0),
        ),
    ],
)
def test_remaining_cost_today(
    current_cost_rate: Decimal,
    now: datetime,
    expected: Decimal,
) -> None:
    """Test projected remaining cost at different times."""
    assert remaining_cost_today(current_cost_rate, now) == expected


def test_remaining_cost_today_with_minutes() -> None:
    """Test that partial hours are included."""
    result = remaining_cost_today(
        Decimal(4),
        dt(20, 15),
    )

    assert result == Decimal(15)


def test_remaining_cost_today_with_seconds() -> None:
    """Test that seconds are included in the calculation."""
    result = remaining_cost_today(
        Decimal("3.60"),
        dt(23, 59, 30),
    )

    assert result == Decimal("0.030")


def test_remaining_cost_today_at_midnight() -> None:
    """Test that a full day remains at the start of the day."""
    result = remaining_cost_today(
        Decimal("1.25"),
        dt(0),
    )

    assert result == Decimal("30.00")


def test_remaining_cost_today_returns_none_without_rate() -> None:
    """Test unavailable current cost rate."""
    assert remaining_cost_today(None, dt(12)) is None


def test_remaining_cost_today_returns_none_for_negative_rate() -> None:
    """Test that an invalid negative cost rate is rejected."""
    assert remaining_cost_today(Decimal(-1), dt(12)) is None


def test_remaining_cost_today_requires_timezone() -> None:
    """Reject timezone-naive datetimes."""
    with pytest.raises(ValueError, match="timezone-aware"):
        remaining_cost_today(
            Decimal(4),
            naive_dt(12),
        )
