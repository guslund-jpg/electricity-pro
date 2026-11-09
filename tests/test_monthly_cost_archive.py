"""Verify calendar-keyed chart data and its optional checkpoint section."""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from custom_components.electricity_pro.monthly_cost_archive import (
    MonthlyVariableCostArchive,
)
from custom_components.electricity_pro.pricing import VariableCostComponent


def local(month, day=1, hour=0, *, year=2026):
    return datetime(year, month, day, hour, tzinfo=ZoneInfo("Europe/Stockholm"))


def record(archive, start, end, amount="0"):
    archive.record(
        start,
        end,
        "SEK",
        Decimal(1),
        ((VariableCostComponent.BUNDLED_PRICE, Decimal(amount)),),
    )


def test_complete_month_across_dst_preserves_known_zero():
    archive = MonthlyVariableCostArchive()
    record(archive, local(10), local(10, 25, 12), "2")
    record(archive, local(10, 25, 12), local(11), "-2")

    restored = MonthlyVariableCostArchive.from_dict(archive.as_dict())
    (month,) = restored.months
    assert month.month == date(2026, 10, 1)
    assert month.complete and not month.has_gaps
    assert month.priced_kwh == 2
    assert dict(month.components) == {VariableCostComponent.BUNDLED_PRICE: Decimal(0)}


def test_late_start_early_end_and_internal_gap_are_partial():
    archive = MonthlyVariableCostArchive()
    record(archive, local(8, 2), local(9))
    record(archive, local(9), local(9, 30))
    record(archive, local(10), local(10, 20))
    record(archive, local(10, 21), local(11))

    restored = MonthlyVariableCostArchive.from_dict(archive.as_dict())
    assert [month.complete for month in restored.months] == [False, False, False]
    assert [month.has_gaps for month in restored.months] == [False, False, True]


def test_window_keeps_calendar_gaps_and_isolates_damaged_months():
    archive = MonthlyVariableCostArchive()
    for year, month in ((2025, 1), (2025, 2), (2025, 4), (2026, 1)):
        record(archive, local(month, year=year), local(month, 2, year=year))

    assert archive.prune(date(2026, 1, 10))
    stored = archive.as_dict()
    assert list(stored) == ["2025-02", "2025-04", "2026-01"]
    stored["2025-04"]["priced_kwh"] = "NaN"
    assert list(MonthlyVariableCostArchive.from_dict(stored).as_dict()) == [
        "2025-02",
        "2026-01",
    ]
