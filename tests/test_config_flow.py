"""Tests for the Electricity Pro config flow."""

from __future__ import annotations

from homeassistant import config_entries, data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_CURRENT_L1_ENTITY,
    CONF_CURRENT_L2_ENTITY,
    CONF_CURRENT_L3_ENTITY,
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FORECAST_PRICE_AREA,
    CONF_FIXED_SUPPLIER_FEE_MONTHLY,
    CONF_FIXED_GRID_FEE_MONTHLY,
    CONF_GOOD_PRICE_THRESHOLD,
    CONF_GRID_FEE_PER_KWH,
    CONF_GRID_FEE_HIGH_END,
    CONF_GRID_FEE_HIGH_PER_KWH,
    CONF_GRID_FEE_HIGH_SEASON_END,
    CONF_GRID_FEE_HIGH_SEASON_START,
    CONF_GRID_FEE_HIGH_START,
    CONF_POWER_ENTITY,
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_ENTITY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICING_STRATEGY,
    CONF_SETUP_METHOD,
    CONF_SOURCE_PROFILE,
    CONF_VOLTAGE_L1_ENTITY,
    CONF_VOLTAGE_L2_ENTITY,
    CONF_VOLTAGE_L3_ENTITY,
    DOMAIN,
)
from custom_components.electricity_pro.pricing import (
    PriceComponent,
    PriceCompleteness,
    PricingStrategy,
    VatTreatment,
)


async def _start_manual_flow(hass):
    """Start setup and enter the custom or mixed source path."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    return await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SETUP_METHOD: "custom"},
    )


async def test_manual_form_orders_sources_before_phase_diagnostics(hass) -> None:
    """Source selection should lead and phase diagnostics should come last."""
    result = await _start_manual_flow(hass)
    keys = [key.schema for key in result["data_schema"].schema]

    assert keys[0] == CONF_FORECAST_NORDPOOL_CONFIG_ENTRY
    assert keys[-6:] == [
        CONF_CURRENT_L1_ENTITY,
        CONF_CURRENT_L2_ENTITY,
        CONF_CURRENT_L3_ENTITY,
        CONF_VOLTAGE_L1_ENTITY,
        CONF_VOLTAGE_L2_ENTITY,
        CONF_VOLTAGE_L3_ENTITY,
    ]
    assert keys[
        keys.index(CONF_GRID_FEE_PER_KWH) + 1 : keys.index(
            CONF_FIXED_SUPPLIER_FEE_MONTHLY
        )
    ] == [
        CONF_GRID_FEE_HIGH_PER_KWH,
        CONF_GRID_FEE_HIGH_START,
        CONF_GRID_FEE_HIGH_END,
        CONF_GRID_FEE_HIGH_SEASON_START,
        CONF_GRID_FEE_HIGH_SEASON_END,
        CONF_FIXED_GRID_FEE_MONTHLY,
    ]


async def test_user_step_creates_entry_with_forecast_config(hass) -> None:
    """A single-area Nord Pool entry should need no duplicate settings."""
    nordpool_entry = MockConfigEntry(
        domain="nordpool",
        title="Nord Pool",
        data={"areas": ["SE3"], "currency": "SEK"},
        entry_id="nordpool-entry-id",
    )
    nordpool_entry.add_to_hass(hass)
    result = await _start_manual_flow(hass)

    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: "nordpool-entry-id",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Electricity Pro"
    assert CONF_FORECAST_PRICE_AREA not in result["data"]
    assert result["data"][CONF_FORECAST_NORDPOOL_CONFIG_ENTRY] == "nordpool-entry-id"


async def test_manual_flow_rejects_invalid_grid_tariff_schedule(hass) -> None:
    """A high tariff should require a valid low fee and schedule."""
    result = await _start_manual_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_GRID_FEE_HIGH_PER_KWH: 0.25,
            CONF_GRID_FEE_HIGH_START: "not-a-time",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_grid_tariff"}


async def test_user_step_asks_for_area_for_multi_area_nordpool_entry(hass) -> None:
    """A multi-area Nord Pool entry should require one area selection."""
    nordpool_entry = MockConfigEntry(
        domain="nordpool",
        title="Nord Pool",
        data={"areas": ["SE3", "SE4"], "currency": "SEK"},
        entry_id="nordpool-entry-id",
    )
    nordpool_entry.add_to_hass(hass)

    result = await _start_manual_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: "nordpool-entry-id",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "forecast_area"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_FORECAST_PRICE_AREA: "SE4"},
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_FORECAST_PRICE_AREA] == "SE4"


async def test_options_flow_updates_forecast_config(hass) -> None:
    """The options flow should persist only the selected Nord Pool entry."""
    nordpool_entry = MockConfigEntry(
        domain="nordpool",
        title="Nord Pool",
        data={"areas": ["SE4"], "currency": "EUR"},
        entry_id="other-nordpool-entry-id",
    )
    nordpool_entry.add_to_hass(hass)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_FORECAST_PRICE_AREA: "SE3",
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: "nordpool-entry-id",
        },
        options={
            CONF_GRID_FEE_PER_KWH: 0.1,
            CONF_GOOD_PRICE_THRESHOLD: 1.0,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: "other-nordpool-entry-id",
            CONF_GRID_FEE_PER_KWH: 0.1,
            CONF_GOOD_PRICE_THRESHOLD: 1.0,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert CONF_FORECAST_PRICE_AREA not in result["data"]
    assert result["data"][CONF_FORECAST_NORDPOOL_CONFIG_ENTRY] == "other-nordpool-entry-id"


async def test_tibber_options_reject_invalid_grid_tariff_time(hass) -> None:
    """Tibber options must reject an invalid saved schedule time."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_SOURCE_PROFILE: "tibber",
        },
        options={
            CONF_GRID_FEE_PER_KWH: 0.125,
            CONF_GRID_FEE_HIGH_PER_KWH: 0.25,
        },
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_GRID_FEE_PER_KWH: 0.125,
            CONF_GRID_FEE_HIGH_PER_KWH: 0.25,
            CONF_GRID_FEE_HIGH_START: "abc",
            CONF_GRID_FEE_HIGH_END: "22:00",
            CONF_GRID_FEE_HIGH_SEASON_START: "11-01",
            CONF_GRID_FEE_HIGH_SEASON_END: "03-31",
            CONF_GOOD_PRICE_THRESHOLD: 0.9,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_grid_tariff"}


async def test_tibber_options_reject_invalid_time_without_high_fee(hass) -> None:
    """Visible schedule fields must be valid even before a high fee is enabled."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_SOURCE_PROFILE: "tibber",
        },
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_GRID_FEE_HIGH_START: "abc",
            CONF_GRID_FEE_HIGH_END: "22:00",
            CONF_GRID_FEE_HIGH_SEASON_START: "11-01",
            CONF_GRID_FEE_HIGH_SEASON_END: "03-31",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_grid_tariff"}


async def test_user_step_requires_explicit_price_metadata(hass) -> None:
    """A new entry with a price source must describe what the price includes."""
    result = await _start_manual_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_PRICE_ENTITY: "sensor.test_price",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "pricing_metadata_required"}


async def test_user_step_stores_explicit_price_metadata(hass) -> None:
    """A complete price declaration should be normalized and persisted."""
    result = await _start_manual_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_PRICE_ENTITY: "sensor.test_price",
            CONF_PRICING_STRATEGY: PricingStrategy.SUPPLIER_CONTRACTED_PRICE.value,
            CONF_PRICE_INCLUDED_COMPONENTS: [
                PriceComponent.SUPPLIER_MARKUP.value,
                PriceComponent.MARKET_ENERGY.value,
                PriceComponent.ENERGY_TAX.value,
            ],
            CONF_PRICE_VAT_TREATMENT: VatTreatment.INCLUDED.value,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PRICE_INCLUDED_COMPONENTS] == [
        PriceComponent.ENERGY_TAX.value,
        PriceComponent.MARKET_ENERGY.value,
        PriceComponent.SUPPLIER_MARKUP.value,
    ]
    assert result["data"][CONF_PRICE_COMPLETENESS] == PriceCompleteness.PARTIAL.value


async def test_legacy_options_require_confirmation_only_when_saved(hass) -> None:
    """A legacy entry loads but cannot be saved with ambiguous price semantics."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_PRICE_ENTITY: "sensor.test_price",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_PRICE_ENTITY: "sensor.test_price",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "pricing_metadata_required"}
