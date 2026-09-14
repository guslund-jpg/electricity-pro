"""Bounded estimates from observed energy deltas and price intervals."""

from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any


class CostLedger:
    """Allocate a meter delta uniformly over its observed price intervals.

    Open intervals are deliberately not restored after restart. Unobserved
    consumption is excluded rather than priced retrospectively at today's rate.
    """

    def __init__(self) -> None:
        self.day: str | None = None
        self.month: str | None = None
        self.daily_supplier = Decimal(0)
        self.monthly_supplier = Decimal(0)
        self.daily_effective = Decimal(0)
        self.daily_energy = Decimal(0)
        self.daily_supplier_energy = Decimal(0)
        self.monthly_supplier_energy = Decimal(0)
        self.unit: str | None = None
        self._meter: Decimal | None = None
        self._at: datetime | None = None
        self._segments: list[tuple[datetime, Decimal | None, Decimal | None]] = []
        self._discard_next_delta = False

    def update(
        self, now: datetime, meter: Decimal | None, supplier: Decimal | None,
        effective: Decimal | None, unit: str | None, *, lifetime: bool,
    ) -> None:
        """Apply readings; gaps over 15 minutes and meter resets are unpriced."""
        if unit is not None and self.unit not in (None, unit):
            self.__init__()
        if unit is not None:
            self.unit = unit
        if self.day != now.date().isoformat():
            self.day = now.date().isoformat()
            self.daily_supplier = self.daily_effective = self.daily_energy = Decimal(0)
            self.daily_supplier_energy = Decimal(0)
        if self.month != self.day[:7]:
            self.month = self.day[:7]
            self.monthly_supplier = self.monthly_supplier_energy = Decimal(0)
        if unit is None:
            supplier = effective = None
        if meter is None or not meter.is_finite() or meter < 0:
            self._meter = self._at = None
            self._segments = []
            return
        if self._at is None or self._meter is None:
            self._baseline(now, meter, supplier, effective)
            return
        seconds = Decimal(str(now.timestamp() - self._at.timestamp()))
        if seconds < 0 or seconds > 900:
            self._discard_next_delta = meter == self._meter
            self._baseline(now, meter, supplier, effective)
            return
        if self._discard_next_delta and meter != self._meter:
            self._discard_next_delta = False
            self._baseline(now, meter, supplier, effective)
            return
        if not lifetime and now.date() != self._at.date() and meter >= self._meter:
            # The provider may still expose yesterday's total after midnight.
            # Do not treat that stale daily total as today's consumption.
            if self._segments[-1][1:] != (supplier, effective):
                self._segments.append((now, supplier, effective))
                if len(self._segments) > 256:
                    self._discard_next_delta = True
                    self._baseline(now, meter, supplier, effective)
            return
        if meter < self._meter:
            # Daily sources reset at midnight; the new reading covers only today.
            if not lifetime and now.date() != self._at.date():
                midnight = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
                self._meter = Decimal(0)
                self._at = midnight
                prices = self._segments[0][1:]
                for at, sp, ep in self._segments:
                    if at.timestamp() <= midnight.timestamp():
                        prices = (sp, ep)
                self._segments = [
                    (midnight, *prices),
                    *[segment for segment in self._segments
                      if segment[0].timestamp() > midnight.timestamp()],
                ]
                seconds = Decimal(str(now.timestamp() - midnight.timestamp()))
            else:
                self._baseline(now, meter, supplier, effective)
                return
        if meter != self._meter and seconds > 0:
            delta = meter - self._meter
            points = [*self._segments, (now, supplier, effective)]
            for (start, sp, ep), (end, _, _) in zip(points, points[1:]):
                while start.timestamp() < end.timestamp():
                    midnight = datetime.combine(
                        start.date() + timedelta(days=1), time.min, tzinfo=start.tzinfo,
                    )
                    stop = min(end, midnight, key=lambda value: value.timestamp())
                    energy = delta * Decimal(str(stop.timestamp() - start.timestamp())) / seconds
                    if sp is not None and sp.is_finite():
                        if start.date().isoformat()[:7] == self.month:
                            self.monthly_supplier += energy * sp
                            self.monthly_supplier_energy += energy
                        if start.date().isoformat() == self.day:
                            self.daily_supplier += energy * sp
                            self.daily_supplier_energy += energy
                    if ep is not None and ep.is_finite() and start.date().isoformat() == self.day:
                        self.daily_effective += energy * ep
                        self.daily_energy += energy
                    start = stop
            self._baseline(now, meter, supplier, effective)
        elif not self._segments or self._segments[-1][1:] != (supplier, effective):
            self._segments.append((now, supplier, effective))
            if len(self._segments) > 256:
                self._discard_next_delta = True
                self._baseline(now, meter, supplier, effective)

    def _baseline(self, now, meter, supplier, effective) -> None:
        self._meter, self._at = meter, now
        self._segments = [(now, supplier, effective)]

    def as_dict(self) -> dict[str, Any]:
        """Persist bounded totals, never an open pricing interval."""
        return {
            "day": self.day, "month": self.month, "unit": self.unit,
            **{name: str(getattr(self, name)) for name in (
                "daily_supplier", "monthly_supplier", "daily_effective",
                "daily_energy", "daily_supplier_energy", "monthly_supplier_energy",
            )},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CostLedger":
        """Validate totals before restoring; signed costs support negative prices."""
        ledger = cls()
        for key in ("day", "month", "unit"):
            value = data.get(key)
            if value is not None and not isinstance(value, str):
                raise ValueError("Invalid cost metadata")
            setattr(ledger, key, value)
        for key in (
            "daily_supplier", "monthly_supplier", "daily_effective",
            "daily_energy", "daily_supplier_energy", "monthly_supplier_energy",
        ):
            value = Decimal(data[key])
            if not value.is_finite() or ("energy" in key and value < 0):
                raise ValueError("Invalid cost totals")
            setattr(ledger, key, value)
        return ledger
