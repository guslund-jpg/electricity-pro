"""Tests for pure adaptive good-price calculations."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

import pytest

from custom_components.electricity_pro.adaptive_price import (
    AdaptiveCohortType,
    AdaptiveEvaluationMethod,
    AdaptivePriceReason,
    AdaptivePriceScope,
    HistoricalPriceObservation,
    evaluate_adaptive_good_price,
    recency_weight,
    weighted_midrank,
    weighted_quantile,
)
from custom_components.electricity_pro.pricing import (
    PriceCompleteness,
    PriceComponent,
    PriceComponentScope,
    PricingMetadata,
    PricingStrategy,
    VatTreatment,
)

_EVALUATION_TIME = datetime(2026, 9, 7, 12, 30, tzinfo=UTC)
_COMPLETE_METADATA = PricingMetadata(
    strategy=PricingStrategy.MARKET_PRICE_PLUS_TARIFF,
    scope=PriceComponentScope(
        frozenset(
            {
                PriceComponent.MARKET_ENERGY,
                PriceComponent.SUPPLIER_MARKUP,
                PriceComponent.ENERGY_TAX,
                PriceComponent.VARIABLE_GRID_FEE,
            }
        ),
        vat=VatTreatment.INCLUDED,
    ),
    completeness=PriceCompleteness.COMPLETE,
)
_SCOPE = AdaptivePriceScope.from_metadata(
    currency="SEK",
    unit="SEK/kWh",
    metadata=_COMPLETE_METADATA,
    tariff_signature="tariff-v1",
)


def _observation(
    days_ago: int,
    price: str,
    *,
    hour: int = 12,
    coverage_minutes: int = 60,
    scope: AdaptivePriceScope = _SCOPE,
) -> HistoricalPriceObservation:
    """Create one prior local-hour observation in UTC."""
    local_date = (_EVALUATION_TIME - timedelta(days=days_ago)).date()
    start = datetime.combine(local_date, time(hour), tzinfo=UTC)
    return HistoricalPriceObservation(
        start=start,
        end=start + timedelta(hours=1),
        effective_price=Decimal(price),
        covered_duration=timedelta(minutes=coverage_minutes),
        scope=scope,
    )


def _four_weeks(
    *,
    weekday_price: str = "1.00",
    weekend_price: str = "2.00",
) -> tuple[HistoricalPriceObservation, ...]:
    """Create four complete weeks of observations for the evaluation hour."""
    return tuple(
        _observation(
            days_ago,
            weekend_price
            if (_EVALUATION_TIME - timedelta(days=days_ago)).weekday() >= 5
            else weekday_price,
        )
        for days_ago in range(1, 29)
    )


@pytest.mark.parametrize(
    ("age_days", "expected"),
    [(0, "1"), (7, "0.5"), (14, "0.25"), (28, "0.0625")],
)
def test_recency_weight_has_seven_day_half_life(
    age_days: int,
    expected: str,
) -> None:
    """Every seven local days should halve an observation's influence."""
    assert recency_weight(age_days) == Decimal(expected)


def test_weighted_quantile_uses_cumulative_weight_without_interpolation() -> None:
    """The threshold should be an observed price at the weighted boundary."""
    prices = (
        (Decimal("-0.20"), Decimal(1)),
        (Decimal("0.10"), Decimal(1)),
        (Decimal("0.80"), Decimal(6)),
    )

    assert weighted_quantile(prices, Decimal("0.25")) == Decimal("0.10")


def test_weighted_midrank_groups_tied_prices() -> None:
    """Tied prices should share the midpoint of their combined weight."""
    prices = (
        (Decimal("0.10"), Decimal(1)),
        (Decimal("0.50"), Decimal(2)),
        (Decimal("0.50"), Decimal(1)),
    )

    assert weighted_midrank(prices, Decimal("0.50")) == Decimal("0.625")


def test_weekday_evaluation_prefers_matching_day_type() -> None:
    """Four weeks provide a populated same-hour weekday cohort."""
    result = evaluate_adaptive_good_price(
        current_price=Decimal("1.00"),
        current_scope=_SCOPE,
        observations=_four_weeks(weekday_price="1.00", weekend_price="0.10"),
        evaluation_time=_EVALUATION_TIME,
    )

    assert result.is_good is True
    assert result.method is AdaptiveEvaluationMethod.ADAPTIVE
    assert result.reason is AdaptivePriceReason.WITHIN_ADAPTIVE_THRESHOLD
    assert result.cohort_type is AdaptiveCohortType.SAME_HOUR_AND_DAY_TYPE
    assert result.threshold == Decimal("1.00")
    assert result.sample_count == 20
    assert result.required_sample_count == 8


def test_weekend_evaluation_has_four_weekend_pairs() -> None:
    """Four retained weeks should supply eight weekend observations."""
    evaluation_time = datetime(2026, 9, 6, 12, 30, tzinfo=UTC)
    observations = tuple(
        HistoricalPriceObservation(
            start=datetime.combine(
                (evaluation_time - timedelta(days=days_ago)).date(),
                time(12),
                tzinfo=UTC,
            ),
            end=datetime.combine(
                (evaluation_time - timedelta(days=days_ago)).date(),
                time(13),
                tzinfo=UTC,
            ),
            effective_price=Decimal("0.50"),
            covered_duration=timedelta(hours=1),
            scope=_SCOPE,
        )
        for days_ago in range(1, 29)
    )

    result = evaluate_adaptive_good_price(
        current_price=Decimal("0.50"),
        current_scope=_SCOPE,
        observations=observations,
        evaluation_time=evaluation_time,
    )

    assert result.cohort_type is AdaptiveCohortType.SAME_HOUR_AND_DAY_TYPE
    assert result.sample_count == 8


def test_same_hour_fallback_is_used_before_day_type_cohort_is_ready() -> None:
    """Fourteen mixed days should enable the less-specific cohort."""
    evaluation_time = datetime(2026, 9, 6, 12, 30, tzinfo=UTC)
    observations = tuple(
        HistoricalPriceObservation(
            start=datetime.combine(
                (evaluation_time - timedelta(days=days_ago)).date(),
                time(12),
                tzinfo=UTC,
            ),
            end=datetime.combine(
                (evaluation_time - timedelta(days=days_ago)).date(),
                time(13),
                tzinfo=UTC,
            ),
            effective_price=Decimal("0.50"),
            covered_duration=timedelta(hours=1),
            scope=_SCOPE,
        )
        for days_ago in range(1, 15)
    )

    result = evaluate_adaptive_good_price(
        current_price=Decimal("0.50"),
        current_scope=_SCOPE,
        observations=observations,
        evaluation_time=evaluation_time,
    )

    assert result.cohort_type is AdaptiveCohortType.SAME_HOUR
    assert result.sample_count == 14
    assert result.required_sample_count == 14


@pytest.mark.parametrize(
    ("current_price", "expected", "reason"),
    [
        ("0.75", True, AdaptivePriceReason.WITHIN_FIXED_FALLBACK),
        ("1.25", False, AdaptivePriceReason.ABOVE_FIXED_FALLBACK),
    ],
)
def test_fixed_threshold_is_explicit_cold_start_fallback(
    current_price: str,
    expected: bool,
    reason: AdaptivePriceReason,
) -> None:
    """Adaptive warm-up should retain a useful, explained fixed rule."""
    result = evaluate_adaptive_good_price(
        current_price=Decimal(current_price),
        current_scope=_SCOPE,
        observations=tuple(_observation(day, "0.50") for day in range(1, 8)),
        evaluation_time=_EVALUATION_TIME,
        fixed_fallback=Decimal("1.00"),
    )

    assert result.is_good is expected
    assert result.method is AdaptiveEvaluationMethod.ADAPTIVE_FALLBACK
    assert result.reason is reason
    assert result.threshold == Decimal("1.00")
    assert result.sample_count == 7
    assert result.required_sample_count == 14


def test_cold_start_without_fixed_fallback_is_unavailable() -> None:
    """An undersized cohort must not silently change the adaptive method."""
    result = evaluate_adaptive_good_price(
        current_price=Decimal("0.50"),
        current_scope=_SCOPE,
        observations=(),
        evaluation_time=_EVALUATION_TIME,
    )

    assert result.is_good is None
    assert result.method is None
    assert result.reason is AdaptivePriceReason.INSUFFICIENT_COMPARABLE_HISTORY


def test_absolute_ceiling_overrides_relative_good_price() -> None:
    """A relatively favourable but objectively high price can be rejected."""
    result = evaluate_adaptive_good_price(
        current_price=Decimal("2.00"),
        current_scope=_SCOPE,
        observations=_four_weeks(weekday_price="2.00"),
        evaluation_time=_EVALUATION_TIME,
        absolute_ceiling=Decimal("1.50"),
    )

    assert result.is_good is False
    assert result.reason is AdaptivePriceReason.ABOVE_ABSOLUTE_CEILING
    assert result.threshold == Decimal("2.00")


def test_negative_prices_are_ranked_normally() -> None:
    """Signed prices should require no special classification branch."""
    observations = tuple(
        _observation(day, "-0.25" if day <= 7 else "0.50") for day in range(1, 29)
    )

    result = evaluate_adaptive_good_price(
        current_price=Decimal("-0.30"),
        current_scope=_SCOPE,
        observations=observations,
        evaluation_time=_EVALUATION_TIME,
    )

    assert result.is_good is True
    assert result.current_percentile == Decimal(0)


def test_recent_prices_can_move_threshold_without_discarding_four_weeks() -> None:
    """The half-life should let a recent regime outweigh older observations."""
    weekday_days = tuple(
        day
        for day in range(1, 29)
        if (_EVALUATION_TIME - timedelta(days=day)).weekday() < 5
    )
    recent_weekdays = frozenset(weekday_days[:4])
    observations = tuple(
        _observation(
            day,
            "0.50" if day in recent_weekdays else "2.00",
        )
        for day in range(1, 29)
    )

    result = evaluate_adaptive_good_price(
        current_price=Decimal("0.50"),
        current_scope=_SCOPE,
        observations=observations,
        evaluation_time=_EVALUATION_TIME,
    )

    assert result.threshold == Decimal("0.50")
    assert result.is_good is True


def test_incompatible_and_low_coverage_observations_are_excluded() -> None:
    """Only compatible summaries with at least 90 percent coverage count."""
    other_scope = AdaptivePriceScope.from_metadata(
        currency="SEK",
        unit="SEK/kWh",
        metadata=_COMPLETE_METADATA,
        tariff_signature="tariff-v2",
    )
    observations = (
        tuple(_observation(day, "0.50") for day in range(1, 8))
        + tuple(_observation(day, "0.10", scope=other_scope) for day in range(8, 22))
        + tuple(_observation(day, "0.10", coverage_minutes=53) for day in range(22, 29))
    )

    result = evaluate_adaptive_good_price(
        current_price=Decimal("0.50"),
        current_scope=_SCOPE,
        observations=observations,
        evaluation_time=_EVALUATION_TIME,
        fixed_fallback=Decimal("1.00"),
    )

    assert result.method is AdaptiveEvaluationMethod.ADAPTIVE_FALLBACK
    assert result.sample_count == 7


def test_observations_older_than_four_weeks_are_excluded() -> None:
    """The evaluator should enforce the bounded 28-day history contract."""
    observations = tuple(_observation(day, "0.50") for day in range(29, 43))

    result = evaluate_adaptive_good_price(
        current_price=Decimal("0.50"),
        current_scope=_SCOPE,
        observations=observations,
        evaluation_time=_EVALUATION_TIME,
    )

    assert result.is_good is None
    assert result.sample_count == 0


def test_incomplete_current_scope_is_unavailable() -> None:
    """Unknown or partial semantics must not enter adaptive comparison."""
    incomplete_scope = AdaptivePriceScope(
        currency="SEK",
        unit="SEK/kWh",
        components=frozenset({PriceComponent.MARKET_ENERGY}),
        vat=VatTreatment.UNKNOWN,
        completeness=PriceCompleteness.PARTIAL,
        tariff_signature="tariff-v1",
    )

    result = evaluate_adaptive_good_price(
        current_price=Decimal("0.50"),
        current_scope=incomplete_scope,
        observations=(),
        evaluation_time=_EVALUATION_TIME,
        fixed_fallback=Decimal("1.00"),
    )

    assert result.is_good is None
    assert result.reason is AdaptivePriceReason.INCOMPATIBLE_CURRENT_PRICE


@pytest.mark.parametrize(
    "weighted_prices",
    [
        (),
        ((Decimal("NaN"), Decimal(1)),),
        ((Decimal(1), Decimal(0)),),
        ((Decimal(1), Decimal("Infinity")),),
    ],
)
def test_weighted_helpers_reject_invalid_input(
    weighted_prices: tuple[tuple[Decimal, Decimal], ...],
) -> None:
    """Invalid values and weights should fail at the pure boundary."""
    with pytest.raises(ValueError):
        weighted_quantile(weighted_prices, Decimal("0.25"))


def test_historical_summary_requires_aware_valid_boundaries() -> None:
    """Malformed persisted summaries should be rejected deterministically."""
    start = datetime(2026, 9, 1, 12, tzinfo=UTC).replace(tzinfo=None)
    with pytest.raises(ValueError):
        HistoricalPriceObservation(
            start=start,
            end=start + timedelta(hours=1),
            effective_price=Decimal("0.50"),
            covered_duration=timedelta(hours=1),
            scope=_SCOPE,
        )
