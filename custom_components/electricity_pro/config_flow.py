"""Config flow for Electricity Pro."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import time
from decimal import Decimal, InvalidOperation
from typing import Any

import probatio as vol
from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryBaseFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
    CONF_ADAPTIVE_PRICE_CEILING,
    CONF_ADAPTIVE_TARGET_PERCENTILE,
    CONF_BILLED_DEMAND_CHARGES,
    CONF_CURRENT_L1_ENTITY,
    CONF_CURRENT_L2_ENTITY,
    CONF_CURRENT_L3_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_HOURLY_IMPORT_ENTITY,
    CONF_HOURLY_IMPORT_METER,
    CONF_ENERGY_SOURCE_TYPE,
    CONF_ENERGY_TAX_PER_KWH,
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
    CONF_GOOD_PRICE_MODE,
    CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
    CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICE_VAT_RATE,
    CONF_PRICING_STRATEGY,
    CONF_SETUP_METHOD,
    CONF_SUPPLIER_MARKUP_PER_KWH,
    CONF_TIBBER_DEVICE,
    CONF_VOLTAGE_L1_ENTITY,
    CONF_VOLTAGE_L2_ENTITY,
    CONF_VOLTAGE_L3_ENTITY,
    DOMAIN,
    DEFAULT_ADAPTIVE_TARGET_PERCENTILE,
    ENERGY_SOURCE_DAILY,
    ENERGY_SOURCE_LIFETIME,
    GOOD_PRICE_MODE_ADAPTIVE,
    GOOD_PRICE_MODE_FIXED,
)
from .pricing import (
    PriceComponent,
    PricingStrategy,
    VatTreatment,
)
from .grid_tariff import HighLowGridTariff
from .grid_config import GridFlow, without_grid_fields
from .household_cost import (
    BilledDemandCharge,
    DemandChargeCoverage,
    billed_demand_charges,
    demand_charge_basis,
    parse_billing_period,
)
from .source_adapters import DiscoveredSource, discover_tibber_sources
from .settings import resolve_settings
from .measurement_config import (
    MeasurementFlow,
    measurement_suggestions,
    remaining_settings_schema,
)
from .market_config import (
    MARKET_KEYS,
    MarketPriceFlow,
    market_suggestions,
    without_market_fields,
)
from .supplier_config import SUPPLIER_KEYS, SupplierFlow, without_supplier_fields
from .pricing_config import prepare_pricing_metadata as _prepare_pricing_metadata
from .flow_sources import FLOW_KEYS
from .production_config import ProductionFlow
from .insight_config import InsightFlow
from .review_config import ReviewFlow
from .markup_estimate import CONF_ESTIMATE_MARKUP, MarkupEstimate, async_estimate_markup
from .vat_suggestions import CONF_SUGGEST_VAT, assistance_field


_SETUP_TIBBER = "tibber"
_SETUP_CUSTOM = "custom"

_PRICING_STRATEGY_OPTIONS: list[selector.SelectOptionDict] = [
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

_PRICE_COMPONENT_OPTIONS: list[selector.SelectOptionDict] = [
    {"value": PriceComponent.MARKET_ENERGY.value, "label": "Market energy"},
    {"value": PriceComponent.SUPPLIER_MARKUP.value, "label": "Supplier markup"},
    {"value": PriceComponent.ENERGY_TAX.value, "label": "Energy tax"},
    {
        "value": PriceComponent.VARIABLE_GRID_FEE.value,
        "label": "Variable grid fee",
    },
]

_VAT_OPTIONS: list[selector.SelectOptionDict] = [
    {"value": VatTreatment.INCLUDED.value, "label": "VAT included"},
    {"value": VatTreatment.EXCLUDED.value, "label": "VAT excluded"},
    {"value": VatTreatment.UNKNOWN.value, "label": "Unknown"},
]

_ENERGY_SOURCE_TYPE_OPTIONS: list[selector.SelectOptionDict] = [
    {
        "value": ENERGY_SOURCE_DAILY,
        "label": "Accumulated since midnight",
    },
    {
        "value": ENERGY_SOURCE_LIFETIME,
        "label": "Total accumulated energy",
    },
]

_GOOD_PRICE_MODE_OPTIONS: list[selector.SelectOptionDict] = [
    {"value": GOOD_PRICE_MODE_FIXED, "label": "Fixed threshold"},
    {"value": GOOD_PRICE_MODE_ADAPTIVE, "label": "Adaptive"},
]


def _own_source_entities(hass: HomeAssistant | None) -> list[str]:
    """Identify our outputs by registry ownership, including renamed entities."""
    if hass is None:
        return []
    return [
        entity.entity_id
        for entity in er.async_get(hass).entities.values()
        if entity.platform == DOMAIN
    ]


def _source_input_errors(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> dict[str, str]:
    """Prevent our outputs from feeding back into source inputs."""
    own_entities = set(_own_source_entities(hass))
    source_fields = (
        CONF_POWER_ENTITY,
        CONF_PRICE_ENTITY,
        CONF_ENERGY_ENTITY,
        CONF_ACCUMULATED_COST_TODAY_ENTITY,
        CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
        CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
        CONF_CURRENT_L1_ENTITY,
        CONF_CURRENT_L2_ENTITY,
        CONF_CURRENT_L3_ENTITY,
        CONF_VOLTAGE_L1_ENTITY,
        CONF_VOLTAGE_L2_ENTITY,
        CONF_VOLTAGE_L3_ENTITY,
        CONF_GRID_FEE_WORKDAY_ENTITY,
        *FLOW_KEYS,
    )
    errors = {
        field: "electricity_pro_source"
        for field in source_fields
        if user_input.get(field) in own_entities
    }
    flows = [user_input.get(key) for key in FLOW_KEYS if user_input.get(key)]
    imports = {user_input.get(CONF_POWER_ENTITY), user_input.get(CONF_ENERGY_ENTITY)}
    if len(flows) != len(set(flows)) or any(source in imports for source in flows):
        errors["base"] = "invalid_flow_source"
    return errors


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
                        selector.SelectOptionDict(
                            value=_SETUP_TIBBER, label="Tibber fast track"
                        ),
                        selector.SelectOptionDict(
                            value=_SETUP_CUSTOM, label="Custom or mixed sources"
                        ),
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
        }
    )


def _tibber_settings_schema(
    *,
    include_forecast_pricing: bool = False,
    forecast_nordpool_config_entry_default: str | None = None,
    vat_rate_default: float | None = None,
    grid_fee_default: float | None = None,
    supplier_markup_default: float | None = None,
    energy_tax_default: float | None = None,
    good_price_threshold_default: float | None = None,
    good_price_mode_default: str = GOOD_PRICE_MODE_FIXED,
    adaptive_target_percentile_default: float = DEFAULT_ADAPTIVE_TARGET_PERCENTILE,
    adaptive_price_ceiling_default: float | None = None,
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
    forecast_entry_key = (
        vol.Optional(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY)
        if forecast_nordpool_config_entry_default is None
        else vol.Optional(
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
            description={
                "suggested_value": forecast_nordpool_config_entry_default,
            },
        )
    )
    grid_fee_key = (
        vol.Optional(CONF_GRID_FEE_PER_KWH)
        if grid_fee_default is None
        else vol.Optional(CONF_GRID_FEE_PER_KWH, default=grid_fee_default)
    )
    supplier_markup_key = (
        vol.Optional(CONF_SUPPLIER_MARKUP_PER_KWH)
        if supplier_markup_default is None
        else vol.Optional(
            CONF_SUPPLIER_MARKUP_PER_KWH,
            default=supplier_markup_default,
        )
    )
    energy_tax_key = (
        vol.Optional(CONF_ENERGY_TAX_PER_KWH)
        if energy_tax_default is None
        else vol.Optional(CONF_ENERGY_TAX_PER_KWH, default=energy_tax_default)
    )
    threshold_key = (
        vol.Optional(CONF_GOOD_PRICE_THRESHOLD)
        if good_price_threshold_default is None
        else vol.Optional(
            CONF_GOOD_PRICE_THRESHOLD,
            default=good_price_threshold_default,
        )
    )
    adaptive_ceiling_key = (
        vol.Optional(CONF_ADAPTIVE_PRICE_CEILING)
        if adaptive_price_ceiling_default is None
        else vol.Optional(
            CONF_ADAPTIVE_PRICE_CEILING,
            default=adaptive_price_ceiling_default,
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
            forecast_entry_key: selector.ConfigEntrySelector(
                selector.ConfigEntrySelectorConfig(integration="nordpool")
            ),
            **(
                {
                    supplier_markup_key: selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            step=0.001,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    **_vat_rate_field(vat_rate_default),
                }
                if include_forecast_pricing
                else {}
            ),
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
            energy_tax_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.001,
                    mode=selector.NumberSelectorMode.BOX,
                )
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
            vol.Required(
                CONF_GOOD_PRICE_MODE,
                default=good_price_mode_default,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_GOOD_PRICE_MODE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            threshold_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.001,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_ADAPTIVE_TARGET_PERCENTILE,
                default=adaptive_target_percentile_default,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            adaptive_ceiling_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    step=0.001,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _entity_schema(
    *,
    hass: HomeAssistant | None = None,
    power_default: str | None = None,
    price_default: str | None = None,
    pricing_strategy_default: str | None = None,
    price_included_components_default: list[str] | None = None,
    price_vat_treatment_default: str | None = None,
    vat_rate_default: float | None = None,
    energy_default: str | None = None,
    energy_source_type_default: str = ENERGY_SOURCE_DAILY,
    accumulated_cost_today_default: str | None = None,
    current_l1_default: str | None = None,
    current_l2_default: str | None = None,
    current_l3_default: str | None = None,
    voltage_l1_default: str | None = None,
    voltage_l2_default: str | None = None,
    voltage_l3_default: str | None = None,
    monthly_peak_hour_consumption_default: str | None = None,
    monthly_peak_hour_time_default: str | None = None,
    grid_fee_per_kwh_default: float | None = None,
    supplier_markup_per_kwh_default: float | None = None,
    energy_tax_per_kwh_default: float | None = None,
    good_price_threshold_default: float | None = None,
    good_price_mode_default: str = GOOD_PRICE_MODE_FIXED,
    adaptive_target_percentile_default: float = DEFAULT_ADAPTIVE_TARGET_PERCENTILE,
    adaptive_price_ceiling_default: float | None = None,
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
    excluded_sources = _own_source_entities(hass)

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
    energy_source_type_key = vol.Optional(
        CONF_ENERGY_SOURCE_TYPE,
        default=energy_source_type_default,
    )

    if accumulated_cost_today_default is None:
        accumulated_cost_today_key = vol.Optional(CONF_ACCUMULATED_COST_TODAY_ENTITY)
    else:
        accumulated_cost_today_key = vol.Optional(
            CONF_ACCUMULATED_COST_TODAY_ENTITY,
            default=accumulated_cost_today_default,
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
        monthly_peak_hour_time_key = vol.Optional(CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY)
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
    supplier_markup_key = (
        vol.Optional(CONF_SUPPLIER_MARKUP_PER_KWH)
        if supplier_markup_per_kwh_default is None
        else vol.Optional(
            CONF_SUPPLIER_MARKUP_PER_KWH,
            default=supplier_markup_per_kwh_default,
        )
    )
    energy_tax_key = (
        vol.Optional(CONF_ENERGY_TAX_PER_KWH)
        if energy_tax_per_kwh_default is None
        else vol.Optional(
            CONF_ENERGY_TAX_PER_KWH,
            default=energy_tax_per_kwh_default,
        )
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
    adaptive_price_ceiling_key = (
        vol.Optional(CONF_ADAPTIVE_PRICE_CEILING)
        if adaptive_price_ceiling_default is None
        else vol.Optional(
            CONF_ADAPTIVE_PRICE_CEILING,
            default=adaptive_price_ceiling_default,
        )
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
                    exclude_entities=excluded_sources,
                    domain="sensor",
                    device_class="power",
                )
            ),
            price_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    exclude_entities=excluded_sources,
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
            supplier_markup_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.001,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            **_vat_rate_field(vat_rate_default),
            energy_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    exclude_entities=excluded_sources,
                    domain="sensor",
                )
            ),
            energy_source_type_key: selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_ENERGY_SOURCE_TYPE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            accumulated_cost_today_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    exclude_entities=excluded_sources,
                    domain="sensor",
                    device_class="monetary",
                )
            ),
            monthly_peak_hour_consumption_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    exclude_entities=excluded_sources,
                    domain="sensor",
                    device_class="energy",
                )
            ),
            monthly_peak_hour_time_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    exclude_entities=excluded_sources,
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
            energy_tax_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.001,
                    mode=selector.NumberSelectorMode.BOX,
                )
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
            vol.Required(
                CONF_GOOD_PRICE_MODE,
                default=good_price_mode_default,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_GOOD_PRICE_MODE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            good_price_threshold_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.001,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_ADAPTIVE_TARGET_PERCENTILE,
                default=adaptive_target_percentile_default,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            adaptive_price_ceiling_key: selector.NumberSelector(
                selector.NumberSelectorConfig(
                    step=0.001,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            current_l1_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    exclude_entities=excluded_sources,
                    domain="sensor",
                    device_class="current",
                )
            ),
            current_l2_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    exclude_entities=excluded_sources,
                    domain="sensor",
                    device_class="current",
                )
            ),
            current_l3_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    exclude_entities=excluded_sources,
                    domain="sensor",
                    device_class="current",
                )
            ),
            voltage_l1_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    exclude_entities=excluded_sources,
                    domain="sensor",
                    device_class="voltage",
                )
            ),
            voltage_l2_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    exclude_entities=excluded_sources,
                    domain="sensor",
                    device_class="voltage",
                )
            ),
            voltage_l3_key: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    exclude_entities=excluded_sources,
                    domain="sensor",
                    device_class="voltage",
                )
            ),
        }
    )


def _supplier_schema(
    hass: HomeAssistant | None, values: dict[str, Any], known_tibber: bool
) -> vol.Schema:
    """Compose supplier controls from the existing selector contracts."""
    if known_tibber:
        schema = _tibber_settings_schema(
            include_forecast_pricing=bool(
                values.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY)
            ),
            vat_rate_default=values.get(CONF_PRICE_VAT_RATE),
            supplier_markup_default=values.get(CONF_SUPPLIER_MARKUP_PER_KWH),
            fixed_supplier_fee_default=values.get(CONF_FIXED_SUPPLIER_FEE_MONTHLY),
        )
    else:
        schema = _entity_schema(
            hass=hass,
            price_default=values.get(CONF_PRICE_ENTITY),
            pricing_strategy_default=values.get(CONF_PRICING_STRATEGY),
            price_included_components_default=values.get(
                CONF_PRICE_INCLUDED_COMPONENTS
            ),
            price_vat_treatment_default=values.get(CONF_PRICE_VAT_TREATMENT),
            vat_rate_default=values.get(CONF_PRICE_VAT_RATE),
            supplier_markup_per_kwh_default=values.get(CONF_SUPPLIER_MARKUP_PER_KWH),
            fixed_supplier_fee_monthly_default=values.get(
                CONF_FIXED_SUPPLIER_FEE_MONTHLY
            ),
            accumulated_cost_today_default=values.get(
                CONF_ACCUMULATED_COST_TODAY_ENTITY
            ),
        )
    fields: dict[vol.Marker, Any] = {}
    for key, value in schema.schema.items():
        if key.schema not in (*SUPPLIER_KEYS, CONF_SUGGEST_VAT):
            continue
        if key.schema in SUPPLIER_KEYS:
            # Suggestions remain editable/clearable. Schema defaults would
            # restore an old value when the frontend omits a cleared field.
            key = vol.Optional(
                key.schema,
                description={"suggested_value": values.get(key.schema)},
            )
        fields[key] = value
    for key in fields:
        choices = {
            CONF_PRICING_STRATEGY: [item.value for item in PricingStrategy],
            CONF_PRICE_INCLUDED_COMPONENTS: [item.value for item in PriceComponent],
            CONF_PRICE_VAT_TREATMENT: [item.value for item in VatTreatment],
        }.get(key.schema)
        if choices is not None:
            fields[key] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=choices,
                    multiple=key.schema == CONF_PRICE_INCLUDED_COMPONENTS,
                    translation_key=key.schema,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
    if known_tibber and values.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY):
        fields[vol.Optional(CONF_ESTIMATE_MARKUP, default=False)] = (
            selector.BooleanSelector()
        )
    return vol.Schema(fields)


class _MarkupEstimateFlow(ConfigEntryBaseFlow):
    """Shared opt-in estimate and review steps for setup and options."""

    _pending_forecast_settings: dict[str, Any] | None
    _selected_tibber_source: DiscoveredSource | None = None
    _markup_estimate: MarkupEstimate
    _markup_estimate_area: str
    _supplier_values: dict[str, Any] | None

    async def async_step_supplier(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Continue through the concrete setup or options flow."""
        raise NotImplementedError

    async def async_step_tibber_markup_estimate(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        pending = self._pending_forecast_settings
        if pending is None:
            return await self.async_step_supplier()
        entry = self.hass.config_entries.async_get_entry(
            pending.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY, "")
        )
        areas = entry.data.get("areas", []) if entry else []
        if not isinstance(areas, list):
            areas = []
        selected_area = pending.get(CONF_FORECAST_PRICE_AREA)
        if selected_area in areas:
            # A reviewed markup estimate must use the area already selected for
            # forecasting. Changing it belongs to the shared market screen.
            areas = [selected_area]
        errors = {}
        if user_input is not None:
            if not user_input.get("confirm_matching_area"):
                return await self.async_step_supplier()
            area = user_input.get(CONF_FORECAST_PRICE_AREA)
            try:
                if (
                    entry is None
                    or not isinstance(area, str)
                    or area not in areas
                    or pending.get(CONF_PRICE_VAT_RATE) is None
                ):
                    raise ValueError("An area and explicit VAT rate are required")
                selected = self._selected_tibber_source
                source: dict[str, object]
                if selected is not None:
                    source = selected.data
                elif isinstance(self, OptionsFlow):
                    source = {
                        **self.config_entry.data,
                        **self.config_entry.options,
                    }
                else:
                    raise ValueError("A Tibber source is required")
                price_entity = source.get(CONF_PRICE_ENTITY, "")
                if not isinstance(price_entity, str):
                    raise ValueError("A price entity ID is required")
                async with asyncio.timeout(30):
                    self._markup_estimate = await async_estimate_markup(
                        self.hass,
                        price_entity=price_entity,
                        nordpool_entry_id=entry.entry_id,
                        area=area,
                        vat_rate=pending[CONF_PRICE_VAT_RATE],
                    )
                self._markup_estimate_area = area
                return await self.async_step_tibber_markup_review()
            except ValueError, HomeAssistantError, TimeoutError:
                errors["base"] = "markup_estimate_unavailable"
        return self.async_show_form(
            step_id="tibber_markup_estimate",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_FORECAST_PRICE_AREA,
                        description={
                            "suggested_value": pending.get(CONF_FORECAST_PRICE_AREA)
                            or (areas[0] if len(areas) == 1 else None),
                        },
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=areas)
                    ),
                    vol.Optional(
                        "confirm_matching_area", default=False
                    ): selector.BooleanSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_tibber_markup_review(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        pending = self._pending_forecast_settings
        if pending is None:
            return await self.async_step_supplier()
        estimate = self._markup_estimate
        if user_input is not None:
            if user_input.get("use_estimate"):
                return await self.async_step_supplier(
                    {
                        **(self._supplier_values or {}),
                        CONF_PRICE_VAT_RATE: pending[CONF_PRICE_VAT_RATE],
                        CONF_SUPPLIER_MARKUP_PER_KWH: user_input[
                            CONF_SUPPLIER_MARKUP_PER_KWH
                        ],
                    }
                )
            return await self.async_step_supplier()
        return self.async_show_form(
            step_id="tibber_markup_review",
            description_placeholders={
                "count": str(estimate.count),
                "spread": str(estimate.spread),
                "currency": estimate.currency,
                "area": self._markup_estimate_area,
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SUPPLIER_MARKUP_PER_KWH, default=float(estimate.value)
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            step=0.001,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        "use_estimate", default=False
                    ): selector.BooleanSelector(),
                }
            ),
        )


class ElectricityProConfigFlow(
    MeasurementFlow,
    MarketPriceFlow,
    SupplierFlow,
    GridFlow,
    ProductionFlow,
    InsightFlow,
    ReviewFlow,
    _MarkupEstimateFlow,
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle the Electricity Pro config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._pending_review_values: dict[str, Any] | None = None
        self._pending_user_input: dict[str, Any] | None = None
        self._pending_forecast_settings: dict[str, Any] | None = None
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
                return await self.async_step_measurements()

        return self.async_show_form(
            step_id="user",
            data_schema=_setup_method_schema(),
        )

    def _measurement_defaults(self) -> dict[str, Any]:
        if self._selected_tibber_source is not None:
            return dict(self._selected_tibber_source.data)
        return measurement_suggestions(self.hass)

    async def _async_measurements_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        if self._selected_tibber_source is not None:
            self._selected_tibber_source.data.update(values)
        return await self.async_step_market_prices()

    def _market_defaults(self) -> dict[str, Any]:
        return market_suggestions(self.hass)

    async def _async_market_prices_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        if self._selected_tibber_source is not None:
            self._selected_tibber_source.data.update(values)
        return await self.async_step_supplier()

    def _supplier_defaults(self) -> dict[str, Any]:
        return {
            **(
                self._selected_tibber_source.data
                if self._selected_tibber_source
                and self._selected_tibber_source.is_complete_tibber_fast_track
                else {}
            ),
            **(self._measurement_values or {}),
            **(self._market_values or {}),
        }

    def _supplier_form_schema(
        self, values: dict[str, Any], known_tibber: bool
    ) -> vol.Schema:
        return _supplier_schema(self.hass, values, known_tibber)

    async def _async_supplier_estimate(self) -> ConfigFlowResult:
        return await self.async_step_tibber_markup_estimate()

    async def _async_supplier_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        self._setup_tibber = (
            self._selected_tibber_source is not None
            and self._selected_tibber_source.is_complete_tibber_fast_track
        )
        if self._selected_tibber_source is not None:
            self._selected_tibber_source.data.update(values)
        return await self.async_step_grid()

    def _grid_defaults(self) -> dict[str, Any]:
        return (
            dict(self._selected_tibber_source.data)
            if self._selected_tibber_source
            else {}
        )

    async def _async_grid_complete(self, values: dict[str, Any]) -> ConfigFlowResult:
        self._grid_values = values
        return await self.async_step_energy_flows()

    def _production_defaults(self) -> dict[str, Any]:
        return {
            **self._supplier_defaults(),
            **(self._supplier_values or {}),
            **(self._grid_values or {}),
        }

    def _production_binding_errors(self, values: dict[str, Any]) -> dict[str, str]:
        errors = _source_input_errors(
            self.hass, {**self._production_reference, **values}
        )
        return {
            key: error
            for key, error in errors.items()
            if key == "base" or key in FLOW_KEYS
        }

    async def _async_production_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        self._production_values = values
        return await self.async_step_insights()

    def _insight_defaults(self) -> dict[str, Any]:
        return {**self._production_defaults(), **(self._production_values or {})}

    async def _async_insights_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        data = {
            **(
                self._selected_tibber_source.data
                if self._setup_tibber and self._selected_tibber_source
                else {}
            ),
            **(self._measurement_values or {}),
            **(self._market_values or {}),
            **(self._supplier_values or {}),
            **(self._grid_values or {}),
            **(self._production_values or {}),
            **{key: value for key, value in values.items() if value is not None},
        }
        # Unset thresholds must not create an unavailable Good Time entity by default.
        # Single-area entries inherit the area without a redundant stored override.
        if (
            len(
                _nordpool_areas(
                    self.hass, data.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY)
                )
            )
            <= 1
        ):
            data.pop(CONF_FORECAST_PRICE_AREA, None)
        self._pending_review_values = deepcopy(data)
        return await self.async_step_review()

    def _review_defaults(self) -> dict[str, Any] | None:
        return deepcopy(self._pending_review_values)

    async def _async_review_complete(self, values: dict[str, Any]) -> ConfigFlowResult:
        return self.async_create_entry(title="Electricity Pro", data=values)

    def _manual_schema(self) -> vol.Schema:
        schema = _entity_schema(
            hass=self.hass,
            vat_rate_default=self._vat_form_values(self._market_values or {}).get(
                CONF_PRICE_VAT_RATE
            ),
        )
        if self._market_values is not None:
            schema = without_market_fields(schema)
        if self._supplier_values is not None:
            schema = without_supplier_fields(schema)
        if self._grid_values is not None:
            schema = without_grid_fields(schema)
        return (
            remaining_settings_schema(schema)
            if self._measurement_values is not None
            else schema
        )

    async def async_step_manual(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure independent or mixed sources manually."""
        if user_input is not None and self._measurement_values is not None:
            user_input = {**self._measurement_values, **user_input}
        if user_input is not None and self._market_values is not None:
            user_input = {**user_input, **self._market_values}
        if user_input is not None and self._supplier_values is not None:
            user_input = {**user_input, **self._supplier_values}
        if user_input is not None and self._grid_values is not None:
            user_input = {**user_input, **self._grid_values}
        if user_input is not None and self._production_values is not None:
            user_input = {**user_input, **self._production_values}
        if user_input is not None and self._supplier_values is None:
            result = await self._async_maybe_suggest_vat(user_input, "manual")
            if result is not None:
                return result
        if user_input is not None and (
            errors := _source_input_errors(self.hass, user_input)
        ):
            return self.async_show_form(
                step_id="manual",
                data_schema=self.add_suggested_values_to_schema(
                    self._manual_schema(), user_input
                ),
                errors=errors,
            )
        if user_input is not None:
            if self._grid_values is None and not _grid_tariff_input_valid(user_input):
                return self.async_show_form(
                    step_id="manual",
                    data_schema=self.add_suggested_values_to_schema(
                        self._manual_schema(), user_input
                    ),
                    errors={"base": "invalid_grid_tariff"},
                )
            if not _good_price_input_valid(user_input):
                return self.async_show_form(
                    step_id="manual",
                    data_schema=self.add_suggested_values_to_schema(
                        self._manual_schema(), user_input
                    ),
                    errors={"base": "invalid_good_price_settings"},
                )
            if not _prepare_pricing_metadata(user_input):
                return self.async_show_form(
                    step_id="manual",
                    data_schema=self.add_suggested_values_to_schema(
                        self._manual_schema(), user_input
                    ),
                    errors={"base": "pricing_metadata_required"},
                )
            areas = _nordpool_areas(
                self.hass, user_input.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY)
            )
            if len(areas) > 1 and user_input.get(CONF_FORECAST_PRICE_AREA) not in areas:
                self._pending_user_input = user_input
                self._forecast_areas = [str(area) for area in areas]
                return self.async_show_form(
                    step_id="forecast_area",
                    data_schema=_forecast_area_schema(self._forecast_areas),
                )

            if len(areas) <= 1:
                user_input.pop(CONF_FORECAST_PRICE_AREA, None)
            return self.async_create_entry(
                title="Electricity Pro",
                data=user_input,
            )

        return self.async_show_form(step_id="manual", data_schema=self._manual_schema())

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
            if CONF_POWER_ENTITY in source.data
        }

        if not self._tibber_sources:
            return self.async_show_form(
                step_id="tibber",
                data_schema=vol.Schema({}),
                errors={"base": "tibber_sources_not_found"},
            )

        if len(self._tibber_sources) == 1:
            self._selected_tibber_source = next(iter(self._tibber_sources.values()))
            return await self.async_step_measurements()

        if user_input is not None:
            device_id = user_input[CONF_TIBBER_DEVICE]
            self._selected_tibber_source = self._tibber_sources[device_id]
            return await self.async_step_measurements()

        device_registry = dr.async_get(self.hass)
        options: list[selector.SelectOptionDict] = []
        for device_id in self._tibber_sources:
            device = device_registry.async_get(device_id)
            label = (
                device.name_by_user or device.name or device_id if device else device_id
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
            if self._market_values is not None:
                user_input = {**user_input, **self._market_values}
            if self._supplier_values is not None:
                user_input = {**user_input, **self._supplier_values}
            if self._grid_values is not None:
                user_input = {**user_input, **self._grid_values}
            if self._production_values is not None:
                user_input = {**user_input, **self._production_values}
            errors = {}
            if self._grid_values is None and not _grid_tariff_input_valid(user_input):
                errors = {"base": "invalid_grid_tariff"}
            elif not _good_price_input_valid(user_input):
                errors = {"base": "invalid_good_price_settings"}
            if errors:
                return self._show_tibber_settings(user_input, errors)
            areas = _nordpool_areas(
                self.hass, user_input.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY)
            )
            if len(areas) > 1 and user_input.get(CONF_FORECAST_PRICE_AREA) not in areas:
                self._pending_user_input = {
                    **self._selected_tibber_source.data,
                    **user_input,
                }
                self._forecast_areas = [str(area) for area in areas]
                return self.async_show_form(
                    step_id="forecast_area",
                    data_schema=_forecast_area_schema(self._forecast_areas),
                )

            data = {**self._selected_tibber_source.data, **user_input}
            return self.async_create_entry(title="Electricity Pro", data=data)

        return self._show_tibber_settings()

    def _show_tibber_settings(
        self,
        user_input: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        """Keep discovered-source explanations and submitted settings on retry."""
        assert self._selected_tibber_source is not None
        data = self._selected_tibber_source.data
        return self.async_show_form(
            step_id="tibber_settings",
            data_schema=self.add_suggested_values_to_schema(
                without_grid_fields(
                    without_supplier_fields(
                        without_market_fields(_tibber_settings_schema())
                    )
                ),
                user_input,
            ),
            errors=errors,
            description_placeholders={
                "power_entity": str(data[CONF_POWER_ENTITY]),
                "price_entity": str(data[CONF_PRICE_ENTITY]),
                "entity_count": str(
                    sum(
                        1 for value in data.values() if str(value).startswith("sensor.")
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


class ElectricityProOptionsFlow(
    MeasurementFlow,
    MarketPriceFlow,
    SupplierFlow,
    GridFlow,
    ProductionFlow,
    InsightFlow,
    ReviewFlow,
    _MarkupEstimateFlow,
    OptionsFlow,
):
    """Handle Electricity Pro options."""

    _review_step_id = "overview"

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._pending_forecast_settings: dict[str, Any] | None = None
        self._supplier_open = False
        self._hourly_import_meter: str | None = None

    def _measurement_defaults(self) -> dict[str, Any]:
        return resolve_settings(self.config_entry.data, self.config_entry.options)

    async def _async_measurements_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        return self.async_create_entry(
            title="", data={**self.config_entry.options, **values}
        )

    def _market_defaults(self) -> dict[str, Any]:
        return resolve_settings(self.config_entry.data, self.config_entry.options)

    def _settings_defaults(self) -> dict[str, Any]:
        """Resolve saved settings with a draft legacy-area correction."""
        values = resolve_settings(self.config_entry.data, self.config_entry.options)
        if self._supplier_open and self._market_values is not None:
            values.update(self._market_values)
        return values

    async def _async_market_prices_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        if self._supplier_open:
            self._market_values = values
            return await self.async_step_supplier()
        return self.async_create_entry(
            title="", data={**self.config_entry.options, **values}
        )

    def _supplier_defaults(self) -> dict[str, Any]:
        return self._settings_defaults()

    def _supplier_form_schema(
        self, values: dict[str, Any], known_tibber: bool
    ) -> vol.Schema:
        return _supplier_schema(self.hass, values, known_tibber)

    async def _async_supplier_market(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult | None:
        self._supplier_open = True
        market_entry = self._market_entry(values)
        areas = self._market_areas(market_entry)
        if (
            self._market_source_valid(market_entry)
            and len(areas) > 1
            and values.get(CONF_FORECAST_PRICE_AREA) not in areas
        ):
            self._market_values = {key: values.get(key) for key in MARKET_KEYS}
            return await self.async_step_market_area()
        return None

    async def _async_supplier_estimate(self) -> ConfigFlowResult:
        return await self.async_step_tibber_markup_estimate()

    async def _async_supplier_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        return self.async_create_entry(
            title="",
            data={**self.config_entry.options, **(self._market_values or {}), **values},
        )

    def _grid_defaults(self) -> dict[str, Any]:
        return self._settings_defaults()

    async def _async_grid_complete(self, values: dict[str, Any]) -> ConfigFlowResult:
        return self.async_create_entry(
            title="", data={**self.config_entry.options, **values}
        )

    async def async_step_billed_demand_charge(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Save, replace or remove the charge for an exact meter and period."""
        settings = self._settings_defaults()
        meter = settings.get(CONF_ENERGY_ENTITY)
        if not isinstance(meter, str) or not meter:
            return await self.async_step_menu()

        errors: dict[str, str] = {}
        charges = billed_demand_charges(settings.get(CONF_BILLED_DEMAND_CHARGES))
        if user_input is not None:
            try:
                start, end = parse_billing_period(
                    user_input.get("period_start"), user_input.get("period_end")
                )
                charge = None
                if not user_input.get("remove"):
                    charge = BilledDemandCharge.from_dict(
                        {
                            **user_input,
                            "meter": meter,
                            "basis": demand_charge_basis(
                                settings, str(dt_util.get_default_time_zone())
                            ),
                        }
                    )
            except KeyError, ValueError:
                errors["base"] = "invalid_billed_demand_charge"
            else:
                remaining = [
                    saved
                    for saved in charges
                    if (saved.meter, saved.period_start, saved.period_end)
                    != (meter, start, end)
                ]
                if charge is not None and any(
                    saved.meter == meter
                    and saved.period_start <= end
                    and start <= saved.period_end
                    for saved in remaining
                ):
                    errors["base"] = "overlapping_billing_period"
                else:
                    if charge is not None:
                        remaining.append(charge)
                    return self.async_create_entry(
                        title="",
                        data={
                            **self.config_entry.options,
                            CONF_BILLED_DEMAND_CHARGES: [
                                saved.as_dict() for saved in remaining
                            ],
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required("period_start"): selector.DateSelector(),
                vol.Required("period_end"): selector.DateSelector(),
                vol.Optional("amount"): selector.TextSelector(),
                vol.Optional("currency"): selector.TextSelector(),
                vol.Optional("coverage", default=DemandChargeCoverage.UNKNOWN.value): (
                    selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=list(DemandChargeCoverage),
                            translation_key="demand_charge_coverage",
                        )
                    )
                ),
                vol.Optional("remove", default=False): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="billed_demand_charge",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
            description_placeholders={"meter": meter},
        )

    async def async_step_hourly_import(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Bind the hourly sensor to the confirmed meter for this entry."""
        settings = self._settings_defaults()
        meter = settings.get(CONF_ENERGY_ENTITY)
        if not isinstance(meter, str) or not meter:
            return await self.async_step_menu()

        own = _own_source_entities(self.hass)
        errors: dict[str, str] = {}
        if user_input is not None:
            source = user_input.get(CONF_HOURLY_IMPORT_ENTITY)
            if source and (
                source == meter or source in own or not source.startswith("sensor.")
            ):
                errors[CONF_HOURLY_IMPORT_ENTITY] = "invalid_hourly_import_source"
            elif source and meter != self._hourly_import_meter:
                errors["base"] = "hourly_import_meter_changed"
            elif source and not user_input.get("confirm_hourly_import_meter"):
                errors["confirm_hourly_import_meter"] = "confirm_hourly_import_meter"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        **self.config_entry.options,
                        CONF_HOURLY_IMPORT_ENTITY: source,
                        CONF_HOURLY_IMPORT_METER: meter if source else None,
                    },
                )

        self._hourly_import_meter = meter
        schema = vol.Schema(
            {
                vol.Optional(CONF_HOURLY_IMPORT_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", exclude_entities=[*own, meter]
                    )
                ),
                vol.Optional(
                    "confirm_hourly_import_meter", default=False
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="hourly_import",
            data_schema=self.add_suggested_values_to_schema(
                schema,
                {
                    CONF_HOURLY_IMPORT_ENTITY: (
                        user_input.get(CONF_HOURLY_IMPORT_ENTITY)
                        if user_input is not None
                        else settings.get(CONF_HOURLY_IMPORT_ENTITY)
                    )
                },
            ),
            errors=errors,
            description_placeholders={"meter": meter},
        )

    def _production_defaults(self) -> dict[str, Any]:
        return self._settings_defaults()

    def _production_binding_errors(self, values: dict[str, Any]) -> dict[str, str]:
        errors = _source_input_errors(
            self.hass, {**self._production_reference, **values}
        )
        return {
            key: error
            for key, error in errors.items()
            if key == "base" or key in FLOW_KEYS
        }

    async def _async_production_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        return self.async_create_entry(
            title="", data={**self.config_entry.options, **values}
        )

    def _insight_defaults(self) -> dict[str, Any]:
        return self._settings_defaults()

    async def _async_insights_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        return self.async_create_entry(
            title="", data={**self.config_entry.options, **values}
        )

    def _review_defaults(self) -> dict[str, Any]:
        return self._settings_defaults()

    async def _async_review_complete(self, values: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_menu()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the configuration section to edit."""
        return await self.async_step_menu()

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Expose the same shared sections used during setup."""
        return self.async_show_menu(
            step_id="menu",
            menu_options=[
                "measurements",
                "market_prices",
                "supplier",
                "grid",
                *(
                    ["hourly_import", "billed_demand_charge"]
                    if self._settings_defaults().get(CONF_ENERGY_ENTITY)
                    else []
                ),
                "energy_flows",
                "insights",
                "overview",
            ],
        )


def _nordpool_areas(hass: HomeAssistant, entry_id: object) -> list[object]:
    """Read area metadata without changing its values or inferring missing areas."""
    if not isinstance(entry_id, str):
        return []
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        return []
    areas: object = entry.data.get("areas", [])
    return areas if isinstance(areas, list) else []


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
    except InvalidOperation, TypeError, ValueError:
        return False
    return True


def _good_price_input_valid(user_input: dict[str, Any]) -> bool:
    """Validate explicit fixed/adaptive Good Time settings."""
    mode = user_input.get(CONF_GOOD_PRICE_MODE, GOOD_PRICE_MODE_FIXED)
    if mode not in {GOOD_PRICE_MODE_FIXED, GOOD_PRICE_MODE_ADAPTIVE}:
        return False
    try:
        target = Decimal(
            str(
                user_input.get(
                    CONF_ADAPTIVE_TARGET_PERCENTILE,
                    DEFAULT_ADAPTIVE_TARGET_PERCENTILE,
                )
            )
        )
        ceiling_value = user_input.get(CONF_ADAPTIVE_PRICE_CEILING)
        ceiling = Decimal(str(ceiling_value)) if ceiling_value is not None else None
    except InvalidOperation, ValueError:
        return False
    return (
        target.is_finite()
        and Decimal(0) < target <= Decimal(100)
        and (ceiling is None or ceiling.is_finite())
    )


def _parse_month_day_input(value: Any) -> tuple[int, int]:
    """Parse a recurring MM-DD form value."""
    month, day = str(value).split("-", maxsplit=1)
    return int(month), int(day)


def _vat_rate_field(default: float | None) -> dict[Any, Any]:
    """Offer an explicit percentage for VAT-exclusive live and forecast prices."""
    key = (
        vol.Optional(CONF_PRICE_VAT_RATE)
        if default is None
        else vol.Optional(CONF_PRICE_VAT_RATE, default=default)
    )
    return {
        key: selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=100,
                step=0.01,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="%",
            )
        ),
        **assistance_field(),
    }
