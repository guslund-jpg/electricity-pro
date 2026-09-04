"""Pure adaptive good-price calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

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
    BETTER_PRICE_FORECAST = "better_price_forecast"


class ForecastComparisonStatus(StrEnum):
    """Outcome of the optional adaptive forecast comparison."""

    NOT_APPLICABLE = "not_applicable"
    NOT_CONFIGURED = "not_configured"
    WITHHELD_UNAVAILABLE = "withheld_unavailable"
    WITHHELD_INCOMPATIBLE = "withheld_incompatible"
    WITHHELD_NO_REFERENCE_RANGE = "withheld_no_reference_range"
    NO_MATERIALLY_BETTER_PRICE = "no_materially_better_price"
    SUPPRESSED = "suppressed"


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

    def as_dict(self) -> dict[str, Any]:
        """Return a storage-safe compatibility identity."""
        return {
            "currency": self.currency,
            "unit": self.unit,
            "components": sorted(component.value for component in self.components),
            "vat": self.vat.value,
            "completeness": self.completeness.value,
            "tariff_signature": self.tariff_signature,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdaptivePriceScope:
        """Restore and validate a persisted compatibility identity."""
        try:
            components = data["components"]
            if not isinstance(components, list):
                raise TypeError
            scope = cls(
                currency=data["currency"],
                unit=data["unit"],
                components=frozenset(PriceComponent(value) for value in components),
                vat=VatTreatment(data["vat"]),
                completeness=PriceCompleteness(data["completeness"]),
                tariff_signature=data["tariff_signature"],
            )
            if (
                not isinstance(scope.currency, str)
                or not isinstance(scope.unit, str)
                or not isinstance(scope.tariff_signature, str)
                or not scope.is_comparable
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError) as err:
            raise ValueError("invalid adaptive price scope") from err
        return scope


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

    def as_dict(self) -> dict[str, str]:
        """Return a storage-safe hourly observation without repeated scope."""
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "effective_price": str(self.effective_price),
            "covered_seconds": str(_seconds(self.covered_duration)),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        scope: AdaptivePriceScope,
    ) -> HistoricalPriceObservation:
        """Restore and validate one persisted hourly observation."""
        try:
            return cls(
                start=datetime.fromisoformat(data["start"]),
                end=datetime.fromisoformat(data["end"]),
                effective_price=Decimal(data["effective_price"]),
                covered_duration=_timedelta_from_decimal_seconds(
                    Decimal(data["covered_seconds"])
                ),
                scope=scope,
            )
        except (InvalidOperation, KeyError, TypeError, ValueError) as err:
            raise ValueError("invalid historical price observation") from err


@dataclass(frozen=True, slots=True)
class AdaptiveForecastPrice:
    """One future complete Effective Price eligible for comparison."""

    start: datetime
    end: datetime
    effective_price: Decimal
    scope: AdaptivePriceScope

    def __post_init__(self) -> None:
        """Reject malformed or semantically incomplete forecast values."""
        if (
            self.start.tzinfo is None
            or self.end.tzinfo is None
            or self.start >= self.end
            or not self.effective_price.is_finite()
            or not self.scope.is_comparable
        ):
            raise ValueError("invalid adaptive forecast price")


@dataclass(frozen=True, slots=True)
class AdaptiveForecastResult:
    """Explain the optional forecast refinement of an adaptive result."""

    status: ForecastComparisonStatus
    suppress: bool = False
    interval: AdaptiveForecastPrice | None = None
    price_difference: Decimal | None = None
    reference_range: Decimal | None = None


@dataclass(slots=True)
class _MutablePriceHour:
    """Mutable duration-weighted aggregate for one absolute local hour."""

    start: datetime
    end: datetime
    price_seconds: Decimal = Decimal(0)
    covered_seconds: Decimal = Decimal(0)


class AdaptivePriceHistory:
    """Build and persist a bounded sequence of compatible hourly prices."""

    def __init__(self, local_timezone: tzinfo, *, history_days: int = 28) -> None:
        """Initialize an empty adaptive price history."""
        if history_days <= 0:
            raise ValueError("history days must be positive")
        self._local_timezone = local_timezone
        self._history_days = history_days
        self._scope: AdaptivePriceScope | None = None
        self._observations: dict[datetime, HistoricalPriceObservation] = {}
        self._hours: dict[datetime, _MutablePriceHour] = {}
        self._restarted_at: datetime | None = None
        self._restart_reason: str | None = None

    @property
    def scope(self) -> AdaptivePriceScope | None:
        """Return the active compatibility partition."""
        return self._scope

    @property
    def local_timezone(self) -> tzinfo:
        """Return the timezone used to classify local price hours."""
        return self._local_timezone

    @property
    def observations(self) -> tuple[HistoricalPriceObservation, ...]:
        """Return ordered eligible completed-hour observations."""
        return tuple(self._observations[key] for key in sorted(self._observations))

    @property
    def restarted_at(self) -> datetime | None:
        """Return when incompatible history was most recently cleared."""
        return self._restarted_at

    @property
    def restart_reason(self) -> str | None:
        """Return why incompatible history was most recently cleared."""
        return self._restart_reason

    def ensure_scope(
        self,
        scope: AdaptivePriceScope,
        *,
        changed_at: datetime,
        reason: str = "price_configuration_changed",
    ) -> bool:
        """Activate a scope, clearing history only when compatibility changes."""
        if changed_at.tzinfo is None or changed_at.utcoffset() is None:
            raise ValueError("scope change time must be timezone-aware")
        if not scope.is_comparable:
            raise ValueError("adaptive price scope must be comparable")
        if self._scope == scope:
            return False
        had_scope = self._scope is not None
        self._scope = scope
        self._observations.clear()
        self._hours.clear()
        self._restarted_at = changed_at if had_scope else None
        self._restart_reason = reason if had_scope else None
        return True

    def add_segment(
        self,
        *,
        start: datetime,
        end: datetime,
        effective_price: Decimal,
    ) -> bool:
        """Add one constant-price segment and finalize any closed local hours."""
        if self._scope is None:
            raise ValueError("adaptive price scope is not initialized")
        if (
            start.tzinfo is None
            or start.utcoffset() is None
            or end.tzinfo is None
            or end.utcoffset() is None
            or end.astimezone(UTC) <= start.astimezone(UTC)
            or not effective_price.is_finite()
        ):
            raise ValueError("invalid adaptive price segment")

        cursor = start.astimezone(UTC)
        utc_end = end.astimezone(UTC)
        while cursor < utc_end:
            hour_start = _local_hour_start(cursor, self._local_timezone)
            hour_end = _next_local_hour_boundary(cursor, self._local_timezone)
            segment_end = min(hour_end, utc_end)
            seconds = _seconds(segment_end - cursor)
            hour = self._hours.setdefault(
                hour_start,
                _MutablePriceHour(start=hour_start, end=hour_end),
            )
            if hour.end != hour_end:
                raise ValueError("conflicting adaptive price hour boundary")
            hour.price_seconds += effective_price * seconds
            hour.covered_seconds += seconds
            cursor = segment_end

        hour_closed = self._finalize_closed_hours(utc_end)
        self.retain_for_date(utc_end.astimezone(self._local_timezone).date())
        return hour_closed

    def retain_for_date(self, local_today: date) -> None:
        """Retain completed dates in the bounded four-week window."""
        earliest = local_today - timedelta(days=self._history_days)
        self._observations = {
            key: observation
            for key, observation in self._observations.items()
            if earliest <= observation.local_date <= local_today
        }
        self._hours = {
            key: hour
            for key, hour in self._hours.items()
            if hour.start.astimezone(self._local_timezone).date() >= earliest
        }

    def as_dict(self) -> dict[str, Any]:
        """Return bounded history in a storage-safe representation."""
        return {
            "history_days": self._history_days,
            "scope": self._scope.as_dict() if self._scope is not None else None,
            "restarted_at": (
                self._restarted_at.isoformat()
                if self._restarted_at is not None
                else None
            ),
            "restart_reason": self._restart_reason,
            "observations": [
                observation.as_dict() for observation in self.observations
            ],
            "open_hours": [
                {
                    "start": hour.start.isoformat(),
                    "end": hour.end.isoformat(),
                    "price_seconds": str(hour.price_seconds),
                    "covered_seconds": str(hour.covered_seconds),
                }
                for _, hour in sorted(self._hours.items())
            ],
        }

    @classmethod
    def from_dict(
        cls,
        local_timezone: tzinfo,
        data: dict[str, Any],
    ) -> AdaptivePriceHistory:
        """Restore and validate persisted adaptive price history."""
        try:
            history_days = data["history_days"]
            if not isinstance(history_days, int):
                raise TypeError
            history = cls(local_timezone, history_days=history_days)
            raw_scope = data["scope"]
            if raw_scope is not None:
                if not isinstance(raw_scope, dict):
                    raise ValueError
                history._scope = AdaptivePriceScope.from_dict(raw_scope)

            restarted_at = data["restarted_at"]
            if restarted_at is not None:
                history._restarted_at = datetime.fromisoformat(restarted_at)
                if (
                    history._restarted_at.tzinfo is None
                    or history._restarted_at.utcoffset() is None
                ):
                    raise ValueError
            restart_reason = data["restart_reason"]
            if restart_reason is not None and (
                not isinstance(restart_reason, str) or not restart_reason
            ):
                raise ValueError
            history._restart_reason = restart_reason

            if history._scope is None and (data["observations"] or data["open_hours"]):
                raise ValueError
            if history._scope is not None:
                for item in data["observations"]:
                    observation = HistoricalPriceObservation.from_dict(
                        item,
                        scope=history._scope,
                    )
                    key = observation.start.astimezone(UTC)
                    if (
                        key in history._observations
                        or observation.coverage < _MIN_COVERAGE
                    ):
                        raise ValueError
                    history._observations[key] = observation
                for item in data["open_hours"]:
                    start = datetime.fromisoformat(item["start"])
                    end = datetime.fromisoformat(item["end"])
                    price_seconds = Decimal(item["price_seconds"])
                    covered_seconds = Decimal(item["covered_seconds"])
                    if (
                        start.tzinfo is None
                        or start.utcoffset() is None
                        or end.tzinfo is None
                        or end.utcoffset() is None
                        or end.astimezone(UTC) <= start.astimezone(UTC)
                        or not price_seconds.is_finite()
                        or not covered_seconds.is_finite()
                        or covered_seconds <= 0
                        or covered_seconds
                        > _seconds(end.astimezone(UTC) - start.astimezone(UTC))
                    ):
                        raise ValueError
                    key = start.astimezone(UTC)
                    if key in history._hours or key in history._observations:
                        raise ValueError
                    history._hours[key] = _MutablePriceHour(
                        start=key,
                        end=end.astimezone(UTC),
                        price_seconds=price_seconds,
                        covered_seconds=covered_seconds,
                    )
        except (InvalidOperation, KeyError, TypeError, ValueError) as err:
            raise ValueError("invalid adaptive price history") from err
        return history

    def _finalize_closed_hours(self, through: datetime) -> bool:
        """Move closed, sufficiently covered hours into immutable history."""
        closed_keys = sorted(
            key for key, hour in self._hours.items() if hour.end <= through
        )
        for key in closed_keys:
            hour = self._hours.pop(key)
            actual_seconds = _seconds(hour.end - hour.start)
            if hour.covered_seconds / actual_seconds < _MIN_COVERAGE:
                continue
            if self._scope is None:
                raise AssertionError("closed adaptive history lost its scope")
            self._observations[key] = HistoricalPriceObservation(
                start=hour.start.astimezone(self._local_timezone),
                end=hour.end.astimezone(self._local_timezone),
                effective_price=hour.price_seconds / hour.covered_seconds,
                covered_duration=_timedelta_from_decimal_seconds(hour.covered_seconds),
                scope=self._scope,
            )
        return bool(closed_keys)


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


def evaluate_adaptive_forecast(
    *,
    current_result: AdaptivePriceResult,
    current_price: Decimal,
    current_scope: AdaptivePriceScope,
    observations: tuple[HistoricalPriceObservation, ...],
    forecast_prices: tuple[AdaptiveForecastPrice, ...],
    evaluation_time: datetime,
    target_percentile: Decimal = _DEFAULT_TARGET_PERCENTILE,
    absolute_ceiling: Decimal | None = None,
    look_ahead_hours: int = 6,
    history_days: int = _DEFAULT_HISTORY_DAYS,
    half_life_days: int = _DEFAULT_HALF_LIFE_DAYS,
) -> AdaptiveForecastResult:
    """Suppress a good-now result for a materially better comparable forecast."""
    if (
        current_result.method is not AdaptiveEvaluationMethod.ADAPTIVE
        or current_result.is_good is not True
    ):
        return AdaptiveForecastResult(ForecastComparisonStatus.NOT_APPLICABLE)

    eligible = _eligible_observations(
        observations,
        current_scope=current_scope,
        evaluation_time=evaluation_time,
        history_days=history_days,
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
        for observation in eligible
    )
    reference_range = (
        weighted_quantile(weighted_prices, Decimal("0.90"))
        - weighted_quantile(weighted_prices, Decimal("0.10"))
    )
    if reference_range <= 0:
        return AdaptiveForecastResult(
            ForecastComparisonStatus.WITHHELD_NO_REFERENCE_RANGE,
            reference_range=reference_range,
        )

    evaluation_utc = evaluation_time.astimezone(UTC)
    look_ahead_end = evaluation_utc + timedelta(hours=look_ahead_hours)
    material_difference = reference_range * Decimal("0.10")
    for forecast in sorted(forecast_prices, key=lambda item: item.start):
        local_start = forecast.start.astimezone(evaluation_time.tzinfo)
        forecast_start_utc = forecast.start.astimezone(UTC)
        if (
            forecast.scope != current_scope
            or forecast_start_utc < evaluation_utc
            or forecast_start_utc >= look_ahead_end
        ):
            continue
        future_result = evaluate_adaptive_good_price(
            current_price=forecast.effective_price,
            current_scope=forecast.scope,
            observations=observations,
            evaluation_time=local_start,
            target_percentile=target_percentile,
            absolute_ceiling=absolute_ceiling,
            history_days=history_days,
            half_life_days=half_life_days,
        )
        difference = current_price - forecast.effective_price
        if future_result.is_good is True and difference >= material_difference:
            return AdaptiveForecastResult(
                ForecastComparisonStatus.SUPPRESSED,
                suppress=True,
                interval=forecast,
                price_difference=difference,
                reference_range=reference_range,
            )

    return AdaptiveForecastResult(
        ForecastComparisonStatus.NO_MATERIALLY_BETTER_PRICE,
        reference_range=reference_range,
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


def _timedelta_from_decimal_seconds(value: Decimal) -> timedelta:
    """Restore persisted Decimal seconds without precision loss."""
    microseconds = value * Decimal(1_000_000)
    if (
        not microseconds.is_finite()
        or microseconds <= 0
        or microseconds != microseconds.to_integral_value()
    ):
        raise ValueError("invalid adaptive price duration")
    return timedelta(microseconds=int(microseconds))


def _local_hour_start(instant: datetime, local_timezone: tzinfo) -> datetime:
    """Return the absolute start of the local clock hour containing instant."""
    local = instant.astimezone(local_timezone)
    return local.replace(minute=0, second=0, microsecond=0).astimezone(UTC)


def _next_local_hour_boundary(
    instant: datetime,
    local_timezone: tzinfo,
) -> datetime:
    """Return the next absolute instant on a local clock-hour boundary."""
    candidate = instant.astimezone(UTC).replace(second=0, microsecond=0)
    candidate += timedelta(minutes=1)
    limit = candidate + timedelta(hours=3)
    while candidate <= limit:
        local = candidate.astimezone(local_timezone)
        if local.minute == 0:
            return candidate
        candidate += timedelta(minutes=1)
    raise ValueError("unable to find next local hour boundary")
