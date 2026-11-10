"""Verify hourly demand charge selection, coverage and calendar boundaries."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from custom_components.electricity_pro.demand_charge import (
    HourlyDemandTariff,
    HourlyImportBlock,
    estimate_hourly_demand_charge,
)

STOCKHOLM = ZoneInfo("Europe/Stockholm")
NOVEMBER = date(2026, 11, 1)


def local(month: int, day: int, hour: int, *, fold: int = 0) -> datetime:
    return datetime(2026, month, day, hour, tzinfo=STOCKHOLM, fold=fold)


def block(start: datetime, energy: str) -> HourlyImportBlock:
    end = start.astimezone(UTC) + timedelta(hours=1)
    return HourlyImportBlock(start, end, Decimal(energy))


def test_selects_highest_block_from_each_eligible_day() -> None:
    tariff = HourlyDemandTariff(
        STOCKHOLM,
        3,
        Decimal(80),
        "SEK",
        weekdays=frozenset(range(5)),
        start_hour=8,
        end_hour=10,
    )
    measured = [
        block(local(11, 4, 9), "3"),
        block(local(11, 4, 8), "4"),
        block(local(11, 3, 9), "5"),
        block(local(11, 3, 8), "5"),
        block(local(11, 2, 9), "5.5"),
        block(local(11, 2, 8), "6"),
        block(local(11, 2, 7), "99"),
        block(local(11, 2, 10), "99"),
        block(local(11, 1, 8), "99"),
    ]
    estimate = estimate_hourly_demand_charge(
        tariff, NOVEMBER, local(11, 4, 10), measured
    )

    assert estimate.peaks == (measured[5], measured[3], measured[1])
    assert estimate.average_peak_kw == Decimal(5)
    assert estimate.amount == Decimal(400)
    assert estimate.currency == "SEK"
    assert (estimate.observed_blocks, estimate.eligible_blocks) == (6, 6)
    assert not estimate.partial


def test_missing_blocks_are_counted_only_after_they_close() -> None:
    tariff = HourlyDemandTariff(
        STOCKHOLM, 2, Decimal(80), "SEK", start_hour=8, end_hour=10
    )
    peak = block(local(11, 1, 8), "4")
    off_boundary = block(local(11, 1, 9).replace(minute=15), "90")
    future = block(local(11, 2, 9), "100")
    cutoff = local(11, 2, 9).replace(minute=30)
    missing_day = estimate_hourly_demand_charge(
        tariff, NOVEMBER, cutoff, [peak, off_boundary, future]
    )
    assert missing_day.peaks == (peak,)
    assert missing_day.amount is None
    assert (missing_day.observed_blocks, missing_day.eligible_blocks) == (1, 3)
    assert missing_day.partial

    measured_zero = block(local(11, 2, 8), "0")
    partial = estimate_hourly_demand_charge(
        tariff, NOVEMBER, cutoff, [peak, measured_zero, future]
    )
    assert partial.peaks == (peak, measured_zero)
    assert partial.amount == Decimal(160)
    assert (partial.observed_blocks, partial.eligible_blocks) == (2, 3)
    assert partial.partial


def test_zero_import_counts_and_conflicting_duplicates_leave_a_gap() -> None:
    tariff = HourlyDemandTariff(
        STOCKHOLM, 1, Decimal(80), "SEK", start_hour=8, end_hour=10
    )
    first = block(local(11, 1, 8), "0")
    second = block(local(11, 1, 9), "0")
    closed = local(11, 1, 10)
    estimate = estimate_hourly_demand_charge(
        tariff, NOVEMBER, closed, [first, first, second]
    )
    assert estimate.amount == Decimal(0)
    assert (estimate.observed_blocks, estimate.eligible_blocks) == (2, 2)
    assert not estimate.partial

    conflict = block(local(11, 1, 8), "9")
    estimate = estimate_hourly_demand_charge(
        tariff, NOVEMBER, closed, [conflict, first, conflict, second]
    )
    assert estimate.peaks == (second,)
    assert estimate.amount == Decimal(0)
    assert (estimate.observed_blocks, estimate.eligible_blocks) == (1, 2)
    assert estimate.partial


def test_spring_clock_gap_does_not_create_a_missing_block() -> None:
    tariff = HourlyDemandTariff(
        STOCKHOLM,
        1,
        Decimal(80),
        "SEK",
        weekdays=frozenset({6}),
        start_hour=1,
        end_hour=4,
    )
    first = HourlyImportBlock(local(3, 29, 1), local(3, 29, 3), Decimal(3))
    second = block(local(3, 29, 3), "2")
    month = date(2026, 3, 1)
    before = estimate_hourly_demand_charge(tariff, month, local(3, 29, 1), [])
    after = estimate_hourly_demand_charge(
        tariff, month, local(3, 29, 4), [first, second]
    )

    assert after.eligible_blocks - before.eligible_blocks == 2
    assert after.observed_blocks == 2
    assert after.peaks == (first,)
    assert first.average_kw == Decimal(3)
    assert after.amount == Decimal(240)


def test_autumn_repeated_hour_counts_twice_but_shares_one_daily_peak() -> None:
    tariff = HourlyDemandTariff(
        STOCKHOLM,
        2,
        Decimal(80),
        "SEK",
        weekdays=frozenset({6}),
        start_hour=2,
        end_hour=3,
    )
    first_start = local(10, 25, 2)
    second_start = local(10, 25, 2, fold=1)
    first = HourlyImportBlock(first_start, second_start, Decimal(8))
    second = HourlyImportBlock(second_start, local(10, 25, 3), Decimal(10))
    previous_day = block(local(10, 18, 2), "4")
    month = date(2026, 10, 1)
    halfway = estimate_hourly_demand_charge(
        tariff, month, second_start, [first, second, previous_day]
    )
    after = estimate_hourly_demand_charge(
        tariff, month, local(10, 25, 3), [first, second, previous_day]
    )

    assert first.start == datetime(2026, 10, 25, 0, tzinfo=UTC)
    assert second.start == datetime(2026, 10, 25, 1, tzinfo=UTC)
    assert (halfway.observed_blocks, halfway.eligible_blocks) == (2, 4)
    assert (after.observed_blocks, after.eligible_blocks) == (3, 5)
    assert after.peaks == (second, previous_day)
    assert after.amount == Decimal(560)


def test_month_rollover_keeps_the_hour_ending_at_midnight_in_the_old_period() -> None:
    tariff = HourlyDemandTariff(STOCKHOLM, 1, Decimal(80), "SEK")
    last_hour = block(local(11, 30, 23), "6")
    first_hour = block(local(12, 1, 0), "2")
    measured = [last_hour, first_hour]
    december = date(2026, 12, 1)
    old = estimate_hourly_demand_charge(tariff, NOVEMBER, local(12, 1, 0), measured)
    at_midnight = estimate_hourly_demand_charge(
        tariff, december, local(12, 1, 0), measured
    )
    new = estimate_hourly_demand_charge(tariff, december, local(12, 1, 1), measured)

    assert (old.period_start, old.period_end) == (NOVEMBER, date(2026, 11, 30))
    assert old.peaks == (last_hour,)
    assert old.amount == Decimal(480)
    assert (at_midnight.observed_blocks, at_midnight.eligible_blocks) == (0, 0)
    assert at_midnight.amount is None
    assert new.peaks == (first_hour,)
    assert new.amount == Decimal(160)
    assert (new.observed_blocks, new.eligible_blocks) == (1, 1)


def test_rejects_short_blocks_and_nonexistent_local_timestamps() -> None:
    with pytest.raises(ValueError, match="span one elapsed hour"):
        HourlyImportBlock(
            local(11, 1, 8), local(11, 1, 8).replace(minute=45), Decimal(2)
        )
    with pytest.raises(ValueError, match="local clock gap"):
        HourlyImportBlock(local(3, 29, 2), local(3, 29, 4), Decimal(2))


def test_rejects_an_eligible_block_crossing_a_half_hour_clock_change() -> None:
    lord_howe = ZoneInfo("Australia/Lord_Howe")
    tariff = HourlyDemandTariff(lord_howe, 1, Decimal(80), "AUD")
    with pytest.raises(ValueError, match="between local hour boundaries"):
        estimate_hourly_demand_charge(
            tariff,
            date(2026, 10, 1),
            datetime(2026, 10, 5, 0, tzinfo=lord_howe),
            [],
        )
