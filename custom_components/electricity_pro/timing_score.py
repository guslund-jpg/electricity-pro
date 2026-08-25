"""Pure models for retrospective consumption-timing analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum

_SECONDS_PER_HOUR = Decimal(3600)
_WATTS_PER_KILOWATT = Decimal(1000)
_ONE_HUNDRED = Decimal(100)
_DEFAULT_MINIMUM_COVERAGE = Decimal("0.90")
_DEFAULT_MINIMUM_PRICE_VARIATION = Decimal("0.02")
_DEFAULT_MAXIMUM_GAP = timedelta(hours=1)
_BUCKET_SECONDS = 15 * 60


class TimingScoreUnavailableReason(StrEnum):
    """Reasons a timing score cannot be published."""

    INSUFFICIENT_COVERAGE = "insufficient_coverage"
    LONG_DATA_GAP = "long_data_gap"
    NO_CONSUMPTION = "no_consumption"
    INSUFFICIENT_PRICE_VARIATION = "insufficient_price_variation"


class TimingScoreRating(StrEnum):
    """Plain-language rating for a timing score."""

    WELL_TIMED = "well_timed"
    MIXED_TIMING = "mixed_timing"
    COSTLY_TIMING = "costly_timing"


@dataclass(frozen=True, slots=True)
class TimingInterval:
    """One aggregate interval with matched energy and Effective Price."""

    energy_kwh: Decimal
    effective_price: Decimal
    covered_duration: timedelta

    def __post_init__(self) -> None:
        """Validate interval values."""
        if (
            not self.energy_kwh.is_finite()
            or self.energy_kwh < 0
            or not self.effective_price.is_finite()
            or self.covered_duration <= timedelta(0)
        ):
            raise ValueError("invalid timing interval")


@dataclass(frozen=True, slots=True)
class TimingScoreResult:
    """Calculated score and the compact metadata needed to explain it."""

    score: Decimal | None
    unavailable_reason: TimingScoreUnavailableReason | None
    coverage_percent: Decimal
    energy_kwh: Decimal
    consumption_weighted_price: Decimal | None
    time_weighted_price: Decimal | None
    price_variation_percent: Decimal | None
    rating: TimingScoreRating | None


def calculate_timing_score(
    intervals: tuple[TimingInterval, ...],
    *,
    period_duration: timedelta,
    longest_uncovered_gap: timedelta,
    minimum_coverage: Decimal = _DEFAULT_MINIMUM_COVERAGE,
    maximum_gap: timedelta = _DEFAULT_MAXIMUM_GAP,
    minimum_price_variation: Decimal = _DEFAULT_MINIMUM_PRICE_VARIATION,
) -> TimingScoreResult:
    """Calculate a provider-independent score for one completed local day."""
    if period_duration <= timedelta(0) or longest_uncovered_gap < timedelta(0):
        raise ValueError("invalid timing-score period")

    covered_seconds = sum(
        (_seconds(interval.covered_duration) for interval in intervals),
        Decimal(0),
    )
    period_seconds = _seconds(period_duration)
    coverage = min(covered_seconds / period_seconds, Decimal(1))
    coverage_percent = coverage * _ONE_HUNDRED
    energy = sum((interval.energy_kwh for interval in intervals), Decimal(0))

    if coverage < minimum_coverage:
        return _unavailable(
            TimingScoreUnavailableReason.INSUFFICIENT_COVERAGE,
            coverage_percent,
            energy,
        )
    if longest_uncovered_gap > maximum_gap:
        return _unavailable(
            TimingScoreUnavailableReason.LONG_DATA_GAP,
            coverage_percent,
            energy,
        )
    if energy <= 0:
        return _unavailable(
            TimingScoreUnavailableReason.NO_CONSUMPTION,
            coverage_percent,
            energy,
        )

    time_weighted_price = (
        sum(
            (
                interval.effective_price
                * _seconds(interval.covered_duration)
                for interval in intervals
            ),
            Decimal(0),
        )
        / covered_seconds
    )
    consumption_weighted_price = (
        sum(
            (interval.effective_price * interval.energy_kwh for interval in intervals),
            Decimal(0),
        )
        / energy
    )
    mean_absolute_price = (
        sum(
            (
                abs(interval.effective_price)
                * _seconds(interval.covered_duration)
                for interval in intervals
            ),
            Decimal(0),
        )
        / covered_seconds
    )
    prices = [interval.effective_price for interval in intervals]
    price_range = max(prices) - min(prices)
    variation = (
        price_range / mean_absolute_price
        if mean_absolute_price > 0
        else Decimal(0)
    )
    variation_percent = variation * _ONE_HUNDRED
    if variation < minimum_price_variation:
        return TimingScoreResult(
            score=None,
            unavailable_reason=(
                TimingScoreUnavailableReason.INSUFFICIENT_PRICE_VARIATION
            ),
            coverage_percent=coverage_percent,
            energy_kwh=energy,
            consumption_weighted_price=consumption_weighted_price,
            time_weighted_price=time_weighted_price,
            price_variation_percent=variation_percent,
            rating=None,
        )

    ranks = _duration_weighted_midranks(intervals, covered_seconds)
    energy_weighted_rank = sum(
        (
            interval.energy_kwh * ranks[interval.effective_price]
            for interval in intervals
        ),
        Decimal(0),
    ) / energy
    score = (_ONE_HUNDRED * (Decimal(1) - energy_weighted_rank)).quantize(
        Decimal(1),
        rounding=ROUND_HALF_UP,
    )

    return TimingScoreResult(
        score=score,
        unavailable_reason=None,
        coverage_percent=coverage_percent,
        energy_kwh=energy,
        consumption_weighted_price=consumption_weighted_price,
        time_weighted_price=time_weighted_price,
        price_variation_percent=variation_percent,
        rating=_rating(score),
    )


def _duration_weighted_midranks(
    intervals: tuple[TimingInterval, ...],
    total_duration_seconds: Decimal,
) -> dict[Decimal, Decimal]:
    """Return midpoint percentile ranks grouped by exact price."""
    duration_by_price: dict[Decimal, Decimal] = {}
    for interval in intervals:
        duration_by_price[interval.effective_price] = duration_by_price.get(
            interval.effective_price,
            Decimal(0),
        ) + _seconds(interval.covered_duration)

    ranks: dict[Decimal, Decimal] = {}
    cheaper_duration = Decimal(0)
    for price, duration in sorted(duration_by_price.items()):
        ranks[price] = (cheaper_duration + duration / 2) / total_duration_seconds
        cheaper_duration += duration
    return ranks


def _unavailable(
    reason: TimingScoreUnavailableReason,
    coverage_percent: Decimal,
    energy_kwh: Decimal,
) -> TimingScoreResult:
    """Build a result without price metadata that cannot be trusted."""
    return TimingScoreResult(
        score=None,
        unavailable_reason=reason,
        coverage_percent=coverage_percent,
        energy_kwh=energy_kwh,
        consumption_weighted_price=None,
        time_weighted_price=None,
        price_variation_percent=None,
        rating=None,
    )


def _rating(score: Decimal) -> TimingScoreRating:
    """Return the presentation rating for a valid score."""
    if score >= 75:
        return TimingScoreRating.WELL_TIMED
    if score >= 40:
        return TimingScoreRating.MIXED_TIMING
    return TimingScoreRating.COSTLY_TIMING


def _seconds(duration: timedelta) -> Decimal:
    """Return exact-enough Decimal seconds for datetime arithmetic."""
    return Decimal(str(duration.total_seconds()))


@dataclass(slots=True)
class _MutableBucket:
    """Mutable aggregate used internally while building timing intervals."""

    energy_kwh: Decimal = Decimal(0)
    price_seconds: Decimal = Decimal(0)
    covered_seconds: Decimal = Decimal(0)


class TimingBucketAccumulator:
    """Aggregate valid power-price segments into bounded 15-minute buckets."""

    def __init__(self, local_timezone: tzinfo) -> None:
        """Initialize an empty accumulator."""
        self._local_timezone = local_timezone
        self._buckets: dict[tuple[date, datetime], _MutableBucket] = {}

    def add_segment(
        self,
        *,
        start: datetime,
        end: datetime,
        power_w: Decimal,
        effective_price: Decimal,
    ) -> None:
        """Add one valid constant-power, constant-price segment."""
        if (
            start.tzinfo is None
            or start.utcoffset() is None
            or end.tzinfo is None
            or end.utcoffset() is None
            or end <= start
            or not power_w.is_finite()
            or power_w < 0
            or not effective_price.is_finite()
        ):
            raise ValueError("invalid timing segment")

        cursor = start.astimezone(UTC)
        utc_end = end.astimezone(UTC)
        while cursor < utc_end:
            timestamp = int(cursor.timestamp())
            bucket_timestamp = timestamp - timestamp % _BUCKET_SECONDS
            bucket_start = datetime.fromtimestamp(bucket_timestamp, tz=UTC)
            bucket_end = bucket_start + timedelta(seconds=_BUCKET_SECONDS)
            segment_end = min(bucket_end, utc_end)
            seconds = _seconds(segment_end - cursor)
            local_date = cursor.astimezone(self._local_timezone).date()
            bucket = self._buckets.setdefault(
                (local_date, bucket_start),
                _MutableBucket(),
            )
            bucket.energy_kwh += (
                power_w * seconds / _SECONDS_PER_HOUR / _WATTS_PER_KILOWATT
            )
            bucket.price_seconds += effective_price * seconds
            bucket.covered_seconds += seconds
            cursor = segment_end

    def intervals_for_date(self, period_start: date) -> tuple[TimingInterval, ...]:
        """Return immutable ordered aggregates for one local date."""
        matching = sorted(
            (
                (bucket_start, bucket)
                for (stored_date, bucket_start), bucket in self._buckets.items()
                if stored_date == period_start
            ),
            key=lambda item: item[0],
        )
        return tuple(
            TimingInterval(
                energy_kwh=bucket.energy_kwh,
                effective_price=bucket.price_seconds / bucket.covered_seconds,
                covered_duration=timedelta(seconds=float(bucket.covered_seconds)),
            )
            for _, bucket in matching
        )
