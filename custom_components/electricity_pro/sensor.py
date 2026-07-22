"""Sensor platform for Electricity Pro."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_POWER_ENTITY, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Electricity Pro sensors."""

    async_add_entities(
        [
            ElectricityProCurrentPowerSensor(
                hass=hass,
                entry=entry,
                source_entity_id=entry.data[CONF_POWER_ENTITY],
            )
        ]
    )


class ElectricityProCurrentPowerSensor(SensorEntity):
    """Canonical current power sensor."""

    _attr_has_entity_name = True
    _attr_name = "Current power"

    _attr_icon = "mdi:flash"

    _attr_should_poll = False

    _attr_entity_registry_enabled_default = True

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        source_entity_id: str,
    ) -> None:
        """Initialize the sensor."""

        self.hass = hass
        self._entry = entry
        self._source_entity_id = source_entity_id

        self._attr_unique_id = f"{entry.entry_id}_current_power"

        self._attr_available = False
        self._attr_native_value = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""

        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Electricity Pro",
            manufacturer="Electricity Pro",
            model="Canonical Electricity Monitor",
        )

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        await super().async_added_to_hass()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_entity_id],
                self._async_source_state_changed,
            )
        )

        self._update_from_source()

    @callback
    def _async_source_state_changed(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle source updates."""

        self._update_from_source()
        self.async_write_ha_state()

    @callback
    def _update_from_source(self) -> None:
        """Update state from configured source."""

        source_state = self.hass.states.get(self._source_entity_id)

        if (
            source_state is None
            or source_state.state in ("unknown", "unavailable", "")
        ):
            self._attr_available = False
            self._attr_native_value = None
            return

        try:
            value = Decimal(source_state.state)
        except (InvalidOperation, ValueError):
            self._attr_available = False
            self._attr_native_value = None
            return

        watts = self._convert_to_watts(
            value,
            source_state.attributes.get("unit_of_measurement"),
        )

        if watts is None or watts < 0:
            self._attr_available = False
            self._attr_native_value = None
            return

        self._attr_available = True
        self._attr_native_value = watts

    @staticmethod
    def _convert_to_watts(
        value: Decimal,
        unit: Any,
    ) -> Decimal | None:
        """Convert supported units to watts."""

        if unit == UnitOfPower.WATT:
            return value

        if unit == UnitOfPower.KILO_WATT:
            return value * Decimal("1000")

        return None
