"""Tests for the pure Consumption Timing Score models."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from custom_components.electricity_pro.timing_score import (
    CompletedTimingScore,
    TimingBucketAccumulator,
    TimingInterval,
    TimingObservation,
    TimingScoreRating,
    TimingScoreUnavailableReason,
    calculate_timing_score,
)


def _interval(energy: str, price: str, minutes: int = 15) -> TimingInterval:
    """Create a timing interval for tests."""
    return TimingInterval(
        energy_kwh=Decimal(energy),
        effective_price=Decimal(price),
        covered_duration=timedelta(minutes=minutes),
    )


@pytest.mark.parametrize(
    ("energies", "expected_score", "expected_rating"),
    [
        (("4", "0", "0", "0"), Decimal(88), TimingScoreRating.WELL_TIMED),
        (("1", "1", "1", "1"), Decimal(50), TimingScoreRating.MIXED_TIMING),
        (("0", "0", "0", "4"), Decimal(13), TimingScoreRating.COSTLY_TIMING),
    ],
)
def test_score_worked_examples(
    energies: tuple[str, ...],
    expected_score: Decimal,
    expected_rating: TimingScoreRating,
) -> None:
    """Cheap, uniform, and expensive timing should match the ADR examples."""
    intervals = tuple(
        _interval(energy, price, minutes=360)
        for energy, price in zip(energies, ("1", "2", "3", "4"), strict=True)
    )

    result = calculate_timing_score(
        intervals,
        period_duration=timedelta(hours=24),
        longest_uncovered_gap=timedelta(0),
    )

    assert result.score == expected_score
    assert result.rating is expected_rating
    assert result.unavailable_reason is None


def test_score_handles_tied_and_negative_prices() -> None:
    """Exact ties should share a rank and negative prices should remain valid."""
    result = calculate_timing_score(
        (
            _interval("2", "-1", 360),
            _interval("2", "-1", 360),
            _interval("0", "1", 360),
            _interval("0", "2", 360),
        ),
        period_duration=timedelta(hours=24),
        longest_uncovered_gap=timedelta(0),
    )
    assert result.score == Decimal(75)
    assert result.rating is TimingScoreRating.WELL_TIMED


def test_score_rejects_bidirectional_power_day() -> None:
    """Net export makes an imported-consumption timing score unsupported."""
    result = calculate_timing_score(
        (_interval("1", "1", 43200), _interval("1", "2", 43200)),
        period_duration=timedelta(days=1),
        longest_uncovered_gap=timedelta(0),
        bidirectional_power_observed=True,
    )

    assert result.score is None
    assert (
        result.unavailable_reason
        is TimingScoreUnavailableReason.UNSUPPORTED_BIDIRECTIONAL_POWER
    )
    assert result.rating is None
    assert type(result).from_dict(result.as_dict()) == result


@pytest.mark.parametrize(
    ("intervals", "period", "gap", "reason"),
    [
        (
            (_interval("1", "1", 1200), _interval("1", "2", 60)),
            timedelta(hours=24),
            timedelta(minutes=30),
            TimingScoreUnavailableReason.INSUFFICIENT_COVERAGE,
        ),
        (
            (_interval("1", "1", 720), _interval("1", "2", 720)),
            timedelta(hours=24),
            timedelta(minutes=61),
            TimingScoreUnavailableReason.LONG_DATA_GAP,
        ),
        (
            (_interval("0", "1", 720), _interval("0", "2", 720)),
            timedelta(hours=24),
            timedelta(0),
            TimingScoreUnavailableReason.NO_CONSUMPTION,
        ),
        (
            (_interval("1", "1", 720), _interval("1", "1.01", 720)),
            timedelta(hours=24),
            timedelta(0),
            TimingScoreUnavailableReason.INSUFFICIENT_PRICE_VARIATION,
        ),
    ],
)
def test_score_unavailable_reasons(
    intervals: tuple[TimingInterval, ...],
    period: timedelta,
    gap: timedelta,
    reason: TimingScoreUnavailableReason,
) -> None:
    """Each data-quality rule should return its explicit reason."""
    result = calculate_timing_score(
        intervals,
        period_duration=period,
        longest_uncovered_gap=gap,
    )
    assert result.score is None
    assert result.unavailable_reason is reason


@pytest.mark.parametrize("hours", [23, 25])
def test_score_uses_actual_dst_day_duration(hours: int) -> None:
    """Coverage should use the supplied 23-hour or 25-hour local day."""
    result = calculate_timing_score(
        (_interval("1", "1", hours * 30), _interval("1", "2", hours * 30)),
        period_duration=timedelta(hours=hours),
        longest_uncovered_gap=timedelta(0),
    )
    assert result.coverage_percent == Decimal(100)
    assert result.score == Decimal(50)


def test_bucket_accumulator_splits_and_aggregates_segments() -> None:
    """Segments should be split into ordered 15-minute aggregate intervals."""
    accumulator = TimingBucketAccumulator(ZoneInfo("Europe/Stockholm"))
    start = datetime(2026, 8, 25, 10, 5, tzinfo=UTC)
    accumulator.add_segment(
        start=start,
        end=start + timedelta(minutes=20),
        power_w=Decimal("3000"),
        effective_price=Decimal("1.5"),
    )

    intervals = accumulator.intervals_for_date(date(2026, 8, 25))
    assert len(intervals) == 2
    assert [interval.covered_duration for interval in intervals] == [
        timedelta(minutes=10),
        timedelta(minutes=10),
    ]
    assert sum((interval.energy_kwh for interval in intervals), Decimal(0)) == Decimal(
        1
    )
    assert all(interval.effective_price == Decimal("1.5") for interval in intervals)


def test_bucket_accumulator_averages_price_by_duration() -> None:
    """Multiple prices in one bucket should produce a duration-weighted average."""
    accumulator = TimingBucketAccumulator(UTC)
    start = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)
    accumulator.add_segment(
        start=start,
        end=start + timedelta(minutes=5),
        power_w=Decimal("1000"),
        effective_price=Decimal("1"),
    )
    accumulator.add_segment(
        start=start + timedelta(minutes=5),
        end=start + timedelta(minutes=15),
        power_w=Decimal("1000"),
        effective_price=Decimal("2"),
    )

    interval = accumulator.intervals_for_date(date(2026, 8, 25))[0]
    assert interval.energy_kwh == Decimal("0.25")
    assert interval.effective_price == Decimal(5) / Decimal(3)


def test_bucket_history_and_result_round_trip() -> None:
    """Persisted aggregate history and a valid result should restore losslessly."""
    accumulator = TimingBucketAccumulator(UTC)
    start = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)
    accumulator.add_segment(
        start=start,
        end=start + timedelta(minutes=15),
        power_w=Decimal("1000"),
        effective_price=Decimal("1.5"),
    )
    restored = TimingBucketAccumulator.from_dict(UTC, accumulator.as_dict())
    assert restored.intervals_for_date(date(2026, 8, 25)) == (_interval("0.25", "1.5"),)
    assert restored.longest_uncovered_gap(
        date(2026, 8, 25),
        day_start=start,
        day_end=start + timedelta(minutes=15),
    ) == timedelta(0)

    result = calculate_timing_score(
        (_interval("1", "1", 720), _interval("1", "2", 720)),
        period_duration=timedelta(hours=24),
        longest_uncovered_gap=timedelta(0),
    )
    assert type(result).from_dict(result.as_dict()) == result


def test_bucket_history_rejects_invalid_storage() -> None:
    """Corrupt aggregate history must not enter the runtime accumulator."""
    with pytest.raises(ValueError, match="invalid timing bucket history"):
        TimingBucketAccumulator.from_dict(
            UTC,
            {"buckets": [{"period_start": "bad"}], "covered_ranges": []},
        )


@pytest.mark.parametrize(
    ("power", "price"),
    [(Decimal("-1"), Decimal("1")), (Decimal("1"), Decimal("NaN"))],
)
def test_bucket_accumulator_rejects_invalid_segments(
    power: Decimal,
    price: Decimal,
) -> None:
    """Invalid normalized inputs must not enter timing history."""
    accumulator = TimingBucketAccumulator(UTC)
    start = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="invalid timing segment"):
        accumulator.add_segment(
            start=start,
            end=start + timedelta(minutes=5),
            power_w=power,
            effective_price=price,
        )


@pytest.mark.parametrize("bidirectional", [False, True])
def test_completed_score_leaves_bucket_retention_to_caller(bidirectional: bool) -> None:
    """Finalization reads history and an explicit export marker without pruning."""
    buckets = TimingBucketAccumulator(UTC)
    start = datetime(2026, 8, 24, tzinfo=UTC)
    for index in range(2):
        buckets.add_segment(
            start=start + timedelta(hours=12 * index),
            end=start + timedelta(hours=12 * (index + 1)),
            power_w=Decimal(1000),
            effective_price=Decimal(index + 1),
        )
    buckets.add_segment(
        start=start + timedelta(days=1),
        end=start + timedelta(days=1, minutes=15),
        power_w=Decimal(1000),
        effective_price=Decimal(2),
    )
    before = buckets.as_dict()
    completed = CompletedTimingScore(UTC)

    completed.finalize_day(
        start.date(), buckets, bidirectional_power_observed=bidirectional
    )

    assert buckets.as_dict() == before
    assert completed.result is not None
    assert completed.result[0] == start.date()
    result = completed.result[1]
    assert result.coverage_percent == Decimal(100)
    assert result.energy_kwh == Decimal(24)
    if bidirectional:
        assert result.score is None
        assert (
            result.unavailable_reason
            is TimingScoreUnavailableReason.UNSUPPORTED_BIDIRECTIONAL_POWER
        )
    else:
        assert result.score == Decimal(50)
        assert result.unavailable_reason is None


def test_completed_score_storage_containers_do_not_alias_result() -> None:
    """Mutating input or saved mappings must not change the owned result."""
    completed = CompletedTimingScore(UTC)
    assert completed.result is None
    assert completed.as_dict() is None
    source = calculate_timing_score(
        (_interval("1", "1", 720), _interval("1", "2", 720)),
        period_duration=timedelta(hours=24),
        longest_uncovered_gap=timedelta(0),
    ).as_dict()
    completed.restore(period_start="2026-08-24", result=source)
    expected = completed.result
    saved = completed.as_dict()
    assert saved is not None
    source["score"] = "0"
    saved["period_start"] = "2026-08-25"
    saved["result"]["score"] = "100"

    assert completed.result == expected
    assert completed.as_dict()["period_start"] == "2026-08-24"
    assert completed.as_dict()["result"]["score"] == "50"
    completed.clear()
    assert completed.result is None
    assert completed.as_dict() is None


def test_live_timing_observation_uses_supplied_history_and_explicit_price() -> None:
    """A restored accumulator receives future intervals; a price alone is not power."""
    start = datetime(2026, 8, 24, tzinfo=UTC)
    observation = TimingObservation()
    original = TimingBucketAccumulator(UTC)

    def advance(observer, buckets, minute, *, observed=False):
        return observer.advance(
            start + timedelta(minutes=minute),
            buckets,
            power_w=Decimal(600),
            power_observed=observed,
            maximum_hold=timedelta(minutes=10),
        )

    advance(observation, original, 0, observed=True)
    observation.set_effective_price(Decimal(1))
    advance(observation, original, 5)
    restored = TimingBucketAccumulator.from_dict(UTC, original.as_dict())
    observation.set_effective_price(Decimal(2))
    advance(observation, restored, 8)

    assert original.intervals_for_date(start.date()) == (
        TimingInterval(Decimal("0.05"), Decimal(1), timedelta(minutes=5)),
    )
    assert restored.intervals_for_date(start.date()) == (
        TimingInterval(Decimal("0.08"), Decimal("1.375"), timedelta(minutes=8)),
    )
    before = restored.as_dict()
    fresh = TimingObservation()
    fresh.set_effective_price(Decimal(3))
    assert not advance(fresh, restored, 9)
    assert restored.as_dict() == before
