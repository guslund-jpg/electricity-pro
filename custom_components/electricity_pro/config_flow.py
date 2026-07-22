"""Config flow for Electricity Pro."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import selector

from .const import CONF_POWER_ENTITY, DOMAIN


class ElectricityProConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle the Electricity Pro config flow."""

    VERSION = 1

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

        data_schema = vol.Schema(
            {
                vol.Required(CONF_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="power",
                    )
                )
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )
