"""Direct tests for Good Time decisions without a Home Assistant fixture."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from custom_components.electricity_pro.adaptive_price import (
    AdaptivePriceScope,
    HistoricalPriceObservation,
)
from custom_components.electricity_pro.good_time import evaluate_good_time
from custom_components.electricity_pro.pricing import PriceCompleteness, VatTreatment

_NOW = datetime(2026, 9, 7, 12, 30, tzinfo=UTC)
_SCOPE = AdaptivePriceScope(
    currency="SEK",
    unit="SEK/kWh",
    components=frozenset(),
    vat=VatTreatment.INCLUDED,
    completeness=PriceCompleteness.COMPLETE,
    tariff_signature="test-tariff",
)


@pytest.mark.parametrize(
    ("price", "threshold", "expected", "reason"),
    [
        ("1.00", "1.00", True, "within_fixed_threshold"),
        ("1.01", "1.00", False, "above_fixed_threshold"),
        ("-0.50", "0", True, "within_fixed_threshold"),
        (None, "1.00", None, "invalid_current_price"),
        ("1.00", None, None, "fixed_threshold_not_configured"),
    ],
)
def test_fixed_decision(price, threshold, expected, reason) -> None:
    """Normalized inputs retain Decimal boundaries and unknown states."""
    result = evaluate_good_time(
        effective_price=Decimal(price) if price is not None else None,
        fixed_threshold=Decimal(threshold) if threshold is not None else None,
        evaluation_time=_NOW,
    )
    assert result.is_good is expected
    assert result.attributes["reason"] == reason
    assert result.attributes["current_price"] == price
    assert result.attributes["fixed_threshold"] == threshold


@pytest.mark.parametrize(
    ("configured", "available", "comparable", "status"),
    [
        (False, False, False, "not_configured"),
        (True, False, False, "withheld_unavailable"),
        (True, True, False, "withheld_incompatible"),
    ],
)
def test_forecast_gates_preserve_historical_decision(
    configured, available, comparable, status
) -> None:
    """Missing or incompatible forecasts cannot overturn a valid good price."""
    observations = tuple(
        HistoricalPriceObservation(
            start=_NOW.replace(minute=0) - timedelta(days=days),
            end=_NOW.replace(minute=0) - timedelta(days=days) + timedelta(hours=1),
            effective_price=Decimal("1.00"),
            covered_duration=timedelta(hours=1),
            scope=_SCOPE,
        )
        for days in range(1, 29)
    )
    result = evaluate_good_time(
        effective_price=Decimal("0.80"),
        fixed_threshold=None,
        evaluation_time=_NOW,
        mode="adaptive",
        observations=observations,
        current_scope=_SCOPE,
        forecast_configured=configured,
        forecast_available=available,
        forecast_prices_comparable=comparable,
    )
    assert result.is_good is True
    assert result.attributes["evaluation_method"] == "adaptive"
    assert result.attributes["forecast_comparison_status"] == status
    assert result.attributes["next_better_price"] is None
    assert all(item.effective_price == Decimal("1.00") for item in observations)


def test_explicit_inputs_produce_independent_repeatable_results() -> None:
    """Repeated evaluation does not share mutable explanation dictionaries."""
    inputs = dict(
        effective_price=Decimal("0.80"),
        fixed_threshold=Decimal("1.00"),
        evaluation_time=_NOW,
        mode="adaptive",
        current_scope=_SCOPE,
    )
    first = evaluate_good_time(**inputs)
    second = evaluate_good_time(**inputs)
    assert first == second
    assert first.attributes is not second.attributes
    first.attributes["reason"] = "changed by caller"
    assert second.attributes["reason"] == "within_fixed_fallback"
