"""Sensor platform for Electricity Pro."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
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
    """Represent canonical current electricity power."""

    _attr_has_entity_name = True
    _attr_name = "Current power"
    _attr_icon = "mdi:flash"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        source_entity_id: str,
    ) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._source_entity_id = source_entity_id

        self._attr_unique_id = f"{entry.entry_id}_current_power"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Electricity Pro",
            manufacturer="Electricity Pro",
            model="Electricity monitor",
        )

        self._attr_available = False
        self._attr_native_value = None

    async def async_added_to_hass(self) -> None:
        """Start tracking the configured source sensor."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_track_state_change_event(
                self._hass,
                [self._source_entity_id],
                self._async_source_changed,
            )
        )

        self._update_from_state(
            self._hass.states.get(self._source_entity_id)
        )

    @callback
    def _async_source_changed(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle a source sensor state change."""
        self._update_from_state(event.data["new_state"])
        self.async_write_ha_state()

    @callback
    def _update_from_state(
        self,
        source_state: State | None,
    ) -> None:
        """Update the canonical sensor from its source."""
        if (
            source_state is None
            or source_state.state
            in {
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
                "",
            }
        ):
            self._set_unavailable()
            return

        try:
            source_value = Decimal(source_state.state)
        except (InvalidOperation, ValueError):
            self._set_unavailable()
            return

        source_unit = source_state.attributes.get(
            "unit_of_measurement"
        )

        if source_unit == UnitOfPower.WATT:
            watts = source_value
        elif source_unit == UnitOfPower.KILO_WATT:
            watts = source_value * Decimal("1000")
        else:
            self._set_unavailable()
            return

        if not watts.is_finite() or watts < 0:
            self._set_unavailable()
            return

        self._attr_native_value = watts
        self._attr_available = True

    @callback
    def _set_unavailable(self) -> None:
        """Mark the canonical sensor unavailable."""
        self._attr_native_value = None
        self._attr_available = False
