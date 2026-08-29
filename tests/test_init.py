"""Tests for Electricity Pro integration setup."""

from collections.abc import Callable
from datetime import UTC, datetime
from types import CoroutineType
from typing import Any
from unittest.mock import patch

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.const import ATTR_CONFIG_ENTRY_ID
from homeassistant.exceptions import ConfigEntryError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro import async_setup_entry
from custom_components.electricity_pro.const import (
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
    DOMAIN,
    SERVICE_GET_MARKET_PRICE_FORECAST,
)

ENTITY_ID = "sensor.electricity_pro_current_power"


async def test_setup_rejects_price_source_without_metadata(
    hass: HomeAssistant,
) -> None:
    """A configured price source must have explicit component semantics."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_PRICE_ENTITY: "sensor.test_price",
        },
    )

    with pytest.raises(ConfigEntryError, match="explicit pricing metadata"):
        await async_setup_entry(hass, entry)


async def test_setup_and_unload_entry(
    hass: HomeAssistant,
) -> None:
    """Test setting up and unloading Electricity Pro."""
    source_entity_id = "sensor.test_power"

    hass.states.async_set(
        source_entity_id,
        "1000",
        {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: source_entity_id,
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(ENTITY_ID) is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED

    state = hass.states.get(ENTITY_ID)

    if state is not None:
        assert state.state == "unavailable"
        assert state.attributes.get("restored") is True


async def test_get_market_price_forecast_action_returns_normalized_series(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """The response-only action should return one explicit entry's series."""
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 10, 1, tzinfo=UTC),
    ):
        entry = await setup_electricity_pro(
            forecast_price_area="SE3",
            forecast_currency="SEK",
            forecast_nordpool_config_entry="nordpool-entry-id",
            forecast_intervals=[
                {
                    "start": "2026-08-13T10:00:00+00:00",
                    "end": "2026-08-13T10:15:00+00:00",
                    "price": -50,
                },
                {
                    "start": "2026-08-13T10:15:00+00:00",
                    "end": "2026-08-13T10:30:00+00:00",
                    "price": 300,
                },
            ],
        )

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MARKET_PRICE_FORECAST,
        {ATTR_CONFIG_ENTRY_ID: entry.entry_id},
        blocking=True,
        return_response=True,
    )

    assert response is not None
    assert response["currency"] == "SEK"
    assert response["area"] == "SE3"
    assert response["intervals"] == [
        {
            "start": "2026-08-13T10:00:00+00:00",
            "end": "2026-08-13T10:15:00+00:00",
            "price": -0.05,
        },
        {
            "start": "2026-08-13T10:15:00+00:00",
            "end": "2026-08-13T10:30:00+00:00",
            "price": 0.3,
        },
    ]


async def test_get_market_price_forecast_action_requires_loaded_entry(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """The action should reject unknown and unloaded config entries."""
    entry = await setup_electricity_pro()
    await hass.config_entries.async_unload(entry.entry_id)

    with pytest.raises(ServiceValidationError, match="not loaded"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_MARKET_PRICE_FORECAST,
            {ATTR_CONFIG_ENTRY_ID: entry.entry_id},
            blocking=True,
            return_response=True,
        )


async def test_get_market_price_forecast_action_rejects_unavailable_series(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """The action should report when no normalized forecast is configured."""
    entry = await setup_electricity_pro()

    with pytest.raises(ServiceValidationError, match="unavailable"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_MARKET_PRICE_FORECAST,
            {ATTR_CONFIG_ENTRY_ID: entry.entry_id},
            blocking=True,
            return_response=True,
        )
