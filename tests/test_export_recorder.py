"""Exercise export compensation against Recorder's SQLite statistics."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util.file import WriteError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
    do_adhoc_statistics,
    statistics_during_period,
)

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.export_ledger import ExportLedger
from tests.test_export_ledger import interval
from tests.test_export_observation import EXPORT, price_period
from tests.test_variable_cost_recorder import recording_home

START = datetime(2026, 11, 30, 22, 55, tzinfo=UTC)
BOUNDARY = START + timedelta(minutes=5)
IDS = [
    f"sensor.electricity_pro_export_compensation_{period}"
    for period in ("today", "this_month")
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """Each independent HA core enables its custom integrations in recording_home."""


def entry_for(prices):
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="export-compensation-recorder",
        title="Electricity Pro",
        data={
            "power_entity": "sensor.import_power",
            "grid_export_energy_entity": EXPORT,
        },
        options={"export_price_periods": prices},
    )


async def start_entry(hass, entry, reading="100"):
    hass.states.async_set("sensor.import_power", "1000", {"unit_of_measurement": "W"})
    hass.states.async_set(EXPORT, reading, {"unit_of_measurement": "kWh"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.runtime_data


async def export(hass, coordinator, value):
    hass.states.async_set(EXPORT, value, {"unit_of_measurement": "kWh"})
    await hass.async_block_till_done()
    # Equal-valued reports are also observed by the normal periodic read.
    await coordinator._async_timing_tick(dt_util.now())


async def compile_stats(hass, start):
    await async_wait_recording_done(hass)
    do_adhoc_statistics(hass, start=start)
    await async_wait_recording_done(hass)


async def statistic(hass, entity, start):
    rows = await hass.async_add_executor_job(
        statistics_during_period,
        hass,
        start,
        start + timedelta(minutes=5),
        {entity},
        "5minute",
        None,
        {"state", "sum", "last_reset"},
    )
    return rows[entity][-1]


@pytest.mark.parametrize("persistent_database", [True])
async def test_signed_sums_period_reset_and_actual_core_restart(
    freezer, hass_tmp_config_dir, async_test_recorder, persistent_database
):
    change = START + timedelta(minutes=2)
    prices = [
        price_period(end=change, start=START),
        price_period("-0.20", start=change),
    ]
    freezer.move_to(START)
    async with recording_home(hass_tmp_config_dir, async_test_recorder) as hass:
        entry = entry_for(prices)
        coordinator = await start_entry(hass, entry)
        freezer.move_to(START + timedelta(seconds=20))
        await export(hass, coordinator, "102")
        with patch.object(
            coordinator._store, "_write_prepared_data", side_effect=WriteError
        ):
            await coordinator._async_save_statistics()
        assert all(hass.states.get(entity).state == "unavailable" for entity in IDS)
        await coordinator._async_save_statistics()
        assert all(Decimal(hass.states.get(entity).state) == 1 for entity in IDS)
        freezer.move_to(change)
        await export(hass, coordinator, "102")
        freezer.move_to(START + timedelta(minutes=4))
        await export(hass, coordinator, "103")
        await coordinator._async_save_statistics()
        assert all(
            Decimal(hass.states.get(entity).state) == Decimal("0.80") for entity in IDS
        )
        freezer.move_to(BOUNDARY)
        await compile_stats(hass, START)
        for entity in IDS:
            row = await statistic(hass, entity, START)
            assert (row["state"], row["sum"]) == (0.8, 0.8)
        coordinator._async_daily_rollover(dt_util.now())
        await coordinator._async_save_statistics()
        await hass.async_block_till_done()
        assert all(hass.states.get(entity).state == "unavailable" for entity in IDS)
        freezer.move_to(BOUNDARY + timedelta(minutes=1))
        await export(hass, coordinator, "104")
        freezer.move_to(BOUNDARY + timedelta(minutes=2))
        await export(hass, coordinator, "106")
        await coordinator._async_save_statistics()
        freezer.move_to(BOUNDARY + timedelta(minutes=5))
        await compile_stats(hass, BOUNDARY)
        for entity in IDS:
            row = await statistic(hass, entity, BOUNDARY)
            assert row["state"] == pytest.approx(-0.4)
            assert row["sum"] == pytest.approx(0.4)
            assert row["last_reset"] == BOUNDARY.timestamp()

    freezer.move_to(BOUNDARY + timedelta(minutes=6))
    async with recording_home(hass_tmp_config_dir, async_test_recorder) as hass:
        coordinator = await start_entry(hass, entry_for(prices), "110")
        assert all(
            Decimal(hass.states.get(entity).state) == Decimal("-0.40") for entity in IDS
        )
        freezer.move_to(BOUNDARY + timedelta(minutes=7))
        await export(hass, coordinator, "111")
        await coordinator._async_save_statistics()
        freezer.move_to(BOUNDARY + timedelta(minutes=10))
        await compile_stats(hass, BOUNDARY + timedelta(minutes=5))
        for entity in IDS:
            row = await statistic(hass, entity, BOUNDARY + timedelta(minutes=5))
            assert row["state"] == pytest.approx(-0.6)
            assert row["sum"] == pytest.approx(0.2)
            assert row["last_reset"] == BOUNDARY.timestamp()


@pytest.mark.parametrize("persistent_database", [True])
async def test_preexisting_bookings_form_start_balance_without_historical_statistics(
    freezer, hass_tmp_config_dir, async_test_recorder, persistent_database
):
    freezer.move_to(START)
    async with recording_home(hass_tmp_config_dir, async_test_recorder) as hass:
        entry = entry_for([price_period(start=START - timedelta(hours=1))])
        ledger = ExportLedger(ZoneInfo("Europe/Stockholm"))
        ledger.advance(START)
        ledger.record(
            interval(
                START - timedelta(minutes=10), START - timedelta(minutes=9), energy="7"
            ),
            0,
        )
        await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.statistics").async_save(
            {"export_ledger": ledger.as_dict()}
        )
        coordinator = await start_entry(hass, entry)
        assert all(
            Decimal(hass.states.get(entity).state) == Decimal("3.50") for entity in IDS
        )
        freezer.move_to(START + timedelta(minutes=1))
        await export(hass, coordinator, "102")
        await coordinator._async_save_statistics()
        freezer.move_to(START + timedelta(minutes=5))
        await compile_stats(hass, START)
        for entity in IDS:
            row = await statistic(hass, entity, START)
            assert (row["state"], row["sum"]) == (4.5, 1)


@pytest.mark.parametrize("persistent_database", [True])
async def test_delayed_checkpoint_publishes_closed_period_before_new_period(
    freezer, hass_tmp_config_dir, async_test_recorder, persistent_database
):
    freezer.move_to(START)
    async with recording_home(hass_tmp_config_dir, async_test_recorder) as hass:
        entry = entry_for([price_period(start=START)])
        coordinator = await start_entry(hass, entry)
        await coordinator._async_save_statistics()
        # Simulate storage latency through the boundary, retaining both periods.
        with patch.object(coordinator, "_schedule_statistics_save"):
            freezer.move_to(START + timedelta(minutes=4))
            await export(hass, coordinator, "102")
            freezer.move_to(BOUNDARY)
            coordinator._async_daily_rollover(dt_util.now())
            freezer.move_to(BOUNDARY + timedelta(seconds=10))
            await export(hass, coordinator, "103")
            freezer.move_to(BOUNDARY + timedelta(seconds=20))
            await export(hass, coordinator, "107")
        observed = []

        def changed(event):
            state = event.data.get("new_state")
            if (
                state is not None
                and event.data["entity_id"] == IDS[0]
                and state.state not in {"unknown", "unavailable"}
            ):
                observed.append((Decimal(state.state), state.attributes["last_reset"]))

        cancel = hass.bus.async_listen("state_changed", changed)
        await coordinator._async_save_statistics()
        # Drive the closing and new-period writes through the real Store.
        await coordinator._async_save_statistics()
        await hass.async_block_till_done()
        cancel()
        old_reset = (BOUNDARY - timedelta(days=1)).isoformat()
        new_reset = BOUNDARY.isoformat()
        assert (Decimal(1), old_reset) in observed, observed
        assert (Decimal(2), new_reset) in observed, observed
        assert observed.index((Decimal(1), old_reset)) < observed.index(
            (Decimal(2), new_reset)
        )
        freezer.move_to(BOUNDARY + timedelta(minutes=5))
        await compile_stats(hass, BOUNDARY)
        for entity in IDS:
            row = await statistic(hass, entity, BOUNDARY)
            assert (row["state"], row["sum"]) == (2, 3)


@pytest.mark.parametrize("persistent_database", [True])
@pytest.mark.parametrize(
    "rate,end_value,amount",
    [
        ("0.50", "103", "1"),
        ("-0.20", "103", "-0.40"),
        ("0", "103", "0"),
        ("0.365", "103.1256", "0.775844"),
    ],
)
async def test_first_priced_period_after_unavailable_period_counts_first_amount(
    freezer,
    hass_tmp_config_dir,
    async_test_recorder,
    persistent_database,
    rate,
    end_value,
    amount,
):
    freezer.move_to(START)
    async with recording_home(hass_tmp_config_dir, async_test_recorder) as hass:
        coordinator = await start_entry(
            hass, entry_for([price_period(rate, start=BOUNDARY)])
        )
        await coordinator._async_save_statistics()
        with patch.object(coordinator, "_schedule_statistics_save"):
            freezer.move_to(BOUNDARY)
            coordinator._async_daily_rollover(dt_util.now())
            freezer.move_to(BOUNDARY + timedelta(seconds=10))
            await export(hass, coordinator, "101")
            freezer.move_to(BOUNDARY + timedelta(seconds=20))
            await export(hass, coordinator, end_value)
        await coordinator._async_save_statistics()
        freezer.move_to(BOUNDARY + timedelta(minutes=5))
        await compile_stats(hass, BOUNDARY)
        for entity in IDS:
            row = await statistic(hass, entity, BOUNDARY)
            assert row["state"] == pytest.approx(float(amount))
            assert row["sum"] == pytest.approx(float(amount))
