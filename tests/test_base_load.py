"""Tests for pure provider-independent base-load calculations."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from zoneinfo import ZoneInfo

from custom_components.electricity_pro.base_load import (
    AveragePowerUnavailableReason,
    BaseLoadUnavailableReason,
    BaseLoadBucketAccumulator,
    DailyBaseLoadSummary,
    DailyBaseLoadUnavailableReason,
    PowerInterval,
    calculate_base_load_estimate,
    calculate_average_power,
    calculate_daily_base_load,
    duration_weighted_percentile,
)

_DAY = timedelta(days=1)


def _interval(power: str, hours: int = 6) -> PowerInterval:
    """Create one covered power interval."""
    return PowerInterval(Decimal(power), timedelta(hours=hours))


def _summary(day: int, estimate: str | None) -> DailyBaseLoadSummary:
    """Create one daily summary in a fixed August 2026 window."""
    return DailyBaseLoadSummary(
        period_start=date(2026, 8, day),
        estimate_w=Decimal(estimate) if estimate is not None else None,
        unavailable_reason=(
            None
            if estimate is not None
            else DailyBaseLoadUnavailableReason.INSUFFICIENT_COVERAGE
        ),
        coverage_percent=Decimal(100 if estimate is not None else 50),
        longest_uncovered_gap=timedelta(
            seconds=0 if estimate is not None else 12 * 3600
        ),
    )


def test_duration_weighted_percentile_interpolates_bucket_midpoints() -> None:
    """The low percentile should interpolate deterministically by duration."""
    intervals = tuple(_interval(str(power)) for power in (100, 200, 300, 400))

    assert duration_weighted_percentile(intervals, Decimal("0.10")) == Decimal(100)
    assert duration_weighted_percentile(intervals, Decimal("0.50")) == Decimal(250)
    assert duration_weighted_percentile(intervals, Decimal("0.90")) == Decimal(400)


def test_average_power_is_duration_weighted() -> None:
    """Irregular intervals must be weighted by time, not observation count."""
    result = calculate_average_power(
        (_interval("100", 1), _interval("300", 3)),
        elapsed_duration=timedelta(hours=4),
        longest_uncovered_gap=timedelta(0),
    )

    assert result.average_power_w == Decimal(250)
    assert result.coverage_percent == Decimal(100)
    assert result.covered_duration == timedelta(hours=4)


@pytest.mark.parametrize(
    ("intervals", "elapsed", "gap", "bidirectional", "reason"),
    [
        (
            (_interval("200", 8),),
            timedelta(hours=10),
            timedelta(hours=2),
            False,
            AveragePowerUnavailableReason.INSUFFICIENT_COVERAGE,
        ),
        (
            (_interval("200", 10),),
            timedelta(hours=10),
            timedelta(hours=2),
            False,
            AveragePowerUnavailableReason.LONG_DATA_GAP,
        ),
        (
            (),
            timedelta(hours=1),
            timedelta(hours=1),
            False,
            AveragePowerUnavailableReason.NO_COVERED_INTERVALS,
        ),
        (
            (_interval("200", 10),),
            timedelta(hours=10),
            timedelta(0),
            True,
            AveragePowerUnavailableReason.UNSUPPORTED_BIDIRECTIONAL_POWER,
        ),
    ],
)
def test_average_power_enforces_quality_contract(
    intervals: tuple[PowerInterval, ...],
    elapsed: timedelta,
    gap: timedelta,
    bidirectional: bool,
    reason: AveragePowerUnavailableReason,
) -> None:
    """Partial, gapped, empty, and bidirectional days must be unavailable."""
    result = calculate_average_power(
        intervals,
        elapsed_duration=elapsed,
        longest_uncovered_gap=gap,
        bidirectional_power_observed=bidirectional,
    )

    assert result.average_power_w is None
    assert result.unavailable_reason is reason


def test_daily_estimate_uses_repeated_low_demand_not_transient_minimum() -> None:
    """A brief zero should not determine a mostly higher low-demand day."""
    intervals = (
        PowerInterval(Decimal(0), timedelta(minutes=15)),
        PowerInterval(Decimal(180), timedelta(hours=3, minutes=45)),
        PowerInterval(Decimal(400), timedelta(hours=20)),
    )

    result = calculate_daily_base_load(
        date(2026, 8, 20),
        intervals,
        period_duration=_DAY,
        longest_uncovered_gap=timedelta(0),
    )

    assert result.estimate_w == Decimal("185.0947368421052631578947368")
    assert result.unavailable_reason is None


@pytest.mark.parametrize(
    ("coverage_hours", "gap", "bidirectional", "expected_reason"),
    [
        (
            20,
            timedelta(0),
            False,
            DailyBaseLoadUnavailableReason.INSUFFICIENT_COVERAGE,
        ),
        (
            24,
            timedelta(hours=2),
            False,
            DailyBaseLoadUnavailableReason.LONG_DATA_GAP,
        ),
        (
            24,
            timedelta(0),
            True,
            DailyBaseLoadUnavailableReason.UNSUPPORTED_BIDIRECTIONAL_POWER,
        ),
    ],
)
def test_daily_estimate_enforces_quality_contract(
    coverage_hours: int,
    gap: timedelta,
    bidirectional: bool,
    expected_reason: DailyBaseLoadUnavailableReason,
) -> None:
    """Incomplete, gapped, or bidirectional days must remain unavailable."""
    result = calculate_daily_base_load(
        date(2026, 8, 20),
        (_interval("200", coverage_hours),),
        period_duration=_DAY,
        longest_uncovered_gap=gap,
        bidirectional_power_observed=bidirectional,
    )

    assert result.estimate_w is None
    assert result.unavailable_reason is expected_reason


def test_rolling_estimate_requires_five_days_in_latest_seven() -> None:
    """Older eligible history must not replace a missing recent day."""
    summaries = tuple(_summary(day, "200") for day in (15, 20, 21, 22, 23))

    result = calculate_base_load_estimate(
        summaries,
        window_end=date(2026, 8, 25),
    )

    assert result.estimate_w is None
    assert result.unavailable_reason is BaseLoadUnavailableReason.INSUFFICIENT_HISTORY
    assert result.eligible_days == 4
    assert result.window_start == date(2026, 8, 19)


def test_rolling_estimate_uses_median_and_rejects_outlier_day() -> None:
    """One unusually high daily estimate should not dominate the result."""
    summaries = tuple(
        _summary(day, estimate)
        for day, estimate in zip(
            (19, 20, 21, 22, 23, 24, 25),
            ("180", "190", "200", "205", "210", "220", "2000"),
        )
    )

    result = calculate_base_load_estimate(
        summaries,
        window_end=date(2026, 8, 25),
    )

    assert result.estimate_w == Decimal(205)
    assert result.eligible_days == 7
    assert result.unavailable_reason is None


def test_rolling_estimate_averages_middle_values_for_even_day_count() -> None:
    """An even eligible-day count should use the exact midpoint average."""
    summaries = tuple(
        _summary(day, estimate)
        for day, estimate in zip(
            (20, 21, 22, 23, 24, 25),
            ("100", "200", "300", "400", "500", "600"),
        )
    )

    result = calculate_base_load_estimate(
        summaries,
        window_end=date(2026, 8, 25),
    )

    assert result.estimate_w == Decimal(350)


def test_daily_summary_round_trip_and_invalid_storage() -> None:
    """Daily summaries should persist losslessly and reject corrupt data."""
    summary = _summary(25, "212.5")
    assert DailyBaseLoadSummary.from_dict(summary.as_dict()) == summary

    with pytest.raises(ValueError, match="invalid daily base-load summary"):
        DailyBaseLoadSummary.from_dict({"period_start": "bad"})


@pytest.mark.parametrize(
    ("power", "duration"),
    [
        (Decimal("-1"), timedelta(minutes=15)),
        (Decimal("NaN"), timedelta(minutes=15)),
        (Decimal(100), timedelta(0)),
    ],
)
def test_power_interval_rejects_invalid_values(
    power: Decimal,
    duration: timedelta,
) -> None:
    """Invalid normalized power must not enter the estimator."""
    with pytest.raises(ValueError, match="invalid power interval"):
        PowerInterval(power, duration)


def test_accumulator_splits_local_days_and_round_trips() -> None:
    """Aggregates should survive storage and split exactly at local midnight."""
    timezone = ZoneInfo("Europe/Stockholm")
    accumulator = BaseLoadBucketAccumulator(timezone)
    start = datetime(2026, 8, 24, 23, 55, tzinfo=timezone)
    accumulator.add_segment(
        start=start,
        end=start + timedelta(minutes=10),
        power_w=Decimal(600),
    )

    assert sum(
        (
            interval.covered_duration
            for interval in accumulator.intervals_for_date(date(2026, 8, 24))
        ),
        timedelta(0),
    ) == timedelta(minutes=5)
    assert sum(
        (
            interval.covered_duration
            for interval in accumulator.intervals_for_date(date(2026, 8, 25))
        ),
        timedelta(0),
    ) == timedelta(minutes=5)
    assert (
        BaseLoadBucketAccumulator.from_dict(timezone, accumulator.as_dict()).as_dict()
        == accumulator.as_dict()
    )


def test_accumulator_marks_negative_power_without_fabricating_coverage() -> None:
    """Export-like negative power should reject its day rather than be clamped."""
    timezone = ZoneInfo("Europe/Stockholm")
    accumulator = BaseLoadBucketAccumulator(timezone)
    start = datetime(2026, 8, 24, 10, tzinfo=UTC)
    accumulator.add_segment(
        start=start,
        end=start + timedelta(minutes=5),
        power_w=Decimal(-100),
    )
    local_date = start.astimezone(timezone).date()

    assert accumulator.bidirectional_observed(local_date)
    assert accumulator.intervals_for_date(local_date) == ()
