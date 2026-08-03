"""Tests for the statistics foundation."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from custom_components.electricity_pro.statistics_engine import (
    CalendarPeriod,
    CumulativeStatistic,
    StatisticsSnapshot,
)


def dt(year: int, month: int, day: int) -> datetime:
    """Create a timezone-aware datetime for tests."""
    return datetime(year, month, day, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("period", "now", "expected"),
    [
        (CalendarPeriod.DAY, dt(2026, 8, 3), date(2026, 8, 3)),
        (CalendarPeriod.MONTH, dt(2026, 8, 3), date(2026, 8, 1)),
    ],
)
def test_calendar_period_start(
    period: CalendarPeriod,
    now: datetime,
    expected: date,
) -> None:
    """Test local calendar-period boundaries."""
    assert period.start(now) == expected


def test_calendar_period_requires_timezone() -> None:
    """Reject timezone-naive period calculations."""
    with pytest.raises(ValueError, match="timezone-aware"):
        CalendarPeriod.MONTH.start(datetime(2026, 8, 3))


def test_snapshot_round_trip() -> None:
    """Test lossless snapshot serialization for persistence."""
    snapshot = StatisticsSnapshot(
        period_start=date(2026, 8, 1),
        last_value=Decimal("1234.567"),
        value=Decimal("45.678"),
    )

    assert StatisticsSnapshot.from_dict(snapshot.as_dict()) == snapshot


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"period_start": "not-a-date", "last_value": "1", "value": "1"},
        {"period_start": "2026-08-01", "last_value": "NaN", "value": "1"},
        {"period_start": "2026-08-01", "last_value": "1", "value": "-1"},
    ],
)
def test_snapshot_rejects_invalid_storage(data: dict[str, str]) -> None:
    """Test that corrupt persisted snapshots are rejected."""
    with pytest.raises(ValueError, match="invalid statistics snapshot"):
        StatisticsSnapshot.from_dict(data)


def test_cumulative_statistic_accumulates_measurement_deltas() -> None:
    """Test accumulation from a cumulative source meter."""
    statistic = CumulativeStatistic(CalendarPeriod.MONTH)

    assert statistic.update(Decimal("100"), dt(2026, 8, 1)) == Decimal(0)
    assert statistic.update(Decimal("102.5"), dt(2026, 8, 2)) == Decimal("2.5")
    assert statistic.update(Decimal("109"), dt(2026, 8, 31)) == Decimal(9)


def test_cumulative_statistic_resets_at_new_period() -> None:
    """Test that the accumulated value resets at a month boundary."""
    statistic = CumulativeStatistic(CalendarPeriod.MONTH)
    statistic.update(Decimal("100"), dt(2026, 8, 1))
    statistic.update(Decimal("109"), dt(2026, 8, 31))

    assert statistic.update(Decimal("110"), dt(2026, 9, 1)) == Decimal(1)
    assert statistic.snapshot == StatisticsSnapshot(
        period_start=date(2026, 9, 1),
        last_value=Decimal("110"),
        value=Decimal(1),
    )


def test_cumulative_statistic_handles_source_reset() -> None:
    """Test a cumulative meter resetting within the current period."""
    statistic = CumulativeStatistic(CalendarPeriod.MONTH)
    statistic.update(Decimal("100"), dt(2026, 8, 1))
    statistic.update(Decimal("109"), dt(2026, 8, 15))

    assert statistic.update(Decimal("2"), dt(2026, 8, 16)) == Decimal(11)


def test_cumulative_statistic_restores_snapshot() -> None:
    """Test continuing accumulation after a restart."""
    snapshot = StatisticsSnapshot(
        period_start=date(2026, 8, 1),
        last_value=Decimal("105"),
        value=Decimal(5),
    )
    statistic = CumulativeStatistic(CalendarPeriod.MONTH, snapshot)

    assert statistic.value == Decimal(5)
    assert statistic.update(Decimal("108"), dt(2026, 8, 20)) == Decimal(8)


@pytest.mark.parametrize("measurement", [Decimal("-1"), Decimal("NaN")])
def test_cumulative_statistic_rejects_invalid_measurement(
    measurement: Decimal,
) -> None:
    """Test validation of cumulative source measurements."""
    statistic = CumulativeStatistic(CalendarPeriod.MONTH)

    with pytest.raises(ValueError, match="non-negative finite"):
        statistic.update(measurement, dt(2026, 8, 1))
