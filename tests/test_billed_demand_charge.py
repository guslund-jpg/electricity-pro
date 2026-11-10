"""Verify manual demand charges through the HA options flow and monthly entities."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from homeassistant import loader
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import frame
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    async_test_home_assistant,
)

from custom_components.electricity_pro.const import CONF_BILLED_DEMAND_CHARGES

ESTIMATE = "sensor.electricity_pro_total_cost_estimate_this_month"
DAILY_ESTIMATE = "sensor.electricity_pro_total_cost_estimate_today"
BILL = "sensor.electricity_pro_billed_demand_charge"
START = datetime(2026, 11, 30, 12, tzinfo=UTC)
NOVEMBER = {"period_start": "2026-11-01", "period_end": "2026-11-30"}


async def _save(hass, entry, values):
    manager = hass.config_entries.options
    menu = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        menu["flow_id"], {"next_step_id": "billed_demand_charge"}
    )
    assert result["step_id"] == "billed_demand_charge"
    result = await manager.async_configure(result["flow_id"], values)
    if result["type"] is FlowResultType.FORM:
        manager.async_abort(result["flow_id"])
    await hass.async_block_till_done()
    return result


@pytest.fixture
async def house(hass, setup_electricity_pro, freezer):
    await hass.config.async_set_time_zone("UTC")
    freezer.move_to(START - timedelta(minutes=1))
    entry = await setup_electricity_pro(
        energy_value="100",
        energy_source_type="lifetime",
        price_value="2",
        supplier_markup_per_kwh=0,
        grid_fee_per_kwh=0,
        energy_tax_per_kwh=0,
        fixed_supplier_fee_monthly=0,
        fixed_grid_fee_monthly=0,
    )
    freezer.move_to(START)
    hass.states.async_set("sensor.test_energy", "600", {"unit_of_measurement": "kWh"})
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert Decimal(hass.states.get(ESTIMATE).state) == 1000
    return entry


@pytest.mark.parametrize(
    ("coverage", "total", "lines"),
    [
        ("excluded", "1150.00", {"variable": "1000.00"}),
        ("included", "1000.00", {"other": "850.00"}),
        ("unknown", "1000.00", {"variable": "1000.00"}),
    ],
)
async def test_invoice_reconciles_monthly_total_without_double_counting(
    hass, house, coverage, total, lines
):
    result = await _save(
        hass,
        house,
        {**NOVEMBER, "amount": "150,00", "currency": "sek", "coverage": coverage},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    estimate = hass.states.get(ESTIMATE)
    assert Decimal(estimate.state) == Decimal(total)
    display = estimate.attributes["monthly_cost_display"]
    assert display["total"] == total
    assert lines.items() <= display["lines"].items()
    assert sum(map(Decimal, display["lines"].values())) == Decimal(total)
    if coverage == "unknown":
        assert "demand_charge" not in display["lines"]
        assert "demand_charges" in estimate.attributes["excluded_charges"]
    else:
        assert display["lines"]["demand_charge"] == "150.00"
        assert "demand_charges" not in estimate.attributes["excluded_charges"]
    assert Decimal(hass.states.get(DAILY_ESTIMATE).state) == 1000
    assert hass.states.get(BILL).attributes["amount"] == "150.00"

    assert await hass.config_entries.async_reload(house.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ESTIMATE).attributes["monthly_cost_display"] == display
    assert hass.states.get(BILL).attributes["period_end"] == NOVEMBER["period_end"]


@pytest.mark.parametrize(
    ("period", "currency"),
    [
        ({"period_start": "2026-10-01", "period_end": "2026-10-31"}, "SEK"),
        ({"period_start": "2026-10-15", "period_end": "2026-11-14"}, "SEK"),
        (NOVEMBER, "EUR"),
    ],
    ids=["late-invoice", "straddles-month", "different-currency"],
)
async def test_incompatible_invoice_keeps_its_dates_and_stays_separate(
    hass, house, period, currency
):
    await _save(
        hass,
        house,
        {**period, "amount": "150", "currency": currency, "coverage": "excluded"},
    )
    estimate = hass.states.get(ESTIMATE)
    assert Decimal(estimate.state) == 1000
    assert "demand_charge" not in estimate.attributes["monthly_cost_display"]["lines"]
    invoice = hass.states.get(BILL)
    assert period.items() <= invoice.attributes.items()
    assert invoice.attributes["unit_of_measurement"] == currency


async def test_correction_removal_and_change_of_cost_basis(hass, house):
    values = {**NOVEMBER, "amount": "150", "currency": "SEK", "coverage": "excluded"}
    await _save(hass, house, values)
    bad = await _save(hass, house, {**values, "amount": "1.234"})
    assert bad["errors"]["base"] == "invalid_billed_demand_charge"
    overlap = await _save(hass, house, {**values, "period_start": "2026-11-02"})
    assert overlap["errors"]["base"] == "overlapping_billing_period"

    # A correction replaces the invoice and a known zero remains visible.
    await _save(hass, house, {**values, "amount": "0"})
    assert len(house.options[CONF_BILLED_DEMAND_CHARGES]) == 1
    assert Decimal(hass.states.get(BILL).state) == 0
    assert (
        hass.states.get(ESTIMATE).attributes["monthly_cost_display"]["lines"][
            "demand_charge"
        ]
        == "0.00"
    )

    # The old overlap confirmation cannot be reused with new grid charges.
    hass.config_entries.async_update_entry(
        house, options={**house.options, "fixed_grid_fee_monthly": 1}
    )
    await hass.async_block_till_done()
    assert "demand_charges" in hass.states.get(ESTIMATE).attributes["excluded_charges"]
    assert Decimal(hass.states.get(BILL).state) == 0
    await _save(hass, house, {**NOVEMBER, "remove": True})
    assert house.options[CONF_BILLED_DEMAND_CHARGES] == []
    assert hass.states.get(BILL).state == "unavailable"


async def test_restart_restores_invoice_even_without_price_or_meter_readings(
    hass, house, freezer, hass_storage
):
    await _save(
        hass,
        house,
        {**NOVEMBER, "amount": "150", "currency": "SEK", "coverage": "excluded"},
    )
    freezer.move_to(START + timedelta(minutes=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert "core.config_entries" in hass_storage

    freezer.move_to("2026-12-01T12:00:00+00:00")
    async with async_test_home_assistant() as restarted:
        restarted.data.pop(loader.DATA_CUSTOM_COMPONENTS)
        frame.async_setup(restarted)
        await restarted.config.async_set_time_zone("UTC")
        await restarted.config_entries.async_initialize()
        try:
            assert await restarted.config_entries.async_setup(house.entry_id)
            await restarted.async_block_till_done()
            assert restarted.states.get(ESTIMATE).state == "unavailable"
            invoice = restarted.states.get(BILL)
            assert Decimal(invoice.state) == 150
            assert NOVEMBER.items() <= invoice.attributes.items()
            assert await restarted.config_entries.async_unload(house.entry_id)
        finally:
            await restarted.async_stop(force=True)
