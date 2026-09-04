"""Tests for pure adaptive good-price calculations."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from custom_components.electricity_pro.adaptive_price import (
    AdaptiveCohortType,
    AdaptiveEvaluationMethod,
    AdaptiveForecastPrice,
    AdaptivePriceHistory,
    AdaptivePriceReason,
    AdaptivePriceScope,
    ForecastComparisonStatus,
    HistoricalPriceObservation,
    evaluate_adaptive_forecast,
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


def test_materially_better_forecast_suppresses_good_now() -> None:
    """A qualifying future price should suppress an otherwise good result."""
    observations = (
        tuple(_observation(day, "0.60", hour=12) for day in range(1, 29))
        + tuple(_observation(day, "0.20", hour=14) for day in range(1, 29))
        + tuple(_observation(day, "0.00", hour=16) for day in range(1, 29))
        + tuple(_observation(day, "1.00", hour=18) for day in range(1, 29))
    )
    current_result = evaluate_adaptive_good_price(
        current_price=Decimal("0.60"),
        current_scope=_SCOPE,
        observations=observations,
        evaluation_time=_EVALUATION_TIME,
    )
    future = AdaptiveForecastPrice(
        start=_EVALUATION_TIME.replace(hour=14, minute=0),
        end=_EVALUATION_TIME.replace(hour=15, minute=0),
        effective_price=Decimal("0.20"),
        scope=_SCOPE,
    )

    result = evaluate_adaptive_forecast(
        current_result=current_result,
        current_price=Decimal("0.60"),
        current_scope=_SCOPE,
        observations=observations,
        forecast_prices=(future,),
        evaluation_time=_EVALUATION_TIME,
    )

    assert result.status is ForecastComparisonStatus.SUPPRESSED
    assert result.suppress is True
    assert result.interval == future
    assert result.price_difference == Decimal("0.40")
    assert result.reference_range == Decimal("1.00")


def test_small_forecast_difference_does_not_suppress() -> None:
    """A future good price must clear the history-scaled materiality rule."""
    observations = (
        tuple(_observation(day, "0.60", hour=12) for day in range(1, 29))
        + tuple(_observation(day, "0.58", hour=14) for day in range(1, 29))
        + tuple(_observation(day, "0.00", hour=16) for day in range(1, 29))
        + tuple(_observation(day, "1.00", hour=18) for day in range(1, 29))
    )
    current_result = evaluate_adaptive_good_price(
        current_price=Decimal("0.60"),
        current_scope=_SCOPE,
        observations=observations,
        evaluation_time=_EVALUATION_TIME,
    )

    result = evaluate_adaptive_forecast(
        current_result=current_result,
        current_price=Decimal("0.60"),
        current_scope=_SCOPE,
        observations=observations,
        forecast_prices=(
            AdaptiveForecastPrice(
                start=_EVALUATION_TIME.replace(hour=14, minute=0),
                end=_EVALUATION_TIME.replace(hour=15, minute=0),
                effective_price=Decimal("0.58"),
                scope=_SCOPE,
            ),
        ),
        evaluation_time=_EVALUATION_TIME,
    )

    assert result.status is ForecastComparisonStatus.NO_MATERIALLY_BETTER_PRICE
    assert result.suppress is False


def test_flat_history_withholds_forecast_suppression() -> None:
    """A zero historical reference range must not invent materiality."""
    observations = tuple(
        _observation(day, "0.50", hour=hour)
        for hour in (12, 14)
        for day in range(1, 29)
    )
    current_result = evaluate_adaptive_good_price(
        current_price=Decimal("0.50"),
        current_scope=_SCOPE,
        observations=observations,
        evaluation_time=_EVALUATION_TIME,
    )

    result = evaluate_adaptive_forecast(
        current_result=current_result,
        current_price=Decimal("0.50"),
        current_scope=_SCOPE,
        observations=observations,
        forecast_prices=(),
        evaluation_time=_EVALUATION_TIME,
    )

    assert result.status is ForecastComparisonStatus.WITHHELD_NO_REFERENCE_RANGE
    assert result.suppress is False


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


def test_scope_storage_round_trip() -> None:
    """Compatibility metadata should round-trip without changing identity."""
    assert AdaptivePriceScope.from_dict(_SCOPE.as_dict()) == _SCOPE


def test_history_builds_duration_weighted_completed_hour() -> None:
    """Segments should form one compact duration-weighted hourly summary."""
    history = AdaptivePriceHistory(UTC)
    history.ensure_scope(_SCOPE, changed_at=_EVALUATION_TIME)
    start = datetime(2026, 9, 7, 12, tzinfo=UTC)

    assert (
        history.add_segment(
            start=start,
            end=start + timedelta(minutes=15),
            effective_price=Decimal("0.20"),
        )
        is False
    )
    assert (
        history.add_segment(
            start=start + timedelta(minutes=15),
            end=start + timedelta(hours=1),
            effective_price=Decimal("1.00"),
        )
        is True
    )

    assert len(history.observations) == 1
    observation = history.observations[0]
    assert observation.effective_price == Decimal("0.80")
    assert observation.covered_duration == timedelta(hours=1)


def test_history_discards_closed_hour_below_coverage_threshold() -> None:
    """A closed hour with less than 90 percent coverage is not eligible."""
    history = AdaptivePriceHistory(UTC)
    history.ensure_scope(_SCOPE, changed_at=_EVALUATION_TIME)
    start = datetime(2026, 9, 7, 12, tzinfo=UTC)

    assert (
        history.add_segment(
            start=start,
            end=start + timedelta(minutes=53),
            effective_price=Decimal("0.50"),
        )
        is False
    )
    assert (
        history.add_segment(
            start=start + timedelta(hours=1),
            end=start + timedelta(hours=1, minutes=1),
            effective_price=Decimal("0.50"),
        )
        is True
    )

    assert history.observations == ()


def test_history_scope_change_clears_incompatible_observations() -> None:
    """A tariff change should start a visibly new compatibility partition."""
    history = AdaptivePriceHistory(UTC)
    history.ensure_scope(_SCOPE, changed_at=_EVALUATION_TIME)
    start = datetime(2026, 9, 7, 12, tzinfo=UTC)
    history.add_segment(
        start=start,
        end=start + timedelta(hours=1),
        effective_price=Decimal("0.50"),
    )
    changed_scope = AdaptivePriceScope(
        currency=_SCOPE.currency,
        unit=_SCOPE.unit,
        components=_SCOPE.components,
        vat=_SCOPE.vat,
        completeness=_SCOPE.completeness,
        tariff_signature="tariff-v2",
    )
    changed_at = start + timedelta(hours=2)

    assert history.ensure_scope(changed_scope, changed_at=changed_at) is True
    assert history.observations == ()
    assert history.scope == changed_scope
    assert history.restarted_at == changed_at
    assert history.restart_reason == "price_configuration_changed"
    assert history.ensure_scope(changed_scope, changed_at=changed_at) is False


def test_history_round_trip_preserves_completed_and_open_hours() -> None:
    """Restart restoration should retain compact completed and partial data."""
    history = AdaptivePriceHistory(UTC)
    history.ensure_scope(_SCOPE, changed_at=_EVALUATION_TIME)
    start = datetime(2026, 9, 5, 12, tzinfo=UTC)
    history.add_segment(
        start=start,
        end=start + timedelta(hours=1, minutes=30),
        effective_price=Decimal("0.75"),
    )

    restored = AdaptivePriceHistory.from_dict(UTC, history.as_dict())

    assert restored.as_dict() == history.as_dict()
    assert len(restored.observations) == 1
    assert (
        restored.add_segment(
            start=start + timedelta(hours=1, minutes=30),
            end=start + timedelta(hours=2),
            effective_price=Decimal("1.25"),
        )
        is True
    )
    assert restored.observations[-1].effective_price == Decimal("1.00")


def test_history_retains_only_four_completed_weeks() -> None:
    """Retention should discard completed hours older than 28 local dates."""
    history = AdaptivePriceHistory(UTC)
    history.ensure_scope(_SCOPE, changed_at=_EVALUATION_TIME)
    for days_ago in range(30, 0, -1):
        start = datetime.combine(
            (_EVALUATION_TIME - timedelta(days=days_ago)).date(),
            time(12),
            tzinfo=UTC,
        )
        history.add_segment(
            start=start,
            end=start + timedelta(hours=1),
            effective_price=Decimal(days_ago),
        )

    history.retain_for_date(_EVALUATION_TIME.date())

    assert len(history.observations) == 28
    assert min(item.local_date for item in history.observations) == (
        _EVALUATION_TIME.date() - timedelta(days=28)
    )


def test_history_distinguishes_repeated_dst_hour() -> None:
    """Both occurrences of a repeated local clock hour must be retained."""
    timezone = ZoneInfo("Europe/Stockholm")
    history = AdaptivePriceHistory(timezone)
    history.ensure_scope(
        _SCOPE,
        changed_at=datetime(2026, 10, 24, 23, tzinfo=UTC),
    )

    history.add_segment(
        start=datetime(2026, 10, 25, 0, tzinfo=UTC),
        end=datetime(2026, 10, 25, 2, tzinfo=UTC),
        effective_price=Decimal("0.50"),
    )

    assert len(history.observations) == 2
    assert [item.local_hour for item in history.observations] == [2, 2]
    assert [item.start.utcoffset() for item in history.observations] == [
        timedelta(hours=2),
        timedelta(hours=1),
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        {"history_days": 0},
        {"scope": {"currency": "SEK"}},
        {"restarted_at": "2026-09-04T12:00:00"},
        {"observations": [{"start": "invalid"}]},
        {
            "open_hours": [
                {
                    "start": "2026-09-04T12:00:00+00:00",
                    "end": "2026-09-04T13:00:00+00:00",
                    "price_seconds": "NaN",
                    "covered_seconds": "3600",
                }
            ]
        },
    ],
)
def test_history_rejects_corrupt_storage(mutation: dict[str, object]) -> None:
    """Invalid persisted fields must not partially restore history."""
    history = AdaptivePriceHistory(UTC)
    history.ensure_scope(_SCOPE, changed_at=_EVALUATION_TIME)
    data = {**history.as_dict(), **mutation}

    with pytest.raises(ValueError):
        AdaptivePriceHistory.from_dict(UTC, data)
