"""Persistent export booking, replay protection and local calendar periods."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util
from homeassistant.util.file import WriteError

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.export_ledger import ExportLedger
from custom_components.electricity_pro.export_observation import ExportIntervalResult
from tests.test_export_observation import (
    CHANGE,
    END,
    EXPORT,
    START,
    config_entry,
    price_period,
    report,
)


def interval(start=START, end=CHANGE, energy="2", rate="0.50", **declaration):
    kwh = Decimal(energy)
    result = ExportIntervalResult(
        source=EXPORT,
        start=start,
        end=end,
        exported_kwh=kwh,
        priced_kwh=kwh if rate is not None else Decimal(0),
        amount=kwh * Decimal(rate) if rate is not None else None,
        amount_per_kwh=Decimal(rate) if rate is not None else None,
        currency="SEK" if rate is not None else None,
        vat_treatment="included" if rate is not None else None,
        components=("supplier_compensation",) if rate is not None else (),
        reason="priced" if rate is not None else "no_single_price_period",
    )
    return replace(result, **declaration)


def ledger_at(start=START):
    ledger = ExportLedger(ZoneInfo("Europe/Stockholm"))
    assert ledger.advance(start)
    return ledger


def test_price_changes_and_replay_before_and_after_json_restore():
    ledger = ledger_at()
    first = interval()
    second = interval(CHANGE, END, "3", "-0.20")
    assert ledger.record(first, 0)
    assert not ledger.record(first, 0)
    assert ledger.record(second, 0)
    assert ledger.today.observed_kwh == Decimal(5)
    assert ledger.today.amounts[0].priced_kwh == Decimal(5)
    assert ledger.today.amounts[0].amount == Decimal("0.40")
    snapshot = json.loads(json.dumps(ledger.as_dict()))
    restored = ExportLedger.from_dict(snapshot)
    for duplicate in (
        first,
        second,
        replace(second, amount=Decimal(999)),
        interval(START, END),
    ):
        assert not restored.record(duplicate, 0)
    assert restored.as_dict() == snapshot
    zero = interval(END, END + timedelta(minutes=1), "2", "0")
    assert restored.record(zero, 0)
    assert restored.today.amounts[0].priced_kwh == Decimal(7)
    assert restored.today.amounts[0].amount == Decimal("0.40")


def test_unpriced_interval_is_consumed_and_cannot_be_repriced_later():
    ledger = ledger_at()
    unpriced = interval(rate=None)
    assert ledger.record(unpriced, 0)
    assert ledger.today.observed_kwh == Decimal(2)
    assert ledger.today.amounts == ()
    restored = ExportLedger.from_dict(ledger.as_dict())
    assert not restored.record(interval(), 0)
    assert restored.today == ledger.today


@pytest.mark.parametrize(
    "declaration,generation",
    [
        ({"currency": "EUR"}, 0),
        ({"vat_treatment": "excluded"}, 0),
        ({"components": ("grid_compensation",)}, 0),
        ({"source": "sensor.other"}, 0),
        ({}, 1),
    ],
)
def test_distinct_declarations_and_meter_generations_keep_separate_amounts(
    declaration, generation
):
    ledger = ledger_at()
    assert ledger.record(interval(), 0)
    assert ledger.record(interval(CHANGE, END, **declaration), generation)
    assert len(ledger.today.amounts) == 2
    assert ledger.today.observed_kwh == Decimal(4)
    assert [row.amount for row in ledger.today.amounts] == [Decimal(1), Decimal(1)]
    assert ExportLedger.from_dict(ledger.as_dict()).today == ledger.today


@pytest.mark.parametrize("date", ["2026-11-19", "2026-11-30", "2026-12-31"])
def test_silent_calendar_rollover_preserves_closed_periods_and_rejects_old_replay(date):
    start = datetime.fromisoformat(date).replace(hour=22, tzinfo=UTC)
    ledger = ledger_at(start)
    booking = interval(start, start + timedelta(minutes=5))
    assert ledger.record(booking, 0)
    day, month = ledger.today, ledger.this_month
    midnight = start + timedelta(hours=1)
    assert ledger.advance(midnight)
    assert ledger.previous_day == day
    assert ledger.today.observed_kwh == 0 and ledger.today.amounts == ()
    assert not ledger.record(booking, 0)
    if date.endswith(("30", "31")):
        assert ledger.previous_month == month
        assert ledger.this_month.observed_kwh == 0
    else:
        assert ledger.this_month == month
    snapshot = ledger.as_dict()
    restored = ExportLedger.from_dict(snapshot)
    assert restored.as_dict() == snapshot
    assert not restored.advance(start)
    assert restored.as_dict() == snapshot


@pytest.mark.parametrize("date,hours", [("2026-03-29", 23), ("2026-10-25", 25)])
def test_day_length_uses_local_midnight_and_UTC_replay_order(date, hours):
    zone = ZoneInfo("Europe/Stockholm")
    start = datetime.fromisoformat(date).replace(tzinfo=zone)
    tomorrow = start + timedelta(days=1)
    assert (
        tomorrow.astimezone(UTC) - start.astimezone(UTC)
    ).total_seconds() == hours * 3600
    ledger = ledger_at(start)
    assert ledger.record(interval(start, start + timedelta(minutes=5)), 0)
    if hours == 25:
        early = datetime(2026, 10, 25, 2, 15, tzinfo=zone)
        late = early.replace(fold=1)
        assert ledger.record(interval(early, late), 0)
        assert not ledger.record(interval(early, late), 0)
    total = ledger.today
    assert ledger.advance(tomorrow)
    assert ledger.previous_day == total
    assert ledger.today.observed_kwh == 0
    assert ExportLedger.from_dict(ledger.as_dict()).as_dict() == ledger.as_dict()


def test_only_current_and_last_closed_periods_are_retained():
    ledger = ledger_at()
    for month in (12, 1, 2):
        ledger.advance(
            datetime(2026 if month == 12 else 2027, month, 1, 12, tzinfo=UTC)
        )
    assert ledger.today.period == "2027-02-01"
    assert ledger.previous_day.period == "2027-01-01"
    assert ledger.this_month.period == "2027-02"
    assert ledger.previous_month.period == "2027-01"
    assert ledger.as_dict()["processed"] == []


@pytest.mark.parametrize(
    "field,value",
    [("version", 2), ("processed", [{}]), ("today", {}), ("timezone", "bad/timezone")],
)
def test_invalid_checkpoint_is_rejected(field, value):
    ledger = ledger_at()
    ledger.record(interval(), 0)
    snapshot = ledger.as_dict()
    snapshot[field] = value
    with pytest.raises((KeyError, ValueError, TypeError)):
        ExportLedger.from_dict(snapshot)


def test_missing_marker_cannot_restore_booked_amounts_without_replay_protection():
    ledger = ledger_at()
    ledger.record(interval(), 0)
    saved = ledger.as_dict()
    saved["processed"] = []
    with pytest.raises(ValueError, match="booking markers"):
        ExportLedger.from_dict(saved)


async def setup_entry(hass, freezer, periods=None):
    await hass.config.async_set_time_zone("UTC")
    freezer.move_to(START)
    hass.states.async_set("sensor.import_power", "500", {"unit_of_measurement": "W"})
    hass.states.async_set(
        "sensor.import_energy", "1000", {"unit_of_measurement": "kWh"}
    )
    hass.states.async_set(EXPORT, "100", {"unit_of_measurement": "kWh"})
    entry = config_entry([price_period()] if periods is None else periods)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_live_price_boundaries_duplicates_and_unpriced_coverage(hass, freezer):
    freezer.move_to(START)
    entry = config_entry([price_period(end=CHANGE), price_period("-0.20", CHANGE)])
    coordinator = ElectricityProCoordinator(hass, entry)
    report(hass, freezer, coordinator, START, "100")
    report(hass, freezer, coordinator, CHANGE, "102")
    report(hass, freezer, coordinator, END, "105")
    assert coordinator.export_ledger.today.amounts[0].amount == Decimal("0.40")
    assert coordinator.export_ledger.today.observed_kwh == Decimal(5)
    before = coordinator.export_ledger.as_dict()
    coordinator._read_flows(dt_util.now())
    assert coordinator.export_ledger.as_dict() == before
    # With a new baseline, one measurement spanning the change remains unpriced.
    freezer.move_to(START)
    other = ElectricityProCoordinator(hass, entry)
    report(hass, freezer, other, START, "100")
    report(hass, freezer, other, END, "105")
    assert other.export_ledger.today.observed_kwh == Decimal(5)
    assert other.export_ledger.today.amounts == ()


async def test_zero_export_report_also_schedules_checkpoint(hass, freezer):
    freezer.move_to(START)
    coordinator = ElectricityProCoordinator(hass, config_entry([price_period()]))
    hass.states.async_set(EXPORT, "100", {"unit_of_measurement": "kWh"})
    with patch.object(coordinator, "_schedule_statistics_save"):
        coordinator._read()
    freezer.move_to(CHANGE)
    hass.states.async_set(EXPORT, "100", {"unit_of_measurement": "kWh"})
    with patch.object(coordinator, "_schedule_statistics_save") as save:
        coordinator._read()
    save.assert_called_once_with()
    saved = coordinator.export_ledger.as_dict()
    assert saved["processed"][0]["end"] == CHANGE.isoformat()
    assert coordinator.export_ledger.today.amounts[0].amount == 0
    with patch.object(coordinator, "_schedule_statistics_save"):
        coordinator._read()
    assert coordinator.export_ledger.as_dict() == saved


async def test_meter_reset_preserves_existing_bookings_and_separates_new_generation(
    hass, freezer
):
    freezer.move_to(START)
    coordinator = ElectricityProCoordinator(hass, config_entry([price_period()]))
    report(hass, freezer, coordinator, START, "100")
    report(hass, freezer, coordinator, CHANGE, "102")
    report(hass, freezer, coordinator, END, "1")
    with patch.object(coordinator._store, "async_save"):
        await coordinator.async_confirm_flow_meter_reset("grid_export", EXPORT)
    report(hass, freezer, coordinator, END + timedelta(minutes=1), "2")
    rows = coordinator.export_ledger.today.amounts
    assert [row.contract.generation for row in rows] == [0, 1]
    assert [row.amount for row in rows] == [Decimal(1), Decimal("0.50")]
    assert coordinator.export_ledger.today.observed_kwh == Decimal(3)


@pytest.mark.parametrize("price_change", [False, True])
async def test_real_reload_flushes_ledger_and_restarts_only_price_baseline(
    hass, hass_storage, freezer, price_change
):
    entry = await setup_entry(hass, freezer)
    coordinator = entry.runtime_data
    report(hass, freezer, coordinator, CHANGE, "102")
    await hass.async_block_till_done()
    expected = deepcopy(coordinator.export_ledger.as_dict())
    freezer.move_to(CHANGE + timedelta(minutes=1))
    if price_change:
        boundary = dt_util.utcnow()
        hass.config_entries.async_update_entry(
            entry,
            options={
                "export_price_periods": [
                    price_period(end=boundary),
                    price_period("-0.20", boundary),
                ]
            },
        )
    else:
        assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    key = f"{DOMAIN}.{entry.entry_id}.statistics"
    assert hass_storage[key]["data"]["export_ledger"] == expected
    restarted = entry.runtime_data
    assert restarted.export_ledger.as_dict() == expected
    assert restarted.export_compensation is None
    assert report(hass, freezer, restarted, END, "105") is None
    report(hass, freezer, restarted, END + timedelta(minutes=1), "106")
    assert restarted.export_ledger.today.amounts[0].amount == Decimal(
        "0.80" if price_change else "1.50"
    )
    assert restarted.export_ledger.today.observed_kwh == Decimal(3)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_source_change_restores_old_bookings_and_books_new_source_separately(
    hass, freezer
):
    await hass.config.async_set_time_zone("UTC")
    freezer.move_to(START)
    coordinator = ElectricityProCoordinator(hass, config_entry([price_period()]))
    report(hass, freezer, coordinator, START, "100")
    report(hass, freezer, coordinator, CHANGE, "102")
    saved = coordinator._statistics_data()
    freezer.move_to(END)
    source = "sensor.replacement_export"
    changed = ElectricityProCoordinator(
        hass,
        config_entry([price_period(meter=source)], grid_export_energy_entity=source),
    )
    with patch.object(changed._store, "async_load", return_value=saved):
        await changed._async_restore_statistics()
    assert report(hass, freezer, changed, END, "500", source=source) is None
    report(hass, freezer, changed, END + timedelta(minutes=1), "501", source=source)
    rows = changed.export_ledger.today.amounts
    assert [row.contract.source for row in rows] == [EXPORT, source]
    assert [row.amount for row in rows] == [Decimal(1), Decimal("0.50")]


async def test_write_failure_keeps_totals_and_markers_at_same_checkpoint_then_retries(
    hass, hass_storage, freezer, caplog
):
    entry = await setup_entry(hass, freezer)
    coordinator = entry.runtime_data
    report(hass, freezer, coordinator, CHANGE, "102")
    await hass.async_block_till_done()
    await coordinator._async_save_statistics()
    key = f"{DOMAIN}.{entry.entry_id}.statistics"
    saved = deepcopy(hass_storage[key]["data"])
    report(hass, freezer, coordinator, END, "104")
    await hass.async_block_till_done()
    with patch(
        "homeassistant.helpers.storage.Store._async_write_data",
        side_effect=WriteError("test write failure"),
    ):
        await coordinator._async_save_statistics()
    assert "test write failure" in caplog.text
    assert hass_storage[key]["data"] == saved
    restarted = ElectricityProCoordinator(hass, entry)
    await restarted._async_restore_statistics()
    assert restarted.export_ledger.as_dict() == saved["export_ledger"]
    assert (
        restarted._statistics_data()["directional_flows"] == saved["directional_flows"]
    )
    assert not restarted.export_ledger.record(interval(), 0)
    await coordinator._async_save_statistics()
    latest = hass_storage[key]["data"]
    assert Decimal(latest["export_ledger"]["today"]["amounts"][0]["amount"]) == 2
    assert latest["export_ledger"]["processed"][0]["end"] == END.isoformat()
    assert latest["directional_flows"]["grid_export"]["counter"]["high_water"] == "104"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("date", ["2026-11-19", "2026-11-30"])
async def test_coordinator_rollover_and_restart_keep_previous_bookings(
    hass, freezer, date
):
    await hass.config.async_set_time_zone("UTC")
    start = datetime.fromisoformat(date).replace(hour=23, minute=57, tzinfo=UTC)
    freezer.move_to(start)
    entry = config_entry([price_period(start=start)])
    coordinator = ElectricityProCoordinator(hass, entry)
    report(hass, freezer, coordinator, start, "100")
    report(hass, freezer, coordinator, start + timedelta(minutes=1), "102")
    next_day = start + timedelta(minutes=3)
    freezer.move_to(next_day)
    with patch.object(coordinator._store, "async_delay_save"):
        coordinator._async_daily_rollover(next_day)
    assert coordinator.export_ledger.previous_day.amounts[0].amount == 1
    assert coordinator.export_ledger.today.amounts == ()
    stored = json.loads(json.dumps(coordinator._statistics_data()))
    restarted = ElectricityProCoordinator(hass, entry)
    with patch.object(restarted._store, "async_load", return_value=stored):
        await restarted._async_restore_statistics()
    assert (
        report(hass, freezer, restarted, next_day + timedelta(minutes=1), "105") is None
    )
    report(hass, freezer, restarted, next_day + timedelta(minutes=2), "106")
    assert restarted.export_ledger.today.amounts[0].amount == Decimal("0.50")
    assert restarted.export_ledger.previous_day.amounts[0].amount == Decimal(1)
    if date.endswith("30"):
        assert restarted.export_ledger.previous_month.amounts[0].amount == Decimal(1)
        assert restarted.export_ledger.this_month.amounts[0].amount == Decimal("0.50")
    else:
        assert restarted.export_ledger.this_month.amounts[0].amount == Decimal("1.50")


@pytest.mark.parametrize("checkpoint", [{}, {"version": 1, "timezone": "bad/timezone"}])
async def test_invalid_ledger_is_preserved_and_booking_pauses_without_blocking_flows(
    hass, freezer, checkpoint, caplog
):
    freezer.move_to(START)
    coordinator = ElectricityProCoordinator(hass, config_entry([price_period()]))
    with patch.object(
        coordinator._store, "async_load", return_value={"export_ledger": checkpoint}
    ):
        await coordinator._async_restore_statistics()
    report(hass, freezer, coordinator, START, "100")
    report(hass, freezer, coordinator, END, "102")
    assert coordinator.export_compensation.amount == 1
    assert coordinator.flow_values["grid_export_today"][0] == 2
    assert coordinator._statistics_data()["export_ledger"] == checkpoint
    assert "Pausing export booking" in caplog.text


async def test_older_snapshot_and_different_timezone(hass, freezer):
    freezer.move_to(START)
    await hass.config.async_set_time_zone("UTC")
    coordinator = ElectricityProCoordinator(hass, config_entry([price_period()]))
    with patch.object(coordinator._store, "async_load", return_value={}):
        await coordinator._async_restore_statistics()
    report(hass, freezer, coordinator, START, "100")
    report(hass, freezer, coordinator, CHANGE, "102")
    assert coordinator.export_ledger.today.amounts[0].amount == 1
    old = ledger_at()
    old.record(interval(), 0)
    saved = old.as_dict()
    changed_zone = ElectricityProCoordinator(hass, config_entry([price_period()]))
    with patch.object(
        changed_zone._store, "async_load", return_value={"export_ledger": saved}
    ):
        await changed_zone._async_restore_statistics()
    assert changed_zone._statistics_data()["export_ledger"] == saved
    assert changed_zone._export_ledger_paused
