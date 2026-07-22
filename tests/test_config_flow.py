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
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_options_flow_shows_existing_sources(
    hass: HomeAssistant,
) -> None:
    """Options flow should suggest the currently configured sources."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.old_power",
            CONF_PRICE_ENTITY: "sensor.old_price",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(
        entry.entry_id
    )

    assert result["type"] == "form"
    assert result["step_id"] == "init"

    schema = result["data_schema"]
    assert schema(
        {
            CONF_POWER_ENTITY: "sensor.old_power",
            CONF_PRICE_ENTITY: "sensor.old_price",
        }
    ) == {
        CONF_POWER_ENTITY: "sensor.old_power",
        CONF_PRICE_ENTITY: "sensor.old_price",
    }


async def test_options_flow_updates_sources(
    hass: HomeAssistant,
) -> None:
    """Options flow should save updated source entities."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.old_power",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(
        entry.entry_id
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "sensor.new_power",
            CONF_PRICE_ENTITY: "sensor.new_price",
        },
    )

    assert result["type"] == "create_entry"
    assert entry.options == {
        CONF_POWER_ENTITY: "sensor.new_power",
        CONF_PRICE_ENTITY: "sensor.new_price",
    }
