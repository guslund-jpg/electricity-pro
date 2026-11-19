"""Export sensor values, coverage, compatibility and checkpoint ordering."""

from datetime import timedelta
from decimal import Decimal
import json
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.util.file import WriteError

from custom_components.electricity_pro.export_statistics import (
    ExportHistory,
    ExportStatistics,
)
from custom_components.electricity_pro.sensor import (
    ElectricityProExportCompensationSensor,
)
from tests.test_export_ledger import interval, ledger_at, setup_entry
from tests.test_export_observation import (
    START,
    CHANGE,
    END,
    EXPORT,
    price_period,
    report,
)

IDS = {
    period: f"sensor.electricity_pro_export_compensation_{period}"
    for period in ("today", "this_month")
}


def test_publication_retains_closing_period_before_new_reset_and_currency():
    ledger = ledger_at()
    history = ExportHistory(ledger.timezone, START, monthly=False)
    ledger.record(interval(), 0)
    history.update(ledger.today)
    first = history.checkpoint
    assert first.amount == 1
    assert first.zero_baseline().amount == 0
    ledger.advance(START + timedelta(days=1))
    history.update(ledger.today)
    restored = ExportHistory(ledger.timezone, END, monthly=False)
    restored.restore(json.loads(json.dumps(history.as_list())))
    assert restored.saved == first
    assert restored.confirm(first)
    assert restored.dirty
    assert restored.checkpoint.last_reset > first.last_reset
    assert restored.currency == "SEK"


def test_initial_booked_amount_is_series_baseline_and_metadata_is_partial():
    ledger = ledger_at()
    ledger.record(interval(), 0)
    history = ExportHistory(ledger.timezone, END, monthly=False)
    history.initialize(ledger.today)
    assert history.saved.amount == 1
    assert not history.dirty
    attrs = history.saved.attributes()
    assert attrs["coverage"] == "partial"
    assert Decimal(attrs["pricing_coverage_percent"]) == 100
    assert attrs["history_started_at"] == END.isoformat()
    assert attrs["price_declarations"][0]["source_entity"] == EXPORT


def test_energy_display_rounding_keeps_full_precision_in_amount_and_coverage():
    ledger = ledger_at()
    ledger.record(interval(energy="2.1256", rate="0.365"), 0)
    snapshot = ExportStatistics(ledger.today, str(ledger.timezone), "SEK", START)
    assert snapshot.amount == Decimal("0.775844")
    assert snapshot.period.observed_kwh == Decimal("2.1256")
    assert snapshot.attributes()["observed_export_kwh"] == "2.126"
    assert snapshot.attributes()["priced_export_kwh"] == "2.126"
    assert Decimal(snapshot.attributes()["pricing_coverage_percent"]) == 100


def test_unrepresentable_sum_is_unavailable_without_losing_bookings():
    ledger = ledger_at()
    ledger.record(interval(energy="1", rate="9e999999"), 0)
    ledger.record(
        interval(CHANGE, END, energy="1", rate="9e999999", source="sensor.other"), 0
    )
    snapshot = ExportStatistics(ledger.today, str(ledger.timezone), "SEK", START)
    assert snapshot.amount is None
    assert snapshot.reason == "invalid_amount"
    assert len(snapshot.period.amounts) == 2


@pytest.mark.parametrize(
    "change",
    [
        {"currency": "EUR"},
        {"vat_treatment": "excluded"},
        {"components": ("grid_compensation",)},
    ],
)
def test_mixed_declarations_are_unavailable(change):
    ledger = ledger_at()
    ledger.record(interval(), 0)
    ledger.record(interval(CHANGE, END, **change), 0)
    snapshot = ExportStatistics(ledger.today, str(ledger.timezone), "SEK", START)
    assert snapshot.amount is None
    assert snapshot.reason == "mixed_declarations"


def test_currency_remains_pinned_after_period_rollover_and_restore():
    ledger = ledger_at()
    ledger.record(interval(), 0)
    history = ExportHistory(ledger.timezone, START, monthly=False)
    history.initialize(ledger.today)
    next_day = START + timedelta(days=1)
    ledger.advance(next_day)
    ledger.record(
        interval(next_day, next_day + timedelta(minutes=1), currency="EUR"), 0
    )
    history.update(ledger.today)
    assert history.checkpoint.currency == "SEK"
    assert history.checkpoint.amount is None
    assert history.checkpoint.reason == "currency_changed"
    restored = ExportHistory(ledger.timezone, END, monthly=False)
    restored.restore(history.as_list())
    assert restored.currency == "SEK"
    assert restored.saved.reason == "currency_changed"


@pytest.mark.parametrize("language", ["en", "sv"])
async def test_sensor_identity_precision_and_checkpointed_values(
    hass, hass_storage, freezer, language
):
    hass.config.language = language
    entry = await setup_entry(hass, freezer, [price_period("0.365")])
    coordinator = entry.runtime_data
    for entity in IDS.values():
        assert hass.states.get(entity).state == "unavailable"
    report(hass, freezer, coordinator, START + timedelta(seconds=20), "102.125")
    await hass.async_block_till_done()
    for entity in IDS.values():
        assert hass.states.get(entity).state == "unavailable"
    with patch(
        "homeassistant.helpers.storage.Store._async_write_data", side_effect=WriteError
    ):
        await coordinator._async_save_statistics()
    assert hass.states.get(IDS["today"]).state == "unavailable"
    await coordinator._async_save_statistics()
    registry = er.async_get(hass)
    for period, entity in IDS.items():
        state = hass.states.get(entity)
        assert Decimal(state.state) == Decimal("0.775625")
        assert state.attributes["device_class"] == "monetary"
        assert state.attributes["state_class"] == "total"
        assert state.attributes["unit_of_measurement"] == "SEK"
        assert state.attributes["coverage"] == "partial"
        assert Decimal(state.attributes["priced_export_kwh"]) == Decimal("2.125")
        assert (
            registry.async_get(entity).unique_id
            == f"{entry.entry_id}_export_compensation_{period}"
        )
        sensor = ElectricityProExportCompensationSensor(entry, period)
        assert sensor.suggested_display_precision == 2
        assert sensor.native_value == Decimal("0.775625")
    expected = (
        "Uppskattad exportersättning"
        if language == "sv"
        else "Export compensation estimate"
    )
    assert expected in hass.states.get(IDS["today"]).name
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "rate,last,priced,percentage",
    [("0", "102", "2", "100"), ("0.50", "100", "0", None)],
)
async def test_known_zero_is_available_and_zero_energy_has_no_percentage(
    hass, freezer, rate, last, priced, percentage
):
    entry = await setup_entry(hass, freezer, [price_period(rate)])
    report(hass, freezer, entry.runtime_data, CHANGE, last)
    await hass.async_block_till_done()
    await entry.runtime_data._async_save_statistics()
    state = hass.states.get(IDS["today"])
    assert Decimal(state.state) == 0
    assert state.attributes["coverage"] == "partial"
    assert Decimal(state.attributes["priced_export_kwh"]) == Decimal(priced)
    assert state.attributes["pricing_coverage_percent"] == percentage
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_partial_pricing_and_disabled_price_preserve_booked_value(hass, freezer):
    entry = await setup_entry(hass, freezer, [price_period(start=CHANGE)])
    coordinator = entry.runtime_data
    report(hass, freezer, coordinator, END, "102")
    await hass.async_block_till_done()
    await coordinator._async_save_statistics()
    assert hass.states.get(IDS["today"]).state == "unavailable"
    report(hass, freezer, coordinator, END + timedelta(minutes=1), "103")
    await hass.async_block_till_done()
    await coordinator._async_save_statistics()
    state = hass.states.get(IDS["today"])
    assert Decimal(state.state) == Decimal("0.50")
    assert Decimal(state.attributes["observed_export_kwh"]) == 3
    assert Decimal(state.attributes["priced_export_kwh"]) == 1
    assert Decimal(state.attributes["unpriced_export_kwh"]) == 2
    assert Decimal(state.attributes["pricing_coverage_percent"]) == Decimal(100) / 3
    boundary = END + timedelta(minutes=2)
    freezer.move_to(boundary)
    hass.config_entries.async_update_entry(
        entry,
        options={"export_price_periods": [price_period(start=CHANGE, end=boundary)]},
    )
    await hass.async_block_till_done()
    state = hass.states.get(IDS["today"])
    assert Decimal(state.state) == Decimal("0.50")
    assert state.attributes["fixed_export_price_enabled"] is False
    assert await hass.config_entries.async_unload(entry.entry_id)
