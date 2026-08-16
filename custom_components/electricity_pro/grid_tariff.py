"""Provider-independent grid-tariff schedules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal

_MonthDay = tuple[int, int]


@dataclass(frozen=True, slots=True)
class HighLowGridTariff:
    """Select a high or low per-kWh fee from a local wall-clock schedule.

    Weekdays use Python's convention where Monday is 0 and Sunday is 6.
    Public holidays and other non-working days are supplied as excluded dates
    so the calculation model does not contain country-specific calendar rules.
    """

    low_fee_per_kwh: Decimal
    high_fee_per_kwh: Decimal
    high_start_time: time
    high_end_time: time
    high_season_start: _MonthDay
    high_season_end: _MonthDay
    high_weekdays: frozenset[int] = field(
        default_factory=lambda: frozenset(range(5))
    )
    excluded_dates: frozenset[date] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Validate a deterministic and unambiguous schedule."""
        for fee in (self.low_fee_per_kwh, self.high_fee_per_kwh):
            if not fee.is_finite() or fee < 0:
                raise ValueError("Grid tariff fees must be finite and non-negative")

        if self.high_start_time == self.high_end_time:
            raise ValueError("High-period start and end times must differ")

        _validate_month_day(self.high_season_start)
        _validate_month_day(self.high_season_end)

        if not self.high_weekdays or any(
            weekday < 0 or weekday > 6 for weekday in self.high_weekdays
        ):
            raise ValueError("High-period weekdays must contain values from 0 to 6")

    def fee_at(self, local_at: datetime) -> Decimal:
        """Return the applicable fee for a timezone-aware local datetime."""
        if local_at.tzinfo is None or local_at.utcoffset() is None:
            raise ValueError("Grid tariff evaluation requires a local timezone")

        if (
            local_at.date() in self.excluded_dates
            or local_at.weekday() not in self.high_weekdays
            or not _month_day_in_period(
                (local_at.month, local_at.day),
                self.high_season_start,
                self.high_season_end,
            )
            or not _time_in_period(
                local_at.timetz().replace(tzinfo=None),
                self.high_start_time,
                self.high_end_time,
            )
        ):
            return self.low_fee_per_kwh

        return self.high_fee_per_kwh


def _validate_month_day(value: _MonthDay) -> None:
    """Validate a recurring month/day using a leap year."""
    month, day = value
    try:
        date(2000, month, day)
    except (TypeError, ValueError) as err:
        raise ValueError(
            "Grid tariff season dates must be valid month/day pairs"
        ) from err


def _month_day_in_period(
    value: _MonthDay,
    start: _MonthDay,
    end: _MonthDay,
) -> bool:
    """Return whether a month/day is in an inclusive recurring period."""
    if start <= end:
        return start <= value <= end
    return value >= start or value <= end


def _time_in_period(value: time, start: time, end: time) -> bool:
    """Return whether a time is in a half-open, possibly overnight period."""
    if start < end:
        return start <= value < end
    return value >= start or value < end
