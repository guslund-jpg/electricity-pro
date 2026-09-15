"""Validate bounded, partial cost estimates with matched priced energy."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from zoneinfo import ZoneInfo

import pytest

from custom_components.electricity_pro.cost_ledger import CostLedger

START = datetime(2026, 9, 14, 12, tzinfo=UTC)


def update(c, minutes, energy, price="2", effective="3", start=START, lifetime=True):
    c.update(start + timedelta(minutes=minutes), None if energy is None else D(energy),
             None if price is None else D(price),
             None if effective is None else D(effective), "SEK", lifetime=lifetime)


def test_weight_prices_over_unchanged_meter_and_keep_effective_separate():
    c = CostLedger()
    update(c, 0, "100")
    update(c, 5, "100", "4", "5")
    update(c, 10, "102", "4", "5")
    assert c.daily_supplier == D(6)
    assert c.daily_effective == D(8)
    assert c.daily_energy == D(2)
    assert c.monthly_supplier == D(6)


def test_negative_prices_reduce_cost_without_counter_reset():
    c = CostLedger()
    update(c, 0, "100", "-2", "-1")
    update(c, 5, "101", "-2", "-1")
    assert c.daily_supplier == D(-2)
    assert c.monthly_supplier == D(-2)
    assert c.daily_effective == D(-1)


def test_missing_prices_only_count_matched_coverage():
    c = CostLedger()
    update(c, 0, "100", None, None)
    update(c, 5, "100")
    update(c, 10, "102")
    assert c.daily_supplier == D(2)
    assert c.daily_energy == D(1)
    assert c.daily_effective == D(3)


@pytest.mark.parametrize("gap", ["direct", "unchanged", "unavailable"])
def test_no_pricing_of_unobserved_gaps(gap):
    c = CostLedger()
    update(c, 0, "100")
    if gap == "unchanged":
        update(c, 16, "100")
    elif gap == "unavailable":
        update(c, 5, None)
    update(c, 20, "120")
    assert c.monthly_supplier == 0
    update(c, 25, "121")
    assert c.monthly_supplier == 2


def test_restart_preserves_totals_but_not_open_interval():
    c = CostLedger()
    update(c, 0, "100")
    update(c, 5, "101")
    restored = CostLedger.from_dict(c.as_dict())
    update(restored, 10, "120")
    update(restored, 15, "121")
    assert restored.monthly_supplier == 4
    assert restored.daily_supplier_energy == 2


def test_lifetime_reset_is_not_consumption():
    c = CostLedger()
    update(c, 0, "100")
    update(c, 5, "10")
    update(c, 10, "11")
    assert c.monthly_supplier == 0
    c.confirm_meter_reset(D(11))
    update(c, 11, "11")
    update(c, 12, "12")
    assert c.monthly_supplier == 2


@pytest.mark.parametrize("restart", [False, True])
def test_backward_lifetime_readings_never_reprice_recovery(restart):
    c = CostLedger()
    update(c, 0, "54705")
    update(c, 1, "54706")
    update(c, 2, "54701")
    if restart:
        c = CostLedger.from_dict(c.as_dict())
    update(c, 3, None)
    update(c, 25, "54702")
    update(c, 26, "54706")
    update(c, 27, "54707")
    assert c.monthly_supplier_energy == 2
    assert c.monthly_energy == 2
    assert c.monthly_supplier == 4
    assert c.monthly_effective == 6


def test_backward_lifetime_readings_across_midnight():
    c = CostLedger()
    start = datetime(2026, 9, 30, 23, 55, tzinfo=UTC)
    update(c, 0, "100", start=start)
    update(c, 4, "90", start=start)
    update(c, 6, "91", start=start)
    update(c, 7, "100", start=start)
    update(c, 8, "101", start=start)
    assert c.daily_energy == c.monthly_energy == 1


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1"])
def test_invalid_persisted_high_water_rejected(value):
    c = CostLedger()
    stored = c.as_dict()
    stored["lifetime_high_water"] = value
    with pytest.raises(ValueError):
        CostLedger.from_dict(stored)


def test_lifetime_delta_splits_at_day_and_month_boundary():
    c = CostLedger()
    start = datetime(2026, 9, 30, 23, 55, tzinfo=UTC)
    update(c, 0, "100", start=start)
    update(c, 10, "102", start=start)
    assert c.daily_supplier == 2
    assert c.monthly_supplier == 2
    assert c.daily_energy == 1


def test_daily_source_reset_counts_only_new_day_reading():
    c = CostLedger()
    start = datetime(2026, 9, 14, 23, 55, tzinfo=UTC)
    update(c, 0, "20", start=start, lifetime=False)
    update(c, 10, "1", start=start, lifetime=False)
    assert c.daily_supplier == 2
    assert c.daily_energy == 1


def test_daily_source_stale_at_midnight_is_not_charged_again():
    c = CostLedger()
    start = datetime(2026, 9, 14, 23, 55, tzinfo=UTC)
    update(c, 0, "20", start=start, lifetime=False)
    update(c, 5, "20", start=start, lifetime=False)
    update(c, 6, "20", start=start, lifetime=False)
    assert c.daily_supplier == 0
    update(c, 10, "1", start=start, lifetime=False)
    assert c.daily_supplier == 2


def test_fall_back_interval_uses_elapsed_not_wall_clock_time():
    c = CostLedger()
    tz = ZoneInfo("Europe/Stockholm")
    first = datetime(2026, 10, 25, 0, 55, tzinfo=UTC).astimezone(tz)
    second = datetime(2026, 10, 25, 1, 5, tzinfo=UTC).astimezone(tz)
    c.update(first, D(100), D(2), D(3), "SEK", lifetime=True)
    c.update(second, D(101), D(2), D(3), "SEK", lifetime=True)
    assert c.daily_supplier == 2


def test_storage_is_bounded():
    c = CostLedger()
    for index in range(1000):
        c.update(START + timedelta(milliseconds=index), D(100),
                 D(index), D(index), "SEK", lifetime=True)
    assert len(c._segments) <= 256
    assert len(c.as_dict()) == 12
