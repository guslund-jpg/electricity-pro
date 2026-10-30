"""Pure fixed/adaptive Good Time decisions over explicit normalized inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .adaptive_price import (
    AdaptiveEvaluationMethod,
    AdaptiveForecastPrice,
    AdaptivePriceReason,
    AdaptivePriceScope,
    ForecastComparisonStatus,
    HistoricalPriceObservation,
    evaluate_adaptive_forecast,
    evaluate_adaptive_good_price,
)

GOOD_PRICE_MODE_FIXED = "fixed"
GOOD_PRICE_MODE_ADAPTIVE = "adaptive"


@dataclass(frozen=True, slots=True)
class GoodTimeEvaluation:
    """Explain one fixed or adaptive Good Time evaluation."""

    is_good: bool | None
    attributes: dict[str, str | int | None]


def evaluate_good_time(
    *,
    effective_price: Decimal | None,
    fixed_threshold: Decimal | None,
    evaluation_time: datetime,
    mode: str = GOOD_PRICE_MODE_FIXED,
    observations: tuple[HistoricalPriceObservation, ...] = (),
    current_scope: AdaptivePriceScope | None = None,
    target_percentile: Decimal = Decimal("0.25"),
    absolute_ceiling: Decimal | None = None,
    forecast_prices: tuple[AdaptiveForecastPrice, ...] = (),
    forecast_configured: bool = False,
    forecast_available: bool = False,
    forecast_prices_comparable: bool = False,
) -> GoodTimeEvaluation:
    """Evaluate normalized inputs without HA state, persistence or a clock read."""
    common_attributes: dict[str, str | int | None] = {
        "configured_mode": mode,
        "current_price": _decimal_attribute(effective_price),
        "fixed_threshold": _decimal_attribute(fixed_threshold),
    }
    if mode != GOOD_PRICE_MODE_ADAPTIVE:
        if effective_price is None:
            return GoodTimeEvaluation(
                is_good=None,
                attributes={
                    **common_attributes,
                    "evaluation_method": GOOD_PRICE_MODE_FIXED,
                    "reason": AdaptivePriceReason.INVALID_CURRENT_PRICE.value,
                },
            )
        if fixed_threshold is None:
            return GoodTimeEvaluation(
                is_good=None,
                attributes={
                    **common_attributes,
                    "evaluation_method": GOOD_PRICE_MODE_FIXED,
                    "reason": "fixed_threshold_not_configured",
                },
            )
        is_good = effective_price <= fixed_threshold
        return GoodTimeEvaluation(
            is_good=is_good,
            attributes={
                **common_attributes,
                "evaluation_method": GOOD_PRICE_MODE_FIXED,
                "reason": (
                    "within_fixed_threshold"
                    if is_good
                    else "above_fixed_threshold"
                ),
            },
        )

    adaptive = evaluate_adaptive_good_price(
        current_price=effective_price,
        current_scope=current_scope,
        observations=observations,
        evaluation_time=evaluation_time,
        target_percentile=target_percentile,
        fixed_fallback=fixed_threshold,
        absolute_ceiling=absolute_ceiling,
    )
    forecast_status = ForecastComparisonStatus.NOT_APPLICABLE
    forecast = None
    if (
        adaptive.method is AdaptiveEvaluationMethod.ADAPTIVE
        and adaptive.is_good is True
    ):
        if not forecast_configured:
            forecast_status = ForecastComparisonStatus.NOT_CONFIGURED
        elif not forecast_available:
            forecast_status = ForecastComparisonStatus.WITHHELD_UNAVAILABLE
        elif not forecast_prices_comparable:
            forecast_status = ForecastComparisonStatus.WITHHELD_INCOMPATIBLE
        elif effective_price is not None and current_scope is not None:
            forecast = evaluate_adaptive_forecast(
                current_result=adaptive,
                current_price=effective_price,
                current_scope=current_scope,
                observations=observations,
                forecast_prices=forecast_prices,
                evaluation_time=evaluation_time,
                target_percentile=target_percentile,
                absolute_ceiling=absolute_ceiling,
            )
            forecast_status = forecast.status

    adaptive_is_good = False if forecast is not None and forecast.suppress else adaptive.is_good
    reason = (
        AdaptivePriceReason.BETTER_PRICE_FORECAST
        if forecast is not None and forecast.suppress
        else adaptive.reason
    )
    return GoodTimeEvaluation(
        is_good=adaptive_is_good,
        attributes={
            **common_attributes,
            "evaluation_method": (
                adaptive.method.value if adaptive.method is not None else None
            ),
            "reason": reason.value,
            "adaptive_threshold": _decimal_attribute(adaptive.threshold),
            "absolute_ceiling": _decimal_attribute(absolute_ceiling),
            "target_percentile": _decimal_attribute(target_percentile),
            "current_percentile": _decimal_attribute(adaptive.current_percentile),
            "cohort_type": (
                adaptive.cohort_type.value
                if adaptive.cohort_type is not None
                else None
            ),
            "historical_days": adaptive.historical_days,
            "sample_count": adaptive.sample_count,
            "required_sample_count": adaptive.required_sample_count,
            "forecast_look_ahead_hours": 6,
            "forecast_comparison_status": forecast_status.value,
            "next_better_interval_start": (
                forecast.interval.start.isoformat()
                if forecast is not None and forecast.interval is not None
                else None
            ),
            "next_better_interval_end": (
                forecast.interval.end.isoformat()
                if forecast is not None and forecast.interval is not None
                else None
            ),
            "next_better_price": (
                _decimal_attribute(forecast.interval.effective_price)
                if forecast is not None and forecast.interval is not None
                else None
            ),
            "forecast_price_difference": (
                _decimal_attribute(forecast.price_difference)
                if forecast is not None
                else None
            ),
            "forecast_reference_range": (
                _decimal_attribute(forecast.reference_range)
                if forecast is not None
                else None
            ),
        },
    )


def _decimal_attribute(value: Decimal | None) -> str | None:
    """Serialize a Decimal for stable Home Assistant attributes."""
    return str(value) if value is not None else None
