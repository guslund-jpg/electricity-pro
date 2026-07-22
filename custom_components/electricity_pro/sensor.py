"""Sensor platform for Electricity Pro."""

from __future__ import annotations

from decimal import Decimal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ElectricityProConfigEntry
from .const import CONF_PRICE_ENTITY, DOMAIN
from .coordinator import ElectricityProCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectricityProConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Electricity Pro sensors."""
    entities: list[SensorEntity] = [
        ElectricityProCurrentPowerSensor(
            coordinator=entry.runtime_data,
            entry=entry,
        )
    ]

    if CONF_PRICE_ENTITY in entry.data:
        entities.append(
            ElectricityProCurrentPriceSensor(
                coordinator=entry.runtime_data,
                entry=entry,
            )
        )

    async_add_entities(entities)


class ElectricityProSensorEntity(
    CoordinatorEntity[ElectricityProCoordinator],
    SensorEntity,
):
    """Base class for Electricity Pro sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ElectricityProCoordinator,
        entry: ElectricityProConfigEntry,
    ) -> None:
        """Initialize a common Electricity Pro sensor."""
        super().__init__(coordinator)

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Electricity Pro",
            manufacturer="Electricity Pro",
            model="Electricity monitor",
        )


class ElectricityProCurrentPowerSensor(
    ElectricityProSensorEntity,
):
    """Represent canonical current electricity power."""

    _attr_name = "Current power"
    _attr_icon = "mdi:flash"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(
        self,
        coordinator: ElectricityProCoordinator,
        entry: ElectricityProConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_power"

    @property
    def native_value(self) -> Decimal | None:
        """Return current power in watts."""
        return self.coordinator.data.current_power

    @property
    def available(self) -> bool:
        """Return whether current power is available."""
        return (
            super().available
            and self.coordinator.data.current_power is not None
        )


class ElectricityProCurrentPriceSensor(
    ElectricityProSensorEntity,
):
    """Represent the canonical current electricity price."""

    _attr_name = "Current price"
    _attr_icon = "mdi:currency-usd"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ElectricityProCoordinator,
        entry: ElectricityProConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_price"

    @property
    def native_value(self) -> Decimal | None:
        """Return the current electricity price."""
        return self.coordinator.data.current_price

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the price source's native unit."""
        return self.coordinator.data.current_price_unit

    @property
    def available(self) -> bool:
        """Return whether the current price is available."""
        return (
            super().available
            and self.coordinator.data.current_price is not None
            and self.coordinator.data.current_price_unit is not None
        )
