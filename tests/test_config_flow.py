"""Tests for the Electricity Pro config flow."""

from __future__ import annotations

from homeassistant import data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_FORECAST_CURRENCY,
    CONF_FORECAST_PRICE_AREA,
    CONF_GOOD_PRICE_THRESHOLD,
    CONF_GRID_FEE_PER_KWH,
    CONF_POWER_ENTITY,
    CONF_TAX_PER_KWH,
    DOMAIN,
)


async def test_user_step_creates_entry_with_forecast_config(hass) -> None:
    """The user step should store forecast area and currency."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": data_entry_flow.SOURCE_USER},
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_FORECAST_PRICE_AREA: "SE3",
            CONF_FORECAST_CURRENCY: "SEK",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Electricity Pro"
    assert result["data"][CONF_FORECAST_PRICE_AREA] == "SE3"
    assert result["data"][CONF_FORECAST_CURRENCY] == "SEK"


async def test_options_flow_updates_forecast_config(hass) -> None:
    """The options flow should expose and persist forecast area and currency."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_FORECAST_PRICE_AREA: "SE3",
            CONF_FORECAST_CURRENCY: "SEK",
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
            CONF_GRID_FEE_PER_KWH: 0.1,
            CONF_TAX_PER_KWH: 0.2,
            CONF_GOOD_PRICE_THRESHOLD: 1.0,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_FORECAST_PRICE_AREA] == "SE4"
    assert result["data"][CONF_FORECAST_CURRENCY] == "EUR"
