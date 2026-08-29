"""Electricity Pro integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import ATTR_CONFIG_ENTRY_ID
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ConfigEntryError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_PRICE_ENTITY,
    DOMAIN,
    PLATFORMS,
    SERVICE_GET_MARKET_PRICE_FORECAST,
)
from .coordinator import ElectricityProCoordinator
from .pricing_config import resolve_pricing_metadata

type ElectricityProConfigEntry = ConfigEntry[ElectricityProCoordinator]

_GET_MARKET_PRICE_FORECAST_SCHEMA = vol.Schema(
    {vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string}
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Electricity Pro integration-level actions."""

    async def async_get_market_price_forecast(
        call: ServiceCall,
    ) -> ServiceResponse:
        """Return a normalized forecast for one explicit config entry."""
        entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError("Electricity Pro config entry not found")
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError("Electricity Pro config entry is not loaded")

        try:
            return entry.runtime_data.market_price_forecast_response
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_MARKET_PRICE_FORECAST,
        async_get_market_price_forecast,
        schema=_GET_MARKET_PRICE_FORECAST_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    return True


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
