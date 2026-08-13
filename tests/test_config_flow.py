"""Tests for the Electricity Pro config flow."""

from __future__ import annotations

from homeassistant import config_entries, data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_FORECAST_CURRENCY,
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FORECAST_PRICE_AREA,
    CONF_GOOD_PRICE_THRESHOLD,
    CONF_GRID_FEE_PER_KWH,
    CONF_POWER_ENTITY,
    CONF_TAX_PER_KWH,
    DOMAIN,
)


async def test_user_step_creates_entry_with_forecast_config(hass) -> None:
    """The user step should store forecast area, currency, and Nord Pool entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_FORECAST_PRICE_AREA: "SE3",
            CONF_FORECAST_CURRENCY: "SEK",
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: "nordpool-entry-id",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Electricity Pro"
    assert result["data"][CONF_FORECAST_PRICE_AREA] == "SE3"
    assert result["data"][CONF_FORECAST_CURRENCY] == "SEK"
    assert result["data"][CONF_FORECAST_NORDPOOL_CONFIG_ENTRY] == "nordpool-entry-id"


async def test_options_flow_updates_forecast_config(hass) -> None:
    """The options flow should expose and persist forecast config."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_FORECAST_PRICE_AREA: "SE3",
            CONF_FORECAST_CURRENCY: "SEK",
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: "nordpool-entry-id",
        },
        options={
            CONF_GRID_FEE_PER_KWH: 0.1,
            CONF_TAX_PER_KWH: 0.2,
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
            CONF_FORECAST_PRICE_AREA: "SE4",
            CONF_FORECAST_CURRENCY: "EUR",
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: "other-nordpool-entry-id",
            CONF_GRID_FEE_PER_KWH: 0.1,
            CONF_TAX_PER_KWH: 0.2,
            CONF_GOOD_PRICE_THRESHOLD: 1.0,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_FORECAST_PRICE_AREA] == "SE4"
    assert result["data"][CONF_FORECAST_CURRENCY] == "EUR"
    assert result["data"][CONF_FORECAST_NORDPOOL_CONFIG_ENTRY] == "other-nordpool-entry-id"
