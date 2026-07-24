"""Sensor platform for Electricity Pro."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ElectricityProConfigEntry
from .calculations import calculate_current_cost_rate
from .const import (
    CONF_ENERGY_ENTITY,
    CONF_PRICE_ENTITY,
    DOMAIN,
)
from .coordinator import ElectricityProCoordinator
from .provider import ElectricityProData


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
        value_fn=lambda data: calculate_current_cost_rate(
            data.current_power,
            data.current_price,
        ),
        unit_fn=cost_rate_unit,
        available_fn=lambda data: (
            data.current_power is not None
            and data.current_price is not None
            and cost_rate_unit(data) is not None
        ),
        required_config_key=CONF_PRICE_ENTITY,
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
