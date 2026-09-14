"""Household totals retain cost boundaries and use local calendar accrual."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from custom_components.electricity_pro.household_cost import accrued_fixed_fees
from custom_components.electricity_pro.cost_ledger import CostLedger


@pytest.mark.parametrize("month,days", [(2, 28), (4, 30), (7, 31)])
def test_calendar_fixed_accrual(month, days):
    now = datetime(2026, month, 10, 12, tzinfo=UTC)
    day, total, missing = accrued_fixed_fees(now, D(days), D(days))
    assert day == 1
    assert total == 19
    assert missing == ()


def test_leap_year_and_month_start():
    day, month, _ = accrued_fixed_fees(datetime(2028, 2, 1, tzinfo=UTC), D(29), D(0))
    assert day == month == 0
    day, month, _ = accrued_fixed_fees(datetime(2028, 2, 29, 12, tzinfo=UTC), D(29), D(0))
    assert day == D("0.5")
    assert month == D("28.5")


@pytest.mark.parametrize("start_utc,hours", [
    (datetime(2026, 3, 28, 23, tzinfo=UTC), 23),
    (datetime(2026, 10, 24, 22, tzinfo=UTC), 25),
])
def test_dst_day_fraction(start_utc, hours):
    middle = (start_utc + timedelta(hours=hours / 2)).astimezone(ZoneInfo("Europe/Stockholm"))
    day, _, _ = accrued_fixed_fees(middle, D(31), D(0))
    assert day == D("0.5")


def test_missing_fee_is_explicit_not_assumed_zero():
    _, _, missing = accrued_fixed_fees(datetime(2026, 9, 1, tzinfo=UTC), None, D(0))
    assert missing == ("fixed_supplier_fee",)


def test_old_ledger_does_not_invent_effective_month_history():
    ledger = CostLedger()
    stored = ledger.as_dict()
    stored["daily_effective"] = "12"
    stored.pop("monthly_effective")
    stored.pop("monthly_energy")
    restored = CostLedger.from_dict(stored)
    assert restored.daily_effective == 12
    assert restored.monthly_effective == 0


def test_old_ledger_keeps_known_daily_effective_cost_as_partial_month():
    stored = CostLedger().as_dict()
    stored.update(day="2026-09-14", month="2026-09", daily_effective="12", daily_energy="4")
    stored.pop("monthly_effective")
    stored.pop("monthly_energy")
    restored = CostLedger.from_dict(stored)
    assert restored.monthly_effective == 12
    assert restored.monthly_energy == 4


def test_effective_month_survives_restart_and_rolls_over():
    ledger = CostLedger()
    first = datetime(2026, 9, 30, 23, 50, tzinfo=UTC)
    ledger.update(first, D(100), D(1), D(2), "SEK", lifetime=True)
    ledger.update(first + timedelta(minutes=5), D(101), D(1), D(2), "SEK", lifetime=True)
    restored = CostLedger.from_dict(ledger.as_dict())
    assert restored.monthly_effective == 2
    restored.update(first + timedelta(minutes=6), D(101), D(1), D(2), "SEK", lifetime=True)
    restored.update(first + timedelta(minutes=14), D(103), D(1), D(2), "SEK", lifetime=True)
    assert restored.monthly_effective == 2
    assert restored.monthly_energy == 1


@pytest.mark.parametrize("external", [False, True])
async def test_household_total_does_not_double_count_supplier(hass, setup_electricity_pro, external):
    hass.config.time_zone = "UTC"
    now = datetime(2026, 9, 14, 12, tzinfo=UTC)
    with patch("custom_components.electricity_pro.coordinator.dt_util.now", return_value=now):
        entry = await setup_electricity_pro(
            energy_value="100", energy_source_type="lifetime", price_value="2",
            supplier_markup_per_kwh=0.18, grid_fee_per_kwh=0.1, energy_tax_per_kwh=0.2,
            fixed_supplier_fee_monthly=30, fixed_grid_fee_monthly=60,
            accumulated_cost_today_value="99" if external else None,
        )
    later = now + timedelta(minutes=5)
    with patch("custom_components.electricity_pro.coordinator.dt_util.now", return_value=later):
        hass.states.async_set("sensor.test_energy", "102", {"unit_of_measurement": "kWh"})
        await hass.async_block_till_done()
        data = entry.runtime_data.data
    fixed_day, fixed_month, _ = accrued_fixed_fees(later, D(30), D(60))
    assert data.household_variable_today == D("4.96")
    assert data.household_variable_month == D("4.96")
    assert data.household_cost_today == D("4.96") + fixed_day
    assert data.household_cost_this_month == D("4.96") + fixed_month
    assert data.accumulated_cost_today == (D(99) if external else D("4.36"))
    assert data.household_missing_fees == ()
    assert hass.states.get("sensor.electricity_pro_total_cost_estimate_today") is not None


async def test_incomplete_variable_price_does_not_produce_household_total(hass, setup_electricity_pro):
    entry = await setup_electricity_pro(
        energy_value="100", price_value="2", supplier_markup_per_kwh=0,
    )
    assert entry.runtime_data.data.household_cost_today is None
    assert "complete_variable_price" in entry.runtime_data.data.household_missing_fees
    assert "fixed_grid_fee" in entry.runtime_data.data.household_missing_fees


async def test_household_missing_fixed_fees_are_listed(hass, setup_electricity_pro):
    entry = await setup_electricity_pro(
        energy_value="100", price_value="2", supplier_markup_per_kwh=0,
        grid_fee_per_kwh=0, energy_tax_per_kwh=0, fixed_supplier_fee_monthly=0,
    )
    assert entry.runtime_data.data.household_missing_fees == ("fixed_grid_fee",)
    assert entry.runtime_data.data.household_cost_today == 0
