"""Exercise coverage compaction through both live and restored histories."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from custom_components.electricity_pro.base_load import BaseLoadBucketAccumulator
from custom_components.electricity_pro.timing_score import TimingBucketAccumulator


@pytest.fixture(params=[BaseLoadBucketAccumulator, TimingBucketAccumulator])
def accumulator(request):
    return request.param(UTC)


def add_segment(accumulator, start, end):
    args = {"start": start, "end": end, "power_w": Decimal(600)}
    if isinstance(accumulator, TimingBucketAccumulator):
        args["effective_price"] = Decimal(1)
    accumulator.add_segment(**args)


def test_continuous_samples_are_compacted_without_losing_a_gap(accumulator):
    """Persist connected coverage runs instead of one range per reading."""
    start = datetime(2026, 11, 6, tzinfo=UTC)
    step = timedelta(milliseconds=500)
    cursor = start
    for _ in range(1800):
        add_segment(accumulator, cursor, cursor + step)
        cursor += step
    gap = timedelta(minutes=5)
    end = cursor + gap + step
    add_segment(accumulator, cursor + gap, end)

    assert len(accumulator.as_dict()["covered_ranges"]) == 2
    assert (
        accumulator.longest_uncovered_gap(start.date(), day_start=start, day_end=end)
        == gap
    )
    assert (
        sum(
            (
                interval.covered_duration
                for interval in accumulator.intervals_for_date(start.date())
            ),
            timedelta(0),
        )
        == timedelta(minutes=15) + step
    )


def test_restore_compacts_unordered_legacy_ranges_without_changing_totals(accumulator):
    """Older overlapping and unsorted ranges restore to the same coverage."""
    start = datetime(2026, 11, 6, tzinfo=UTC)
    end = start + timedelta(seconds=60)
    add_segment(accumulator, start, start + timedelta(seconds=30))
    add_segment(accumulator, start + timedelta(seconds=50), end)
    expected = accumulator.as_dict()
    old_ranges = [
        {
            "period_start": start.date().isoformat(),
            "start": (start + timedelta(seconds=left)).isoformat(),
            "end": (start + timedelta(seconds=right)).isoformat(),
        }
        for left, right in [(0, 5), (15, 30), (50, 60), (4, 16), (10, 12), (55, 60)]
    ]
    restored = type(accumulator).from_dict(
        UTC, {**expected, "covered_ranges": old_ranges}
    )

    assert restored.as_dict() == expected
    assert restored.intervals_for_date(start.date()) == accumulator.intervals_for_date(
        start.date()
    )
    assert restored.longest_uncovered_gap(
        start.date(), day_start=start, day_end=end
    ) == timedelta(seconds=20)
