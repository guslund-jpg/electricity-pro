"""Bounded, provider-independent lifetime directional energy tracking."""

from datetime import date, datetime
from decimal import Decimal


class FlowCounter:
    """Track observed increments without billing recovery or boundary gaps.

    These first-increment totals are always partial: no historical backfill or
    inferred midnight reading is provided. Sources are scoped by the caller.
    """

    def __init__(self) -> None:
        self.day: str | None = None
        self.month: str | None = None
        self.high_water: Decimal | None = None
        self.today = Decimal(0)
        self.this_month = Decimal(0)
        self.started: str | None = None
        self.pending_boundary = True
        self.generation = 0
        self.reason = "waiting_for_baseline"

    def update(self, meter: Decimal | None, now: datetime) -> bool:
        """Return whether this observation is safe to expose as current totals."""
        day = now.date().isoformat()
        if self.day is not None and day < self.day:
            self.reason = "out_of_order"
            return False
        if self.day != day:
            self.day = day
            self.today = Decimal(0)
            self.pending_boundary = True
        if self.month != day[:7]:
            self.month = day[:7]
            self.this_month = Decimal(0)
        if meter is None or not meter.is_finite() or meter < 0:
            self.reason = "invalid_or_missing_source"
            return False
        if self.high_water is not None and meter < self.high_water:
            self.reason = "backward_reading"
            return False
        if self.started is None:
            self.started = now.isoformat()
        if self.high_water is not None and not self.pending_boundary:
            delta = meter - self.high_water
            self.today += delta
            self.this_month += delta
        self.high_water = meter
        self.pending_boundary = False
        self.reason = "partial"
        return True

    def confirm_reset(self, meter: Decimal, now: datetime) -> None:
        """Accept a verified meter replacement without clearing known totals."""
        if not meter.is_finite() or meter < 0:
            raise ValueError("A valid lifetime reading is required")
        self.update(None, now)
        if self.reason == "out_of_order":
            raise ValueError("Cannot reset a meter before its tracked period")
        self.high_water = meter
        self.pending_boundary = False
        self.started = self.started or now.isoformat()
        self.generation += 1
        self.reason = "partial"

    def as_dict(self) -> dict:
        """Persist constant-size state, not a sample history."""
        return {
            "day": self.day, "month": self.month,
            "high_water": str(self.high_water) if self.high_water is not None else None,
            "today": str(self.today), "this_month": str(self.this_month),
            "started": self.started, "pending_boundary": self.pending_boundary,
            "generation": self.generation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FlowCounter":
        """Reject malformed persistence instead of reviving invalid counters."""
        result = cls()
        day = data["day"]
        if day is not None:
            date.fromisoformat(day)
        if data["month"] != (day[:7] if day else None):
            raise ValueError("Mismatched flow periods")
        result.day, result.month = day, data["month"]
        for name in ("high_water", "today", "this_month"):
            raw = data[name]
            if name == "high_water" and raw is None:
                continue
            value = Decimal(raw)
            if not value.is_finite() or value < 0:
                raise ValueError("Invalid flow total")
            setattr(result, name, value)
        started = data["started"]
        if started is not None and datetime.fromisoformat(started).tzinfo is None:
            raise ValueError("Naive tracking timestamp")
        if type(data["pending_boundary"]) is not bool:
            raise ValueError("Invalid boundary flag")
        generation = data["generation"]
        if type(generation) is not int or generation < 0:
            raise ValueError("Invalid meter generation")
        result.started = started
        result.pending_boundary = data["pending_boundary"]
        result.generation = generation
        return result
