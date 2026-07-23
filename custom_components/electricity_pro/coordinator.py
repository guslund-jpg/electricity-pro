"""Data coordinator for Electricity Pro."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .provider import (
    ElectricityProData,
    ElectricityProEntityProvider,
)

_LOGGER = logging.getLogger(__name__)


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

    async def async_start(self) -> None:
        """Start listening for provider source changes."""
        self._entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                self._provider.source_entity_ids,
                self._async_source_changed,
            )
        )

        self.async_set_updated_data(self._provider.read())

    @callback
    def _async_source_changed(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle a configured source entity change."""
        self.async_set_updated_data(self._provider.read())
