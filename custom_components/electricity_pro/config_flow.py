"""Config flow for Electricity Pro."""

from __future__ import annotations

from datetime import time
from decimal import Decimal, InvalidOperation
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
    CONF_CURRENT_L1_ENTITY,
    CONF_CURRENT_L2_ENTITY,
    CONF_CURRENT_L3_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FIXED_SUPPLIER_FEE_MONTHLY,
    CONF_FIXED_GRID_FEE_MONTHLY,
    CONF_FORECAST_PRICE_AREA,
    CONF_GRID_FEE_PER_KWH,
    CONF_GRID_FEE_HIGH_END,
    CONF_GRID_FEE_WORKDAY_ENTITY,
    CONF_GRID_FEE_HIGH_PER_KWH,
    CONF_GRID_FEE_HIGH_SEASON_END,
    CONF_GRID_FEE_HIGH_SEASON_START,
    CONF_GRID_FEE_HIGH_START,
    CONF_GOOD_PRICE_THRESHOLD,
    CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
    CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
    CONF_PEAK_POWER_TODAY_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_ENTITY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICING_STRATEGY,
    CONF_SETUP_METHOD,
    CONF_SOURCE_PROFILE,
    CONF_TIBBER_DEVICE,
    CONF_VOLTAGE_L1_ENTITY,
    CONF_VOLTAGE_L2_ENTITY,
    CONF_VOLTAGE_L3_ENTITY,
    DOMAIN,
)
from .pricing import (
    PriceComponent,
    PriceCompleteness,
    PricingStrategy,
    VatTreatment,
)
from .grid_tariff import HighLowGridTariff
from .source_adapters import DiscoveredSource, discover_tibber_sources

_SETUP_TIBBER = "tibber"
_SETUP_CUSTOM = "custom"

_PRICING_STRATEGY_OPTIONS = [
    {
        "value": PricingStrategy.SUPPLIER_CONTRACTED_PRICE.value,
        "label": "Supplier-contracted price",
    },
    {
        "value": PricingStrategy.MARKET_PRICE_PLUS_TARIFF.value,
        "label": "Market price plus configured tariffs",
    },
    {
        "value": PricingStrategy.EXTERNAL_COMPLETE_PRICE.value,
        "label": "Externally calculated complete price",
    },
]

_PRICE_COMPONENT_OPTIONS = [
    {"value": PriceComponent.MARKET_ENERGY.value, "label": "Market energy"},
    {"value": PriceComponent.SUPPLIER_MARKUP.value, "label": "Supplier markup"},
    {"value": PriceComponent.ENERGY_TAX.value, "label": "Energy tax"},
    {
        "value": PriceComponent.VARIABLE_GRID_FEE.value,
        "label": "Variable grid fee",
    },
]

_VAT_OPTIONS = [
    {"value": VatTreatment.INCLUDED.value, "label": "VAT included"},
    {"value": VatTreatment.EXCLUDED.value, "label": "VAT excluded"},
    {"value": VatTreatment.UNKNOWN.value, "label": "Unknown"},
]


def _time_of_use_tariff_fields(
    *,
    high_fee_default: float | None = None,
    high_start_default: str = "06:00",
    high_end_default: str = "22:00",
    season_start_default: str = "11-01",
    season_end_default: str = "03-31",
    workday_entity_default: str | None = None,
) -> dict[vol.Marker, Any]:
    """Return optional high/low tariff schedule fields."""
    high_fee_key = (
        vol.Optional(CONF_GRID_FEE_HIGH_PER_KWH)
        if high_fee_default is None
        else vol.Optional(CONF_GRID_FEE_HIGH_PER_KWH, default=high_fee_default)
    )
    workday_entity_key = (
        vol.Optional(CONF_GRID_FEE_WORKDAY_ENTITY)
        if workday_entity_default is None
        else vol.Optional(
            CONF_GRID_FEE_WORKDAY_ENTITY,
            default=workday_entity_default,
        )
    )
    return {
        high_fee_key: selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                step=0.001,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(
            CONF_GRID_FEE_HIGH_START, default=high_start_default
        ): selector.TextSelector(),
        vol.Optional(
            CONF_GRID_FEE_HIGH_END, default=high_end_default
        ): selector.TextSelector(),
        vol.Optional(
            CONF_GRID_FEE_HIGH_SEASON_START, default=season_start_default
        ): selector.TextSelector(),
        vol.Optional(
            CONF_GRID_FEE_HIGH_SEASON_END, default=season_end_default
        ): selector.TextSelector(),
        workday_entity_key: selector.EntitySelector(
            selector.EntitySelectorConfig(
                filter={"domain": "binary_sensor", "integration": "workday"}
            )
        ),
    }


def _setup_method_schema() -> vol.Schema:
    """Return the first guided setup choice."""
    return vol.Schema(
        {
            vol.Required(CONF_SETUP_METHOD): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": _SETUP_TIBBER, "label": "Tibber fast track"},
                        {"value": _SETUP_CUSTOM, "label": "Custom or mixed sources"},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
        }
    )


def _tibber_settings_schema(
    *,
    grid_fee_default: float | None = None,
    good_price_threshold_default: float | None = None,
    high_fee_default: float | None = None,
    high_start_default: str = "06:00",
    high_end_default: str = "22:00",
    season_start_default: str = "11-01",
    season_end_default: str = "03-31",
    workday_entity_default: str | None = None,
    fixed_supplier_fee_default: float | None = None,
    fixed_grid_fee_default: float | None = None,
) -> vol.Schema:
    """Return only the settings Tibber cannot determine."""
    grid_fee_key = (
        vol.Optional(CONF_GRID_FEE_PER_KWH)
        if grid_fee_default is None
        else vol.Optional(CONF_GRID_FEE_PER_KWH, default=grid_fee_default)
    )
    threshold_key = (
        vol.Optional(CONF_GOOD_PRICE_THRESHOLD)
        if good_price_threshold_default is None
        else vol.Optional(
            CONF_GOOD_PRICE_THRESHOLD,
            default=good_price_threshold_default,
        )
    )
    fixed_supplier_fee_key = (
        vol.Optional(CONF_FIXED_SUPPLIER_FEE_MONTHLY)
        if fixed_supplier_fee_default is None
        else vol.Optional(
            CONF_FIXED_SUPPLIER_FEE_MONTHLY,
            default=fixed_supplier_fee_default,
        )
    )
    fixed_grid_fee_key = (
        vol.Optional(CONF_FIXED_GRID_FEE_MONTHLY)
        if fixed_grid_fee_default is None
        else vol.Optional(
            CONF_FIXED_GRID_FEE_MONTHLY,
            default=fixed_grid_fee_default,
        )
    )
    return vol.Schema(
        {
            grid_fee_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.001,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            **_time_of_use_tariff_fields(
                high_fee_default=high_fee_default,
                high_start_default=high_start_default,
                high_end_default=high_end_default,
                season_start_default=season_start_default,
                season_end_default=season_end_default,
                workday_entity_default=workday_entity_default,
            ),
            fixed_grid_fee_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.01,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            fixed_supplier_fee_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.01,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            threshold_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.001,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _entity_schema(
    *,
    power_default: str | None = None,
    price_default: str | None = None,
    pricing_strategy_default: str | None = None,
    price_included_components_default: list[str] | None = None,
    price_vat_treatment_default: str | None = None,
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
    good_price_threshold_default: float | None = None,
    forecast_nordpool_config_entry_default: str | None = None,
    grid_fee_high_per_kwh_default: float | None = None,
    grid_fee_high_start_default: str = "06:00",
    grid_fee_high_end_default: str = "22:00",
    grid_fee_high_season_start_default: str = "11-01",
    grid_fee_high_season_end_default: str = "03-31",
    grid_fee_workday_entity_default: str | None = None,
    fixed_supplier_fee_monthly_default: float | None = None,
    fixed_grid_fee_monthly_default: float | None = None,
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

    if pricing_strategy_default is None:
        pricing_strategy_key = vol.Optional(CONF_PRICING_STRATEGY)
    else:
        pricing_strategy_key = vol.Optional(
            CONF_PRICING_STRATEGY,
            default=pricing_strategy_default,
        )
    if price_included_components_default is None:
        price_components_key = vol.Optional(CONF_PRICE_INCLUDED_COMPONENTS)
    else:
        price_components_key = vol.Optional(
            CONF_PRICE_INCLUDED_COMPONENTS,
            default=price_included_components_default,
        )
    if price_vat_treatment_default is None:
        vat_treatment_key = vol.Optional(CONF_PRICE_VAT_TREATMENT)
    else:
        vat_treatment_key = vol.Optional(
            CONF_PRICE_VAT_TREATMENT,
            default=price_vat_treatment_default,
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
    fixed_supplier_fee_key = (
        vol.Optional(CONF_FIXED_SUPPLIER_FEE_MONTHLY)
        if fixed_supplier_fee_monthly_default is None
        else vol.Optional(
            CONF_FIXED_SUPPLIER_FEE_MONTHLY,
            default=fixed_supplier_fee_monthly_default,
        )
    )
    fixed_grid_fee_key = (
        vol.Optional(CONF_FIXED_GRID_FEE_MONTHLY)
        if fixed_grid_fee_monthly_default is None
        else vol.Optional(
            CONF_FIXED_GRID_FEE_MONTHLY,
            default=fixed_grid_fee_monthly_default,
        )
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
            forecast_nordpool_config_entry_key: selector.ConfigEntrySelector(
                selector.ConfigEntrySelectorConfig(
                    integration="nordpool",
                )
            ),
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
            pricing_strategy_key: selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_PRICING_STRATEGY_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            price_components_key: selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_PRICE_COMPONENT_OPTIONS,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vat_treatment_key: selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_VAT_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
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
            **_time_of_use_tariff_fields(
                high_fee_default=grid_fee_high_per_kwh_default,
                high_start_default=grid_fee_high_start_default,
                high_end_default=grid_fee_high_end_default,
                season_start_default=grid_fee_high_season_start_default,
                season_end_default=grid_fee_high_season_end_default,
                workday_entity_default=grid_fee_workday_entity_default,
            ),
            fixed_grid_fee_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.01,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            fixed_supplier_fee_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.01,
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
        self._tibber_sources: dict[str, DiscoveredSource] = {}
        self._selected_tibber_source: DiscoveredSource | None = None

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
        """Choose a guided or custom setup path."""
        if user_input is not None:
            # Preserve compatibility with callers that submit the former first form.
            if CONF_POWER_ENTITY in user_input:
                return await self.async_step_manual(user_input)
            if user_input.get(CONF_SETUP_METHOD) == _SETUP_TIBBER:
                return await self.async_step_tibber()
            if user_input.get(CONF_SETUP_METHOD) == _SETUP_CUSTOM:
                return await self.async_step_manual()

        return self.async_show_form(
            step_id="user",
            data_schema=_setup_method_schema(),
        )

    async def async_step_manual(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure independent or mixed sources manually."""
        if user_input is not None:
            if not _grid_tariff_input_valid(user_input):
                return self.async_show_form(
                    step_id="manual",
                    data_schema=_entity_schema(),
                    errors={"base": "invalid_grid_tariff"},
                )
            if not _prepare_pricing_metadata(user_input):
                return self.async_show_form(
                    step_id="manual",
                    data_schema=_entity_schema(),
                    errors={"base": "pricing_metadata_required"},
                )
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

        return self.async_show_form(step_id="manual", data_schema=_entity_schema())

    async def async_step_tibber(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Discover and select a Tibber home."""
        registry = er.async_get(self.hass)
        sources = discover_tibber_sources(registry.entities.values())
        self._tibber_sources = {
            source.device_id: source
            for source in sources
            if source.is_complete_tibber_fast_track
        }

        if not self._tibber_sources:
            return self.async_show_form(
                step_id="tibber",
                data_schema=vol.Schema({}),
                errors={"base": "tibber_sources_not_found"},
            )

        if len(self._tibber_sources) == 1:
            self._selected_tibber_source = next(iter(self._tibber_sources.values()))
            return await self.async_step_tibber_settings()

        if user_input is not None:
            device_id = user_input[CONF_TIBBER_DEVICE]
            self._selected_tibber_source = self._tibber_sources[device_id]
            return await self.async_step_tibber_settings()

        device_registry = dr.async_get(self.hass)
        options = []
        for device_id in self._tibber_sources:
            device = device_registry.async_get(device_id)
            label = (
                device.name_by_user or device.name or device_id
                if device
                else device_id
            )
            options.append({"value": device_id, "label": label})

        return self.async_show_form(
            step_id="tibber",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TIBBER_DEVICE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_tibber_settings(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Confirm discovered Tibber sources and add unresolved settings."""
        if self._selected_tibber_source is None:
            return await self.async_step_tibber()

        if user_input is not None:
            if not _grid_tariff_input_valid(user_input):
                return self.async_show_form(
                    step_id="tibber_settings",
                    data_schema=_tibber_settings_schema(),
                    errors={"base": "invalid_grid_tariff"},
                )
            data = {**self._selected_tibber_source.data, **user_input}
            return self.async_create_entry(title="Electricity Pro", data=data)

        data = self._selected_tibber_source.data
        return self.async_show_form(
            step_id="tibber_settings",
            data_schema=_tibber_settings_schema(),
            description_placeholders={
                "power_entity": str(data[CONF_POWER_ENTITY]),
                "price_entity": str(data[CONF_PRICE_ENTITY]),
                "entity_count": str(
                    sum(
                        1
                        for value in data.values()
                        if str(value).startswith("sensor.")
                    )
                ),
            },
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
        if user_input is not None and not _grid_tariff_input_valid(user_input):
            return self.async_show_form(
                step_id="init",
                data_schema=(
                    _tibber_settings_schema()
                    if self.config_entry.data.get(CONF_SOURCE_PROFILE) == _SETUP_TIBBER
                    else _entity_schema()
                ),
                errors={"base": "invalid_grid_tariff"},
            )
        if self.config_entry.data.get(CONF_SOURCE_PROFILE) == _SETUP_TIBBER:
            if user_input is not None:
                return self.async_create_entry(title="", data=user_input)
            current_grid_fee = self.config_entry.options.get(
                CONF_GRID_FEE_PER_KWH,
                self.config_entry.data.get(CONF_GRID_FEE_PER_KWH),
            )
            current_threshold = self.config_entry.options.get(
                CONF_GOOD_PRICE_THRESHOLD,
                self.config_entry.data.get(CONF_GOOD_PRICE_THRESHOLD),
            )
            values = {**self.config_entry.data, **self.config_entry.options}
            return self.async_show_form(
                step_id="init",
                data_schema=_tibber_settings_schema(
                    grid_fee_default=current_grid_fee,
                    good_price_threshold_default=current_threshold,
                    high_fee_default=values.get(CONF_GRID_FEE_HIGH_PER_KWH),
                    high_start_default=values.get(
                        CONF_GRID_FEE_HIGH_START, "06:00"
                    ),
                    high_end_default=values.get(CONF_GRID_FEE_HIGH_END, "22:00"),
                    season_start_default=values.get(
                        CONF_GRID_FEE_HIGH_SEASON_START, "11-01"
                    ),
                    season_end_default=values.get(
                        CONF_GRID_FEE_HIGH_SEASON_END, "03-31"
                    ),
                    workday_entity_default=values.get(
                        CONF_GRID_FEE_WORKDAY_ENTITY
                    ),
                    fixed_supplier_fee_default=values.get(
                        CONF_FIXED_SUPPLIER_FEE_MONTHLY
                    ),
                    fixed_grid_fee_default=values.get(
                        CONF_FIXED_GRID_FEE_MONTHLY
                    ),
                ),
                description_placeholders={"source_profile": "Tibber fast track"},
            )

        if user_input is not None:
            if not _prepare_pricing_metadata(user_input):
                return self.async_show_form(
                    step_id="init",
                    data_schema=_entity_schema(),
                    errors={"base": "pricing_metadata_required"},
                )
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
        current_pricing_strategy = self.config_entry.options.get(
            CONF_PRICING_STRATEGY,
            self.config_entry.data.get(CONF_PRICING_STRATEGY),
        )
        current_price_components = self.config_entry.options.get(
            CONF_PRICE_INCLUDED_COMPONENTS,
            self.config_entry.data.get(CONF_PRICE_INCLUDED_COMPONENTS),
        )
        current_vat_treatment = self.config_entry.options.get(
            CONF_PRICE_VAT_TREATMENT,
            self.config_entry.data.get(CONF_PRICE_VAT_TREATMENT),
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
        tariff_values = {**self.config_entry.data, **self.config_entry.options}
        current_fixed_supplier_fee = self.config_entry.options.get(
            CONF_FIXED_SUPPLIER_FEE_MONTHLY,
            self.config_entry.data.get(CONF_FIXED_SUPPLIER_FEE_MONTHLY),
        )
        current_fixed_grid_fee = self.config_entry.options.get(
            CONF_FIXED_GRID_FEE_MONTHLY,
            self.config_entry.data.get(CONF_FIXED_GRID_FEE_MONTHLY),
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
                pricing_strategy_default=current_pricing_strategy,
                price_included_components_default=current_price_components,
                price_vat_treatment_default=current_vat_treatment,
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
                good_price_threshold_default=current_good_price_threshold,
                forecast_nordpool_config_entry_default=current_forecast_nordpool_config_entry,
                grid_fee_high_per_kwh_default=tariff_values.get(
                    CONF_GRID_FEE_HIGH_PER_KWH
                ),
                grid_fee_high_start_default=tariff_values.get(
                    CONF_GRID_FEE_HIGH_START, "06:00"
                ),
                grid_fee_high_end_default=tariff_values.get(
                    CONF_GRID_FEE_HIGH_END, "22:00"
                ),
                grid_fee_high_season_start_default=tariff_values.get(
                    CONF_GRID_FEE_HIGH_SEASON_START, "11-01"
                ),
                grid_fee_high_season_end_default=tariff_values.get(
                    CONF_GRID_FEE_HIGH_SEASON_END, "03-31"
                ),
                grid_fee_workday_entity_default=tariff_values.get(
                    CONF_GRID_FEE_WORKDAY_ENTITY
                ),
                fixed_supplier_fee_monthly_default=current_fixed_supplier_fee,
                fixed_grid_fee_monthly_default=current_fixed_grid_fee,
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


def _grid_tariff_input_valid(user_input: dict[str, Any]) -> bool:
    """Validate an optional high/low grid-tariff submission."""
    high_fee = user_input.get(CONF_GRID_FEE_HIGH_PER_KWH)
    low_fee = user_input.get(CONF_GRID_FEE_PER_KWH)
    try:
        high_start = time.fromisoformat(
            str(user_input.get(CONF_GRID_FEE_HIGH_START, "06:00"))
        )
        high_end = time.fromisoformat(
            str(user_input.get(CONF_GRID_FEE_HIGH_END, "22:00"))
        )
        season_start = _parse_month_day_input(
            user_input.get(CONF_GRID_FEE_HIGH_SEASON_START, "11-01")
        )
        season_end = _parse_month_day_input(
            user_input.get(CONF_GRID_FEE_HIGH_SEASON_END, "03-31")
        )
        if high_fee is not None and low_fee is None:
            return False
        HighLowGridTariff(
            low_fee_per_kwh=Decimal(str(low_fee or 0)),
            high_fee_per_kwh=Decimal(str(high_fee or 0)),
            high_start_time=high_start,
            high_end_time=high_end,
            high_season_start=season_start,
            high_season_end=season_end,
        )
    except (InvalidOperation, TypeError, ValueError):
        return False
    return True


def _parse_month_day_input(value: Any) -> tuple[int, int]:
    """Parse a recurring MM-DD form value."""
    month, day = str(value).split("-", maxsplit=1)
    return int(month), int(day)


def _prepare_pricing_metadata(user_input: dict[str, Any]) -> bool:
    """Validate and normalize explicit price semantics in submitted data."""
    metadata_keys = (
        CONF_PRICING_STRATEGY,
        CONF_PRICE_INCLUDED_COMPONENTS,
        CONF_PRICE_VAT_TREATMENT,
        CONF_PRICE_COMPLETENESS,
    )
    if not user_input.get(CONF_PRICE_ENTITY):
        for key in metadata_keys:
            user_input.pop(key, None)
        return True

    raw_strategy = user_input.get(CONF_PRICING_STRATEGY)
    raw_components = user_input.get(CONF_PRICE_INCLUDED_COMPONENTS)
    raw_vat = user_input.get(CONF_PRICE_VAT_TREATMENT)
    if not isinstance(raw_components, list):
        return False

    try:
        strategy = PricingStrategy(raw_strategy)
        components = frozenset(PriceComponent(value) for value in raw_components)
        vat = VatTreatment(raw_vat)
    except (TypeError, ValueError):
        return False

    if PriceComponent.MARKET_ENERGY not in components:
        return False

    all_components = frozenset(PriceComponent)
    completeness = (
        PriceCompleteness.COMPLETE
        if strategy is PricingStrategy.EXTERNAL_COMPLETE_PRICE
        or components == all_components
        else PriceCompleteness.PARTIAL
    )
    user_input[CONF_PRICING_STRATEGY] = strategy.value
    user_input[CONF_PRICE_INCLUDED_COMPONENTS] = sorted(
        component.value for component in components
    )
    user_input[CONF_PRICE_VAT_TREATMENT] = vat.value
    user_input[CONF_PRICE_COMPLETENESS] = completeness.value
    return True
