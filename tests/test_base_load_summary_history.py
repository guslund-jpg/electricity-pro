"""Characterize completed base-load summaries before ownership extraction."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.base_load import BaseLoadUnavailableReason
from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator

_SUMMARY_KEY = "base_load_daily_summaries"
_DAYS = [date(2026, 11, 7), date(2026, 3, 29), date(2026, 10, 25)]


@pytest.fixture
async def coordinator(hass):
    await hass.config.async_set_time_zone("Europe/Stockholm")
    entry = MockConfigEntry(domain=DOMAIN, data={"power_entity": "sensor.power"})
    return ElectricityProCoordinator(hass, entry)


def _row(day, estimate="250.00"):
    """Keep the pre-extraction five-field storage shape explicit."""
    return {
        "period_start": day.isoformat(),
        "estimate_w": estimate,
        "unavailable_reason": None,
        "coverage_percent": "100",
        "longest_uncovered_gap_seconds": "0.0",
    }


async def _restore(coordinator, stored):
    """Round-trip JSON to exercise the same shapes as existing HA storage."""
    payload = json.loads(json.dumps(stored))
    with patch.object(
        coordinator._store, "async_load", AsyncMock(return_value=payload)
    ):
        await coordinator._async_restore_statistics()


@pytest.mark.parametrize("day", _DAYS)
@pytest.mark.parametrize("quality", ["complete", "half-covered", "bidirectional"])
def test_finalized_summary_preserves_calendar_coverage_and_decimal_shape(
    coordinator, day, quality
):
    zone = coordinator._local_timezone
    start = datetime.combine(day, datetime.min.time(), tzinfo=zone)
    end = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    duration = end.astimezone(UTC) - start.astimezone(UTC)
    segment_end = (
        start.astimezone(UTC) + duration / 2 if quality == "half-covered" else end
    )
    coordinator._base_load_buckets.add_segment(
        start=start,
        end=segment_end,
        power_w=Decimal(-1) if quality == "bidirectional" else Decimal("250.00"),
    )
    coordinator._finalize_base_load_day(day)

    expected = _row(day)
    if quality == "half-covered":
        expected.update(
            estimate_w=None,
            unavailable_reason="insufficient_coverage",
            coverage_percent="50.0",
            longest_uncovered_gap_seconds=f"{int(duration.total_seconds()) // 2}.0",
        )
    elif quality == "bidirectional":
        expected.update(
            estimate_w=None,
            unavailable_reason="unsupported_bidirectional_power",
            coverage_percent="0E+1",
            longest_uncovered_gap_seconds=f"{int(duration.total_seconds())}.0",
        )
    assert coordinator._statistics_data()[_SUMMARY_KEY] == [expected]
    result = coordinator.estimated_base_load
    assert result.window_end == day
    assert result.window_start == day - timedelta(days=6)
    assert result.eligible_days == (1 if quality == "complete" else 0)
    assert result.unavailable_reason is BaseLoadUnavailableReason.INSUFFICIENT_HISTORY


@pytest.mark.parametrize(
    "count,expected", [(4, None), (5, "120.00"), (6, "125.00"), (7, "130.00")]
)
async def test_old_json_summaries_preserve_five_day_gate_and_rolling_median(
    coordinator, count, expected
):
    end = date(2026, 11, 7)
    start = end - timedelta(days=6)
    rows = [
        _row(start + timedelta(days=i), str(Decimal("100.00") + 10 * i))
        for i in range(count)
    ]
    await _restore(coordinator, {_SUMMARY_KEY: list(reversed(rows))})
    assert coordinator.estimated_base_load is None
    assert coordinator._statistics_data()[_SUMMARY_KEY] == rows
    coordinator._recalculate_base_load(end)
    result = coordinator.estimated_base_load
    assert result.estimate_w == (None if expected is None else Decimal(expected))
    assert result.eligible_days == count
    assert result.required_days == 5
    assert result.window_start == start
    assert result.window_end == end
    assert result.daily_estimates == tuple(
        (date.fromisoformat(row["period_start"]), Decimal(row["estimate_w"]))
        for row in rows
    )
    assert coordinator._statistics_data()[_SUMMARY_KEY] == rows


async def test_recalculation_keeps_exactly_the_existing_seven_day_window(coordinator):
    end = date(2026, 11, 7)
    rows = [
        _row(end + timedelta(days=i), str(Decimal("170.00") + 10 * i))
        for i in range(-7, 2)
    ]
    await _restore(coordinator, {_SUMMARY_KEY: list(reversed(rows))})
    coordinator._recalculate_base_load(end)
    assert coordinator._statistics_data()[_SUMMARY_KEY] == rows[1:-1]
    assert coordinator.estimated_base_load.eligible_days == 7
    assert coordinator.estimated_base_load.estimate_w == Decimal("140.00")


async def test_valid_restore_leaves_result_until_explicit_recalculation(coordinator):
    end = date(2026, 11, 7)
    rows = [_row(end - timedelta(days=i)) for i in range(5)]
    await _restore(coordinator, {_SUMMARY_KEY: rows})
    coordinator._recalculate_base_load(end)
    result = coordinator.estimated_base_load
    assert result.estimate_w == Decimal("250.00")
    await _restore(coordinator, {_SUMMARY_KEY: [_row(end, "999.00")]})
    assert coordinator.estimated_base_load is result
    coordinator._recalculate_base_load(end)
    assert coordinator.estimated_base_load.estimate_w is None
    assert coordinator.estimated_base_load.eligible_days == 1


@pytest.mark.parametrize(
    "invalid",
    [
        "duplicate-date",
        "missing-date",
        "nan-coverage",
        "unknown-reason",
        "excess-coverage",
        "negative-gap",
    ],
)
async def test_invalid_restore_is_atomic_and_keeps_existing_history(
    coordinator, caplog, invalid
):
    day = date(2026, 11, 7)
    await _restore(coordinator, {_SUMMARY_KEY: [_row(day)]})
    coordinator._recalculate_base_load(day)
    result = coordinator.estimated_base_load
    before = coordinator._statistics_data()[_SUMMARY_KEY]
    changed = _row(day - timedelta(days=1))
    if invalid == "missing-date":
        changed.pop("period_start")
    elif invalid == "nan-coverage":
        changed["coverage_percent"] = "NaN"
    elif invalid == "unknown-reason":
        changed["unavailable_reason"] = "unexpected"
    elif invalid == "excess-coverage":
        changed["coverage_percent"] = "101"
    elif invalid == "negative-gap":
        changed["longest_uncovered_gap_seconds"] = "-1"
    rows = (
        [changed, changed]
        if invalid == "duplicate-date"
        else [_row(day + timedelta(days=1)), changed]
    )
    await _restore(coordinator, {_SUMMARY_KEY: rows})
    assert "Ignoring invalid persisted base-load summaries" in caplog.text
    assert coordinator._statistics_data()[_SUMMARY_KEY] == before
    assert coordinator.estimated_base_load is result


@pytest.mark.parametrize("old_value", [None, {}, "legacy"])
async def test_non_list_summary_storage_retains_existing_ignore_behavior(
    coordinator, old_value
):
    await _restore(coordinator, {_SUMMARY_KEY: old_value})
    assert coordinator._statistics_data()[_SUMMARY_KEY] == []
    assert coordinator.estimated_base_load is None


@pytest.mark.parametrize("stored_gap", ["0", "0.0"])
async def test_serialized_summary_rows_are_fresh(coordinator, stored_gap):
    row = _row(date(2026, 11, 7))
    await _restore(
        coordinator,
        {_SUMMARY_KEY: [{**row, "longest_uncovered_gap_seconds": stored_gap}]},
    )
    stored = coordinator._statistics_data()[_SUMMARY_KEY]
    stored[0]["estimate_w"] = "999"
    stored.append(_row(date(2026, 11, 8)))
    assert coordinator._statistics_data()[_SUMMARY_KEY] == [row]


@pytest.mark.parametrize("day", _DAYS)
async def test_restart_finalizes_previous_day_before_retaining_current_buckets(
    coordinator, hass, day
):
    zone = coordinator._local_timezone
    start = datetime.combine(day, datetime.min.time(), tzinfo=zone)
    next_start = datetime.combine(
        day + timedelta(days=1), datetime.min.time(), tzinfo=zone
    )
    coordinator._base_load_buckets.add_segment(
        start=start, end=next_start, power_w=Decimal("222.00")
    )
    coordinator._base_load_buckets.add_segment(
        start=next_start, end=next_start + timedelta(minutes=30), power_w=Decimal(100)
    )
    stored = coordinator._statistics_data()
    restored = ElectricityProCoordinator(
        hass, MockConfigEntry(domain=DOMAIN, data={"power_entity": "sensor.power"})
    )
    await _restore(restored, stored)
    assert restored.estimated_base_load is None
    restored._finalize_restored_base_load_days(day + timedelta(days=1))
    assert restored._statistics_data()[_SUMMARY_KEY] == [_row(day, "222.00")]
    assert restored._base_load_buckets.intervals_for_date(day) == ()
    assert restored._base_load_buckets.intervals_for_date(day + timedelta(days=1))
    assert restored.estimated_base_load.window_end == day
    assert restored.estimated_base_load.eligible_days == 1


def test_new_summary_history_starts_without_a_result(coordinator):
    assert coordinator.estimated_base_load is None
    assert coordinator._statistics_data()[_SUMMARY_KEY] == []
