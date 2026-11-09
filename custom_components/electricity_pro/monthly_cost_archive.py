"""Bounded, calendar-keyed variable cost data for monthly charts."""

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from .history_storage import stored_decimal, stored_record, stored_string
from .pricing import VariableCostComponent
from .statistics_engine import CalendarPeriod

_WINDOW_MONTHS = 12


def _month_number(day: date) -> int:
    return day.year * 12 + day.month


def _at_month_start(instant: datetime) -> bool:
    return instant.day == 1 and instant.time() == time.min


@dataclass(frozen=True, slots=True)
class MonthlyVariableCost:
    """Recorded portions of one local calendar month in a single currency."""

    currency: str
    started_at: datetime
    covered_until: datetime
    priced_kwh: Decimal
    components: tuple[tuple[VariableCostComponent, Decimal], ...]
    has_gaps: bool = False

    @property
    def month(self) -> date:
        """Return the local calendar key independently of publication time."""
        return CalendarPeriod.MONTH.start(self.started_at)

    @property
    def total(self) -> Decimal:
        """Return the signed total of the archived components."""
        return sum((amount for _, amount in self.components), Decimal(0))

    @property
    def complete(self) -> bool:
        """Report whether observed pricing covers the entire calendar month."""
        return (
            not self.has_gaps
            and _at_month_start(self.started_at)
            and _month_number(self.covered_until.date())
            == _month_number(self.month) + 1
            and _at_month_start(self.covered_until)
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "currency": self.currency,
            "started_at": self.started_at.isoformat(),
            "covered_until": self.covered_until.isoformat(),
            "priced_kwh": str(self.priced_kwh),
            "components": {key.value: str(amount) for key, amount in self.components},
            "has_gaps": self.has_gaps,
        }

    @classmethod
    def from_dict(cls, value: object) -> "MonthlyVariableCost":
        data = stored_record(value)
        currency = stored_string(data["currency"])
        start = datetime.fromisoformat(stored_string(data["started_at"]))
        end = datetime.fromisoformat(stored_string(data["covered_until"]))
        energy = stored_decimal(data["priced_kwh"])
        components = tuple(
            (VariableCostComponent(key), stored_decimal(amount))
            for key, amount in stored_record(data["components"]).items()
        )
        has_gaps = data["has_gaps"]
        month_span = _month_number(end.date()) - _month_number(start.date())
        if (
            not currency
            or start.utcoffset() is None
            or end.utcoffset() is None
            or end <= start
            or not (month_span == 0 or (month_span == 1 and _at_month_start(end)))
            or not energy.is_finite()
            or energy <= 0
            or not components
            or any(not amount.is_finite() for _, amount in components)
            or not isinstance(has_gaps, bool)
        ):
            raise ValueError("Invalid monthly variable cost record")
        return cls(currency, start, end, energy, components, has_gaps)


class MonthlyVariableCostArchive:
    """Keep up to twelve local calendar months of already booked intervals."""

    def __init__(self) -> None:
        self._months: dict[date, MonthlyVariableCost] = {}

    @property
    def months(self) -> tuple[MonthlyVariableCost, ...]:
        """Return existing months in order, leaving absent months as gaps."""
        return tuple(self._months[month] for month in sorted(self._months))

    def record(
        self,
        start: datetime,
        end: datetime,
        currency: str,
        energy: Decimal,
        amounts: tuple[tuple[VariableCostComponent, Decimal], ...],
    ) -> None:
        """Add one priced ledger slice under the calendar month it covers."""
        month = CalendarPeriod.MONTH.start(start)
        previous = self._months.get(month)
        if previous is None:
            self._months[month] = MonthlyVariableCost(
                currency, start, end, energy, amounts
            )
            return
        if (
            previous.currency != currency
            or start.timestamp() < previous.covered_until.timestamp()
        ):
            return
        components = dict(previous.components)
        for key, amount in amounts:
            components[key] = components.get(key, Decimal(0)) + amount
        self._months[month] = MonthlyVariableCost(
            currency,
            previous.started_at,
            end,
            previous.priced_kwh + energy,
            tuple(components.items()),
            previous.has_gaps
            or start.timestamp() != previous.covered_until.timestamp(),
        )

    def prune(self, today: date) -> bool:
        """Drop months outside the calendar window, including after a long outage."""
        current = _month_number(today)
        expired = [
            month
            for month in self._months
            if current - _month_number(month) >= _WINDOW_MONTHS
        ]
        for month in expired:
            del self._months[month]
        return bool(expired)

    def as_dict(self) -> dict[str, object]:
        return {row.month.isoformat()[:7]: row.as_dict() for row in self.months}

    @classmethod
    def from_dict(cls, value: object) -> "MonthlyVariableCostArchive":
        archive = cls()
        for key, raw in stored_record(value).items():
            try:
                row = MonthlyVariableCost.from_dict(raw)
                if key == row.month.isoformat()[:7]:
                    archive._months[row.month] = row
            except KeyError, ValueError, TypeError, ArithmeticError:
                # A damaged month is a gap. Preserve the other saved months.
                continue
        return archive


def monthly_cost_chart_rows(
    months: tuple[MonthlyVariableCost, ...], today: date
) -> list[dict[str, object]]:
    """Project one currency onto a full calendar window for the chart."""
    current = _month_number(today)
    known = {_month_number(month.month): month for month in months}
    rows: list[dict[str, object]] = []
    for number in range(current - _WINDOW_MONTHS + 1, current + 1):
        year, month_index = divmod(number - 1, 12)
        row: dict[str, object] = {
            "month": f"{year:04d}-{month_index + 1:02d}",
            "coverage": "missing",
            "priced_kwh": None,
            "total": None,
            "components": {},
        }
        if (period := known.get(number)) is not None:
            row.update(
                coverage="ongoing"
                if number == current
                else "complete"
                if period.complete
                else "partial",
                priced_kwh=str(period.priced_kwh),
                total=str(period.total),
                components={key.value: str(value) for key, value in period.components},
            )
        rows.append(row)
    return rows
