"""Exercise measured hourly import through Home Assistant and its checkpoints."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from homeassistant import loader
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import frame
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    async_test_home_assistant,
)

from custom_components.electricity_pro.const import (
    CONF_ENERGY_ENTITY,
    CONF_HOURLY_IMPORT_ENTITY,
    CONF_HOURLY_IMPORT_METER,
    DOMAIN,
)

SOURCE = "sensor.hourly_import"
METER = "sensor.test_energy"


def report(hass, start, value, *, source=SOURCE, unit="kWh", end=None):
    start = datetime.fromisoformat(start)
    end = end or (start + timedelta(hours=1)).isoformat()
    hass.states.async_set(
        source,
        value,
        {
            "unit_of_measurement": unit,
            "interval_start": start.isoformat(),
            "interval_end": end,
        },
    )


def blocks(entry):
    return {
        block.start.isoformat(): block.energy_kwh
        for block in entry.runtime_data.hourly_import_blocks
    }


async def open_source_form(hass, entry):
    manager = hass.config_entries.options
    menu = await manager.async_init(entry.entry_id)
    return await manager.async_configure(
        menu["flow_id"], {"next_step_id": "hourly_import"}
    )


async def select_source(hass, entry, source=SOURCE):
    form = await open_source_form(hass, entry)
    result = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {CONF_HOURLY_IMPORT_ENTITY: source, "confirm_hourly_import_meter": True}
        if source
        else {},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


@pytest.fixture
async def meter(hass, setup_electricity_pro, freezer):
    await hass.config.async_set_time_zone("Europe/Stockholm")
    freezer.move_to("2026-11-10T12:00:00+00:00")
    return await setup_electricity_pro(energy_value="120")


async def test_confirmed_source_reads_startup_and_late_reports_without_duplicates(
    hass, meter
):
    report(hass, "2026-11-10T10:00:00+00:00", "2")
    form = await open_source_form(hass, meter)
    assert form["description_placeholders"]["meter"] == METER
    rejected = await hass.config_entries.options.async_configure(
        form["flow_id"], {CONF_HOURLY_IMPORT_ENTITY: SOURCE}
    )
    assert rejected["errors"] == {
        "confirm_hourly_import_meter": "confirm_hourly_import_meter"
    }
    assert CONF_HOURLY_IMPORT_ENTITY not in meter.options
    with pytest.raises(InvalidData, match=CONF_HOURLY_IMPORT_ENTITY):
        await hass.config_entries.options.async_configure(
            form["flow_id"],
            {CONF_HOURLY_IMPORT_ENTITY: METER, "confirm_hourly_import_meter": True},
        )
    result = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {CONF_HOURLY_IMPORT_ENTITY: SOURCE, "confirm_hourly_import_meter": True},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert meter.options[CONF_HOURLY_IMPORT_METER] == METER

    report(hass, "2026-11-10T08:00:00+00:00", "1250", unit="Wh")
    report(hass, "2026-11-10T09:00:00+00:00", "0")
    report(hass, "2026-11-10T08:00:00+00:00", "1.25")
    await hass.async_block_till_done()
    assert blocks(meter) == {
        "2026-11-10T08:00:00+00:00": Decimal("1.25"),
        "2026-11-10T09:00:00+00:00": Decimal(0),
        "2026-11-10T10:00:00+00:00": Decimal(2),
    }


@pytest.mark.parametrize(
    ("start", "value", "unit", "end"),
    [
        ("2026-11-10T10:00:00", "2", "kWh", None),
        ("2026-11-10T10:00:00+00:00", "unavailable", "kWh", None),
        ("2026-11-10T10:00:00+00:00", "2", "W", None),
        ("2026-11-10T10:00:00+00:00", "-1", "kWh", None),
        ("2026-11-10T10:00:00+00:00", "2", "kWh", "2026-11-10T10:30:00+00:00"),
        ("2026-11-10T10:05:00+00:00", "2", "kWh", None),
        ("2026-11-10T12:00:00+00:00", "2", "kWh", None),
    ],
    ids=[
        "missing-offset",
        "unavailable",
        "wrong-unit",
        "negative",
        "short",
        "off-boundary",
        "unfinished",
    ],
)
async def test_rejects_reports_without_a_valid_closed_hour(
    hass, meter, start, value, unit, end
):
    await select_source(hass, meter)
    report(hass, start, value, unit=unit, end=end)
    await hass.async_block_till_done()
    assert blocks(meter) == {}


async def test_source_change_and_meter_change_keep_measurements_separate(hass, meter):
    await select_source(hass, meter)
    report(hass, "2026-11-10T08:00:00+00:00", "1")
    await hass.async_block_till_done()
    assert len(blocks(meter)) == 1

    replacement = "sensor.replacement_hourly_import"
    await select_source(hass, meter, replacement)
    report(hass, "2026-11-10T09:00:00+00:00", "20")
    report(hass, "2026-11-10T08:00:00+00:00", "2", source=replacement)
    await hass.async_block_till_done()
    assert blocks(meter) == {"2026-11-10T08:00:00+00:00": Decimal(2)}

    hass.config_entries.async_update_entry(
        meter, options={**meter.options, CONF_ENERGY_ENTITY: "sensor.replacement_meter"}
    )
    await hass.async_block_till_done()
    assert blocks(meter) == {}
    report(hass, "2026-11-10T09:00:00+00:00", "3", source=replacement)
    await hass.async_block_till_done()
    assert blocks(meter) == {}

    await select_source(hass, meter, replacement)
    assert blocks(meter) == {"2026-11-10T09:00:00+00:00": Decimal(3)}
    await select_source(hass, meter, None)
    assert meter.options[CONF_HOURLY_IMPORT_ENTITY] is None
    assert blocks(meter) == {}


async def test_reloading_does_not_make_a_premature_report_valid(hass, meter, freezer):
    await select_source(hass, meter)
    start = "2026-11-10T12:00:00+00:00"
    report(hass, start, "2")
    await hass.async_block_till_done()
    assert blocks(meter) == {}

    freezer.move_to("2026-11-10T13:01:00+00:00")
    assert await hass.config_entries.async_reload(meter.entry_id)
    await hass.async_block_till_done()
    assert blocks(meter) == {}

    report(hass, start, "2")
    await hass.async_block_till_done()
    assert blocks(meter) == {start: Decimal(2)}


async def test_restart_restores_good_blocks_and_conflicts_and_reads_current_report(
    hass, meter, freezer, hass_storage
):
    await select_source(hass, meter)
    report(hass, "2026-11-10T08:00:00+00:00", "1")
    report(hass, "2026-11-10T09:00:00+00:00", "2")
    report(hass, "2026-11-10T09:00:00+00:00", "3")
    await hass.async_block_till_done()
    freezer.move_to("2026-11-10T12:01:00+00:00")
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    checkpoint = hass_storage[f"{DOMAIN}.{meter.entry_id}.statistics"]["data"]
    assert checkpoint["hourly_import"]["blocks"] == {
        "2026-11-10T08:00:00+00:00": "1",
        "2026-11-10T09:00:00+00:00": None,
    }
    assert "core.config_entries" in hass_storage

    assert await hass.config_entries.async_unload(meter.entry_id)
    async with async_test_home_assistant() as restarted:
        restarted.data.pop(loader.DATA_CUSTOM_COMPONENTS)
        frame.async_setup(restarted)
        await restarted.config.async_set_time_zone("Europe/Stockholm")
        await restarted.config_entries.async_initialize()
        try:
            report(restarted, "2026-11-10T10:00:00+00:00", "4")
            assert await restarted.config_entries.async_setup(meter.entry_id)
            entry = restarted.config_entries.async_get_entry(meter.entry_id)
            report(restarted, "2026-11-10T09:00:00+00:00", "2")
            await restarted.async_block_till_done()
            assert blocks(entry) == {
                "2026-11-10T08:00:00+00:00": Decimal(1),
                "2026-11-10T10:00:00+00:00": Decimal(4),
            }
            assert await restarted.config_entries.async_unload(meter.entry_id)
        finally:
            await restarted.async_stop(force=True)


async def test_local_month_rollover_keeps_late_previous_month_and_prunes_older_data(
    hass, meter, freezer
):
    freezer.move_to("2026-11-30T22:50:00+00:00")
    await select_source(hass, meter)
    report(hass, "2026-10-31T22:00:00+00:00", "1")
    report(hass, "2026-11-30T21:00:00+00:00", "2")
    await hass.async_block_till_done()
    assert len(blocks(meter)) == 2

    freezer.move_to("2026-11-30T23:05:00+00:00")
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    report(hass, "2026-11-30T22:00:00+00:00", "3")
    report(hass, "2026-10-31T22:00:00+00:00", "4")
    freezer.move_to("2026-12-01T00:05:00+00:00")
    report(hass, "2026-11-30T23:00:00+00:00", "5")
    await hass.async_block_till_done()
    assert blocks(meter) == {
        "2026-11-30T21:00:00+00:00": Decimal(2),
        "2026-11-30T22:00:00+00:00": Decimal(3),
        "2026-11-30T23:00:00+00:00": Decimal(5),
    }


async def test_both_autumn_clock_hours_can_report_the_same_amount(hass, meter, freezer):
    freezer.move_to("2026-10-25T03:00:00+00:00")
    await select_source(hass, meter)
    report(hass, "2026-10-25T02:00:00+02:00", "2", end="2026-10-25T02:00:00+01:00")
    report(hass, "2026-10-25T02:00:00+01:00", "2")
    await hass.async_block_till_done()
    assert blocks(meter) == {
        "2026-10-25T00:00:00+00:00": Decimal(2),
        "2026-10-25T01:00:00+00:00": Decimal(2),
    }
