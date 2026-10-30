"""Characterize the existing Good Time adapter before extracting decisions."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.electricity_pro.binary_sensor import (
    evaluate_good_time,
    good_time_to_use_electricity,
)
from custom_components.electricity_pro.pricing import PriceCompleteness

_NOW = datetime(2026, 9, 7, 12, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("price", "threshold", "expected", "reason"),
    [
        ("1.00", 1.0, True, "within_fixed_threshold"),
        ("1.01", 1.0, False, "above_fixed_threshold"),
        ("-0.50", 0.0, True, "within_fixed_threshold"),
        ("unavailable", 1.0, None, "invalid_current_price"),
        ("1.00", None, None, "fixed_threshold_not_configured"),
    ],
)
async def test_fixed_adapter_exact_result(
    setup_electricity_pro, price, threshold, expected, reason,
):
    """Preserve fixed state, Decimal strings and the complete attribute shape."""
    entry = await setup_electricity_pro(
        price_value=price,
        good_price_threshold=threshold,
    )
    result = evaluate_good_time(entry.runtime_data.data, evaluation_time=_NOW)
    assert result.is_good is expected
    assert result.attributes == {
        "configured_mode": "fixed",
        "current_price": None if price == "unavailable" else str(Decimal(price)),
        "fixed_threshold": None if threshold is None else str(Decimal(str(threshold))),
        "evaluation_method": "fixed",
        "reason": reason,
    }
    assert good_time_to_use_electricity(entry.runtime_data.data) is expected


@pytest.mark.parametrize(
    ("threshold", "expected", "method", "reason"),
    [
        (1.0, True, "adaptive_fallback", "within_fixed_fallback"),
        (0.5, False, "adaptive_fallback", "above_fixed_fallback"),
        (None, None, None, "insufficient_comparable_history"),
    ],
)
async def test_adaptive_cold_start_exact_result(
    setup_electricity_pro, threshold, expected, method, reason,
):
    """Retain all fallback/unknown attributes, including withheld forecast fields."""
    entry = await setup_electricity_pro(
        price_value="0.80",
        price_completeness=PriceCompleteness.COMPLETE,
        good_price_mode="adaptive",
        good_price_threshold=threshold,
    )
    result = evaluate_good_time(
        entry.runtime_data.data,
        mode="adaptive",
        current_scope=entry.runtime_data.adaptive_price_scope,
        evaluation_time=_NOW,
    )
    threshold_text = None if threshold is None else str(Decimal(str(threshold)))
    assert result.is_good is expected
    assert result.attributes == {
        "configured_mode": "adaptive",
        "current_price": "0.80",
        "fixed_threshold": threshold_text,
        "evaluation_method": method,
        "reason": reason,
        "adaptive_threshold": threshold_text,
        "absolute_ceiling": None,
        "target_percentile": "0.25",
        "current_percentile": None,
        "cohort_type": None,
        "historical_days": 0,
        "sample_count": 0,
        "required_sample_count": 14,
        "forecast_look_ahead_hours": 6,
        "forecast_comparison_status": "not_applicable",
        "next_better_interval_start": None,
        "next_better_interval_end": None,
        "next_better_price": None,
        "forecast_price_difference": None,
        "forecast_reference_range": None,
    }


async def test_good_time_entity_identity_and_unavailable_state(
    hass, setup_electricity_pro,
):
    """An invalid fixed price retains the existing entity but makes it unavailable."""
    entry = await setup_electricity_pro(
        price_value="unavailable", good_price_threshold=1.0,
    )
    entity_id = "binary_sensor.electricity_pro_good_time_to_use_electricity"
    registered = er.async_get(hass).async_get(entity_id)
    assert registered is not None
    assert registered.unique_id == f"{entry.entry_id}_good_time_to_use_electricity"
    assert registered.config_entry_id == entry.entry_id
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"
