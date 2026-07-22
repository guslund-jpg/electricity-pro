"""Tests for the Electricity Pro config flow."""

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.electricity_pro.const import (
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
    DOMAIN,
)


async def test_user_flow_power_only(hass: HomeAssistant) -> None:
    """Create an entry with only a power sensor."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] == "form"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "sensor.power",
        },
    )

    assert result["type"] == "create_entry"

    assert result["data"] == {
        CONF_POWER_ENTITY: "sensor.power",
    }


async def test_user_flow_power_and_price(
    hass: HomeAssistant,
) -> None:
    """Create an entry with both power and price sensors."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "sensor.power",
            CONF_PRICE_ENTITY: "sensor.price",
        },
    )

    assert result["type"] == "create_entry"

    assert result["data"] == {
        CONF_POWER_ENTITY: "sensor.power",
        CONF_PRICE_ENTITY: "sensor.price",
    }
