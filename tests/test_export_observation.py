"""Price accepted HA export reports using the configured validity periods."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator

START = datetime(2026, 11, 19, 12, tzinfo=UTC)
CHANGE = START + timedelta(minutes=5)
END = START + timedelta(minutes=10)
EXPORT = "sensor.export_energy"


def price_period(rate="0.50", start=START, end=None, meter=EXPORT):
    return {
        "meter": meter,
        "amount_per_kwh": rate,
        "currency": "SEK",
        "vat_treatment": "included",
        "components": ["supplier_compensation"],
        "valid_from": start.isoformat(),
        "valid_until": end.isoformat() if end else None,
    }


def config_entry(periods, **settings):
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "power_entity": "sensor.import_power",
            "energy_entity": "sensor.import_energy",
            "energy_source_type": "lifetime",
            "grid_export_energy_entity": EXPORT,
            **settings,
        },
        options={"export_price_periods": periods},
    )


def report(hass, freezer, coordinator, at, value, unit="kWh", source=EXPORT):
    freezer.move_to(at)
    hass.states.async_set(
        source,
        value,
        {"unit_of_measurement": unit, "device_class": "energy"},
    )
    coordinator._read_flows(dt_util.now())
    return coordinator.export_compensation


@pytest.mark.parametrize(
    "unit,first,last", [("kWh", "100", "102.125"), ("Wh", "100000", "102125")]
)
@pytest.mark.parametrize(
    "rate,amount", [("0.365", "0.775625"), ("-0.20", "-0.425"), ("0", "0")]
)
async def test_measured_increment_keeps_decimal_precision_and_declaration(
    hass, freezer, unit, first, last, rate, amount
):
    freezer.move_to(START)
    coordinator = ElectricityProCoordinator(hass, config_entry([price_period(rate)]))
    assert report(hass, freezer, coordinator, START, first, unit) is None
    result = report(hass, freezer, coordinator, END, last, unit)
    assert result.exported_kwh == result.priced_kwh == Decimal("2.125")
    assert result.amount == Decimal(amount)
    assert result.amount_per_kwh == Decimal(rate)
    assert (result.source, result.start, result.end) == (EXPORT, START, END)
    assert result.currency == "SEK"
    assert result.vat_treatment == "included"
    assert result.components == ("supplier_compensation",)
    assert result.timestamp_provenance == "ha_receipt"
    assert result.reason == "priced"
    assert coordinator.flow_values["grid_export_today"][0] == Decimal("2.125")


@pytest.mark.parametrize(
    "start,end,expected",
    [(START, CHANGE, "1.00"), (CHANGE, END, "-0.40"), (START, END, None)],
)
async def test_exact_price_boundaries_and_spanning_increment(
    hass, freezer, start, end, expected
):
    periods = [price_period(end=CHANGE), price_period("-0.20", CHANGE)]
    freezer.move_to(start)
    coordinator = ElectricityProCoordinator(hass, config_entry(periods))
    report(hass, freezer, coordinator, start, "100")
    result = report(hass, freezer, coordinator, end, "102")
    assert result.exported_kwh == Decimal(2)
    assert result.amount == (Decimal(expected) if expected is not None else None)
    assert result.priced_kwh == (Decimal(2) if expected is not None else Decimal(0))
    assert coordinator.flow_values["grid_export_today"][0] == Decimal(2)


async def test_polling_duplicate_does_not_move_interval_start_or_reprice(hass, freezer):
    freezer.move_to(START)
    coordinator = ElectricityProCoordinator(
        hass, config_entry([price_period(end=CHANGE), price_period("-0.20", CHANGE)])
    )
    report(hass, freezer, coordinator, START, "100")
    freezer.move_to(CHANGE)
    coordinator._read_flows(dt_util.now())
    assert coordinator.export_compensation is None
    result = report(hass, freezer, coordinator, END, "102")
    assert result.start == START
    assert result.amount is None
    freezer.move_to(END + timedelta(minutes=1))
    coordinator._read_flows(dt_util.now())
    assert coordinator.export_compensation is result
    assert coordinator.flow_values["grid_export_today"][0] == Decimal(2)
    # A genuine new report with the same reading represents measured zero export.
    zero = report(hass, freezer, coordinator, END + timedelta(minutes=2), "102")
    assert zero.start == END
    assert zero.exported_kwh == zero.priced_kwh == zero.amount == 0


@pytest.mark.parametrize("vat", ["included", "excluded", "not_applicable"])
async def test_export_keeps_declared_vat_and_currency_separate_from_import(
    hass, freezer, vat
):
    freezer.move_to(START)
    period = {**price_period(), "vat_treatment": vat, "currency": "EUR"}
    coordinator = ElectricityProCoordinator(hass, config_entry([period]))
    report(hass, freezer, coordinator, START, "100")
    result = report(hass, freezer, coordinator, END, "102")
    assert result.amount == Decimal("1.00")
    assert result.vat_treatment == vat
    assert result.currency == "EUR"


async def test_stale_report_clears_result_and_new_report_uses_receipt_interval(
    hass, freezer
):
    freezer.move_to(START)
    coordinator = ElectricityProCoordinator(hass, config_entry([price_period()]))
    report(hass, freezer, coordinator, START, "100")
    report(hass, freezer, coordinator, CHANGE, "102")
    freezer.move_to(CHANGE + timedelta(minutes=16))
    coordinator._read_flows(dt_util.now())
    assert coordinator.export_compensation is None
    result = report(hass, freezer, coordinator, CHANGE + timedelta(minutes=17), "103")
    assert result.start == CHANGE
    assert result.amount == Decimal("0.50")


@pytest.mark.parametrize("bad", ["unavailable", "NaN", "-1", "99"])
async def test_rejected_readings_keep_trusted_baseline_and_allow_same_day_gap(
    hass, freezer, bad
):
    freezer.move_to(START)
    coordinator = ElectricityProCoordinator(hass, config_entry([price_period()]))
    report(hass, freezer, coordinator, START, "100")
    assert report(hass, freezer, coordinator, CHANGE, bad) is None
    result = report(hass, freezer, coordinator, END, "102")
    assert result.start == START
    assert result.exported_kwh == Decimal(2)
    assert result.amount == Decimal("1.00")


@pytest.mark.parametrize(
    "periods",
    [
        [],
        [price_period(meter="sensor.other_export")],
        [price_period(start=CHANGE)],
        [price_period(end=CHANGE)],
        [price_period(), price_period()],
        [price_period(), price_period(start=CHANGE, end=END)],
    ],
)
async def test_missing_partial_or_ambiguous_prices_leave_measured_energy_unpriced(
    hass, freezer, periods
):
    freezer.move_to(START)
    coordinator = ElectricityProCoordinator(hass, config_entry(periods))
    report(hass, freezer, coordinator, START, "100")
    result = report(hass, freezer, coordinator, END, "102")
    assert result.exported_kwh == Decimal(2)
    assert result.priced_kwh == 0
    assert result.amount is None
    assert coordinator.flow_values["grid_export_today"][0] == Decimal(2)


@pytest.mark.parametrize(
    "periods", [None, {}, [None], [{"meter": EXPORT}], [price_period("NaN")]]
)
async def test_malformed_price_storage_does_not_break_energy_counter(
    hass, freezer, periods
):
    freezer.move_to(START)
    coordinator = ElectricityProCoordinator(hass, config_entry(periods))
    report(hass, freezer, coordinator, START, "100")
    result = report(hass, freezer, coordinator, END, "102")
    assert result.amount is None
    assert result.reason == "invalid_price_periods"
    assert coordinator.flow_values["grid_export_today"][0] == Decimal(2)


async def test_repeated_hour_compares_UTC_instants(hass, freezer):
    await hass.config.async_set_time_zone("Europe/Stockholm")
    start = datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
    change = start + timedelta(hours=1)
    end = change + timedelta(minutes=10)
    periods = [price_period(end=change), price_period("-0.20", change)]
    periods[0]["valid_from"] = start.isoformat()
    freezer.move_to(start)
    coordinator = ElectricityProCoordinator(hass, config_entry(periods))
    report(hass, freezer, coordinator, start, "100")
    # Intervening source outage may leave a trustworthy cumulative increment.
    result = report(hass, freezer, coordinator, change, "102")
    assert result.amount == Decimal("1.00")
    result = report(hass, freezer, coordinator, end, "103")
    assert result.amount == Decimal("-0.20")
    assert result.start == change


@pytest.mark.parametrize("date", ["2026-11-19", "2026-11-30"])
async def test_calendar_boundary_establishes_fresh_pricing_baseline(
    hass, freezer, date
):
    await hass.config.async_set_time_zone("UTC")
    start = datetime.fromisoformat(date).replace(hour=23, minute=59, tzinfo=UTC)
    freezer.move_to(start)
    coordinator = ElectricityProCoordinator(
        hass, config_entry([price_period(start=start)])
    )
    report(hass, freezer, coordinator, start, "100")
    freezer.move_to(start + timedelta(minutes=1))
    coordinator._read_flows(dt_util.now())
    assert coordinator.export_compensation is None
    assert (
        report(hass, freezer, coordinator, start + timedelta(minutes=2), "102") is None
    )
    result = report(hass, freezer, coordinator, start + timedelta(minutes=3), "103")
    assert result.exported_kwh == Decimal(1)
    assert result.amount == Decimal("0.50")
    assert coordinator.flow_values["grid_export_today"][0] == Decimal(1)


async def test_confirmed_meter_reset_restarts_price_baseline(hass, freezer):
    freezer.move_to(START)
    coordinator = ElectricityProCoordinator(hass, config_entry([price_period()]))
    report(hass, freezer, coordinator, START, "100")
    assert report(hass, freezer, coordinator, CHANGE, "102").amount == Decimal("1.00")
    assert report(hass, freezer, coordinator, END, "1") is None
    with patch.object(coordinator._store, "async_save"):
        await coordinator.async_confirm_flow_meter_reset("grid_export", EXPORT)
    assert coordinator.export_compensation is None
    result = report(hass, freezer, coordinator, END + timedelta(minutes=1), "2")
    assert result.start == END
    assert result.amount == Decimal("0.50")
    assert coordinator.flow_values["grid_export_today"][0] == Decimal(3)


async def test_real_reload_rebaselines_export_pricing_and_preserves_import_totals(
    hass, freezer
):
    freezer.move_to(START)
    hass.states.async_set("sensor.import_power", "500", {"unit_of_measurement": "W"})
    hass.states.async_set(
        "sensor.import_energy", "1000", {"unit_of_measurement": "kWh"}
    )
    hass.states.async_set(EXPORT, "100", {"unit_of_measurement": "kWh"})
    entry = config_entry([price_period()])
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = entry.runtime_data
    freezer.move_to(CHANGE)
    hass.states.async_set(
        "sensor.import_energy", "1001", {"unit_of_measurement": "kWh"}
    )
    hass.states.async_set(EXPORT, "102", {"unit_of_measurement": "kWh"})
    await hass.async_block_till_done()
    assert coordinator.export_compensation.amount == Decimal("1.00")
    import_before = coordinator.data.results.energy_this_month
    stored = coordinator._statistics_data()
    assert "export_compensation" not in stored
    freezer.move_to(CHANGE + timedelta(minutes=1))
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    restarted = entry.runtime_data
    assert restarted is not coordinator
    assert restarted.export_compensation is None
    assert restarted.data.results.energy_this_month == import_before
    assert restarted.flow_values["grid_export_today"][0] == Decimal(2)
    # A cached pre-start report and the first new report cannot price downtime.
    assert report(hass, freezer, restarted, END, "105") is None
    result = report(hass, freezer, restarted, END + timedelta(minutes=1), "106")
    assert result.start == END
    assert result.exported_kwh == Decimal(1)
    assert result.amount == Decimal("0.50")
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_restored_counters_and_new_source_need_new_pricing_baseline(
    hass, freezer
):
    freezer.move_to(START)
    entry = config_entry([price_period()])
    coordinator = ElectricityProCoordinator(hass, entry)
    report(hass, freezer, coordinator, START, "100")
    report(hass, freezer, coordinator, CHANGE, "102")
    stored = coordinator._statistics_data()
    freezer.move_to(CHANGE + timedelta(minutes=1))
    restarted = ElectricityProCoordinator(hass, entry)
    with patch.object(restarted._store, "async_load", return_value=stored):
        await restarted._async_restore_statistics()
    restarted._read_flows(dt_util.now())
    assert restarted.export_compensation is None
    assert report(hass, freezer, restarted, END, "105") is None
    result = report(hass, freezer, restarted, END + timedelta(minutes=1), "106")
    assert result.exported_kwh == Decimal(1)
    assert result.amount == Decimal("0.50")
    assert restarted.flow_values["grid_export_today"][0] == Decimal(6)
    replacement = ElectricityProCoordinator(
        hass,
        config_entry([price_period()], grid_export_energy_entity="sensor.other_export"),
    )
    with patch.object(replacement._store, "async_load", return_value=stored):
        await replacement._async_restore_statistics()
    assert (
        report(
            hass,
            freezer,
            replacement,
            END + timedelta(minutes=2),
            "500",
            source="sensor.other_export",
        )
        is None
    )
    unpriced = report(
        hass,
        freezer,
        replacement,
        END + timedelta(minutes=3),
        "502",
        source="sensor.other_export",
    )
    assert unpriced.exported_kwh == Decimal(2)
    assert unpriced.amount is None
