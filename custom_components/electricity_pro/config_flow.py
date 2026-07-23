"""Config flow for Electricity Pro."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
    DOMAIN,
)


def _entity_schema(
    *,
    power_default: str | None = None,
    price_default: str | None = None,
) -> vol.Schema:
    """Return the source entity selection schema."""
    power_key: vol.Marker

    if power_default is None:
        power_key = vol.Required(CONF_POWER_ENTITY)
    else:
        power_key = vol.Required(
            CONF_POWER_ENTITY,
            default=power_default,
        )

    price_key: vol.Marker

    if price_default is None:
        price_key = vol.Optional(CONF_PRICE_ENTITY)
    else:
        price_key = vol.Optional(
            CONF_PRICE_ENTITY,
            default=price_default,
        )

    return vol.Schema(
        {
            power_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="power",
                )
            ),
            price_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                )
            ),
        }
    )

class ElectricityProConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle the Electricity Pro config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> ElectricityProOptionsFlow:
        """Create the options flow."""
        return ElectricityProOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle setup initiated by the user."""
        if user_input is not None:
            return self.async_create_entry(
                title="Electricity Pro",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_entity_schema(),
        )


class ElectricityProOptionsFlow(OptionsFlow):
    """Handle Electricity Pro options."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage source entity options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=user_input,
            )

        current_power = self.config_entry.options.get(
            CONF_POWER_ENTITY,
            self.config_entry.data[CONF_POWER_ENTITY],
        )
        current_price = self.config_entry.options.get(
            CONF_PRICE_ENTITY,
            self.config_entry.data.get(CONF_PRICE_ENTITY),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=_entity_schema(
                power_default=current_power,
                price_default=current_price,
            ),
        )
