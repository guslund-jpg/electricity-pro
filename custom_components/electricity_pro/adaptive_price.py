"""Pure adaptive good-price calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from .pricing import (
    PriceCompleteness,
    PriceComponent,
    PricingMetadata,
    VatTreatment,
)

_DEFAULT_HISTORY_DAYS = 28
_DEFAULT_HALF_LIFE_DAYS = 7
_DEFAULT_TARGET_PERCENTILE = Decimal("0.25")
_MIN_DAY_TYPE_SAMPLES = 8
_MIN_HOUR_SAMPLES = 14
_MIN_COVERAGE = Decimal("0.90")
_SECONDS_PER_DAY = Decimal(24 * 60 * 60)


class AdaptiveEvaluationMethod(StrEnum):
    """Method used to produce an adaptive-mode result."""

    ADAPTIVE = "adaptive"
    ADAPTIVE_FALLBACK = "adaptive_fallback"


class AdaptiveCohortType(StrEnum):
    """Historical cohort selected for an adaptive evaluation."""

    SAME_HOUR_AND_DAY_TYPE = "same_hour_and_day_type"
    SAME_HOUR = "same_hour"


class AdaptivePriceReason(StrEnum):
    """Reason for an adaptive-mode classification or unavailable result."""

    WITHIN_ADAPTIVE_THRESHOLD = "within_adaptive_threshold"
    ABOVE_ADAPTIVE_THRESHOLD = "above_adaptive_threshold"
    ABOVE_ABSOLUTE_CEILING = "above_absolute_ceiling"
    WITHIN_FIXED_FALLBACK = "within_fixed_fallback"
    ABOVE_FIXED_FALLBACK = "above_fixed_fallback"
    INSUFFICIENT_COMPARABLE_HISTORY = "insufficient_comparable_history"
    INVALID_CURRENT_PRICE = "invalid_current_price"
    INCOMPATIBLE_CURRENT_PRICE = "incompatible_current_price"


@dataclass(frozen=True, slots=True)
class AdaptivePriceScope:
    """Compatibility identity for historical Effective Price values."""

    currency: str
    unit: str
    components: frozenset[PriceComponent]
    vat: VatTreatment
    completeness: PriceCompleteness
    tariff_signature: str

    @classmethod
    def from_metadata(
        cls,
        *,
        currency: str,
        unit: str,
        metadata: PricingMetadata,
        tariff_signature: str,
    ) -> AdaptivePriceScope:
        """Create a compatibility identity from normalized pricing metadata."""
        return cls(
            currency=currency,
            unit=unit,
            components=metadata.scope.included,
            vat=metadata.scope.vat,
            completeness=metadata.completeness,
            tariff_signature=tariff_signature,
        )

    @property
    def is_comparable(self) -> bool:
        """Return whether the scope can participate in adaptive comparison."""
        return (
            bool(self.currency.strip())
            and bool(self.unit.strip())
            and bool(self.tariff_signature.strip())
            and self.vat is not VatTreatment.UNKNOWN
            and self.completeness is PriceCompleteness.COMPLETE
        )


@dataclass(frozen=True, slots=True)
class HistoricalPriceObservation:
    """One compact hourly Effective Price summary."""

    start: datetime
    end: datetime
    effective_price: Decimal
    covered_duration: timedelta
    scope: AdaptivePriceScope

    def __post_init__(self) -> None:
        """Reject malformed summaries at the pure-model boundary."""
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("historical price boundaries must be timezone-aware")
        actual_duration = self.end.astimezone(UTC) - self.start.astimezone(UTC)
        if actual_duration <= timedelta(0):
            raise ValueError("historical price period must have positive duration")
        if (
            not self.effective_price.is_finite()
            or self.covered_duration <= timedelta(0)
            or self.covered_duration > actual_duration
        ):
            raise ValueError("invalid historical price summary")

    @property
    def local_date(self) -> date:
        """Return the local date represented by the stored start boundary."""
        return self.start.date()

    @property
    def local_hour(self) -> int:
        """Return the local clock hour represented by the summary."""
        return self.start.hour

    @property
    def is_weekend(self) -> bool:
        """Return whether the summary belongs to a weekend."""
        return self.local_date.weekday() >= 5

    @property
    def coverage(self) -> Decimal:
        """Return covered duration as a fraction of the actual period."""
        actual_seconds = _seconds(self.end.astimezone(UTC) - self.start.astimezone(UTC))
        return _seconds(self.covered_duration) / actual_seconds


@dataclass(frozen=True, slots=True)
class AdaptivePriceResult:
    """Explainable result of evaluating Adaptive mode."""

    is_good: bool | None
    method: AdaptiveEvaluationMethod | None
    reason: AdaptivePriceReason
    threshold: Decimal | None
    current_percentile: Decimal | None
    cohort_type: AdaptiveCohortType | None
    historical_days: int
    sample_count: int
    required_sample_count: int


def evaluate_adaptive_good_price(
    *,
    current_price: Decimal | None,
    current_scope: AdaptivePriceScope | None,
    observations: tuple[HistoricalPriceObservation, ...],
    evaluation_time: datetime,
    target_percentile: Decimal = _DEFAULT_TARGET_PERCENTILE,
    fixed_fallback: Decimal | None = None,
    absolute_ceiling: Decimal | None = None,
    history_days: int = _DEFAULT_HISTORY_DAYS,
    half_life_days: int = _DEFAULT_HALF_LIFE_DAYS,
) -> AdaptivePriceResult:
    """Classify the current Effective Price using compatible recent history."""
    _validate_evaluation_options(
        evaluation_time=evaluation_time,
        target_percentile=target_percentile,
        fixed_fallback=fixed_fallback,
        absolute_ceiling=absolute_ceiling,
        history_days=history_days,
        half_life_days=half_life_days,
    )
    if current_price is None or not current_price.is_finite():
        return _unavailable(AdaptivePriceReason.INVALID_CURRENT_PRICE)
    if current_scope is None or not current_scope.is_comparable:
        return _unavailable(AdaptivePriceReason.INCOMPATIBLE_CURRENT_PRICE)

    eligible = _eligible_observations(
        observations,
        current_scope=current_scope,
        evaluation_time=evaluation_time,
        history_days=history_days,
    )
    cohort, cohort_type, required_samples = _select_cohort(
        eligible,
        evaluation_time=evaluation_time,
    )
    if cohort is None:
        candidate_count = sum(
            observation.local_hour == evaluation_time.hour for observation in eligible
        )
        if fixed_fallback is not None:
            return AdaptivePriceResult(
                is_good=current_price <= fixed_fallback,
                method=AdaptiveEvaluationMethod.ADAPTIVE_FALLBACK,
                reason=(
                    AdaptivePriceReason.WITHIN_FIXED_FALLBACK
                    if current_price <= fixed_fallback
                    else AdaptivePriceReason.ABOVE_FIXED_FALLBACK
                ),
                threshold=fixed_fallback,
                current_percentile=None,
                cohort_type=None,
                historical_days=len(
                    {observation.local_date for observation in eligible}
                ),
                sample_count=candidate_count,
                required_sample_count=required_samples,
            )
        return AdaptivePriceResult(
            is_good=None,
            method=None,
            reason=AdaptivePriceReason.INSUFFICIENT_COMPARABLE_HISTORY,
            threshold=None,
            current_percentile=None,
            cohort_type=None,
            historical_days=len({observation.local_date for observation in eligible}),
            sample_count=candidate_count,
            required_sample_count=required_samples,
        )

    weighted_prices = tuple(
        (
            observation.effective_price,
            _seconds(observation.covered_duration)
            * recency_weight(
                (evaluation_time.date() - observation.local_date).days,
                half_life_days=half_life_days,
            ),
        )
        for observation in cohort
    )
    threshold = weighted_quantile(weighted_prices, target_percentile)
    current_percentile = weighted_midrank(weighted_prices, current_price)

    if absolute_ceiling is not None and current_price > absolute_ceiling:
        is_good = False
        reason = AdaptivePriceReason.ABOVE_ABSOLUTE_CEILING
    elif current_price <= threshold:
        is_good = True
        reason = AdaptivePriceReason.WITHIN_ADAPTIVE_THRESHOLD
    else:
        is_good = False
        reason = AdaptivePriceReason.ABOVE_ADAPTIVE_THRESHOLD

    return AdaptivePriceResult(
        is_good=is_good,
        method=AdaptiveEvaluationMethod.ADAPTIVE,
        reason=reason,
        threshold=threshold,
        current_percentile=current_percentile,
        cohort_type=cohort_type,
        historical_days=len({observation.local_date for observation in cohort}),
        sample_count=len(cohort),
        required_sample_count=required_samples,
    )


def recency_weight(age_days: int, *, half_life_days: int = 7) -> Decimal:
    """Return exponential recency weight for a whole-number local-day age."""
    if age_days < 0 or half_life_days <= 0:
        raise ValueError("invalid recency weight input")
    return Decimal(2) ** (-Decimal(age_days) / Decimal(half_life_days))


def weighted_quantile(
    weighted_prices: tuple[tuple[Decimal, Decimal], ...],
    percentile: Decimal,
) -> Decimal:
    """Return the lowest price whose cumulative weight reaches percentile."""
    grouped = _group_valid_weighted_prices(weighted_prices)
    if not Decimal(0) < percentile <= Decimal(1):
        raise ValueError("percentile must be greater than zero and at most one")
    target_weight = sum(grouped.values(), Decimal(0)) * percentile
    cumulative_weight = Decimal(0)
    for price, weight in sorted(grouped.items()):
        cumulative_weight += weight
        if cumulative_weight >= target_weight:
            return price
    raise AssertionError("weighted quantile calculation failed")


def weighted_midrank(
    weighted_prices: tuple[tuple[Decimal, Decimal], ...],
    price: Decimal,
) -> Decimal:
    """Return the midpoint empirical percentile of a price."""
    if not price.is_finite():
        raise ValueError("price must be finite")
    grouped = _group_valid_weighted_prices(weighted_prices)
    total_weight = sum(grouped.values(), Decimal(0))
    cheaper_weight = sum(
        (weight for candidate, weight in grouped.items() if candidate < price),
        Decimal(0),
    )
    equal_weight = grouped.get(price, Decimal(0))
    return (cheaper_weight + equal_weight / Decimal(2)) / total_weight


def _eligible_observations(
    observations: tuple[HistoricalPriceObservation, ...],
    *,
    current_scope: AdaptivePriceScope,
    evaluation_time: datetime,
    history_days: int,
) -> tuple[HistoricalPriceObservation, ...]:
    """Return complete prior-date observations inside the retention window."""
    evaluation_date = evaluation_time.date()
    earliest_date = evaluation_date - timedelta(days=history_days)
    return tuple(
        observation
        for observation in observations
        if observation.scope == current_scope
        and observation.scope.is_comparable
        and earliest_date <= observation.local_date < evaluation_date
        and observation.coverage >= _MIN_COVERAGE
    )


def _select_cohort(
    observations: tuple[HistoricalPriceObservation, ...],
    *,
    evaluation_time: datetime,
) -> tuple[
    tuple[HistoricalPriceObservation, ...] | None,
    AdaptiveCohortType | None,
    int,
]:
    """Select the most specific sufficiently populated historical cohort."""
    same_hour = tuple(
        observation
        for observation in observations
        if observation.local_hour == evaluation_time.hour
    )
    current_is_weekend = evaluation_time.date().weekday() >= 5
    same_day_type = tuple(
        observation
        for observation in same_hour
        if observation.is_weekend is current_is_weekend
    )
    if len(same_day_type) >= _MIN_DAY_TYPE_SAMPLES:
        return (
            same_day_type,
            AdaptiveCohortType.SAME_HOUR_AND_DAY_TYPE,
            _MIN_DAY_TYPE_SAMPLES,
        )
    if len(same_hour) >= _MIN_HOUR_SAMPLES:
        return same_hour, AdaptiveCohortType.SAME_HOUR, _MIN_HOUR_SAMPLES
    return None, None, _MIN_HOUR_SAMPLES


def _group_valid_weighted_prices(
    weighted_prices: tuple[tuple[Decimal, Decimal], ...],
) -> dict[Decimal, Decimal]:
    """Validate and group weights by exact price."""
    if not weighted_prices:
        raise ValueError("weighted prices must not be empty")
    grouped: dict[Decimal, Decimal] = {}
    for price, weight in weighted_prices:
        if not price.is_finite() or not weight.is_finite() or weight <= 0:
            raise ValueError("weighted prices must be finite with positive weights")
        grouped[price] = grouped.get(price, Decimal(0)) + weight
    return grouped


def _validate_evaluation_options(
    *,
    evaluation_time: datetime,
    target_percentile: Decimal,
    fixed_fallback: Decimal | None,
    absolute_ceiling: Decimal | None,
    history_days: int,
    half_life_days: int,
) -> None:
    """Validate caller-controlled calculation options."""
    if evaluation_time.tzinfo is None:
        raise ValueError("evaluation time must be timezone-aware")
    if not target_percentile.is_finite() or not Decimal(0) < target_percentile <= 1:
        raise ValueError("invalid target percentile")
    if history_days <= 0 or half_life_days <= 0:
        raise ValueError("history and half-life days must be positive")
    for value in (fixed_fallback, absolute_ceiling):
        if value is not None and not value.is_finite():
            raise ValueError("configured price limits must be finite")


def _unavailable(reason: AdaptivePriceReason) -> AdaptivePriceResult:
    """Build an unavailable result before a historical cohort can be selected."""
    return AdaptivePriceResult(
        is_good=None,
        method=None,
        reason=reason,
        threshold=None,
        current_percentile=None,
        cohort_type=None,
        historical_days=0,
        sample_count=0,
        required_sample_count=0,
    )


def _seconds(duration: timedelta) -> Decimal:
    """Return exact-enough Decimal seconds for datetime arithmetic."""
    return Decimal(str(duration.total_seconds()))
