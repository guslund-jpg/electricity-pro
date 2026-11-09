"""Validate bounded, partial cost estimates with matched priced energy."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from types import MappingProxyType
from zoneinfo import ZoneInfo

import pytest

from custom_components.electricity_pro.cost_ledger import CostLedger
from custom_components.electricity_pro.pricing import (
    EffectivePriceBreakdown,
    VariableCostComponent,
)

START = datetime(2026, 9, 14, 12, tzinfo=UTC)


def update(
    c,
    minutes,
    energy,
    price="2",
    effective="3",
    start=START,
    lifetime=True,
    *,
    breakdown=None,
):
    c.update(
        start + timedelta(minutes=minutes),
        None if energy is None else D(energy),
        None if price is None else D(price),
        None if effective is None else D(effective),
        "SEK",
        lifetime=lifetime,
        breakdown=breakdown,
    )


def test_weight_prices_over_unchanged_meter_and_keep_effective_separate():
    c = CostLedger()
    update(c, 0, "100")
    update(c, 5, "100", "4", "5")
    update(c, 10, "102", "4", "5")
    assert c.daily_supplier == D(6)
    assert c.daily_effective == D(8)
    assert c.daily_energy == D(2)
    assert c.monthly_supplier == D(6)


def test_weight_components_when_rates_change_at_the_same_total():
    c = CostLedger()
    old = EffectivePriceBreakdown(
        D(3),
        (
            (VariableCostComponent.MARKET_ENERGY, D(1)),
            (VariableCostComponent.VARIABLE_GRID_FEE, D(2)),
        ),
    )
    new = EffectivePriceBreakdown(
        D(3),
        (
            (VariableCostComponent.MARKET_ENERGY, D(2)),
            (VariableCostComponent.VARIABLE_GRID_FEE, D(1)),
        ),
    )

    update(c, 0, "100", breakdown=old)
    update(c, 4, "100", breakdown=new)
    update(c, 10, "110", breakdown=new)

    stored = c.as_dict()
    expected = {
        "started_at": START.isoformat(),
        "priced_kwh": "10",
        "covered_cost": "30",
        "components": {"market_energy": "16", "variable_grid_fee": "14"},
    }
    assert stored["variable_cost_breakdown"] == {
        "version": 1,
        "daily": expected,
        "monthly": expected,
    }
    assert c.daily_effective == c.monthly_effective == D(30)
    assert c.daily_energy == c.monthly_energy == D(10)
    assert CostLedger.from_dict(stored).as_dict() == stored


def test_track_only_new_priced_intervals_after_legacy_restore():
    c = CostLedger()
    update(c, 0, "100")
    update(c, 5, "102")
    legacy = c.as_dict()
    assert "variable_cost_breakdown" not in legacy
    restored = CostLedger.from_dict(legacy)
    price = EffectivePriceBreakdown(
        D(3), ((VariableCostComponent.BUNDLED_PRICE, D(3)),)
    )

    update(restored, 10, "110", breakdown=price)
    update(restored, 15, "111", breakdown=price)

    stored = restored.as_dict()
    daily = stored["variable_cost_breakdown"]["daily"]
    assert restored.daily_effective == D(9)
    assert restored.daily_energy == D(3)
    assert daily == {
        "started_at": (START + timedelta(minutes=10)).isoformat(),
        "priced_kwh": "1",
        "covered_cost": "3",
        "components": {"bundled_price": "3"},
    }

    daily["priced_kwh"] = "NaN"
    without_details = CostLedger.from_dict(stored)
    assert without_details.daily_effective == D(9)
    assert "variable_cost_breakdown" not in without_details.as_dict()


def test_track_components_after_midnight_in_the_new_month():
    c = CostLedger()
    start = datetime(2026, 9, 30, 23, 55, tzinfo=ZoneInfo("Europe/Stockholm"))
    price = EffectivePriceBreakdown(
        D(3), ((VariableCostComponent.BUNDLED_PRICE, D(3)),)
    )
    update(c, 0, "100", start=start, breakdown=price)
    update(c, 2, "101", start=start, breakdown=price)
    update(c, 8, "103", start=start, breakdown=price)

    stored = c.as_dict()
    details = stored["variable_cost_breakdown"]
    assert c.daily_energy == c.monthly_energy == D(1)
    assert c.daily_effective == c.monthly_effective == D(3)
    assert D(details["daily"]["components"]["bundled_price"]) == c.daily_effective
    assert details["monthly"] == details["daily"]
    assert details["daily"]["started_at"] == (start + timedelta(minutes=5)).isoformat()
    assert CostLedger.from_dict(stored).as_dict() == stored


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
        c.update(
            START + timedelta(milliseconds=index),
            D(100),
            D(index),
            D(index),
            "SEK",
            lifetime=True,
        )
    assert len(c._segments) <= 256
    assert len(c.as_dict()) == 12


def test_persistence_round_trip_keeps_exact_signed_totals_and_closed_interval():
    c = CostLedger()
    update(c, 0, "100", "-2.25", "-1.125")
    update(c, 5, "102", "-2.25", "-1.125")
    expected = {
        "day": "2026-09-14",
        "month": "2026-09",
        "unit": "SEK",
        "lifetime_high_water": "102",
        "daily_supplier": "-4.50",
        "monthly_supplier": "-4.50",
        "daily_effective": "-2.250",
        "monthly_effective": "-2.250",
        "daily_energy": "2",
        "monthly_energy": "2",
        "daily_supplier_energy": "2",
        "monthly_supplier_energy": "2",
    }
    assert c.as_dict() == expected
    restored = CostLedger.from_dict(MappingProxyType(expected))
    assert restored.as_dict() == expected
    assert restored._meter is None
    assert restored._at is None
    assert restored._segments == []


@pytest.mark.parametrize("key", ["day", "month", "unit"])
@pytest.mark.parametrize("value", [0, [], {}])
def test_invalid_persisted_metadata_rejected(key, value):
    stored = CostLedger().as_dict()
    stored[key] = value
    with pytest.raises(ValueError):
        CostLedger.from_dict(stored)


TOTAL_KEYS = (
    "daily_supplier",
    "monthly_supplier",
    "daily_effective",
    "monthly_effective",
    "daily_energy",
    "monthly_energy",
    "daily_supplier_energy",
    "monthly_supplier_energy",
)


@pytest.mark.parametrize("key", [*TOTAL_KEYS, "lifetime_high_water"])
@pytest.mark.parametrize("value", [[], {}, "NaN", "Infinity"])
def test_invalid_persisted_numeric_values_rejected(key, value):
    stored = CostLedger().as_dict()
    stored[key] = value
    with pytest.raises(ValueError):
        CostLedger.from_dict(stored)


@pytest.mark.parametrize("key", TOTAL_KEYS)
def test_stored_energy_cannot_be_negative_but_costs_can(key):
    stored = CostLedger().as_dict()
    stored[key] = "-1"
    if "energy" in key:
        with pytest.raises(ValueError):
            CostLedger.from_dict(stored)
    else:
        assert getattr(CostLedger.from_dict(stored), key) == -1


@pytest.mark.parametrize("value", ["1.25", 1, 1.25, D("1.25")])
def test_stored_numeric_scalars_remain_supported(value):
    stored = CostLedger().as_dict()
    for key in (*TOTAL_KEYS, "lifetime_high_water"):
        stored[key] = value
    restored = CostLedger.from_dict(stored)
    for key in TOTAL_KEYS:
        assert getattr(restored, key) == D(value)
    assert restored._lifetime_high_water == D(value)


def test_currency_change_resets_totals_high_water_and_pending_gap():
    c = CostLedger()
    update(c, 0, "100")
    update(c, 5, "101")
    update(c, 25, "101")
    assert c._discard_next_delta
    c.update(START + timedelta(minutes=26), D(10), D(4), D(5), "EUR", lifetime=True)
    assert c.unit == "EUR"
    assert all(getattr(c, key) == 0 for key in TOTAL_KEYS)
    assert c._lifetime_high_water == 10
    assert not c._discard_next_delta
    c.update(START + timedelta(minutes=27), D(11), D(4), D(5), "EUR", lifetime=True)
    assert c.daily_supplier == c.monthly_supplier == 4
    assert c.daily_effective == c.monthly_effective == 5
    assert c.daily_energy == c.monthly_energy == 1
