"""Data providers for Electricity Pro."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
    CONF_CURRENT_L1_ENTITY,
    CONF_CURRENT_L2_ENTITY,
    CONF_CURRENT_L3_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_GRID_FEE_PER_KWH,
    CONF_GOOD_PRICE_THRESHOLD,
    CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
    CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
    CONF_PEAK_POWER_TODAY_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
    CONF_TAX_PER_KWH,
    CONF_VOLTAGE_L1_ENTITY,
    CONF_VOLTAGE_L2_ENTITY,
    CONF_VOLTAGE_L3_ENTITY,
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
    voltage_l1: Decimal | None
    voltage_l2: Decimal | None
    voltage_l3: Decimal | None
    monthly_peak_hour_consumption: Decimal | None
    monthly_peak_hour_consumption_unit: str | None
    monthly_peak_hour_time: datetime | None
    energy_this_month: Decimal | None
    energy_this_month_unit: str | None
    cost_this_month: Decimal | None
    cost_this_month_unit: str | None
    grid_fee_per_kwh: Decimal | None
    tax_per_kwh: Decimal | None
    good_price_threshold: Decimal | None


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
        self._voltage_l1_entity_id: str | None = entry.options.get(
            CONF_VOLTAGE_L1_ENTITY,
            entry.data.get(CONF_VOLTAGE_L1_ENTITY),
        )
        self._voltage_l2_entity_id: str | None = entry.options.get(
            CONF_VOLTAGE_L2_ENTITY,
            entry.data.get(CONF_VOLTAGE_L2_ENTITY),
        )
        self._voltage_l3_entity_id: str | None = entry.options.get(
            CONF_VOLTAGE_L3_ENTITY,
            entry.data.get(CONF_VOLTAGE_L3_ENTITY),
        )
        self._monthly_peak_hour_consumption_entity_id: str | None = entry.options.get(
            CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
            entry.data.get(CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY),
        )
        self._monthly_peak_hour_time_entity_id: str | None = entry.options.get(
            CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
            entry.data.get(CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY),
        )
        self._grid_fee_per_kwh = self._normalize_adjustment(
            entry.options.get(
                CONF_GRID_FEE_PER_KWH,
                entry.data.get(CONF_GRID_FEE_PER_KWH),
            )
        )
        self._tax_per_kwh = self._normalize_adjustment(
            entry.options.get(
                CONF_TAX_PER_KWH,
                entry.data.get(CONF_TAX_PER_KWH),
            )
        )
        self._good_price_threshold = self._normalize_adjustment(
            entry.options.get(
                CONF_GOOD_PRICE_THRESHOLD,
                entry.data.get(CONF_GOOD_PRICE_THRESHOLD),
            )
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

        if self._voltage_l1_entity_id is not None:
            entity_ids.append(self._voltage_l1_entity_id)

        if self._voltage_l2_entity_id is not None:
            entity_ids.append(self._voltage_l2_entity_id)

        if self._voltage_l3_entity_id is not None:
            entity_ids.append(self._voltage_l3_entity_id)

        if self._monthly_peak_hour_consumption_entity_id is not None:
            entity_ids.append(self._monthly_peak_hour_consumption_entity_id)

        if self._monthly_peak_hour_time_entity_id is not None:
            entity_ids.append(self._monthly_peak_hour_time_entity_id)

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
        voltage_l1 = self._normalize_voltage(
            self._hass.states.get(self._voltage_l1_entity_id)
            if self._voltage_l1_entity_id is not None
            else None
        )
        voltage_l2 = self._normalize_voltage(
            self._hass.states.get(self._voltage_l2_entity_id)
            if self._voltage_l2_entity_id is not None
            else None
        )
        voltage_l3 = self._normalize_voltage(
            self._hass.states.get(self._voltage_l3_entity_id)
            if self._voltage_l3_entity_id is not None
            else None
        )
        (
            monthly_peak_hour_consumption,
            monthly_peak_hour_consumption_unit,
        ) = self._normalize_energy(
            self._hass.states.get(self._monthly_peak_hour_consumption_entity_id)
            if self._monthly_peak_hour_consumption_entity_id is not None
            else None
        )
        monthly_peak_hour_time = self._normalize_timestamp(
            self._hass.states.get(self._monthly_peak_hour_time_entity_id)
            if self._monthly_peak_hour_time_entity_id is not None
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
            voltage_l1=voltage_l1,
            voltage_l2=voltage_l2,
            voltage_l3=voltage_l3,
            monthly_peak_hour_consumption=monthly_peak_hour_consumption,
            monthly_peak_hour_consumption_unit=(
                monthly_peak_hour_consumption_unit
            ),
            monthly_peak_hour_time=monthly_peak_hour_time,
            energy_this_month=None,
            energy_this_month_unit=None,
            cost_this_month=None,
            cost_this_month_unit=None,
            grid_fee_per_kwh=self._grid_fee_per_kwh,
            tax_per_kwh=self._tax_per_kwh,
            good_price_threshold=self._good_price_threshold,
        )

    @staticmethod
    def _parse_state(source_state: State | None) -> Decimal | None:
        """Parse a HA state into a Decimal, or return None if unavailable/invalid."""
        if source_state is None or source_state.state in {
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
            "",
        }:
            return None
        try:
            return Decimal(source_state.state)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _normalize_timestamp(source_state: State | None) -> datetime | None:
        """Normalize a timestamp source to a timezone-aware datetime."""
        if source_state is None or source_state.state in {
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
            "",
        }:
            return None

        timestamp = dt_util.parse_datetime(source_state.state)
        if timestamp is None or timestamp.tzinfo is None:
            return None

        return timestamp

    @staticmethod
    def _normalize_adjustment(value: Any) -> Decimal | None:
        """Normalize an optional configured per-kWh adjustment."""
        if value is None:
            return None
        try:
            adjustment = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
        if not adjustment.is_finite() or adjustment < 0:
            return None
        return adjustment

    @staticmethod
    def _normalize_power(
        source_state: State | None,
    ) -> Decimal | None:
        """Normalize a source power state to watts."""
        source_value = ElectricityProEntityProvider._parse_state(source_state)
        if source_value is None:
            return None

        source_unit: Any = source_state.attributes.get("unit_of_measurement")  # type: ignore[union-attr]

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
        source_value = ElectricityProEntityProvider._parse_state(source_state)
        if source_value is None:
            return None, None

        source_unit = source_state.attributes.get("unit_of_measurement")  # type: ignore[union-attr]

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
        source_value = ElectricityProEntityProvider._parse_state(source_state)
        if source_value is None:
            return None, None

        source_unit = source_state.attributes.get("unit_of_measurement")  # type: ignore[union-attr]

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
        source_value = ElectricityProEntityProvider._parse_state(source_state)
        if source_value is None:
            return None, None

        source_unit = source_state.attributes.get("unit_of_measurement")  # type: ignore[union-attr]

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
        source_value = ElectricityProEntityProvider._parse_state(source_state)
        if source_value is None:
            return None

        source_unit: Any = source_state.attributes.get("unit_of_measurement")  # type: ignore[union-attr]

        if source_unit == "A":
            amperes = source_value
        elif source_unit == "mA":
            amperes = source_value / Decimal(1000)
        else:
            return None

        if not amperes.is_finite() or amperes < 0:
            return None

        return amperes

    @staticmethod
    def _normalize_voltage(
        source_state: State | None,
    ) -> Decimal | None:
        """Normalize a source electrical voltage to volts."""
        source_value = ElectricityProEntityProvider._parse_state(source_state)
        if source_value is None:
            return None

        source_unit: Any = source_state.attributes.get("unit_of_measurement")  # type: ignore[union-attr]

        if source_unit == "V":
            volts = source_value
        elif source_unit == "mV":
            volts = source_value / Decimal(1000)
        else:
            return None

        if not volts.is_finite() or volts < 0:
            return None

        return volts
