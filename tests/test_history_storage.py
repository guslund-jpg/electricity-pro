"""Stored history must narrow JSON shapes before validating model values."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from custom_components.electricity_pro.base_load import (
    BaseLoadBucketAccumulator,
    DailyBaseLoadSummary,
)
from custom_components.electricity_pro.statistics_engine import (
    DailyPeakSnapshot,
    StatisticsSnapshot,
)
from custom_components.electricity_pro.timing_score import (
    TimingBucketAccumulator,
    TimingScoreResult,
)


@pytest.mark.parametrize("model", [BaseLoadBucketAccumulator, TimingBucketAccumulator])
@pytest.mark.parametrize("field", ["buckets", "covered_ranges"])
@pytest.mark.parametrize("invalid", [None, "", {}, 1, [None], [1], [{}], [{1: "bad"}]])
def test_history_rejects_malformed_collections(model, field, invalid):
    """Even empty non-arrays and non-record items are corrupt history."""
    data = {"buckets": [], "covered_ranges": [], "bidirectional_dates": []}
    model.from_dict(UTC, data)
    data[field] = invalid
    with pytest.raises(ValueError, match="invalid .*bucket history"):
        model.from_dict(UTC, data)


@pytest.mark.parametrize("model", [BaseLoadBucketAccumulator, TimingBucketAccumulator])
@pytest.mark.parametrize("populated", [False, True])
def test_history_json_round_trip(model, populated):
    """JSON storage preserves aggregate precision, including negative prices."""
    accumulator = model(UTC)
    start = datetime(2026, 8, 25, 10, tzinfo=UTC)
    if populated:
        kwargs = (
            {"effective_price": Decimal("-1.123456789")}
            if model is TimingBucketAccumulator
            else {}
        )
        accumulator.add_segment(
            start=start,
            end=start + timedelta(minutes=15),
            power_w=Decimal("1234.56789"),
            **kwargs,
        )
    serialized = accumulator.as_dict()
    restored = model.from_dict(UTC, json.loads(json.dumps(serialized)))
    assert restored.as_dict() == serialized
    assert restored.intervals_for_date(start.date()) == accumulator.intervals_for_date(
        start.date()
    )


@pytest.mark.parametrize("invalid", [None, "", {}, [None], [123]])
def test_base_load_rejects_malformed_bidirectional_dates(invalid):
    with pytest.raises(ValueError, match="invalid base-load bucket history"):
        BaseLoadBucketAccumulator.from_dict(
            UTC, {"buckets": [], "covered_ranges": [], "bidirectional_dates": invalid}
        )


@pytest.mark.parametrize("value", ["1.25", 1, 1.25, Decimal("1.25"), True])
def test_snapshot_retains_legacy_numeric_conversion(value):
    """Do not round floats or change historically accepted scalar conversion."""
    snapshot = StatisticsSnapshot.from_dict(
        {"period_start": "2026-08-25", "last_value": value, "value": value}
    )
    assert snapshot.last_value == snapshot.value == Decimal(value)


@pytest.mark.parametrize(
    ("model", "data", "field"),
    [
        (
            StatisticsSnapshot,
            {"period_start": "2026-08-25", "last_value": "1", "value": "1"},
            "value",
        ),
        (
            DailyPeakSnapshot,
            {
                "period_start": "2026-08-25",
                "peak_time": "2026-08-25T10:00:00+00:00",
                "peak_power_w": "800",
            },
            "peak_power_w",
        ),
        (
            DailyBaseLoadSummary,
            {
                "period_start": "2026-08-25",
                "estimate_w": "200",
                "coverage_percent": "100",
                "longest_uncovered_gap_seconds": "0",
            },
            "estimate_w",
        ),
        (
            TimingScoreResult,
            {"score": "50", "coverage_percent": "100", "energy_kwh": "1"},
            "score",
        ),
    ],
)
@pytest.mark.parametrize("invalid", [[], {}, "not-a-number", "NaN", "Infinity"])
def test_readers_reject_malformed_and_nonfinite_numbers(model, data, field, invalid):
    model.from_dict(data)
    with pytest.raises(ValueError, match="invalid"):
        model.from_dict({**data, field: invalid})


@pytest.mark.parametrize("invalid", [None, [], {}, date(2026, 8, 25)])
def test_snapshot_requires_serialized_date(invalid):
    with pytest.raises(ValueError, match="invalid statistics snapshot"):
        StatisticsSnapshot.from_dict(
            {"period_start": invalid, "last_value": "1", "value": "1"}
        )
