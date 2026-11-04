"""Tests for Electricity Pro insight binary sensors."""

from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from types import CoroutineType
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.adaptive_price import (
    AdaptiveForecastPrice,
    HistoricalPriceObservation,
)
from custom_components.electricity_pro.binary_sensor import (
    _optional_decimal,
    _percentile_setting,
    evaluate_good_time,
)
from custom_components.electricity_pro.const import (
    DOMAIN,
    GOOD_PRICE_MODE_ADAPTIVE,
)
from custom_components.electricity_pro.pricing import PriceCompleteness

ENTITY_ID = f"binary_sensor.{DOMAIN}_good_time_to_use_electricity"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("1.25", Decimal("1.25")),
        (0, Decimal(0)),
        (-1.5, Decimal("-1.5")),
        (Decimal("2.5"), Decimal("2.5")),
        ("NaN", None),
        (float("inf"), None),
        (True, None),
        ([], None),
        ({}, None),
        ("invalid", None),
    ],
)
def test_optional_numeric_setting_contract(
    value: object, expected: Decimal | None
) -> None:
    """Loose settings retain finite numeric conversion and invalid fallback."""
    assert _optional_decimal(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("50", Decimal("0.5")),
        (100, Decimal(1)),
        (Decimal("0.5"), Decimal("0.005")),
        (None, Decimal("0.25")),
        (0, Decimal("0.25")),
        (-1, Decimal("0.25")),
        (101, Decimal("0.25")),
        ("NaN", Decimal("0.25")),
        ({}, Decimal("0.25")),
    ],
)
def test_percentile_setting_contract(value: object, expected: Decimal) -> None:
    """Percentages keep their existing range and default behaviour."""
    assert _percentile_setting(value) == expected


async def test_good_time_is_on_at_or_below_threshold(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Insight should be on when Effective Price equals the threshold."""
    await setup_electricity_pro(
        price_value="0.80",
        grid_fee_per_kwh=0.25,
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


async def test_good_time_accepts_negative_effective_price(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A negative price is valid and should compare below the threshold."""
    await setup_electricity_pro(
        price_value="-0.50",
        grid_fee_per_kwh=0.20,
        good_price_threshold=0.00,
    )

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "on"


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


async def test_fixed_good_time_explains_legacy_evaluation(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Existing threshold-only setups should remain fixed and explainable."""
    await setup_electricity_pro(
        price_value="0.80",
        good_price_threshold=1.00,
    )

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "on"
    assert state.attributes["configured_mode"] == "fixed"
    assert state.attributes["evaluation_method"] == "fixed"
    assert state.attributes["reason"] == "within_fixed_threshold"
    assert state.attributes["fixed_threshold"] == "1.0"


async def test_adaptive_good_time_uses_fixed_threshold_during_cold_start(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Adaptive mode should remain useful while comparable history builds."""
    await setup_electricity_pro(
        price_value="0.80",
        price_completeness=PriceCompleteness.COMPLETE,
        good_price_mode=GOOD_PRICE_MODE_ADAPTIVE,
        good_price_threshold=1.00,
        adaptive_target_percentile=25,
    )

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "on"
    assert state.attributes["configured_mode"] == "adaptive"
    assert state.attributes["evaluation_method"] == "adaptive_fallback"
    assert state.attributes["reason"] == "within_fixed_fallback"
    assert state.attributes["sample_count"] == 0
    assert state.attributes["target_percentile"] == "0.25"


async def test_adaptive_good_time_is_unavailable_without_history_or_fallback(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Adaptive mode should state why a cold start cannot be classified."""
    await setup_electricity_pro(
        price_value="0.80",
        price_completeness=PriceCompleteness.COMPLETE,
        good_price_mode=GOOD_PRICE_MODE_ADAPTIVE,
    )

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "unknown"
    assert state.attributes["configured_mode"] == "adaptive"
    assert state.attributes["reason"] == "insufficient_comparable_history"
    assert state.attributes["required_sample_count"] == 14


async def test_adaptive_good_time_rejects_partial_current_price(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Adaptive comparisons must not mix incomplete price semantics."""
    await setup_electricity_pro(
        price_value="0.80",
        good_price_mode=GOOD_PRICE_MODE_ADAPTIVE,
        good_price_threshold=1.00,
    )

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "unknown"
    assert state.attributes["reason"] == "incompatible_current_price"


async def test_adaptive_good_time_explains_withheld_native_forecast(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Partial native Nord Pool data must never suppress adaptive advice."""
    entry = await setup_electricity_pro(
        price_value="0.60",
        price_completeness=PriceCompleteness.COMPLETE,
        good_price_mode=GOOD_PRICE_MODE_ADAPTIVE,
        forecast_price_area="SE3",
        forecast_currency="SEK",
        forecast_nordpool_config_entry="nordpool-entry-id",
        forecast_intervals=[
            {
                "start": "2026-09-07T14:00:00+00:00",
                "end": "2026-09-07T15:00:00+00:00",
                "price": 200,
            }
        ],
    )
    evaluation_time = datetime(2026, 9, 7, 12, 30, tzinfo=UTC)
    scope = entry.runtime_data.adaptive_price_scope
    assert scope is not None
    observations = tuple(
        HistoricalPriceObservation(
            start=datetime.combine(
                (evaluation_time - timedelta(days=day)).date(),
                time(12),
                tzinfo=UTC,
            ),
            end=datetime.combine(
                (evaluation_time - timedelta(days=day)).date(),
                time(13),
                tzinfo=UTC,
            ),
            effective_price=Decimal("0.60"),
            covered_duration=timedelta(hours=1),
            scope=scope,
        )
        for day in range(1, 29)
    )

    result = evaluate_good_time(
        entry.runtime_data.data,
        mode=GOOD_PRICE_MODE_ADAPTIVE,
        observations=observations,
        current_scope=scope,
        evaluation_time=evaluation_time,
        forecast_configured=True,
        forecast_available=True,
        forecast_prices_comparable=False,
    )

    assert result.is_good is True
    assert result.attributes["forecast_comparison_status"] == "withheld_incompatible"


async def test_adaptive_good_time_reports_forecast_suppression(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """The public evaluation should expose the materially better interval."""
    entry = await setup_electricity_pro(
        price_value="0.60",
        price_completeness=PriceCompleteness.COMPLETE,
        good_price_mode=GOOD_PRICE_MODE_ADAPTIVE,
    )
    evaluation_time = datetime(2026, 9, 7, 12, 30, tzinfo=UTC)
    scope = entry.runtime_data.adaptive_price_scope
    assert scope is not None
    observations = tuple(
        HistoricalPriceObservation(
            start=datetime.combine(
                (evaluation_time - timedelta(days=day)).date(),
                time(hour),
                tzinfo=UTC,
            ),
            end=datetime.combine(
                (evaluation_time - timedelta(days=day)).date(),
                time(hour),
                tzinfo=UTC,
            )
            + timedelta(hours=1),
            effective_price=Decimal(price),
            covered_duration=timedelta(hours=1),
            scope=scope,
        )
        for hour, price in ((12, "0.60"), (14, "0.20"), (16, "0.00"), (18, "1.00"))
        for day in range(1, 29)
    )
    future = AdaptiveForecastPrice(
        start=evaluation_time.replace(hour=14, minute=0),
        end=evaluation_time.replace(hour=15, minute=0),
        effective_price=Decimal("0.20"),
        scope=scope,
    )

    result = evaluate_good_time(
        entry.runtime_data.data,
        mode=GOOD_PRICE_MODE_ADAPTIVE,
        observations=observations,
        current_scope=scope,
        evaluation_time=evaluation_time,
        forecast_prices=(future,),
        forecast_configured=True,
        forecast_available=True,
        forecast_prices_comparable=True,
    )

    assert result.is_good is False
    assert result.attributes["reason"] == "better_price_forecast"
    assert result.attributes["forecast_comparison_status"] == "suppressed"
    assert result.attributes["next_better_price"] == "0.20"
