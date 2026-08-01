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
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_PEAK_POWER_TODAY_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
    DOMAIN,
)


def _entity_schema(
    *,
    power_default: str | None = None,
    price_default: str | None = None,
    energy_default: str | None = None,
    accumulated_cost_today_default: str | None = None,
    peak_power_today_default: str | None = None,
) -> vol.Schema:
    """Return the source entity selection schema."""

    if power_default is None:
        power_key = vol.Required(CONF_POWER_ENTITY)
    else:
        power_key = vol.Required(
            CONF_POWER_ENTITY,
            default=power_default,
        )

    if price_default is None:
        price_key = vol.Optional(CONF_PRICE_ENTITY)
    else:
        price_key = vol.Optional(
            CONF_PRICE_ENTITY,
            default=price_default,
        )

    if energy_default is None:
        energy_key = vol.Optional(CONF_ENERGY_ENTITY)
    else:
        energy_key = vol.Optional(
            CONF_ENERGY_ENTITY,
            default=energy_default,
        )

    if accumulated_cost_today_default is None:
        accumulated_cost_today_key = vol.Optional(CONF_ACCUMULATED_COST_TODAY_ENTITY)
    else:
        accumulated_cost_today_key = vol.Optional(
            CONF_ACCUMULATED_COST_TODAY_ENTITY,
            default=accumulated_cost_today_default,
        )

    if peak_power_today_default is None:
        peak_power_today_key = vol.Optional(CONF_PEAK_POWER_TODAY_ENTITY)
    else:
        peak_power_today_key = vol.Optional(
            CONF_PEAK_POWER_TODAY_ENTITY,
            default=peak_power_today_default,
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
            energy_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                )
            ),
            accumulated_cost_today_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="monetary",
                )
            ),
            peak_power_today_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="power",
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

        current_energy = self.config_entry.options.get(
            CONF_ENERGY_ENTITY,
            self.config_entry.data.get(CONF_ENERGY_ENTITY),
        )

        current_accumulated_cost_today = self.config_entry.options.get(
            CONF_ACCUMULATED_COST_TODAY_ENTITY,
            self.config_entry.data.get(
                CONF_ACCUMULATED_COST_TODAY_ENTITY,
            ),
        )
        current_peak_power_today = self.config_entry.options.get(
            CONF_PEAK_POWER_TODAY_ENTITY,
            self.config_entry.data.get(
                CONF_PEAK_POWER_TODAY_ENTITY,
            ),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=_entity_schema(
                power_default=current_power,
                price_default=current_price,
                energy_default=current_energy,
                accumulated_cost_today_default=current_accumulated_cost_today,
                peak_power_today_default=current_peak_power_today,
            ),
        )
