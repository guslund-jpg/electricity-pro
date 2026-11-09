"""Exercise coordinator checkpoints through Home Assistant's Store."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed_exact

from custom_components.electricity_pro.const import DOMAIN, ENERGY_SOURCE_LIFETIME
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.pricing import PriceCompleteness


def set_energy(hass, value):
    hass.states.async_set(
        "sensor.test_energy",
        str(value),
        {
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
        },
    )


@pytest.fixture
def advance_clock(hass, freezer, monkeypatch):
    """Advance wall and loop clocks together for Store and calendar callbacks."""
    loop_start = hass.loop.time()
    elapsed = 0.0
    monkeypatch.setattr(hass.loop, "time", lambda: loop_start + elapsed)

    async def advance(seconds):
        nonlocal elapsed
        elapsed += seconds
        freezer.tick(timedelta(seconds=seconds))
        async_fire_time_changed_exact(hass, dt_util.utcnow())
        # Allow immediate writes queued by the rollover timer to start.
        await asyncio.sleep(0)
        await hass.async_block_till_done()

    return advance


@pytest.mark.parametrize("gap", [0.5, 2], ids=["subsecond", "two-seconds"])
async def test_continuous_readings_write_latest_checkpoint(
    hass, hass_storage, setup_electricity_pro, advance_clock, gap
):
    """A stream neither writes per reading nor postpones the first checkpoint."""
    entry = await setup_electricity_pro(
        energy_value="0", price_value="1", price_completeness=PriceCompleteness.COMPLETE
    )
    key = f"{DOMAIN}.{entry.entry_id}.statistics"
    steps = int(60 / gap)
    for value in range(1, steps):
        await advance_clock(gap)
        set_energy(hass, value)
        await hass.async_block_till_done()
        assert key not in hass_storage

    await advance_clock(gap)
    snapshot = hass_storage[key]["data"]
    assert Decimal(snapshot["energy_this_month"]["value"]) == steps - 1
    assert Decimal(snapshot["local_costs"]["daily_effective"]) == steps - 1
    details = snapshot["local_costs"]["variable_cost_breakdown"]
    for period in ("daily", "monthly"):
        assert Decimal(details[period]["priced_kwh"]) == steps - 1
        assert Decimal(details[period]["components"]["bundled_price"]) == steps - 1

    set_energy(hass, steps)
    await hass.async_block_till_done()
    await advance_clock(gap)
    assert hass_storage[key]["data"] == snapshot

    # A new coordinator models restart without an unload/final write. It can
    # recover the cumulative energy delta, while the uncheckpointed cost is lost.
    restored = ElectricityProCoordinator(hass, entry)
    await restored._async_restore_statistics()
    with patch.object(restored, "_schedule_statistics_save"):
        assert restored._read().results.energy_this_month == Decimal(steps)
    assert restored._statistics_data()["local_costs"] == snapshot["local_costs"]

    await advance_clock(60 - gap)
    assert Decimal(hass_storage[key]["data"]["energy_this_month"]["value"]) == steps


@pytest.mark.parametrize("final_write", ["reload", "shutdown", "reset"])
async def test_lifecycle_writes_pending_statistics(
    hass, hass_storage, setup_electricity_pro, advance_clock, final_write
):
    """Persist pending state at lifecycle boundaries ahead of the next timer."""
    entry = await setup_electricity_pro(energy_value="0")
    key = f"{DOMAIN}.{entry.entry_id}.statistics"
    await advance_clock(2)
    set_energy(hass, 2)
    await hass.async_block_till_done()
    assert key not in hass_storage

    if final_write == "reload":
        assert await hass.config_entries.async_reload(entry.entry_id)
        assert entry.runtime_data.data.results.energy_this_month == Decimal(2)
    elif final_write == "shutdown":
        hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)
        await hass.async_block_till_done()
    else:
        await entry.runtime_data.async_reset_monthly_energy()

    expected = Decimal(0 if final_write == "reset" else 2)
    assert Decimal(hass_storage[key]["data"]["energy_this_month"]["value"]) == expected

    if final_write == "reset":
        set_energy(hass, 3)
        await hass.async_block_till_done()
        await advance_clock(60)
        assert Decimal(hass_storage[key]["data"]["energy_this_month"]["value"]) == 1


async def test_midnight_persists_lifetime_baseline_promptly(
    hass, hass_storage, setup_electricity_pro, freezer, advance_clock
):
    """Rollover writes the new daily baseline before the routine deadline."""
    await hass.config.async_set_time_zone("UTC")
    freezer.move_to(datetime(2026, 11, 30, 23, 59, 50, tzinfo=UTC))
    entry = await setup_electricity_pro(
        energy_value="100", energy_source_type=ENERGY_SOURCE_LIFETIME
    )
    key = f"{DOMAIN}.{entry.entry_id}.statistics"
    assert key not in hass_storage

    freezer.move_to(datetime(2026, 12, 1, tzinfo=UTC))
    entry.runtime_data._async_daily_rollover(dt_util.now())
    await advance_clock(0)
    snapshot = hass_storage[key]["data"]["energy_today_from_total"]
    assert snapshot["period_start"] == "2026-12-01"
    assert Decimal(snapshot["last_value"]) == 100
    assert Decimal(snapshot["value"]) == 0

    await advance_clock(2)
    set_energy(hass, 101)
    await hass.async_block_till_done()
    assert entry.runtime_data.data.results.energy_this_month == Decimal(1)
    await advance_clock(60.01)
    monthly = hass_storage[key]["data"]["energy_this_month"]
    assert monthly["period_start"] == "2026-12-01"
    assert Decimal(monthly["value"]) == 1


async def test_late_checkpoint_keeps_both_cost_months_without_double_counting(
    hass, hass_storage, setup_electricity_pro, freezer
):
    """A first write in December retains the November cost under November."""
    await hass.config.async_set_time_zone("Europe/Stockholm")
    start = datetime(2026, 11, 30, 22, 55, tzinfo=UTC)
    freezer.move_to(start)
    entry = await setup_electricity_pro(
        energy_value="100",
        energy_source_type=ENERGY_SOURCE_LIFETIME,
        price_value="4",
        price_completeness=PriceCompleteness.COMPLETE,
    )
    coordinator = entry.runtime_data
    key = f"{DOMAIN}.{entry.entry_id}.statistics"

    freezer.move_to(start + timedelta(minutes=2))
    set_energy(hass, 102)
    await hass.async_block_till_done()
    assert coordinator.data.results.household_variable_month == 8
    assert key not in hass_storage

    freezer.move_to(start + timedelta(minutes=6))
    set_energy(hass, 104)
    await hass.async_block_till_done()
    assert coordinator.data.results.household_variable_month == 2
    await coordinator._async_save_statistics()
    stored = hass_storage[key]["data"]["monthly_variable_cost_archive"]
    assert list(stored) == ["2026-11", "2026-12"]
    # The straddling reading adds 1.5 kWh to November and 0.5 kWh to December.
    for month, energy, amount in (("2026-11", "3.5", "14"), ("2026-12", "0.5", "2")):
        assert Decimal(stored[month]["priced_kwh"]) == Decimal(energy)
        assert Decimal(stored[month]["components"]["bundled_price"]) == Decimal(amount)
    assert stored["2026-12"]["started_at"] == "2026-12-01T00:00:00+01:00"
    assert stored["2026-11"]["covered_until"] == stored["2026-12"]["started_at"]

    await coordinator._async_save_statistics()
    assert hass_storage[key]["data"]["monthly_variable_cost_archive"] == stored
