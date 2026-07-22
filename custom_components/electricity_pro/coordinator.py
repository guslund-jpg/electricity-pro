"""Data coordinator for Electricity Pro."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfPower,
)
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_POWER_ENTITY, CONF_PRICE_ENTITY, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ElectricityProData:
    """Normalized Electricity Pro data."""

    current_power: Decimal | None
    current_price: Decimal | None
    current_price_unit: str | None


class ElectricityProCoordinator(
    DataUpdateCoordinator[ElectricityProData]
):
    """Coordinate source entity updates."""

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
        self._power_entity_id = entry.data[CONF_POWER_ENTITY]
        self._price_entity_id: str | None = entry.data.get(
            CONF_PRICE_ENTITY
        )

    async def async_start(self) -> None:
        """Start listening for source entity changes."""
        source_entity_ids = [self._power_entity_id]

        if self._price_entity_id is not None:
            source_entity_ids.append(self._price_entity_id)

        self._entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                source_entity_ids,
                self._async_source_changed,
            )
        )

        self.async_set_updated_data(self._read_data())

    @callback
    def _async_source_changed(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle a configured source entity change."""
        self.async_set_updated_data(self._read_data())

    @callback
    def _read_data(self) -> ElectricityProData:
        """Read and normalize configured source entities."""
        current_price, current_price_unit = self._normalize_price(
            self.hass.states.get(self._price_entity_id)
            if self._price_entity_id is not None
            else None
        )

        return ElectricityProData(
            current_power=self._normalize_power(
                self.hass.states.get(self._power_entity_id)
            ),
            current_price=current_price,
            current_price_unit=current_price_unit,
        )

    @staticmethod
    def _normalize_power(
        source_state: State | None,
    ) -> Decimal | None:
        """Normalize a source power state to watts."""
        if (
            source_state is None
            or source_state.state
            in {
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
                "",
            }
        ):
            return None

        try:
            source_value = Decimal(source_state.state)
        except (InvalidOperation, ValueError):
            return None

        source_unit: Any = source_state.attributes.get(
            "unit_of_measurement"
        )

        if source_unit == UnitOfPower.WATT:
            watts = source_value
        elif source_unit == UnitOfPower.KILO_WATT:
            watts = source_value * Decimal("1000")
        else:
            return None

        if not watts.is_finite() or watts < 0:
            return None

        return watts

    @staticmethod
    def _normalize_price(
        source_state: State | None,
    ) -> tuple[Decimal | None, str | None]:
        """Normalize a source electricity price."""
        if (
            source_state is None
            or source_state.state
            in {
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
                "",
            }
        ):
            return None, None

        try:
            source_value = Decimal(source_state.state)
        except (InvalidOperation, ValueError):
            return None, None

        source_unit = source_state.attributes.get(
            "unit_of_measurement"
        )

        if (
            not source_value.is_finite()
            or source_value < 0
            or not isinstance(source_unit, str)
            or not source_unit.strip()
        ):
            return None, None

        return source_value, source_unit
