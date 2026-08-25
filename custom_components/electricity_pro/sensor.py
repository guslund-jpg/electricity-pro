"""Sensor platform for Electricity Pro."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import ElectricityProConfigEntry
from .calculations import (
    calculate_consumption_weighted_average_price,
    calculate_current_cost_rate,
    calculate_declared_effective_price,
)
from .const import (
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
    CONF_CURRENT_L1_ENTITY,
    CONF_CURRENT_L2_ENTITY,
    CONF_CURRENT_L3_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FIXED_SUPPLIER_FEE_MONTHLY,
    CONF_FIXED_GRID_FEE_MONTHLY,
    CONF_GOOD_PRICE_THRESHOLD,
    CONF_PRICE_ENTITY,
    CONF_VOLTAGE_L1_ENTITY,
    CONF_VOLTAGE_L2_ENTITY,
    CONF_VOLTAGE_L3_ENTITY,
    CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
    CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
    DOMAIN,
)
from .coordinator import ElectricityProCoordinator
from .forecast_insights import ForecastDirectionInsight, ForecastWindowInsight
from .pricing import PricingMetadata
from .provider import ElectricityProData
from .statistics import remaining_cost_today
from .timing_score import TimingScoreResult


@dataclass(frozen=True, kw_only=True)
class ElectricityProSensorEntityDescription(
    SensorEntityDescription,
):
    """Describe an Electricity Pro sensor."""

    value_fn: Callable[[ElectricityProData], Decimal | datetime | None]
    available_fn: Callable[[ElectricityProData], bool]
    unit_fn: Callable[[ElectricityProData], str | None] | None = None
    required_config_key: str | None = None
    required_config_keys: tuple[str, ...] = ()


def cost_rate_unit(data: ElectricityProData) -> str | None:
    """Return the currency-per-hour unit for the cost-rate sensor."""
    price_unit = data.current_price_unit

    if price_unit is None:
        return None

    for suffix in ("/kWh", "/kwh"):
        if price_unit.endswith(suffix):
            currency = price_unit[: -len(suffix)]
            return f"{currency}/h"

    return None


def cost_unit(data: ElectricityProData) -> str | None:
    """Return the currency unit for calculated cost sensors."""
    price_unit = data.current_price_unit

    if price_unit is None:
        return None

    for suffix in ("/kWh", "/kwh"):
        if price_unit.endswith(suffix):
            return price_unit[: -len(suffix)]

    return None


def current_cost_rate(data: ElectricityProData) -> Decimal | None:
    """Return the current electricity cost per hour."""
    return calculate_current_cost_rate(
        data.current_power,
        effective_price(data),
    )


def effective_price(data: ElectricityProData) -> Decimal | None:
    """Return electricity price including configured variable adjustments."""
    return calculate_declared_effective_price(
        data.current_price,
        data.pricing_metadata,
        data.grid_fee_per_kwh,
        data.energy_tax_per_kwh,
    )


def _forecast_price_attributes(metadata: PricingMetadata) -> dict[str, Any]:
    """Return transparent component metadata for a forecast-derived price."""
    return {
        "price_components": sorted(component.value for component in metadata.scope.included),
        "vat_treatment": metadata.scope.vat.value,
        "price_completeness": metadata.completeness.value,
    }


def _decimal_string(value: Decimal | None) -> str | None:
    """Return a storage- and attribute-safe decimal representation."""
    return None if value is None else str(value)


def consumption_weighted_average_price(
    data: ElectricityProData,
) -> Decimal | None:
    """Return today's achieved average effective price per kWh."""
    return calculate_consumption_weighted_average_price(
        data.accumulated_cost_today,
        data.current_energy,
        data.current_energy_unit,
        data.grid_fee_per_kwh,
        data.energy_tax_per_kwh,
    )


def consumption_weighted_average_price_unit(
    data: ElectricityProData,
) -> str | None:
    """Return the currency-per-kWh unit for today's achieved average."""
    if (
        data.accumulated_cost_today_unit is None
        or data.current_energy_unit
        not in {UnitOfEnergy.WATT_HOUR, UnitOfEnergy.KILO_WATT_HOUR}
    ):
        return None

    return f"{data.accumulated_cost_today_unit}/kWh"


def projected_remaining_cost(data: ElectricityProData) -> Decimal | None:
    """Return the projected electricity cost until local midnight."""
    return remaining_cost_today(
        current_cost_rate(data),
        dt_util.now(),
    )


PHASES: tuple[str, ...] = ("l1", "l2", "l3")


def _phase_current_descriptions() -> (
    tuple[ElectricityProSensorEntityDescription, ...]
):
    """Return current sensor descriptions for all three phases."""
    conf_keys = (
        CONF_CURRENT_L1_ENTITY,
        CONF_CURRENT_L2_ENTITY,
        CONF_CURRENT_L3_ENTITY,
    )
    return tuple(
        ElectricityProSensorEntityDescription(
            key=f"current_{phase}",
            name=f"Current {phase.upper()}",
            icon="mdi:current-ac",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            suggested_display_precision=2,
            value_fn=lambda data, p=phase: getattr(data, f"current_{p}"),
            available_fn=lambda data, p=phase: getattr(data, f"current_{p}") is not None,
            required_config_key=conf_key,
        )
        for phase, conf_key in zip(PHASES, conf_keys)
    )


def _phase_voltage_descriptions() -> (
    tuple[ElectricityProSensorEntityDescription, ...]
):
    """Return voltage sensor descriptions for all three phases."""
    conf_keys = (
        CONF_VOLTAGE_L1_ENTITY,
        CONF_VOLTAGE_L2_ENTITY,
        CONF_VOLTAGE_L3_ENTITY,
    )
    return tuple(
        ElectricityProSensorEntityDescription(
            key=f"voltage_{phase}",
            name=f"Voltage {phase.upper()}",
            icon="mdi:sine-wave",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            suggested_display_precision=1,
            value_fn=lambda data, p=phase: getattr(data, f"voltage_{p}"),
            available_fn=lambda data, p=phase: getattr(data, f"voltage_{p}") is not None,
            required_config_key=conf_key,
        )
        for phase, conf_key in zip(PHASES, conf_keys)
    )


SENSOR_DESCRIPTIONS: tuple[
    ElectricityProSensorEntityDescription,
    ...,
] = (
    ElectricityProSensorEntityDescription(
        key="current_power",
        name="Current power",
        icon="mdi:flash",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda data: data.current_power,
        available_fn=lambda data: data.current_power is not None,
    ),
    ElectricityProSensorEntityDescription(
        key="current_price",
        name="Current price",
        icon="mdi:currency-usd",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.current_price,
        unit_fn=lambda data: data.current_price_unit,
        available_fn=lambda data: (
            data.current_price is not None and data.current_price_unit is not None
        ),
        required_config_key=CONF_PRICE_ENTITY,
    ),
    ElectricityProSensorEntityDescription(
        key="current_cost_rate",
        name="Current cost rate",
        icon="mdi:cash-clock",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=current_cost_rate,
        unit_fn=cost_rate_unit,
        available_fn=lambda data: (
            current_cost_rate(data) is not None and cost_rate_unit(data) is not None
        ),
        required_config_key=CONF_PRICE_ENTITY,
    ),
    ElectricityProSensorEntityDescription(
        key="effective_price",
        name="Effective price",
        icon="mdi:cash-plus",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=effective_price,
        unit_fn=lambda data: data.current_price_unit,
        available_fn=lambda data: (
            effective_price(data) is not None
            and data.current_price_unit is not None
        ),
        required_config_key=CONF_PRICE_ENTITY,
    ),
    ElectricityProSensorEntityDescription(
        key="consumption_weighted_average_price_today",
        name="Consumption-weighted average price today",
        icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=consumption_weighted_average_price,
        unit_fn=consumption_weighted_average_price_unit,
        available_fn=lambda data: (
            consumption_weighted_average_price(data) is not None
            and consumption_weighted_average_price_unit(data) is not None
        ),
        required_config_keys=(
            CONF_ACCUMULATED_COST_TODAY_ENTITY,
            CONF_ENERGY_ENTITY,
        ),
    ),
    ElectricityProSensorEntityDescription(
        key="remaining_cost_today",
        name="Remaining cost today",
        icon="mdi:progress-clock",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=projected_remaining_cost,
        unit_fn=cost_unit,
        available_fn=lambda data: (
            current_cost_rate(data) is not None and cost_unit(data) is not None
        ),
        required_config_key=CONF_PRICE_ENTITY,
    ),
    ElectricityProSensorEntityDescription(
        key="monthly_peak_hour_consumption",
        name="Monthly peak-hour consumption",
        icon="mdi:chart-bell-curve",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.monthly_peak_hour_consumption,
        unit_fn=lambda data: data.monthly_peak_hour_consumption_unit,
        available_fn=lambda data: (
            data.monthly_peak_hour_consumption is not None
            and data.monthly_peak_hour_consumption_unit is not None
        ),
        required_config_key=CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
    ),
    ElectricityProSensorEntityDescription(
        key="monthly_peak_hour_time",
        name="Monthly peak-hour time",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.monthly_peak_hour_time,
        available_fn=lambda data: data.monthly_peak_hour_time is not None,
        required_config_key=CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
    ),
    ElectricityProSensorEntityDescription(
        key="cost_today",
        name="Cost today",
        icon="mdi:cash",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.accumulated_cost_today,
        unit_fn=lambda data: data.accumulated_cost_today_unit,
        available_fn=lambda data: (
            data.accumulated_cost_today is not None
            and data.accumulated_cost_today_unit is not None
        ),
        required_config_key=CONF_ACCUMULATED_COST_TODAY_ENTITY,
    ),
    ElectricityProSensorEntityDescription(
        key="cost_this_month",
        name="Cost this month",
        icon="mdi:calendar-month-outline",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.cost_this_month,
        unit_fn=lambda data: data.cost_this_month_unit,
        available_fn=lambda data: (
            data.cost_this_month is not None
            and data.cost_this_month_unit is not None
        ),
        required_config_key=CONF_ACCUMULATED_COST_TODAY_ENTITY,
    ),
    ElectricityProSensorEntityDescription(
        key="fixed_supplier_fee_this_month",
        name="Fixed supplier fee this month",
        icon="mdi:receipt-text-outline",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.fixed_supplier_fee_this_month,
        unit_fn=lambda data: data.fixed_supplier_fee_this_month_unit,
        available_fn=lambda data: (
            data.fixed_supplier_fee_this_month is not None
            and data.fixed_supplier_fee_this_month_unit is not None
        ),
        required_config_key=CONF_FIXED_SUPPLIER_FEE_MONTHLY,
    ),
    ElectricityProSensorEntityDescription(
        key="fixed_grid_fee_this_month",
        name="Fixed grid fee this month",
        icon="mdi:transmission-tower",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.fixed_grid_fee_this_month,
        unit_fn=lambda data: data.fixed_grid_fee_this_month_unit,
        available_fn=lambda data: (
            data.fixed_grid_fee_this_month is not None
            and data.fixed_grid_fee_this_month_unit is not None
        ),
        required_config_key=CONF_FIXED_GRID_FEE_MONTHLY,
    ),
    ElectricityProSensorEntityDescription(
        key="total_supplier_cost_this_month",
        name="Total supplier cost this month",
        icon="mdi:cash-multiple",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.total_supplier_cost_this_month,
        unit_fn=lambda data: data.total_supplier_cost_this_month_unit,
        available_fn=lambda data: (
            data.total_supplier_cost_this_month is not None
            and data.total_supplier_cost_this_month_unit is not None
        ),
        required_config_keys=(
            CONF_ACCUMULATED_COST_TODAY_ENTITY,
            CONF_FIXED_SUPPLIER_FEE_MONTHLY,
        ),
    ),
    ElectricityProSensorEntityDescription(
        key="peak_power_today",
        name="Peak power today",
        icon="mdi:flash-outline",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda data: data.peak_power_today,
        available_fn=lambda data: data.peak_power_today is not None,
    ),
    ElectricityProSensorEntityDescription(
        key="peak_power_time_today",
        name="Peak power time today",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.peak_power_time_today,
        available_fn=lambda data: data.peak_power_time_today is not None,
    ),
    ElectricityProSensorEntityDescription(
        key="current_energy",
        name="Energy today",
        icon="mdi:lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.current_energy,
        unit_fn=lambda data: data.current_energy_unit,
        available_fn=lambda data: (
            data.current_energy is not None and data.current_energy_unit is not None
        ),
        required_config_key=CONF_ENERGY_ENTITY,
    ),
    ElectricityProSensorEntityDescription(
        key="energy_this_month",
        name="Energy this month",
        icon="mdi:calendar-month",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.energy_this_month,
        unit_fn=lambda data: data.energy_this_month_unit,
        available_fn=lambda data: (
            data.energy_this_month is not None
            and data.energy_this_month_unit is not None
        ),
        required_config_key=CONF_ENERGY_ENTITY,
    ),
    *_phase_current_descriptions(),
    *_phase_voltage_descriptions(),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectricityProConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Electricity Pro sensors."""
    entities = [
        ElectricityProSensor(
            coordinator=entry.runtime_data,
            entry=entry,
            description=description,
        )
        for description in SENSOR_DESCRIPTIONS
        if (
            description.required_config_key is None
            or description.required_config_key in entry.options
            or description.required_config_key in entry.data
        )
        and all(
            key in entry.options or key in entry.data
            for key in description.required_config_keys
        )
    ]

    forecast_configured = (
        CONF_FORECAST_NORDPOOL_CONFIG_ENTRY in entry.options
        or CONF_FORECAST_NORDPOOL_CONFIG_ENTRY in entry.data
    )
    if forecast_configured:
        entities.extend(
            (
                ElectricityProCheapestWindowSensor(
                    coordinator=entry.runtime_data,
                    entry=entry,
                    key="cheapest_1h_window_start",
                    name="Cheapest 1h window start",
                    duration_minutes=60,
                ),
                ElectricityProCheapestWindowSensor(
                    coordinator=entry.runtime_data,
                    entry=entry,
                    key="cheapest_2h_window_start",
                    name="Cheapest 2h window start",
                    duration_minutes=120,
                ),
                ElectricityProCheapestWindowSensor(
                    coordinator=entry.runtime_data,
                    entry=entry,
                    key="cheapest_3h_window_start",
                    name="Cheapest 3h window start",
                    duration_minutes=180,
                ),
                ElectricityProCheapestWindowAverageEffectivePriceSensor(
                    coordinator=entry.runtime_data,
                    entry=entry,
                    duration_minutes=60,
                ),
                ElectricityProCheapestWindowAverageEffectivePriceSensor(
                    coordinator=entry.runtime_data,
                    entry=entry,
                    duration_minutes=120,
                ),
                ElectricityProCheapestWindowAverageEffectivePriceSensor(
                    coordinator=entry.runtime_data,
                    entry=entry,
                    duration_minutes=180,
                ),
                ElectricityProPriceDirectionSensor(
                    coordinator=entry.runtime_data,
                    entry=entry,
                ),
            )
        )

        if (
            CONF_GOOD_PRICE_THRESHOLD in entry.options
            or CONF_GOOD_PRICE_THRESHOLD in entry.data
        ):
            entities.append(
                ElectricityProNextInexpensive1hWindowSensor(
                    coordinator=entry.runtime_data,
                    entry=entry,
                )
            )

    if CONF_PRICE_ENTITY in entry.options or CONF_PRICE_ENTITY in entry.data:
        entities.append(
            ElectricityProConsumptionTimingScoreSensor(
                coordinator=entry.runtime_data,
                entry=entry,
            )
        )

    async_add_entities(entities)


class ElectricityProSensor(
    CoordinatorEntity[ElectricityProCoordinator],
    SensorEntity,
):
    """Represent an Electricity Pro sensor."""

    _attr_has_entity_name = True
    entity_description: ElectricityProSensorEntityDescription

    def __init__(
        self,
        coordinator: ElectricityProCoordinator,
        entry: ElectricityProConfigEntry,
        description: ElectricityProSensorEntityDescription,
    ) -> None:
        """Initialize an Electricity Pro sensor."""
        super().__init__(coordinator)

        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Electricity Pro",
            manufacturer="Electricity Pro",
            model="Electricity monitor",
        )

    async def async_added_to_hass(self) -> None:
        """Register entity update listeners."""
        await super().async_added_to_hass()

        if self.entity_description.key != "remaining_cost_today":
            return

        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._handle_time_update,
                timedelta(minutes=1),
            )
        )

    @callback
    def _handle_time_update(self, now: datetime) -> None:
        """Refresh a time-dependent sensor value."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> Decimal | datetime | None:
        """Return the sensor's native value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the sensor's native unit."""
        if self.entity_description.unit_fn is not None:
            return self.entity_description.unit_fn(self.coordinator.data)

        return self.entity_description.native_unit_of_measurement

    @property
    def available(self) -> bool:
        """Return whether the sensor is available."""
        return super().available and self.entity_description.available_fn(
            self.coordinator.data
        )


class ElectricityProForecastInsightSensor(
    CoordinatorEntity[ElectricityProCoordinator],
    SensorEntity,
):
    """Base entity for coordinator-backed forecast insight sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ElectricityProCoordinator,
        entry: ElectricityProConfigEntry,
        *,
        key: str,
        name: str,
    ) -> None:
        """Initialize a forecast insight sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Electricity Pro",
            manufacturer="Electricity Pro",
            model="Electricity monitor",
        )


class ElectricityProConsumptionTimingScoreSensor(
    CoordinatorEntity[ElectricityProCoordinator],
    SensorEntity,
):
    """Represent the retrospective Consumption Timing Score."""

    _attr_has_entity_name = True
    _attr_name = "Consumption timing score yesterday"
    _attr_icon = "mdi:meter-electric-outline"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(
        self,
        coordinator: ElectricityProCoordinator,
        entry: ElectricityProConfigEntry,
    ) -> None:
        """Initialize the timing-score sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_consumption_timing_score_yesterday"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Electricity Pro",
            manufacturer="Electricity Pro",
            model="Electricity monitor",
        )

    @property
    def _result(self) -> tuple[date, TimingScoreResult] | None:
        """Return the last completed timing result."""
        return self.coordinator.timing_score_yesterday

    @property
    def native_value(self) -> Decimal | None:
        """Return the score for the last completed local day."""
        result = self._result
        return None if result is None else result[1].score

    @property
    def available(self) -> bool:
        """Return whether a quality-approved score is available."""
        return super().available and self.native_value is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return compact metadata explaining the result and availability."""
        stored = self._result
        if stored is None:
            return None
        period_start, result = stored
        return {
            "period_start": period_start.isoformat(),
            "coverage_percent": str(result.coverage_percent),
            "energy_kwh": str(result.energy_kwh),
            "consumption_weighted_price": _decimal_string(
                result.consumption_weighted_price
            ),
            "time_weighted_price": _decimal_string(result.time_weighted_price),
            "price_variation_percent": _decimal_string(
                result.price_variation_percent
            ),
            "rating": result.rating.value if result.rating is not None else None,
        }


class ElectricityProCheapestWindowSensor(ElectricityProForecastInsightSensor):
    """Represent a cheapest upcoming forecast window sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: ElectricityProCoordinator,
        entry: ElectricityProConfigEntry,
        *,
        key: str,
        name: str,
        duration_minutes: int,
    ) -> None:
        """Initialize a cheapest-window sensor."""
        super().__init__(coordinator, entry, key=key, name=name)
        self._duration_minutes = duration_minutes

    @property
    def native_value(self) -> datetime | None:
        """Return the cheapest window start time."""
        insight = self._insight
        return None if insight is None else insight.start

    @property
    def available(self) -> bool:
        """Return whether the cheapest window is available."""
        return super().available and self._insight is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return explanatory attributes for the selected window."""
        insight = self._insight
        if insight is None:
            return None

        return {
            "window_end": insight.end.isoformat(),
            "window_duration_minutes": insight.duration_minutes,
            "interval_count": insight.interval_count,
            "average_market_price": str(insight.average_market_price),
            "average_scheduling_price": str(insight.average_scheduling_price),
            "currency": insight.currency,
            "price_area": insight.area,
            "published_at": (
                insight.published_at.isoformat()
                if insight.published_at is not None
                else None
            ),
            **_forecast_price_attributes(insight.pricing_metadata),
        }

    @property
    def _insight(self) -> ForecastWindowInsight | None:
        """Return the cached window insight for this duration."""
        if self._duration_minutes == 60:
            return self.coordinator.cheapest_1h_window
        if self._duration_minutes == 120:
            return self.coordinator.cheapest_2h_window
        return self.coordinator.cheapest_3h_window


class ElectricityProCheapestWindowAverageEffectivePriceSensor(
    ElectricityProForecastInsightSensor
):
    """Represent the average scheduling price for a cheapest upcoming window."""

    _attr_suggested_display_precision = 5

    def __init__(
        self,
        coordinator: ElectricityProCoordinator,
        entry: ElectricityProConfigEntry,
        *,
        duration_minutes: int,
    ) -> None:
        """Initialize a cheapest-window average scheduling-price sensor."""
        hours = duration_minutes // 60
        super().__init__(
            coordinator,
            entry,
            key=f"cheapest_{hours}h_window_average_effective_price",
            name=f"Cheapest {hours}h window average scheduling price",
        )
        self.internal_integration_suggested_object_id = (
            f"{DOMAIN}_cheapest_{hours}h_window_average_effective_price"
        )
        self._duration_minutes = duration_minutes

    @property
    def _insight(self) -> ForecastWindowInsight | None:
        """Return the cached window insight for this duration."""
        if self._duration_minutes == 60:
            return self.coordinator.cheapest_1h_window
        if self._duration_minutes == 120:
            return self.coordinator.cheapest_2h_window
        return self.coordinator.cheapest_3h_window

    @property
    def native_value(self) -> Decimal | None:
        """Return the average scheduling price of the cheapest upcoming window."""
        insight = self._insight
        return None if insight is None else insight.average_scheduling_price

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the price unit for the cheapest upcoming window."""
        insight = self._insight
        return None if insight is None else f"{insight.currency}/kWh"

    @property
    def available(self) -> bool:
        """Return whether the window average scheduling price is available."""
        return super().available and self._insight is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return explanatory attributes for the cheapest upcoming window."""
        insight = self._insight
        if insight is None:
            return None

        return {
            "window_start": insight.start.isoformat(),
            "window_end": insight.end.isoformat(),
            "window_duration_minutes": insight.duration_minutes,
            "interval_count": insight.interval_count,
            "average_market_price": str(insight.average_market_price),
            "currency": insight.currency,
            "price_area": insight.area,
            "published_at": (
                insight.published_at.isoformat()
                if insight.published_at is not None
                else None
            ),
            **_forecast_price_attributes(insight.pricing_metadata),
        }


class ElectricityProNextInexpensive1hWindowSensor(ElectricityProForecastInsightSensor):
    """Represent the next inexpensive 1-hour forecast window sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: ElectricityProCoordinator,
        entry: ElectricityProConfigEntry,
    ) -> None:
        """Initialize a next inexpensive 1h window sensor."""
        super().__init__(
            coordinator,
            entry,
            key="next_inexpensive_1h_window_start",
            name="Next inexpensive 1h window start",
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the next inexpensive window start time."""
        insight = self.coordinator.next_inexpensive_1h_window
        return None if insight is None else insight.start

    @property
    def available(self) -> bool:
        """Return whether the next inexpensive window is available."""
        return super().available and self.coordinator.next_inexpensive_1h_window is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return explanatory attributes for the next inexpensive 1h window."""
        insight = self.coordinator.next_inexpensive_1h_window
        if insight is None:
            return None

        return {
            "window_end": insight.end.isoformat(),
            "window_duration_minutes": insight.duration_minutes,
            "interval_count": insight.interval_count,
            "average_market_price": str(insight.average_market_price),
            "average_scheduling_price": str(insight.average_scheduling_price),
            "threshold": str(insight.threshold),
            "currency": insight.currency,
            "price_area": insight.area,
            **_forecast_price_attributes(insight.pricing_metadata),
        }


class ElectricityProPriceDirectionSensor(ElectricityProForecastInsightSensor):
    """Represent a near-term forecast price direction sensor."""

    def __init__(
        self,
        coordinator: ElectricityProCoordinator,
        entry: ElectricityProConfigEntry,
    ) -> None:
        """Initialize a price-direction sensor."""
        super().__init__(
            coordinator,
            entry,
            key="price_direction",
            name="Price direction",
        )

    @property
    def native_value(self) -> str | None:
        """Return the direction state."""
        insight = self.coordinator.price_direction
        return None if insight is None else insight.direction

    @property
    def available(self) -> bool:
        """Return whether the price direction is available."""
        return super().available and self.coordinator.price_direction is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return explanatory attributes for price direction."""
        insight = self.coordinator.price_direction
        if insight is None:
            return None

        return {
            "current_interval_start": insight.current_start.isoformat(),
            "current_interval_end": insight.current_end.isoformat(),
            "next_interval_start": insight.next_start.isoformat(),
            "next_interval_end": insight.next_end.isoformat(),
            "current_scheduling_price": str(insight.current_scheduling_price),
            "next_scheduling_price": str(insight.next_scheduling_price),
            "delta": str(insight.delta),
            "currency": insight.currency,
            "price_area": insight.area,
            "published_at": (
                insight.published_at.isoformat()
                if insight.published_at is not None
                else None
            ),
            **_forecast_price_attributes(insight.pricing_metadata),
        }
