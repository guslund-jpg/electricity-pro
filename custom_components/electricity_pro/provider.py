"""Data providers for Electricity Pro."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, State, callback

from .const import CONF_POWER_ENTITY, CONF_PRICE_ENTITY


@dataclass(frozen=True, slots=True)
class ElectricityProData:
    """Normalized Electricity Pro data."""

    current_power: Decimal | None
    current_price: Decimal | None
    current_price_unit: str | None


class ElectricityProEntityProvider:
    """Provide normalized data from Home Assistant entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the entity provider."""
        self._hass = hass
        self._power_entity_id: str = entry.options.get(
            CONF_POWER_ENTITY,
            entry.data[CONF_POWER_ENTITY],
        )

        self._price_entity_id: str | None = entry.options.get(
            CONF_PRICE_ENTITY,
            entry.data.get(CONF_PRICE_ENTITY),
        )

    @property
    def source_entity_ids(self) -> tuple[str, ...]:
        """Return all configured source entity IDs."""
        entity_ids = [self._power_entity_id]

        if self._price_entity_id is not None:
            entity_ids.append(self._price_entity_id)

        return tuple(entity_ids)

    @callback
    def read(self) -> ElectricityProData:
        """Read and normalize all configured source entities."""
        current_price, current_price_unit = self._normalize_price(
            self._hass.states.get(self._price_entity_id)
            if self._price_entity_id is not None
            else None
        )

        return ElectricityProData(
            current_power=self._normalize_power(
                self._hass.states.get(self._power_entity_id)
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
