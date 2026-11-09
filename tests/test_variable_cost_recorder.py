"""Exercise Electricity Pro with Recorder's SQLite database and real statistics."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant import loader
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import frame
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util.file import WriteError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_test_home_assistant,
)
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
    do_adhoc_statistics,
    statistics_during_period,
)

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.cost_ledger import (
    CostLedger,
    VariableCostSummary,
)
from custom_components.electricity_pro.pricing import (
    EffectivePriceBreakdown,
    VariableCostComponent,
)
from custom_components.electricity_pro.variable_cost_statistics import (
    VariableCostHistory,
)

ENTITY = "sensor.electricity_pro_combined_variable_cost_this_month"
START = datetime(2026, 11, 30, 21, 55, tzinfo=UTC)
NOVEMBER = datetime(2026, 10, 31, 23, tzinfo=UTC)
DECEMBER = datetime(2026, 11, 30, 23, tzinfo=UTC)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """The restart test enables custom integrations on each of its own cores."""


@asynccontextmanager
async def recording_home(config_dir, async_test_recorder):
    async with async_test_home_assistant(config_dir=config_dir) as hass:
        hass.data.pop(loader.DATA_CUSTOM_COMPONENTS)
        frame.async_setup(hass)
        await hass.config.async_set_time_zone("Europe/Stockholm")
        try:
            async with async_test_recorder(hass):
                try:
                    yield hass
                finally:
                    for entry in hass.config_entries.async_entries(DOMAIN):
                        if entry.state is ConfigEntryState.LOADED:
                            await hass.config_entries.async_unload(entry.entry_id)
        finally:
            await hass.async_stop(force=True)


def set_price(hass, value):
    hass.states.async_set(
        "sensor.test_price", str(value), {"unit_of_measurement": "SEK/kWh"}
    )


def set_energy(hass, value):
    hass.states.async_set(
        "sensor.test_energy", str(value), {"unit_of_measurement": "kWh"}
    )


def config_entry():
    return MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        entry_id="variable-cost-recorder",
        data={
            "power_entity": "sensor.test_power",
            "price_entity": "sensor.test_price",
            "energy_entity": "sensor.test_energy",
            "energy_source_type": "lifetime",
            "pricing_strategy": "external_complete_price",
            "price_included_components": [
                "market_energy",
                "supplier_markup",
                "energy_tax",
                "variable_grid_fee",
            ],
            "price_vat_treatment": "included",
            "price_completeness": "complete",
        },
    )


async def compile_period(hass, start):
    await async_wait_recording_done(hass)
    do_adhoc_statistics(hass, start=start)
    await async_wait_recording_done(hass)


async def recorded(hass, start, period="5minute"):
    return (
        await hass.async_add_executor_job(
            statistics_during_period,
            hass,
            start,
            start + (timedelta(hours=1) if period == "hour" else timedelta(minutes=5)),
            {ENTITY},
            period,
            None,
            {"state", "sum", "last_reset"},
        )
    )[ENTITY][-1]


def test_checkpoint_keeps_pending_months_in_publication_order():
    component = VariableCostComponent.MARKET_ENERGY
    rate = EffectivePriceBreakdown(Decimal(2), ((component, Decimal(2)),))
    timezone = ZoneInfo("Europe/Stockholm")
    history = VariableCostHistory()
    before = (DECEMBER - timedelta(minutes=1)).astimezone(timezone)
    after = DECEMBER.astimezone(timezone)
    for instant, amount in ((before, Decimal(2)), (after, Decimal(4))):
        booked = VariableCostSummary(
            instant, amount / 2, amount, ((component, amount),)
        )
        history.update(instant, "SEK", rate, None, booked)

    restored = VariableCostHistory()
    restored.restore(history.as_list())
    closing = restored.checkpoint
    assert closing.last_reset == NOVEMBER
    assert dict(closing.amounts) == {component: Decimal(2)}
    assert restored.confirm(closing)
    assert restored.dirty
    assert restored.checkpoint.last_reset == DECEMBER
    assert dict(restored.checkpoint.amounts) == {component: Decimal(4)}


@pytest.mark.parametrize("persistent_database", [True])
async def test_variable_cost_sum_through_month_boundary_and_core_restart(
    freezer, hass_tmp_config_dir, async_test_recorder, persistent_database
):
    freezer.move_to(START)
    async with recording_home(hass_tmp_config_dir, async_test_recorder) as hass:
        entry = config_entry()
        # Simulate an upgrade mid-month. The existing card already has SEK 20
        # of bundled cost. That balance cannot become part of the new history.
        legacy = CostLedger()
        old = (START - timedelta(minutes=10)).astimezone(
            dt_util.get_default_time_zone()
        )
        rate = EffectivePriceBreakdown(
            Decimal(2), ((VariableCostComponent.BUNDLED_PRICE, Decimal(2)),)
        )
        legacy.update(
            old, Decimal(90), None, rate.total, "SEK", lifetime=True, breakdown=rate
        )
        legacy.update(
            old + timedelta(minutes=2),
            Decimal(100),
            None,
            rate.total,
            "SEK",
            lifetime=True,
            breakdown=rate,
        )
        coordinator = ElectricityProCoordinator(hass, entry)
        await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.statistics").async_save(
            {
                "local_cost_scope": coordinator._local_cost_scope,
                "local_costs": legacy.as_dict(),
            }
        )
        hass.states.async_set("sensor.test_power", "1000", {"unit_of_measurement": "W"})
        set_price(hass, 2)
        set_energy(hass, 100)
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        coordinator = entry.runtime_data

        freezer.move_to(START + timedelta(minutes=1))
        set_energy(hass, 102)
        await hass.async_block_till_done()
        assert coordinator.data.results.household_variable_month == 24
        assert hass.states.get(ENTITY).state == "unavailable"
        with patch.object(
            coordinator._store, "_write_prepared_data", side_effect=WriteError
        ):
            await coordinator._async_save_statistics()
        assert hass.states.get(ENTITY).state == "unavailable"
        await coordinator._async_save_statistics()
        assert Decimal(hass.states.get(ENTITY).state) == 4
        (archived,) = coordinator.monthly_variable_cost_history
        assert archived.priced_kwh == 2
        assert dict(archived.components) == {
            VariableCostComponent.BUNDLED_PRICE: Decimal(4)
        }
        assert (
            hass.states.get("sensor.electricity_pro_spot_energy_cost_this_month").state
            == "unavailable"
        )
        set_price(hass, -1)
        await hass.async_block_till_done()

        freezer.move_to(START + timedelta(minutes=5))
        await compile_period(hass, START)
        initial = await recorded(hass, START.replace(minute=0), "hour")
        assert (initial["state"], initial["sum"]) == (4, 4)
        freezer.move_to(START + timedelta(minutes=7))
        set_energy(hass, 103)
        await hass.async_block_till_done()
        await coordinator._async_save_statistics()
        freezer.move_to(START + timedelta(minutes=10))
        await compile_period(hass, START + timedelta(minutes=5))

        # Resume readings just before local midnight after a meter outage.
        freezer.move_to(DECEMBER - timedelta(minutes=4))
        set_energy(hass, "unavailable")
        await hass.async_block_till_done()
        freezer.move_to(DECEMBER - timedelta(minutes=3))
        set_energy(hass, 103)
        await hass.async_block_till_done()

        freezer.move_to(DECEMBER)
        await compile_period(hass, DECEMBER - timedelta(minutes=5))
        november_cycle = await recorded(hass, DECEMBER - timedelta(hours=1), "hour")
        assert (november_cycle["state"], november_cycle["sum"]) == (3, 3)
        assert november_cycle["last_reset"] == NOVEMBER.timestamp()
        coordinator._async_daily_rollover(dt_util.now())
        await coordinator._async_save_statistics()
        assert Decimal(hass.states.get(ENTITY).state) == 0

        freezer.move_to(DECEMBER + timedelta(minutes=1))
        set_energy(hass, 104)
        await hass.async_block_till_done()
        await coordinator._async_save_statistics()
        freezer.move_to(DECEMBER + timedelta(minutes=5))
        await compile_period(hass, DECEMBER)
        first_december = await recorded(hass, DECEMBER)
        # One minute of the four-minute interval lies in the new month.
        assert (first_december["state"], first_december["sum"]) == (-0.25, 2.75)
        assert first_december["last_reset"] == DECEMBER.timestamp()

    freezer.move_to(DECEMBER + timedelta(minutes=54))
    async with recording_home(hass_tmp_config_dir, async_test_recorder) as hass:
        entry = config_entry()
        hass.states.async_set("sensor.test_power", "1000", {"unit_of_measurement": "W"})
        set_price(hass, -1)
        set_energy(hass, 110)
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        restored = hass.states.get(ENTITY)
        assert Decimal(restored.state) == Decimal("-0.25")
        assert restored.attributes["last_reset"] == DECEMBER.isoformat()
        november, december = entry.runtime_data.monthly_variable_cost_history
        assert november.month.month == 11 and november.priced_kwh == Decimal("3.75")
        assert dict(november.components) == {
            VariableCostComponent.BUNDLED_PRICE: Decimal("2.25")
        }
        assert december.month.month == 12 and december.priced_kwh == Decimal("0.25")
        assert dict(december.components) == {
            VariableCostComponent.BUNDLED_PRICE: Decimal("-0.25")
        }

        freezer.move_to(DECEMBER + timedelta(minutes=55))
        await compile_period(hass, DECEMBER + timedelta(minutes=50))
        freezer.move_to(DECEMBER + timedelta(minutes=56))
        set_energy(hass, 112)
        await hass.async_block_till_done()
        await entry.runtime_data._async_save_statistics()
        november_after, december_after = (
            entry.runtime_data.monthly_variable_cost_history
        )
        assert november_after == november
        assert december_after.priced_kwh == Decimal("2.25")
        assert december_after.has_gaps and not december_after.complete
        assert dict(december_after.components) == {
            VariableCostComponent.BUNDLED_PRICE: Decimal("-2.25")
        }
        freezer.move_to(DECEMBER + timedelta(hours=1))
        await compile_period(hass, DECEMBER + timedelta(minutes=55))
        last = await recorded(hass, DECEMBER, "hour")
        assert (last["state"], last["sum"]) == (-2.25, 0.75)
        assert last["last_reset"] == DECEMBER.timestamp()
        assert (
            await recorded(hass, DECEMBER - timedelta(hours=1), "hour")
            == november_cycle
        )
