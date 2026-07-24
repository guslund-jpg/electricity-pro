"""Tests for Electricity Pro calculations."""

from custom_components.electricity_pro.calculations import (
    calculate_current_cost_rate,
)


def test_calculate_current_cost_rate() -> None:
    """Current cost rate should use power and price."""
    result = calculate_current_cost_rate(
        power_w=2400,
        price_per_kwh=1.80,
    )

    assert result == 4.32


def test_calculate_current_cost_rate_with_zero_power() -> None:
    """Zero power should result in zero cost."""
    result = calculate_current_cost_rate(
        power_w=0,
        price_per_kwh=1.80,
    )

    assert result == 0


def test_calculate_current_cost_rate_with_zero_price() -> None:
    """Zero price should result in zero cost."""
    result = calculate_current_cost_rate(
        power_w=2400,
        price_per_kwh=0,
    )

    assert result == 0


def test_calculate_current_cost_rate_without_power() -> None:
    """Unavailable power should result in an unavailable calculation."""
    result = calculate_current_cost_rate(
        power_w=None,
        price_per_kwh=1.80,
    )

    assert result is None


def test_calculate_current_cost_rate_without_price() -> None:
    """Unavailable price should result in an unavailable calculation."""
    result = calculate_current_cost_rate(
        power_w=2400,
        price_per_kwh=None,
    )

    assert result is None


def test_calculate_current_cost_rate_rejects_negative_power() -> None:
    """Negative power should not produce a cost rate."""
    result = calculate_current_cost_rate(
        power_w=-100,
        price_per_kwh=1.80,
    )

    assert result is None


def test_calculate_current_cost_rate_rejects_negative_price() -> None:
    """Negative prices should not produce a cost rate."""
    result = calculate_current_cost_rate(
        power_w=2400,
        price_per_kwh=-0.25,
    )

    assert result is None
