"""Data coordinator for Electricity Pro."""

from __future__ import annotations

import logging

from dataclasses import replace
from decimal import Decimal
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .provider import (
    ElectricityProData,
    ElectricityProEntityProvider,
)
from .statistics_engine import (
    CalendarPeriod,
    CumulativeStatistic,
    StatisticsSnapshot,
)

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1
_ENERGY_THIS_MONTH = "energy_this_month"
_KWH_PER_WH = Decimal("0.001")


class ElectricityProCoordinator(
    DataUpdateCoordinator[ElectricityProData]
):
    """Coordinate Electricity Pro provider updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )

        self._entry = entry
        self._provider = ElectricityProEntityProvider(
            hass=hass,
            entry=entry,
        )
        self._energy_this_month = CumulativeStatistic(CalendarPeriod.MONTH)
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry.entry_id}.statistics",
        )

    async def async_start(self) -> None:
        """Start listening for provider source changes."""
        await self._async_restore_statistics()

        self._entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                self._provider.source_entity_ids,
                self._async_source_changed,
            )
        )

        self.async_set_updated_data(self._read())

    @callback
    def _async_source_changed(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle a configured source entity change."""
        self.async_set_updated_data(self._read())

    async def _async_restore_statistics(self) -> None:
        """Restore persisted statistics state when available."""
        stored = await self._store.async_load()
        if stored is None or _ENERGY_THIS_MONTH not in stored:
            return

        try:
            snapshot = StatisticsSnapshot.from_dict(stored[_ENERGY_THIS_MONTH])
        except ValueError:
            _LOGGER.warning("Ignoring invalid persisted statistics state")
            return

        self._energy_this_month = CumulativeStatistic(
            CalendarPeriod.MONTH,
            snapshot,
        )

    @callback
    def _read(self) -> ElectricityProData:
        """Read provider data and update derived statistics."""
        data = self._provider.read()
        energy_kwh = _energy_in_kwh(
            data.current_energy,
            data.current_energy_unit,
        )

        if energy_kwh is None:
            return replace(
                data,
                energy_this_month=None,
                energy_this_month_unit=None,
            )

        value = self._energy_this_month.update(energy_kwh, dt_util.now())
        self._store.async_delay_save(self._statistics_data, delay=1)

        return replace(
            data,
            energy_this_month=value,
            energy_this_month_unit=UnitOfEnergy.KILO_WATT_HOUR,
        )

    @callback
    def _statistics_data(self) -> dict[str, Any]:
        """Return serializable statistics state."""
        snapshot = self._energy_this_month.snapshot
        if snapshot is None:
            return {}
        return {_ENERGY_THIS_MONTH: snapshot.as_dict()}


def _energy_in_kwh(
    value: Decimal | None,
    unit: str | None,
) -> Decimal | None:
    """Normalize a cumulative energy measurement to kilowatt-hours."""
    if value is None:
        return None
    if unit == UnitOfEnergy.KILO_WATT_HOUR:
        return value
    if unit == UnitOfEnergy.WATT_HOUR:
        return value * _KWH_PER_WH
    return None
