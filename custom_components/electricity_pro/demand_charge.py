"""Estimate a monthly demand charge from complete hourly grid import blocks."""

from __future__ import annotations

import re
from calendar import monthrange
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

_HOUR = timedelta(hours=1)
_WEEKDAYS = frozenset(range(7))


@dataclass(frozen=True, slots=True)
class HourlyDemandTariff:
    """One local calendar-month tariff with a half-open window of start hours."""

    timezone: ZoneInfo
    peak_count: int
    rate_per_kw: Decimal
    currency: str
    weekdays: frozenset[int] = _WEEKDAYS
    start_hour: int = 0
    end_hour: int = 24

    def __post_init__(self) -> None:
        """Require an explicit, usable schedule and VAT-inclusive rate."""
        if not self.weekdays or not self.weekdays <= _WEEKDAYS:
            raise ValueError("Tariff weekdays must contain values from 0 to 6")
        if not 0 <= self.start_hour < self.end_hour <= 24:
            raise ValueError("Tariff hours must form a window within one local day")
        if self.peak_count < 1:
            raise ValueError("Tariff must require at least one daily peak")
        if not self.rate_per_kw.is_finite() or self.rate_per_kw < 0:
            raise ValueError("Tariff rate must be finite and non-negative")
        if not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise ValueError("Tariff currency must be a three-letter uppercase code")


def _to_utc(value: datetime) -> datetime:
    """Normalize a real instant, rejecting nonexistent local times."""
    zone = value.tzinfo
    if zone is None or value.utcoffset() is None:
        raise ValueError("Demand charge calculation requires timezone-aware timestamps")
    instant = value.astimezone(UTC)
    if instant.astimezone(zone).replace(tzinfo=None) != value.replace(tzinfo=None):
        raise ValueError("Demand charge timestamp falls in a local clock gap")
    return instant


@dataclass(frozen=True, slots=True)
class HourlyImportBlock:
    """Measured import energy over one elapsed hour, with UTC bounds."""

    start: datetime
    end: datetime
    energy_kwh: Decimal

    def __post_init__(self) -> None:
        """Validate the block and preserve both folds of a repeated hour."""
        start, end = _to_utc(self.start), _to_utc(self.end)
        if end - start != _HOUR:
            raise ValueError("An hourly import block must span one elapsed hour")
        if not self.energy_kwh.is_finite() or self.energy_kwh < 0:
            raise ValueError("Hourly import energy must be finite and non-negative")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)

    @property
    def average_kw(self) -> Decimal:
        """Energy divided by the block's one elapsed hour."""
        return self.energy_kwh


@dataclass(frozen=True, slots=True)
class HourlyDemandEstimate:
    """Selected peaks, cost and coverage through the calculation cutoff."""

    period_start: date
    period_end: date
    currency: str
    peaks: tuple[HourlyImportBlock, ...]
    eligible_blocks: int
    observed_blocks: int
    average_peak_kw: Decimal | None
    amount: Decimal | None

    @property
    def partial(self) -> bool:
        """Report whether any closed eligible block lacks usable data."""
        return self.observed_blocks < self.eligible_blocks


def _closed_tariff_hours(
    tariff: HourlyDemandTariff, month: date, last_day: int, cutoff: datetime
) -> dict[datetime, date]:
    """Map real UTC starts of closed tariff blocks to their local dates."""
    hours: dict[datetime, date] = {}
    for day in range(1, last_day + 1):
        local_date = month.replace(day=day)
        if local_date.weekday() not in tariff.weekdays:
            continue
        for hour in range(tariff.start_hour, tariff.end_hour):
            wall_start = datetime.combine(local_date, time(hour))
            for fold in (0, 1):
                start = wall_start.replace(
                    tzinfo=tariff.timezone, fold=fold
                ).astimezone(UTC)
                end = start + _HOUR
                if (
                    end > cutoff
                    or start.astimezone(tariff.timezone).replace(tzinfo=None)
                    != wall_start
                ):
                    continue
                local_end = end.astimezone(tariff.timezone)
                if local_end.minute or local_end.second:
                    raise ValueError("Tariff block ends between local hour boundaries")
                hours[start] = local_date
    return hours


def estimate_hourly_demand_charge(
    tariff: HourlyDemandTariff,
    month: date,
    as_of: datetime,
    blocks: Iterable[HourlyImportBlock],
) -> HourlyDemandEstimate:
    """Estimate one month using the highest eligible block per local day."""
    if month.day != 1:
        raise ValueError("The billing month must start on the first local day")
    cutoff = _to_utc(as_of)
    last_day = monthrange(month.year, month.month)[1]
    eligible = _closed_tariff_hours(tariff, month, last_day, cutoff)

    observed: dict[datetime, HourlyImportBlock | None] = {}
    for block in blocks:
        if block.start in eligible:
            if block.start not in observed:
                observed[block.start] = block
            elif observed[block.start] != block:
                # Conflicting measurements make this hour a coverage gap.
                observed[block.start] = None

    # UTC start breaks ties in favor of the earliest block.
    ranked = sorted(
        (block for block in observed.values() if block is not None),
        key=lambda block: (block.average_kw.copy_negate(), block.start),
    )
    daily_peaks: dict[date, HourlyImportBlock] = {}
    for block in ranked:
        daily_peaks.setdefault(eligible[block.start], block)
        if len(daily_peaks) == tariff.peak_count:
            break

    peaks = tuple(daily_peaks.values())
    average_kw = amount = None
    if len(peaks) == tariff.peak_count:
        total_kw = sum((block.average_kw for block in peaks), Decimal(0))
        average_kw = total_kw / tariff.peak_count
        amount = total_kw * tariff.rate_per_kw / tariff.peak_count

    return HourlyDemandEstimate(
        period_start=month,
        period_end=month.replace(day=last_day),
        currency=tariff.currency,
        peaks=peaks,
        eligible_blocks=len(eligible),
        observed_blocks=len(ranked),
        average_peak_kw=average_kw,
        amount=amount,
    )
