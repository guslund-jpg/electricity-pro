"""Sensor platform for Electricity Pro."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import ElectricityProConfigEntry
from .calculations import calculate_current_cost_rate
from .const import (
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_PEAK_POWER_TODAY_ENTITY,
    CONF_PRICE_ENTITY,
    DOMAIN,
)
from .coordinator import ElectricityProCoordinator
from .provider import ElectricityProData
from .statistics import remaining_cost_today


@dataclass(frozen=True, kw_only=True)
class ElectricityProSensorEntityDescription(
    SensorEntityDescription,
):
    """Describe an Electricity Pro sensor."""

    value_fn: Callable[[ElectricityProData], Decimal | None]
    available_fn: Callable[[ElectricityProData], bool]
    unit_fn: Callable[[ElectricityProData], str | None] | None = None
    required_config_key: str | None = None


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
        data.current_price,
    )


def projected_remaining_cost(data: ElectricityProData) -> Decimal | None:
    """Return the projected electricity cost until local midnight."""
    return remaining_cost_today(
        current_cost_rate(data),
        dt_util.now(),
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
        value_fn=lambda data: data.current_power,
        available_fn=lambda data: data.current_power is not None,
    ),
    ElectricityProSensorEntityDescription(
        key="current_price",
        name="Current price",
        icon="mdi:currency-usd",
        state_class=SensorStateClass.MEASUREMENT,
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
        suggested_display_precision=3,
        value_fn=current_cost_rate,
        unit_fn=cost_rate_unit,
        available_fn=lambda data: (
            current_cost_rate(data) is not None and cost_rate_unit(data) is not None
        ),
        required_config_key=CONF_PRICE_ENTITY,
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
        key="peak_power_today",
        name="Peak power today",
        icon="mdi:flash-outline",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda data: data.peak_power_today,
        available_fn=lambda data: data.peak_power_today is not None,
        required_config_key=CONF_PEAK_POWER_TODAY_ENTITY,
    ),
    ElectricityProSensorEntityDescription(
        key="current_energy",
        name="Energy",
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
    ]

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
    def native_value(self) -> Decimal | None:
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
