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
    CONF_CURRENT_L1_ENTITY,
    CONF_CURRENT_L2_ENTITY,
    CONF_CURRENT_L3_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FORECAST_PRICE_AREA,
    CONF_GRID_FEE_PER_KWH,
    CONF_GOOD_PRICE_THRESHOLD,
    CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
    CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
    CONF_PEAK_POWER_TODAY_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
    CONF_TAX_PER_KWH,
    CONF_VOLTAGE_L1_ENTITY,
    CONF_VOLTAGE_L2_ENTITY,
    CONF_VOLTAGE_L3_ENTITY,
    DOMAIN,
)


def _entity_schema(
    *,
    power_default: str | None = None,
    price_default: str | None = None,
    energy_default: str | None = None,
    accumulated_cost_today_default: str | None = None,
    peak_power_today_default: str | None = None,
    current_l1_default: str | None = None,
    current_l2_default: str | None = None,
    current_l3_default: str | None = None,
    voltage_l1_default: str | None = None,
    voltage_l2_default: str | None = None,
    voltage_l3_default: str | None = None,
    monthly_peak_hour_consumption_default: str | None = None,
    monthly_peak_hour_time_default: str | None = None,
    grid_fee_per_kwh_default: float | None = None,
    tax_per_kwh_default: float | None = None,
    good_price_threshold_default: float | None = None,
    forecast_nordpool_config_entry_default: str | None = None,
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
    if current_l1_default is None:
        current_l1_key = vol.Optional(CONF_CURRENT_L1_ENTITY)
    else:
        current_l1_key = vol.Optional(
            CONF_CURRENT_L1_ENTITY,
            default=current_l1_default,
        )

    if current_l2_default is None:
        current_l2_key = vol.Optional(CONF_CURRENT_L2_ENTITY)
    else:
        current_l2_key = vol.Optional(
            CONF_CURRENT_L2_ENTITY,
            default=current_l2_default,
        )

    if current_l3_default is None:
        current_l3_key = vol.Optional(CONF_CURRENT_L3_ENTITY)
    else:
        current_l3_key = vol.Optional(
            CONF_CURRENT_L3_ENTITY,
            default=current_l3_default,
        )
    if voltage_l1_default is None:
        voltage_l1_key = vol.Optional(CONF_VOLTAGE_L1_ENTITY)
    else:
        voltage_l1_key = vol.Optional(
            CONF_VOLTAGE_L1_ENTITY,
            default=voltage_l1_default,
        )
    if voltage_l2_default is None:
        voltage_l2_key = vol.Optional(CONF_VOLTAGE_L2_ENTITY)
    else:
        voltage_l2_key = vol.Optional(
            CONF_VOLTAGE_L2_ENTITY,
            default=voltage_l2_default,
        )
    if voltage_l3_default is None:
        voltage_l3_key = vol.Optional(CONF_VOLTAGE_L3_ENTITY)
    else:
        voltage_l3_key = vol.Optional(
            CONF_VOLTAGE_L3_ENTITY,
            default=voltage_l3_default,
        )
    if monthly_peak_hour_consumption_default is None:
        monthly_peak_hour_consumption_key = vol.Optional(
            CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY
        )
    else:
        monthly_peak_hour_consumption_key = vol.Optional(
            CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
            default=monthly_peak_hour_consumption_default,
        )
    if monthly_peak_hour_time_default is None:
        monthly_peak_hour_time_key = vol.Optional(
            CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY
        )
    else:
        monthly_peak_hour_time_key = vol.Optional(
            CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
            default=monthly_peak_hour_time_default,
        )
    if grid_fee_per_kwh_default is None:
        grid_fee_key = vol.Optional(CONF_GRID_FEE_PER_KWH)
    else:
        grid_fee_key = vol.Optional(
            CONF_GRID_FEE_PER_KWH,
            default=grid_fee_per_kwh_default,
        )
    if tax_per_kwh_default is None:
        tax_key = vol.Optional(CONF_TAX_PER_KWH)
    else:
        tax_key = vol.Optional(
            CONF_TAX_PER_KWH,
            default=tax_per_kwh_default,
        )
    if good_price_threshold_default is None:
        good_price_threshold_key = vol.Optional(CONF_GOOD_PRICE_THRESHOLD)
    else:
        good_price_threshold_key = vol.Optional(
            CONF_GOOD_PRICE_THRESHOLD,
            default=good_price_threshold_default,
        )
    if forecast_nordpool_config_entry_default is None:
        forecast_nordpool_config_entry_key = vol.Optional(
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY
        )
    else:
        forecast_nordpool_config_entry_key = vol.Optional(
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
            default=forecast_nordpool_config_entry_default,
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
            current_l1_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="current",
                )
            ),
            current_l2_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="current",
                )
            ),
            current_l3_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="current",
                )
            ),
            voltage_l1_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="voltage",
                )
            ),
            voltage_l2_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="voltage",
                )
            ),
            voltage_l3_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="voltage",
                )
            ),
            monthly_peak_hour_consumption_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="energy",
                )
            ),
            monthly_peak_hour_time_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="timestamp",
                )
            ),
            grid_fee_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.001,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            tax_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.001,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            good_price_threshold_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.001,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            forecast_nordpool_config_entry_key: selector.ConfigEntrySelector(
                selector.ConfigEntrySelectorConfig(
                    integration="nordpool",
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

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._pending_user_input: dict[str, Any] | None = None
        self._forecast_areas: list[str] = []

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
            nordpool_entry_id = user_input.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY)
            if isinstance(nordpool_entry_id, str):
                nordpool_entry = self.hass.config_entries.async_get_entry(
                    nordpool_entry_id
                )
                if nordpool_entry is not None:
                    areas = nordpool_entry.data.get("areas", [])
                    if isinstance(areas, list) and len(areas) > 1:
                        self._pending_user_input = user_input
                        self._forecast_areas = [str(area) for area in areas]
                        return self.async_show_form(
                            step_id="forecast_area",
                            data_schema=_forecast_area_schema(self._forecast_areas),
                        )

            user_input.pop(CONF_FORECAST_PRICE_AREA, None)
            return self.async_create_entry(
                title="Electricity Pro",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_entity_schema(),
        )

    async def async_step_forecast_area(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Select one area when the Nord Pool entry contains several."""
        if user_input is not None and self._pending_user_input is not None:
            data = {**self._pending_user_input, **user_input}
            return self.async_create_entry(title="Electricity Pro", data=data)

        return self.async_show_form(
            step_id="forecast_area",
            data_schema=_forecast_area_schema(self._forecast_areas),
        )


class ElectricityProOptionsFlow(OptionsFlow):
    """Handle Electricity Pro options."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._pending_user_input: dict[str, Any] | None = None
        self._forecast_areas: list[str] = []

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage source entity options."""
        if user_input is not None:
            nordpool_entry_id = user_input.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY)
            if isinstance(nordpool_entry_id, str):
                nordpool_entry = self.hass.config_entries.async_get_entry(
                    nordpool_entry_id
                )
                if nordpool_entry is not None:
                    areas = nordpool_entry.data.get("areas", [])
                    if isinstance(areas, list) and len(areas) > 1:
                        selected_area = user_input.get(CONF_FORECAST_PRICE_AREA)
                        current_nordpool_entry_id = self.config_entry.options.get(
                            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
                            self.config_entry.data.get(
                                CONF_FORECAST_NORDPOOL_CONFIG_ENTRY
                            ),
                        )
                        if (
                            selected_area is None
                            and nordpool_entry_id == current_nordpool_entry_id
                        ):
                            selected_area = self.config_entry.options.get(
                                CONF_FORECAST_PRICE_AREA,
                                self.config_entry.data.get(CONF_FORECAST_PRICE_AREA),
                            )
                            if selected_area in areas:
                                user_input[CONF_FORECAST_PRICE_AREA] = selected_area
                        if selected_area not in areas:
                            self._pending_user_input = user_input
                            self._forecast_areas = [str(area) for area in areas]
                            return self.async_show_form(
                                step_id="forecast_area",
                                data_schema=_forecast_area_schema(
                                    self._forecast_areas
                                ),
                            )
            user_input.pop(CONF_FORECAST_PRICE_AREA, None)
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
        current_l1 = self.config_entry.options.get(
            CONF_CURRENT_L1_ENTITY,
            self.config_entry.data.get(CONF_CURRENT_L1_ENTITY),
        )

        current_l2 = self.config_entry.options.get(
            CONF_CURRENT_L2_ENTITY,
            self.config_entry.data.get(CONF_CURRENT_L2_ENTITY),
        )

        current_l3 = self.config_entry.options.get(
            CONF_CURRENT_L3_ENTITY,
            self.config_entry.data.get(CONF_CURRENT_L3_ENTITY),
        )
        current_voltage_l1 = self.config_entry.options.get(
            CONF_VOLTAGE_L1_ENTITY,
            self.config_entry.data.get(CONF_VOLTAGE_L1_ENTITY),
        )

        current_voltage_l2 = self.config_entry.options.get(
            CONF_VOLTAGE_L2_ENTITY,
            self.config_entry.data.get(CONF_VOLTAGE_L2_ENTITY),
        )

        current_voltage_l3 = self.config_entry.options.get(
            CONF_VOLTAGE_L3_ENTITY,
            self.config_entry.data.get(CONF_VOLTAGE_L3_ENTITY),
        )
        current_monthly_peak_hour_consumption = self.config_entry.options.get(
            CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
            self.config_entry.data.get(CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY),
        )
        current_monthly_peak_hour_time = self.config_entry.options.get(
            CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
            self.config_entry.data.get(CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY),
        )
        current_grid_fee = self.config_entry.options.get(
            CONF_GRID_FEE_PER_KWH,
            self.config_entry.data.get(CONF_GRID_FEE_PER_KWH),
        )
        current_tax = self.config_entry.options.get(
            CONF_TAX_PER_KWH,
            self.config_entry.data.get(CONF_TAX_PER_KWH),
        )
        current_good_price_threshold = self.config_entry.options.get(
            CONF_GOOD_PRICE_THRESHOLD,
            self.config_entry.data.get(CONF_GOOD_PRICE_THRESHOLD),
        )
        current_forecast_nordpool_config_entry = self.config_entry.options.get(
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
            self.config_entry.data.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=_entity_schema(
                power_default=current_power,
                price_default=current_price,
                energy_default=current_energy,
                accumulated_cost_today_default=current_accumulated_cost_today,
                peak_power_today_default=current_peak_power_today,
                current_l1_default=current_l1,
                current_l2_default=current_l2,
                current_l3_default=current_l3,
                voltage_l1_default=current_voltage_l1,
                voltage_l2_default=current_voltage_l2,
                voltage_l3_default=current_voltage_l3,
                monthly_peak_hour_consumption_default=current_monthly_peak_hour_consumption,
                monthly_peak_hour_time_default=current_monthly_peak_hour_time,
                grid_fee_per_kwh_default=current_grid_fee,
                tax_per_kwh_default=current_tax,
                good_price_threshold_default=current_good_price_threshold,
                forecast_nordpool_config_entry_default=current_forecast_nordpool_config_entry,
            ),
        )

    async def async_step_forecast_area(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Select one area when the Nord Pool entry contains several."""
        if user_input is not None and self._pending_user_input is not None:
            data = {**self._pending_user_input, **user_input}
            return self.async_create_entry(title="", data=data)

        return self.async_show_form(
            step_id="forecast_area",
            data_schema=_forecast_area_schema(self._forecast_areas),
        )


def _forecast_area_schema(areas: list[str]) -> vol.Schema:
    """Return the area selector used only for multi-area Nord Pool entries."""
    return vol.Schema(
        {
            vol.Required(CONF_FORECAST_PRICE_AREA): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=areas,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )
