"""Tests for Electricity Pro insight binary sensors."""

from collections.abc import Callable
from types import CoroutineType
from typing import Any

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN

ENTITY_ID = f"binary_sensor.{DOMAIN}_good_time_to_use_electricity"


async def test_good_time_is_on_at_or_below_threshold(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Insight should be on when Effective Price equals the threshold."""
    await setup_electricity_pro(
        price_value="0.80",
        grid_fee_per_kwh=0.25,
        tax_per_kwh=0.15,
        good_price_threshold=1.20,
    )

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "on"


async def test_good_time_is_off_above_threshold(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Insight should be off when Effective Price exceeds the threshold."""
    await setup_electricity_pro(
        price_value="1.00",
        grid_fee_per_kwh=0.25,
        good_price_threshold=1.20,
    )

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "off"


async def test_good_time_updates_with_price(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Insight should update when the current price changes."""
    await setup_electricity_pro(
        price_value="1.50",
        good_price_threshold=1.00,
    )

    hass.states.async_set(
        "sensor.test_price",
        "0.75",
        {"unit_of_measurement": "SEK/kWh"},
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "on"


async def test_good_time_not_created_without_threshold(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Insight should remain opt-in."""
    await setup_electricity_pro(price_value="0.80")

    assert hass.states.get(ENTITY_ID) is None
