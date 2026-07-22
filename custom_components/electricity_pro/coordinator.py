"""Data coordinator for Electricity Pro."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_POWER_ENTITY, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ElectricityProData:
    """Normalized Electricity Pro data."""

    current_power: Decimal | None


class ElectricityProCoordinator(
    DataUpdateCoordinator[ElectricityProData]
):
    """Coordinate source entity updates for Electricity Pro."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
        )

        self.config_entry = config_entry
        self._power_entity_id = config_entry.data[CONF_POWER_ENTITY]
        self.data = ElectricityProData(current_power=None)

    async def async_start(self) -> None:
        """Start listening for source entity changes."""
        self.config_entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                [self._power_entity_id],
                self._async_source_state_changed,
            )
        )

        self.async_set_updated_data(self._read_source_data())

    @callback
    def _async_source_state_changed(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle a configured source entity update."""
        self.async_set_updated_data(self._read_source_data())

    @callback
    def _read_source_data(self) -> ElectricityProData:
        """Read and normalize all configured source entities."""
        return ElectricityProData(
            current_power=self._read_power_source(),
        )

    @callback
    def _read_power_source(self) -> Decimal | None:
        """Read and normalize the configured power source."""
        source_state = self.hass.states.get(self._power_entity_id)

        if source_state is None:
            return None

        if source_state.state in {
            "unknown",
            "unavailable",
            "",
        }:
            return None

        try:
            source_value = Decimal(source_state.state)
        except (InvalidOperation, ValueError):
            return None

        watts = self._convert_to_watts(
            source_value,
            source_state.attributes.get("unit_of_measurement"),
        )

        if watts is None or watts < 0:
            return None

        return watts

    @staticmethod
    def _convert_to_watts(
        value: Decimal,
        source_unit: Any,
    ) -> Decimal | None:
        """Convert a supported power value to watts."""
        if source_unit == UnitOfPower.WATT:
            return value

        if source_unit == UnitOfPower.KILO_WATT:
            return value * Decimal("1000")

        return None
