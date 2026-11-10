"""Household totals retain cost boundaries and use local calendar accrual."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.electricity_pro.const import (
    CONF_PRICE_VAT_RATE,
    CONF_PRICE_VAT_TREATMENT,
)
from custom_components.electricity_pro.household_cost import accrued_fixed_fees
from custom_components.electricity_pro.cost_ledger import CostLedger
from custom_components.electricity_pro.pricing import VatTreatment


async def test_monthly_vat_only_splits_newly_priced_costs(
    hass, setup_electricity_pro, freezer
):
    await hass.config.async_set_time_zone("UTC")
    start = datetime(2026, 11, 10, 12, tzinfo=UTC)
    freezer.move_to(start)
    entry = await setup_electricity_pro(
        energy_value="100",
        energy_source_type="lifetime",
        price_value="1.25",
        supplier_markup_per_kwh=0.10,
        grid_fee_per_kwh=0.25,
        energy_tax_per_kwh=0.50,
        fixed_supplier_fee_monthly=0,
        fixed_grid_fee_monthly=0,
    )
    entity = "sensor.electricity_pro_total_cost_estimate_this_month"

    async def book(minutes, meter):
        freezer.move_to(start + timedelta(minutes=minutes))
        hass.states.async_set(
            "sensor.test_energy", meter, {"unit_of_measurement": "kWh"}
        )
        await hass.async_block_till_done()
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()

    await book(1, "101")
    first = hass.states.get(entity)
    assert D(first.state) == D("2.10")
    assert "vat_display" not in first.attributes["variable_cost_breakdown"]

    hass.states.async_set("sensor.test_price", "1", {"unit_of_measurement": "SEK/kWh"})
    await hass.async_block_till_done()
    hass.config_entries.async_update_entry(
        entry,
        options={
            **entry.options,
            CONF_PRICE_VAT_TREATMENT: VatTreatment.EXCLUDED.value,
            CONF_PRICE_VAT_RATE: 25,
        },
    )
    await hass.async_block_till_done()
    await book(2, "102")
    state = hass.states.get(entity)
    assert D(state.state) == D("4.20")
    details = state.attributes["variable_cost_breakdown"]
    assert D(details["components"]["market_energy"]) == D("2.50")
    assert details["display"]["lines"]["market_energy"] == "2.50"
    assert details["vat_display"] == {
        "total": "4.20",
        "lines": {
            "market_energy": "1.25",
            "market_energy_excluding_vat": "1.00",
            "supplier_markup": "0.20",
            "energy_tax": "1.00",
            "variable_grid_fee": "0.50",
            "vat": "0.25",
        },
    }
    assert sum(map(D, details["vat_display"]["lines"].values())) == D(state.state)

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    restored = hass.states.get(entity)
    assert restored.state == state.state
    assert restored.attributes["variable_cost_breakdown"] == details


@pytest.mark.parametrize("month,days", [(2, 28), (4, 30), (7, 31)])
def test_calendar_fixed_accrual(month, days):
    now = datetime(2026, month, 10, 12, tzinfo=UTC)
    fees = accrued_fixed_fees(now, D(days), D(days))
    assert fees.today == 1
    assert fees.month == 19
    assert fees.supplier_month == fees.grid_month == D("9.5")
    assert fees.missing == ()


def test_leap_year_and_month_start():
    fees = accrued_fixed_fees(datetime(2028, 2, 1, tzinfo=UTC), D(29), D(0))
    assert fees.today == fees.month == fees.supplier_month == fees.grid_month == 0
    fees = accrued_fixed_fees(datetime(2028, 2, 29, 12, tzinfo=UTC), D(29), D(0))
    assert fees.today == D("0.5")
    assert fees.month == fees.supplier_month == D("28.5")


@pytest.mark.parametrize(
    "start_utc,hours",
    [
        (datetime(2026, 3, 28, 23, tzinfo=UTC), 23),
        (datetime(2026, 10, 24, 22, tzinfo=UTC), 25),
    ],
)
def test_dst_day_fraction(start_utc, hours):
    middle = (start_utc + timedelta(hours=hours / 2)).astimezone(
        ZoneInfo("Europe/Stockholm")
    )
    fees = accrued_fixed_fees(middle, D(31), D(0))
    assert fees.today == D("0.5")
    assert fees.month == fees.supplier_month == D(middle.day - 1) + D("0.5")


def test_missing_fee_is_explicit_not_assumed_zero():
    fees = accrued_fixed_fees(datetime(2026, 9, 1, tzinfo=UTC), None, D(0))
    assert fees.missing == ("fixed_supplier_fee",)
    assert fees.supplier_month is None
    assert fees.grid_month == 0


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
    stored.update(
        day="2026-09-14", month="2026-09", daily_effective="12", daily_energy="4"
    )
    stored.pop("monthly_effective")
    stored.pop("monthly_energy")
    restored = CostLedger.from_dict(stored)
    assert restored.monthly_effective == 12
    assert restored.monthly_energy == 4


def test_effective_month_survives_restart_and_rolls_over():
    ledger = CostLedger()
    first = datetime(2026, 9, 30, 23, 50, tzinfo=UTC)
    ledger.update(first, D(100), D(1), D(2), "SEK", lifetime=True)
    ledger.update(
        first + timedelta(minutes=5), D(101), D(1), D(2), "SEK", lifetime=True
    )
    restored = CostLedger.from_dict(ledger.as_dict())
    assert restored.monthly_effective == 2
    restored.update(
        first + timedelta(minutes=6), D(101), D(1), D(2), "SEK", lifetime=True
    )
    restored.update(
        first + timedelta(minutes=14), D(103), D(1), D(2), "SEK", lifetime=True
    )
    assert restored.monthly_effective == 2
    assert restored.monthly_energy == 1


@pytest.mark.parametrize("external", [False, True])
async def test_household_total_does_not_double_count_supplier(
    hass, setup_electricity_pro, external
):
    await hass.config.async_set_time_zone("UTC")
    now = datetime(2026, 9, 14, 12, tzinfo=UTC)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now", return_value=now
    ):
        entry = await setup_electricity_pro(
            energy_value="100",
            energy_source_type="lifetime",
            price_value="2",
            supplier_markup_per_kwh=0.18,
            grid_fee_per_kwh=0.1,
            energy_tax_per_kwh=0.2,
            fixed_supplier_fee_monthly=30,
            fixed_grid_fee_monthly=60,
            accumulated_cost_today_value="99" if external else None,
        )
    initial_month = hass.states.get(
        "sensor.electricity_pro_total_cost_estimate_this_month"
    )
    assert initial_month.attributes["accrued_fixed_fee_breakdown"] == {
        "supplier": "13.5",
        "grid": "27.0",
    }
    assert D(initial_month.state) == D("40.5")
    later = now + timedelta(minutes=5)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now", return_value=later
    ):
        hass.states.async_set(
            "sensor.test_energy", "102", {"unit_of_measurement": "kWh"}
        )
        await hass.async_block_till_done()
        data = entry.runtime_data.data
    fixed = accrued_fixed_fees(later, D(30), D(60))
    assert data.results.household_variable_today == D("4.96")
    assert data.results.household_variable_month == D("4.96")
    assert data.results.household_cost_today == D("4.96") + fixed.today
    assert data.results.household_cost_this_month == D("4.96") + fixed.month
    assert data.results.accumulated_cost_today == (D(99) if external else D("4.36"))
    assert data.results.household_missing_fees == ()
    assert (
        hass.states.get("sensor.electricity_pro_total_cost_estimate_today") is not None
    )


async def test_incomplete_variable_price_does_not_produce_household_total(
    hass, setup_electricity_pro
):
    entry = await setup_electricity_pro(
        energy_value="100",
        price_value="2",
        supplier_markup_per_kwh=0,
    )
    assert entry.runtime_data.data.results.household_cost_today is None
    assert (
        "complete_variable_price"
        in entry.runtime_data.data.results.household_missing_fees
    )
    assert "fixed_grid_fee" in entry.runtime_data.data.results.household_missing_fees


async def test_household_missing_fixed_fees_are_listed(hass, setup_electricity_pro):
    entry = await setup_electricity_pro(
        energy_value="100",
        price_value="2",
        supplier_markup_per_kwh=0,
        grid_fee_per_kwh=0,
        energy_tax_per_kwh=0,
        fixed_supplier_fee_monthly=0,
    )
    assert entry.runtime_data.data.results.household_missing_fees == ("fixed_grid_fee",)
    assert entry.runtime_data.data.results.household_cost_today == 0
