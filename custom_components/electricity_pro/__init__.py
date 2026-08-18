"""Electricity Pro integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError

from .const import CONF_PRICE_ENTITY, PLATFORMS
from .coordinator import ElectricityProCoordinator
from .pricing_config import resolve_pricing_metadata

type ElectricityProConfigEntry = ConfigEntry[ElectricityProCoordinator]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectricityProConfigEntry,
) -> bool:
    """Set up Electricity Pro from a config entry."""
    settings = {**entry.data, **entry.options}
    if settings.get(CONF_PRICE_ENTITY) and resolve_pricing_metadata(
        entry.data, entry.options
    ) is None:
        raise ConfigEntryError(
            "Configured price source requires explicit pricing metadata; "
            "open Electricity Pro options and confirm the price source"
        )

    coordinator = ElectricityProCoordinator(hass, entry)
    entry.runtime_data = coordinator

    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )

    await coordinator.async_start()
    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ElectricityProConfigEntry,
) -> bool:
    """Unload an Electricity Pro config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )


async def _async_update_listener(
    hass: HomeAssistant,
    entry: ElectricityProConfigEntry,
) -> None:
    """Reload the config entry after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
