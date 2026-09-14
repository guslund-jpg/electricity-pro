"""Monthly source scoping and targeted recovery tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    DOMAIN, CONF_POWER_ENTITY, CONF_ENERGY_ENTITY, CONF_ENERGY_SOURCE_TYPE,
)
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator


def make_entry(source="sensor.energy", mode="daily"):
    return MockConfigEntry(domain=DOMAIN, data={
        CONF_POWER_ENTITY: "sensor.power", CONF_ENERGY_ENTITY: source,
        CONF_ENERGY_SOURCE_TYPE: mode,
    })


@pytest.mark.parametrize("change", ["none", "entity", "semantics", "legacy"])
async def test_monthly_restore_scope(hass, change):
    hass.config.time_zone = "UTC"
    entry = make_entry()
    original = ElectricityProCoordinator(hass, entry)
    now = datetime(2026, 9, 14, 12, tzinfo=UTC)
    original._energy_this_month.update(Decimal(10), now)
    original._energy_this_month.update(Decimal(15), now)
    stored = original._statistics_data()
    if change == "legacy":
        stored.pop("monthly_energy_source")
    changed = make_entry(
        "sensor.other" if change == "entity" else "sensor.energy",
        "lifetime" if change == "semantics" else "daily",
    )
    restored = ElectricityProCoordinator(hass, changed)
    with patch.object(restored._store, "async_load", return_value=stored):
        await restored._async_restore_statistics()
    if change in ("entity", "semantics"):
        assert restored._energy_this_month.snapshot is None
    else:
        assert restored._energy_this_month.value == Decimal(5)
    if change == "legacy":
        assert restored.monthly_energy_attributes["coverage"] == "unverified"


async def test_reset_rebases_only_month_and_survives_restart(hass):
    hass.config.time_zone = "UTC"
    hass.states.async_set("sensor.energy", "59", {"unit_of_measurement": "kWh"})
    entry = make_entry()
    c = ElectricityProCoordinator(hass, entry)
    now = datetime(2026, 9, 14, 12, tzinfo=UTC)
    with (
        patch("custom_components.electricity_pro.coordinator.dt_util.now", return_value=now),
        patch.object(c._store, "async_delay_save"),
        patch.object(c._store, "async_save") as save,
    ):
        c._energy_this_month.update(Decimal(0), now)
        c._energy_this_month.update(Decimal(326950), now)
        await c.async_reset_monthly_energy()
        assert c.data.energy_this_month == 0
        assert c.data.current_energy == Decimal(59)
        assert c.monthly_energy_attributes["coverage"] == "partial"
        stored = save.call_args.args[0]
        restored = ElectricityProCoordinator(hass, entry)
        with patch.object(restored._store, "async_load", return_value=stored):
            await restored._async_restore_statistics()
        hass.states.async_set("sensor.energy", "60", {"unit_of_measurement": "kWh"})
        with patch.object(restored._store, "async_delay_save"):
            assert restored._read().energy_this_month == Decimal(1)
        assert restored.monthly_energy_attributes["coverage"] == "partial"


async def test_reset_unavailable_energy_preserves_total(hass):
    c = ElectricityProCoordinator(hass, make_entry())
    now = datetime(2026, 9, 14, 12, tzinfo=UTC)
    c._energy_this_month.update(Decimal(0), now)
    c._energy_this_month.update(Decimal(5), now)
    with patch.object(c._store, "async_delay_save"):
        with pytest.raises(ValueError, match="valid energy"):
            await c.async_reset_monthly_energy()
    assert c._energy_this_month.value == Decimal(5)
