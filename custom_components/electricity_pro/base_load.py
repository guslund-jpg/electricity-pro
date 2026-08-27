"""Pure models and calculations for household base-load estimation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

_ONE_HUNDRED = Decimal(100)
_DEFAULT_DAILY_PERCENTILE = Decimal("0.10")
_DEFAULT_MINIMUM_COVERAGE = Decimal("0.90")
_DEFAULT_MAXIMUM_GAP = timedelta(hours=1)
_DEFAULT_WINDOW_DAYS = 7
_DEFAULT_REQUIRED_DAYS = 5


class DailyBaseLoadUnavailableReason(StrEnum):
    """Reasons one completed day cannot contribute a base-load estimate."""

    INSUFFICIENT_COVERAGE = "insufficient_coverage"
    LONG_DATA_GAP = "long_data_gap"
    UNSUPPORTED_BIDIRECTIONAL_POWER = "unsupported_bidirectional_power"


class BaseLoadUnavailableReason(StrEnum):
    """Reasons the rolling base-load estimate cannot be published."""

    INSUFFICIENT_HISTORY = "insufficient_history"


@dataclass(frozen=True, slots=True)
class PowerInterval:
    """One covered interval represented by its mean imported power."""

    mean_power_w: Decimal
    covered_duration: timedelta

    def __post_init__(self) -> None:
        """Validate normalized interval values."""
        if (
            not self.mean_power_w.is_finite()
            or self.mean_power_w < 0
            or self.covered_duration <= timedelta(0)
        ):
            raise ValueError("invalid power interval")


@dataclass(frozen=True, slots=True)
class DailyBaseLoadSummary:
    """Quality result and optional low-demand estimate for one local day."""

    period_start: date
    estimate_w: Decimal | None
    unavailable_reason: DailyBaseLoadUnavailableReason | None
    coverage_percent: Decimal
    longest_uncovered_gap: timedelta

    def __post_init__(self) -> None:
        """Validate summary consistency."""
        if (
            not self.coverage_percent.is_finite()
            or not Decimal(0) <= self.coverage_percent <= _ONE_HUNDRED
            or self.longest_uncovered_gap < timedelta(0)
            or (
                self.estimate_w is not None
                and (not self.estimate_w.is_finite() or self.estimate_w < 0)
            )
            or (self.estimate_w is None) == (self.unavailable_reason is None)
        ):
            raise ValueError("invalid daily base-load summary")

    def as_dict(self) -> dict[str, str | None]:
        """Return a storage-safe representation."""
        return {
            "period_start": self.period_start.isoformat(),
            "estimate_w": (
                str(self.estimate_w) if self.estimate_w is not None else None
            ),
            "unavailable_reason": (
                self.unavailable_reason.value
                if self.unavailable_reason is not None
                else None
            ),
            "coverage_percent": str(self.coverage_percent),
            "longest_uncovered_gap_seconds": str(
                _seconds(self.longest_uncovered_gap)
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DailyBaseLoadSummary:
        """Restore and validate a persisted daily summary."""
        try:
            estimate_value = data.get("estimate_w")
            reason_value = data.get("unavailable_reason")
            return cls(
                period_start=date.fromisoformat(data["period_start"]),
                estimate_w=(
                    Decimal(estimate_value) if estimate_value is not None else None
                ),
                unavailable_reason=(
                    DailyBaseLoadUnavailableReason(reason_value)
                    if reason_value is not None
                    else None
                ),
                coverage_percent=Decimal(data["coverage_percent"]),
                longest_uncovered_gap=_timedelta_from_decimal_seconds(
                    Decimal(data["longest_uncovered_gap_seconds"])
                ),
            )
        except (InvalidOperation, KeyError, TypeError, ValueError) as err:
            raise ValueError("invalid daily base-load summary") from err


@dataclass(frozen=True, slots=True)
class BaseLoadEstimateResult:
    """Rolling base-load estimate and compact explanatory metadata."""

    estimate_w: Decimal | None
    unavailable_reason: BaseLoadUnavailableReason | None
    window_start: date
    window_end: date
    eligible_days: int
    required_days: int
    daily_estimates: tuple[tuple[date, Decimal], ...]

    def __post_init__(self) -> None:
        """Validate rolling-result consistency."""
        if (
            self.window_end < self.window_start
            or self.eligible_days < 0
            or self.required_days <= 0
            or self.eligible_days != len(self.daily_estimates)
            or any(
                not value.is_finite() or value < 0
                for _, value in self.daily_estimates
            )
            or (
                self.estimate_w is not None
                and (not self.estimate_w.is_finite() or self.estimate_w < 0)
            )
            or (self.estimate_w is None) == (self.unavailable_reason is None)
        ):
            raise ValueError("invalid base-load estimate result")


def calculate_daily_base_load(
    period_start: date,
    intervals: tuple[PowerInterval, ...],
    *,
    period_duration: timedelta,
    longest_uncovered_gap: timedelta,
    bidirectional_power_observed: bool = False,
    percentile: Decimal = _DEFAULT_DAILY_PERCENTILE,
    minimum_coverage: Decimal = _DEFAULT_MINIMUM_COVERAGE,
    maximum_gap: timedelta = _DEFAULT_MAXIMUM_GAP,
) -> DailyBaseLoadSummary:
    """Calculate one completed local day's low-demand estimate."""
    if (
        period_duration <= timedelta(0)
        or longest_uncovered_gap < timedelta(0)
        or not Decimal(0) <= percentile <= Decimal(1)
        or not Decimal(0) <= minimum_coverage <= Decimal(1)
        or maximum_gap < timedelta(0)
    ):
        raise ValueError("invalid daily base-load period")

    covered_seconds = sum(
        (_seconds(interval.covered_duration) for interval in intervals),
        Decimal(0),
    )
    coverage = min(covered_seconds / _seconds(period_duration), Decimal(1))
    coverage_percent = coverage * _ONE_HUNDRED

    if bidirectional_power_observed:
        return _unavailable_daily(
            period_start,
            DailyBaseLoadUnavailableReason.UNSUPPORTED_BIDIRECTIONAL_POWER,
            coverage_percent,
            longest_uncovered_gap,
        )
    if coverage < minimum_coverage:
        return _unavailable_daily(
            period_start,
            DailyBaseLoadUnavailableReason.INSUFFICIENT_COVERAGE,
            coverage_percent,
            longest_uncovered_gap,
        )
    if longest_uncovered_gap > maximum_gap:
        return _unavailable_daily(
            period_start,
            DailyBaseLoadUnavailableReason.LONG_DATA_GAP,
            coverage_percent,
            longest_uncovered_gap,
        )

    return DailyBaseLoadSummary(
        period_start=period_start,
        estimate_w=duration_weighted_percentile(intervals, percentile),
        unavailable_reason=None,
        coverage_percent=coverage_percent,
        longest_uncovered_gap=longest_uncovered_gap,
    )


def calculate_base_load_estimate(
    summaries: tuple[DailyBaseLoadSummary, ...],
    *,
    window_end: date,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    required_days: int = _DEFAULT_REQUIRED_DAYS,
) -> BaseLoadEstimateResult:
    """Return the median eligible estimate in the latest calendar window."""
    if window_days <= 0 or required_days <= 0 or required_days > window_days:
        raise ValueError("invalid base-load history window")

    window_start = window_end - timedelta(days=window_days - 1)
    estimates_by_date = {
        summary.period_start: summary.estimate_w
        for summary in summaries
        if window_start <= summary.period_start <= window_end
        and summary.estimate_w is not None
    }
    daily_estimates = tuple(sorted(estimates_by_date.items()))
    if len(daily_estimates) < required_days:
        return BaseLoadEstimateResult(
            estimate_w=None,
            unavailable_reason=BaseLoadUnavailableReason.INSUFFICIENT_HISTORY,
            window_start=window_start,
            window_end=window_end,
            eligible_days=len(daily_estimates),
            required_days=required_days,
            daily_estimates=daily_estimates,
        )

    return BaseLoadEstimateResult(
        estimate_w=_median(tuple(value for _, value in daily_estimates)),
        unavailable_reason=None,
        window_start=window_start,
        window_end=window_end,
        eligible_days=len(daily_estimates),
        required_days=required_days,
        daily_estimates=daily_estimates,
    )


def duration_weighted_percentile(
    intervals: tuple[PowerInterval, ...],
    percentile: Decimal,
) -> Decimal:
    """Return a percentile interpolated between duration-weighted midpoints."""
    if not intervals or not Decimal(0) <= percentile <= Decimal(1):
        raise ValueError("invalid weighted percentile input")

    duration_by_power: dict[Decimal, Decimal] = {}
    for interval in intervals:
        duration_by_power[interval.mean_power_w] = duration_by_power.get(
            interval.mean_power_w,
            Decimal(0),
        ) + _seconds(interval.covered_duration)

    total_duration = sum(duration_by_power.values(), Decimal(0))
    points: list[tuple[Decimal, Decimal]] = []
    duration_before = Decimal(0)
    for power, duration in sorted(duration_by_power.items()):
        midpoint = (duration_before + duration / Decimal(2)) / total_duration
        points.append((midpoint, power))
        duration_before += duration

    if percentile <= points[0][0]:
        return points[0][1]
    if percentile >= points[-1][0]:
        return points[-1][1]

    for (lower_rank, lower_power), (upper_rank, upper_power) in zip(
        points,
        points[1:],
    ):
        if percentile <= upper_rank:
            fraction = (percentile - lower_rank) / (upper_rank - lower_rank)
            return lower_power + fraction * (upper_power - lower_power)

    raise AssertionError("weighted percentile interpolation failed")


def _median(values: tuple[Decimal, ...]) -> Decimal:
    """Return the exact median of a non-empty finite tuple."""
    if not values or any(not value.is_finite() for value in values):
        raise ValueError("invalid median input")
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / Decimal(2)


def _unavailable_daily(
    period_start: date,
    reason: DailyBaseLoadUnavailableReason,
    coverage_percent: Decimal,
    longest_uncovered_gap: timedelta,
) -> DailyBaseLoadSummary:
    """Return a consistent unavailable daily summary."""
    return DailyBaseLoadSummary(
        period_start=period_start,
        estimate_w=None,
        unavailable_reason=reason,
        coverage_percent=coverage_percent,
        longest_uncovered_gap=longest_uncovered_gap,
    )


def _seconds(value: timedelta) -> Decimal:
    """Return exact-enough decimal seconds for bounded interval arithmetic."""
    return Decimal(str(value.total_seconds()))


def _timedelta_from_decimal_seconds(value: Decimal) -> timedelta:
    """Restore decimal seconds without a binary floating-point conversion."""
    microseconds = value * Decimal(1_000_000)
    if not microseconds.is_finite() or microseconds != microseconds.to_integral_value():
        raise ValueError("invalid timedelta seconds")
    return timedelta(microseconds=int(microseconds))
