"""Binary sensor platform for Electricity Pro insights."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ElectricityProConfigEntry
from .calculations import calculate_declared_effective_price
from .const import CONF_GOOD_PRICE_THRESHOLD, DOMAIN
from .coordinator import ElectricityProCoordinator
from .provider import ElectricityProData


def good_time_to_use_electricity(data: ElectricityProData) -> bool | None:
    """Return whether Effective Price is within the configured threshold."""
    effective_price = calculate_declared_effective_price(
        data.current_price,
        data.pricing_metadata,
        data.grid_fee_per_kwh,
    )
    if effective_price is None or data.good_price_threshold is None:
        return None
    return effective_price <= data.good_price_threshold


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectricityProConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Electricity Pro insight binary sensors."""
    if (
        CONF_GOOD_PRICE_THRESHOLD not in entry.options
        and CONF_GOOD_PRICE_THRESHOLD not in entry.data
    ):
        return

    async_add_entities([GoodTimeToUseElectricityBinarySensor(entry)])


class GoodTimeToUseElectricityBinarySensor(
    CoordinatorEntity[ElectricityProCoordinator],
    BinarySensorEntity,
):
    """Represent the Good time to use electricity insight."""

    _attr_has_entity_name = True
    _attr_name = "Good time to use electricity"
    _attr_icon = "mdi:check-circle-outline"

    def __init__(self, entry: ElectricityProConfigEntry) -> None:
        """Initialize the insight."""
        super().__init__(entry.runtime_data)
        self._attr_unique_id = f"{entry.entry_id}_good_time_to_use_electricity"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Electricity Pro",
            manufacturer="Electricity Pro",
            model="Electricity monitor",
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether now is a good time to use electricity."""
        return good_time_to_use_electricity(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return whether the insight has sufficient input data."""
        return (
            super().available
            and good_time_to_use_electricity(self.coordinator.data) is not None
        )
