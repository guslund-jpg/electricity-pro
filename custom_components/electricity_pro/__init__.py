"""Electricity Pro integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

entry.runtime_data = coordinator
await coordinator.async_start()

from .const import PLATFORMS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Electricity Pro from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload an Electricity Pro config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
