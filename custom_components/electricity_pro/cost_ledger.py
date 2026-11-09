"""Bounded estimates from observed energy deltas and price intervals."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal

from .history_storage import stored_decimal, stored_record, stored_string
from .monthly_cost_archive import MonthlyVariableCostArchive
from .pricing import EffectivePriceBreakdown, VariableCostComponent

type _PriceSample = tuple[
    Decimal | None, Decimal | None, EffectivePriceBreakdown | None
]


@dataclass(frozen=True, slots=True)
class VariableCostSummary:
    """Published component amounts and their coverage for one period."""

    started_at: datetime
    priced_kwh: Decimal
    covered_cost: Decimal
    components: tuple[tuple[VariableCostComponent, Decimal], ...]


class _VariableCostPeriod:
    """Keep the component coverage of one local calendar period."""

    def __init__(self) -> None:
        self.started_at: datetime | None = None
        self.priced_kwh = Decimal(0)
        self.covered_cost = Decimal(0)
        self.components: dict[VariableCostComponent, Decimal] = {}

    def add(
        self,
        start: datetime,
        energy: Decimal,
        cost: Decimal,
        amounts: tuple[tuple[VariableCostComponent, Decimal], ...],
    ) -> None:
        if self.started_at is None:
            self.started_at = start
        self.priced_kwh += energy
        self.covered_cost += cost
        for component, amount in amounts:
            self.components[component] = (
                self.components.get(component, Decimal(0)) + amount
            )

    def as_dict(self) -> dict[str, object] | None:
        if self.started_at is None:
            return None
        return {
            "started_at": self.started_at.isoformat(),
            "priced_kwh": str(self.priced_kwh),
            "covered_cost": str(self.covered_cost),
            "components": {
                key.value: str(value) for key, value in self.components.items()
            },
        }

    @classmethod
    def from_dict(
        cls, value: object, period: str | None, priced_energy: Decimal
    ) -> "_VariableCostPeriod":
        result = cls()
        if value is None:
            return result
        data = stored_record(value)
        start = datetime.fromisoformat(stored_string(data["started_at"]))
        kwh = stored_decimal(data["priced_kwh"])
        cost = stored_decimal(data["covered_cost"])
        components = {
            VariableCostComponent(key): stored_decimal(amount)
            for key, amount in stored_record(data["components"]).items()
        }
        if (
            period is None
            or start.utcoffset() is None
            or start.date().isoformat()[: len(period)] != period
            or not kwh.is_finite()
            or not Decimal(0) < kwh <= priced_energy
            or not cost.is_finite()
            or not components
            or any(not amount.is_finite() for amount in components.values())
        ):
            raise ValueError("Invalid variable cost component totals")
        result.started_at = start
        result.priced_kwh = kwh
        result.covered_cost = cost
        result.components = components
        return result


class CostLedger:
    """Allocate a meter delta uniformly over its observed price intervals.

    Open intervals are deliberately not restored after restart. Unobserved
    consumption is excluded rather than priced retrospectively at today's rate.
    """

    def __init__(self) -> None:
        self._reset()

    @property
    def monthly_variable_cost(self) -> VariableCostSummary | None:
        """Snapshot the recorded components without sharing mutable ledger state."""
        period = self._monthly_components
        if period.started_at is None:
            return None
        return VariableCostSummary(
            period.started_at,
            period.priced_kwh,
            period.covered_cost,
            tuple(period.components.items()),
        )

    def _reset(self) -> None:
        """Clear totals and observation state when starting a new currency."""
        self.day: str | None = None
        self.month: str | None = None
        self.daily_supplier = Decimal(0)
        self.monthly_supplier = Decimal(0)
        self.daily_effective = Decimal(0)
        self.monthly_effective = Decimal(0)
        self.monthly_energy = Decimal(0)
        self.daily_energy = Decimal(0)
        self.daily_supplier_energy = Decimal(0)
        self.monthly_supplier_energy = Decimal(0)
        self._daily_components = _VariableCostPeriod()
        self._monthly_components = _VariableCostPeriod()
        self.unit: str | None = None
        self._meter: Decimal | None = None
        self._at: datetime | None = None
        self._segments: list[tuple[datetime, _PriceSample]] = []
        self._discard_next_delta = False
        self._lifetime_high_water: Decimal | None = None

    def update(
        self,
        now: datetime,
        meter: Decimal | None,
        supplier: Decimal | None,
        effective: Decimal | None,
        unit: str | None,
        *,
        lifetime: bool,
        breakdown: EffectivePriceBreakdown | None = None,
        monthly_archive: MonthlyVariableCostArchive | None = None,
    ) -> None:
        """Apply readings; gaps over 15 minutes and meter resets are unpriced."""
        if unit is not None and self.unit not in (None, unit):
            self._reset()
        if unit is not None:
            self.unit = unit
        if self.day != now.date().isoformat():
            self.day = now.date().isoformat()
            self.daily_supplier = self.daily_effective = self.daily_energy = Decimal(0)
            self.daily_supplier_energy = Decimal(0)
            self._daily_components = _VariableCostPeriod()
        if self.month != self.day[:7]:
            self.month = self.day[:7]
            self.monthly_supplier = self.monthly_supplier_energy = Decimal(0)
            self.monthly_effective = self.monthly_energy = Decimal(0)
            self._monthly_components = _VariableCostPeriod()
        if unit is None:
            supplier = effective = None
        if breakdown is not None and breakdown.total != effective:
            breakdown = None
        prices = (supplier, effective, breakdown)
        if lifetime and meter is not None and meter.is_finite() and meter >= 0:
            if (
                self._lifetime_high_water is not None
                and meter < self._lifetime_high_water
            ):
                # Reject stale/backward readings before any gap can rebaseline us.
                # Pricing across the suspect interval is deliberately omitted.
                self._meter = self._at = None
                self._segments = []
                return
            self._lifetime_high_water = meter
        if meter is None or not meter.is_finite() or meter < 0:
            self._meter = self._at = None
            self._segments = []
            return
        if self._at is None or self._meter is None:
            self._baseline(now, meter, prices)
            return
        seconds = Decimal(str(now.timestamp() - self._at.timestamp()))
        if seconds < 0 or seconds > 900:
            self._discard_next_delta = meter == self._meter
            self._baseline(now, meter, prices)
            return
        if self._discard_next_delta and meter != self._meter:
            self._discard_next_delta = False
            self._baseline(now, meter, prices)
            return
        if not lifetime and now.date() != self._at.date() and meter >= self._meter:
            # The provider may still expose yesterday's total after midnight.
            # Do not treat that stale daily total as today's consumption.
            if self._segments[-1][1] != prices:
                self._segments.append((now, prices))
                if len(self._segments) > 256:
                    self._discard_next_delta = True
                    self._baseline(now, meter, prices)
            return
        if meter < self._meter:
            # Daily sources reset at midnight; the new reading covers only today.
            if not lifetime and now.date() != self._at.date():
                midnight = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
                self._meter = Decimal(0)
                self._at = midnight
                midnight_prices = self._segments[0][1]
                for at, observation in self._segments:
                    if at.timestamp() <= midnight.timestamp():
                        midnight_prices = observation
                self._segments = [
                    (midnight, midnight_prices),
                    *[
                        segment
                        for segment in self._segments
                        if segment[0].timestamp() > midnight.timestamp()
                    ],
                ]
                seconds = Decimal(str(now.timestamp() - midnight.timestamp()))
            else:
                self._baseline(now, meter, prices)
                return
        if meter != self._meter and seconds > 0:
            delta = meter - self._meter
            points = [*self._segments, (now, prices)]
            for (start, (sp, ep, parts)), (end, _) in zip(points, points[1:]):
                while start.timestamp() < end.timestamp():
                    midnight = datetime.combine(
                        start.date() + timedelta(days=1),
                        time.min,
                        tzinfo=start.tzinfo,
                    )
                    stop = min(end, midnight, key=lambda value: value.timestamp())
                    energy = (
                        delta
                        * Decimal(str(stop.timestamp() - start.timestamp()))
                        / seconds
                    )
                    day = start.date().isoformat()
                    same_month = day[:7] == self.month
                    same_day = day == self.day
                    if sp is not None and sp.is_finite():
                        if same_month:
                            self.monthly_supplier += energy * sp
                            self.monthly_supplier_energy += energy
                        if same_day:
                            self.daily_supplier += energy * sp
                            self.daily_supplier_energy += energy
                    if ep is not None and ep.is_finite():
                        cost = energy * ep
                        amounts = (
                            tuple(
                                (key, energy * rate) for key, rate in parts.components
                            )
                            if parts is not None
                            else ()
                        )
                        if (
                            amounts
                            and monthly_archive is not None
                            and self.unit is not None
                            and energy > 0
                        ):
                            # A reading just after midnight can close a priced
                            # slice in the previous month as well as the new one.
                            monthly_archive.record(
                                start, stop, self.unit, energy, amounts
                            )
                        if same_month:
                            self.monthly_effective += cost
                            self.monthly_energy += energy
                            if amounts:
                                self._monthly_components.add(
                                    start, energy, cost, amounts
                                )
                        if same_day:
                            self.daily_effective += cost
                            self.daily_energy += energy
                            if amounts:
                                self._daily_components.add(start, energy, cost, amounts)
                    start = stop
            self._baseline(now, meter, prices)
        elif not self._segments or self._segments[-1][1] != prices:
            self._segments.append((now, prices))
            if len(self._segments) > 256:
                self._discard_next_delta = True
                self._baseline(now, meter, prices)

    def _baseline(
        self,
        now: datetime,
        meter: Decimal,
        prices: _PriceSample,
    ) -> None:
        self._meter, self._at = meter, now
        self._segments = [(now, prices)]

    def confirm_meter_reset(self, meter: Decimal) -> None:
        """Accept an explicitly confirmed replacement; preserve known totals."""
        if not meter.is_finite() or meter < 0:
            raise ValueError("A valid lifetime meter reading is required")
        self._lifetime_high_water = meter
        self._meter = self._at = None
        self._segments = []
        self._discard_next_delta = False

    def as_dict(self) -> dict[str, object]:
        """Persist bounded totals, never an open pricing interval."""
        data: dict[str, object] = {
            "day": self.day,
            "month": self.month,
            "unit": self.unit,
            "lifetime_high_water": (
                str(self._lifetime_high_water)
                if self._lifetime_high_water is not None
                else None
            ),
            "daily_supplier": str(self.daily_supplier),
            "monthly_supplier": str(self.monthly_supplier),
            "daily_effective": str(self.daily_effective),
            "daily_energy": str(self.daily_energy),
            "daily_supplier_energy": str(self.daily_supplier_energy),
            "monthly_supplier_energy": str(self.monthly_supplier_energy),
            "monthly_effective": str(self.monthly_effective),
            "monthly_energy": str(self.monthly_energy),
        }
        daily = self._daily_components.as_dict()
        monthly = self._monthly_components.as_dict()
        if daily is not None or monthly is not None:
            data["variable_cost_breakdown"] = {
                "version": 1,
                "daily": daily,
                "monthly": monthly,
            }
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CostLedger":
        """Validate totals before restoring; signed costs support negative prices."""
        ledger = cls()
        raw_high_water = data.get("lifetime_high_water")
        if raw_high_water is not None:
            high_water = stored_decimal(raw_high_water)
            if not high_water.is_finite() or high_water < 0:
                raise ValueError("Invalid lifetime meter baseline")
            ledger._lifetime_high_water = high_water

        def metadata(key: str) -> str | None:
            value = data.get(key)
            return stored_string(value) if value is not None else None

        ledger.day = metadata("day")
        ledger.month = metadata("month")
        ledger.unit = metadata("unit")

        def total(key: str) -> Decimal:
            if key in ("monthly_effective", "monthly_energy") and key not in data:
                # Keep the known current day as partial monthly coverage;
                # never infer earlier days from supplier-only totals.
                same_month = ledger.day is not None and ledger.day[:7] == ledger.month
                daily_key = (
                    "daily_effective" if key == "monthly_effective" else "daily_energy"
                )
                value = stored_decimal(data.get(daily_key, "0") if same_month else "0")
            else:
                value = stored_decimal(data[key])
            if not value.is_finite() or ("energy" in key and value < 0):
                raise ValueError("Invalid cost totals")
            return value

        ledger.daily_supplier = total("daily_supplier")
        ledger.monthly_supplier = total("monthly_supplier")
        ledger.daily_effective = total("daily_effective")
        ledger.daily_energy = total("daily_energy")
        ledger.daily_supplier_energy = total("daily_supplier_energy")
        ledger.monthly_supplier_energy = total("monthly_supplier_energy")
        ledger.monthly_effective = total("monthly_effective")
        ledger.monthly_energy = total("monthly_energy")
        raw_breakdown = data.get("variable_cost_breakdown")
        if raw_breakdown is None:
            return ledger
        try:
            breakdown = stored_record(raw_breakdown)
            if breakdown.get("version") == 1:
                daily = _VariableCostPeriod.from_dict(
                    breakdown.get("daily"), ledger.day, ledger.daily_energy
                )
                monthly = _VariableCostPeriod.from_dict(
                    breakdown.get("monthly"), ledger.month, ledger.monthly_energy
                )
                ledger._daily_components, ledger._monthly_components = daily, monthly
        except KeyError, ValueError, TypeError, ArithmeticError:
            # The optional breakdown must not invalidate the existing totals.
            pass
        return ledger
