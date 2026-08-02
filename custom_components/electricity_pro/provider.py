"""Data providers for Electricity Pro."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, State, callback

from .const import (
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
    CONF_CURRENT_L1_ENTITY,
    CONF_CURRENT_L2_ENTITY,
    CONF_CURRENT_L3_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_PEAK_POWER_TODAY_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
)


@dataclass(frozen=True, slots=True)
class ElectricityProData:
    """Normalized Electricity Pro data."""

    current_power: Decimal | None
    current_price: Decimal | None
    current_price_unit: str | None
    current_energy: Decimal | None
    current_energy_unit: str | None
    accumulated_cost_today: Decimal | None
    accumulated_cost_today_unit: str | None
    peak_power_today: Decimal | None
    current_l1: Decimal | None
    current_l2: Decimal | None
    current_l3: Decimal | None


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

        self._energy_entity_id: str | None = entry.options.get(
            CONF_ENERGY_ENTITY,
            entry.data.get(CONF_ENERGY_ENTITY),
        )

        self._accumulated_cost_today_entity_id: str | None = entry.options.get(
            CONF_ACCUMULATED_COST_TODAY_ENTITY,
            entry.data.get(CONF_ACCUMULATED_COST_TODAY_ENTITY),
        )
        self._peak_power_today_entity_id: str | None = entry.options.get(
            CONF_PEAK_POWER_TODAY_ENTITY,
            entry.data.get(CONF_PEAK_POWER_TODAY_ENTITY),
        )
        self._current_l1_entity_id: str | None = entry.options.get(
            CONF_CURRENT_L1_ENTITY,
            entry.data.get(CONF_CURRENT_L1_ENTITY),
        )
        self._current_l2_entity_id: str | None = entry.options.get(
            CONF_CURRENT_L2_ENTITY,
            entry.data.get(CONF_CURRENT_L2_ENTITY),
        )
        self._current_l3_entity_id: str | None = entry.options.get(
            CONF_CURRENT_L3_ENTITY,
            entry.data.get(CONF_CURRENT_L3_ENTITY),
        )

    @property
    def source_entity_ids(self) -> tuple[str, ...]:
        """Return all configured source entity IDs."""
        entity_ids = [self._power_entity_id]

        if self._price_entity_id is not None:
            entity_ids.append(self._price_entity_id)

        if self._energy_entity_id is not None:
            entity_ids.append(self._energy_entity_id)

        if self._accumulated_cost_today_entity_id is not None:
            entity_ids.append(self._accumulated_cost_today_entity_id)

        if self._peak_power_today_entity_id is not None:
            entity_ids.append(self._peak_power_today_entity_id)

        if self._current_l1_entity_id is not None:
            entity_ids.append(self._current_l1_entity_id)

        if self._current_l2_entity_id is not None:
            entity_ids.append(self._current_l2_entity_id)

        if self._current_l3_entity_id is not None:
            entity_ids.append(self._current_l3_entity_id)

        return tuple(entity_ids)

    @callback
    def read(self) -> ElectricityProData:
        """Read and normalize all configured source entities."""
        current_energy, current_energy_unit = self._normalize_energy(
            self._hass.states.get(self._energy_entity_id)
            if self._energy_entity_id is not None
            else None
        )

        current_price, current_price_unit = self._normalize_price(
            self._hass.states.get(self._price_entity_id)
            if self._price_entity_id is not None
            else None
        )

        accumulated_cost_today, accumulated_cost_today_unit = self._normalize_cost(
            self._hass.states.get(self._accumulated_cost_today_entity_id)
            if self._accumulated_cost_today_entity_id is not None
            else None
        )
        peak_power_today = self._normalize_power(
            self._hass.states.get(self._peak_power_today_entity_id)
            if self._peak_power_today_entity_id is not None
            else None
        )
        current_l1 = self._normalize_current(
            self._hass.states.get(self._current_l1_entity_id)
            if self._current_l1_entity_id is not None
            else None
        )

        current_l2 = self._normalize_current(
            self._hass.states.get(self._current_l2_entity_id)
            if self._current_l2_entity_id is not None
            else None
        )

        current_l3 = self._normalize_current(
            self._hass.states.get(self._current_l3_entity_id)
            if self._current_l3_entity_id is not None
            else None
        )

        return ElectricityProData(
            current_power=self._normalize_power(
                self._hass.states.get(self._power_entity_id)
            ),
            current_price=current_price,
            current_price_unit=current_price_unit,
            current_energy=current_energy,
            current_energy_unit=current_energy_unit,
            accumulated_cost_today=accumulated_cost_today,
            accumulated_cost_today_unit=accumulated_cost_today_unit,
            peak_power_today=peak_power_today,
            current_l1=current_l1,
            current_l2=current_l2,
            current_l3=current_l3,
        )

    @staticmethod
    def _normalize_power(
        source_state: State | None,
    ) -> Decimal | None:
        """Normalize a source power state to watts."""
        if source_state is None or source_state.state in {
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
            "",
        }:
            return None

        try:
            source_value = Decimal(source_state.state)
        except (InvalidOperation, ValueError):
            return None

        source_unit: Any = source_state.attributes.get("unit_of_measurement")

        if source_unit == UnitOfPower.WATT:
            watts = source_value
        elif source_unit == UnitOfPower.KILO_WATT:
            watts = source_value * Decimal(1000)
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
        if source_state is None or source_state.state in {
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
            "",
        }:
            return None, None

        try:
            source_value = Decimal(source_state.state)
        except (InvalidOperation, ValueError):
            return None, None

        source_unit = source_state.attributes.get("unit_of_measurement")

        if (
            not source_value.is_finite()
            or source_value < 0
            or not isinstance(source_unit, str)
            or not source_unit.strip()
        ):
            return None, None

        return source_value, source_unit

    @staticmethod
    def _normalize_energy(
        source_state: State | None,
    ) -> tuple[Decimal | None, str | None]:
        """Normalize a source electricity energy value."""
        if source_state is None or source_state.state in {
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
            "",
        }:
            return None, None

        try:
            source_value = Decimal(source_state.state)
        except (InvalidOperation, ValueError):
            return None, None

        source_unit = source_state.attributes.get("unit_of_measurement")

        if source_unit not in {
            UnitOfEnergy.WATT_HOUR,
            UnitOfEnergy.KILO_WATT_HOUR,
        }:
            return None, None

        if not source_value.is_finite() or source_value < 0:
            return None, None

        return source_value, source_unit

    @staticmethod
    def _normalize_cost(
        source_state: State | None,
    ) -> tuple[Decimal | None, str | None]:
        """Normalize an accumulated electricity cost."""
        if source_state is None or source_state.state in {
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
            "",
        }:
            return None, None

        try:
            source_value = Decimal(source_state.state)
        except (InvalidOperation, ValueError):
            return None, None

        source_unit = source_state.attributes.get("unit_of_measurement")

        if (
            not source_value.is_finite()
            or source_value < 0
            or not isinstance(source_unit, str)
            or not source_unit.strip()
        ):
            return None, None

        return source_value, source_unit

    @staticmethod
    def _normalize_current(
        source_state: State | None,
    ) -> Decimal | None:
        """Normalize a source electrical current to amperes."""
        if source_state is None or source_state.state in {
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
            "",
        }:
            return None

        try:
            source_value = Decimal(source_state.state)
        except (InvalidOperation, ValueError):
            return None

        source_unit: Any = source_state.attributes.get("unit_of_measurement")

        if source_unit == "A":
            amperes = source_value
        elif source_unit == "mA":
            amperes = source_value / Decimal(1000)
        else:
            return None

        if not amperes.is_finite() or amperes < 0:
            return None

        return amperes
