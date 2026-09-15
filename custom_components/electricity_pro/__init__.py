"""Electricity Pro integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
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
    ATTR_CONFIG_ENTRY_ID,
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
    async def async_reset_monthly_energy(call: ServiceCall) -> None:
        """Reset monthly energy only for an explicitly selected loaded entry."""
        entry = hass.config_entries.async_get_entry(call.data[ATTR_CONFIG_ENTRY_ID])
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError("Electricity Pro config entry not found")
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError("Electricity Pro config entry is not loaded")
        try:
            await entry.runtime_data.async_reset_monthly_energy()
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    hass.services.async_register(
        DOMAIN,
        "reset_monthly_energy",
        async_reset_monthly_energy,
        schema=vol.Schema({
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required("confirm_reset"): vol.All(bool, vol.In([True])),
        }),
    )
    async def async_confirm_meter_reset(call: ServiceCall) -> None:
        """Accept a genuine meter replacement only with explicit confirmation."""
        entry = hass.config_entries.async_get_entry(call.data[ATTR_CONFIG_ENTRY_ID])
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError("Electricity Pro config entry not found")
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError("Electricity Pro config entry is not loaded")
        try:
            await entry.runtime_data.async_confirm_meter_reset()
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    hass.services.async_register(
        DOMAIN, "confirm_meter_reset", async_confirm_meter_reset,
        schema=vol.Schema({
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required("confirm_reset"): vol.All(bool, vol.In([True])),
        }),
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
