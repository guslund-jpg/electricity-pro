"""Foundation for statistics derived from cumulative measurements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any


class CalendarPeriod(StrEnum):
    """Supported calendar periods."""

    DAY = "day"
    MONTH = "month"

    def start(self, now: datetime) -> date:
        """Return the local start date for this period."""
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("period calculation requires a timezone-aware datetime")

        if self is CalendarPeriod.DAY:
            return now.date()

        return now.date().replace(day=1)


@dataclass(frozen=True, slots=True)
class StatisticsSnapshot:
    """Persisted state for one cumulative statistic."""

    period_start: date
    last_value: Decimal
    value: Decimal

    def as_dict(self) -> dict[str, str]:
        """Return a storage-safe representation of the snapshot."""
        return {
            "period_start": self.period_start.isoformat(),
            "last_value": str(self.last_value),
            "value": str(self.value),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatisticsSnapshot:
        """Restore a snapshot from storage."""
        try:
            period_start = date.fromisoformat(data["period_start"])
            last_value = Decimal(data["last_value"])
            value = Decimal(data["value"])
        except (InvalidOperation, TypeError, ValueError, KeyError) as err:
            raise ValueError("invalid statistics snapshot") from err

        if (
            not last_value.is_finite()
            or not value.is_finite()
            or last_value < 0
            or value < 0
        ):
            raise ValueError("invalid statistics snapshot")

        return cls(
            period_start=period_start,
            last_value=last_value,
            value=value,
        )


class CumulativeStatistic:
    """Accumulate deltas from a non-negative cumulative measurement."""

    def __init__(
        self,
        period: CalendarPeriod,
        snapshot: StatisticsSnapshot | None = None,
    ) -> None:
        """Initialize the statistic, optionally from persisted state."""
        self._period = period
        self._snapshot = snapshot

    @property
    def snapshot(self) -> StatisticsSnapshot | None:
        """Return the current persistable state."""
        return self._snapshot

    @property
    def value(self) -> Decimal | None:
        """Return the accumulated value for the current period."""
        if self._snapshot is None:
            return None
        return self._snapshot.value

    def update(self, measurement: Decimal, now: datetime) -> Decimal:
        """Apply a cumulative measurement and return the period value."""
        if not measurement.is_finite() or measurement < 0:
            raise ValueError("measurement must be a non-negative finite value")

        period_start = self._period.start(now)
        previous = self._snapshot

        if previous is None:
            value = Decimal(0)
        else:
            delta = (
                measurement - previous.last_value
                if measurement >= previous.last_value
                else measurement
            )
            value = (
                previous.value + delta
                if previous.period_start == period_start
                else delta
            )

        self._snapshot = StatisticsSnapshot(
            period_start=period_start,
            last_value=measurement,
            value=value,
        )
        return value
