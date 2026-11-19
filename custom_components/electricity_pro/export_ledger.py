"""Checkpointed export compensation and coverage for local calendar periods."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta, tzinfo
from decimal import Decimal
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from .history_storage import stored_decimal, stored_list, stored_record, stored_string

if TYPE_CHECKING:
    from .export_observation import ExportIntervalResult


@dataclass(frozen=True, slots=True)
class ExportContract:
    """Keep each meter generation and monetary declaration identifiable."""

    source: str
    generation: int
    currency: str
    vat_treatment: str
    components: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExportAmount:
    """Sum already-valued increments under one compatible declaration."""

    contract: ExportContract
    priced_kwh: Decimal
    amount: Decimal


@dataclass(frozen=True, slots=True)
class ExportPeriod:
    """Immutable partial coverage and booked amounts for a day or month."""

    period: str
    observed_kwh: Decimal = Decimal(0)
    amounts: tuple[ExportAmount, ...] = ()

    def as_dict(self) -> dict[str, object]:
        """Serialize the same immutable period used by booking and publication."""
        return {
            "period": self.period,
            "observed_kwh": str(self.observed_kwh),
            "amounts": [
                {
                    "source": row.contract.source,
                    "generation": row.contract.generation,
                    "currency": row.contract.currency,
                    "vat_treatment": row.contract.vat_treatment,
                    "components": list(row.contract.components),
                    "priced_kwh": str(row.priced_kwh),
                    "amount": str(row.amount),
                }
                for row in self.amounts
            ],
        }

    @classmethod
    def from_dict(cls, value: object, *, monthly: bool = False) -> ExportPeriod:
        """Apply booking's validation to a checkpointed publication period."""
        period = _restore_period(value, monthly=monthly)
        if period is None:
            raise ValueError("Missing export period")
        return period


def _add(
    period: ExportPeriod, observed_kwh: Decimal, booking: ExportAmount | None
) -> ExportPeriod:
    amounts = list(period.amounts)
    if booking is not None:
        for index, previous in enumerate(amounts):
            if previous.contract == booking.contract:
                booking = replace(
                    booking,
                    priced_kwh=previous.priced_kwh + booking.priced_kwh,
                    amount=previous.amount + booking.amount,
                )
                amounts[index] = booking
                break
        else:
            amounts.append(booking)
        if not booking.priced_kwh.is_finite() or not booking.amount.is_finite():
            raise ValueError("Non-finite export booking")
    observed = period.observed_kwh + observed_kwh
    if not observed.is_finite():
        raise ValueError("Non-finite export coverage")
    return ExportPeriod(period.period, observed, tuple(amounts))


def _period_data(period: ExportPeriod | None) -> dict[str, object] | None:
    return period.as_dict() if period is not None else None


def _generation(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("Invalid export meter generation")
    return value


def _restore_period(value: object, *, monthly: bool = False) -> ExportPeriod | None:
    if value is None:
        return None
    data = stored_record(value)
    period = stored_string(data["period"])
    parsed = date.fromisoformat(period + "-01" if monthly else period)
    if period != (parsed.isoformat()[:7] if monthly else parsed.isoformat()):
        raise ValueError("Invalid export period")
    observed = stored_decimal(data["observed_kwh"])
    if not observed.is_finite() or observed < 0:
        raise ValueError("Invalid export coverage")
    amounts = []
    for raw in stored_list(data["amounts"]):
        row = stored_record(raw)
        contract = ExportContract(
            stored_string(row["source"]),
            _generation(row["generation"]),
            stored_string(row["currency"]),
            stored_string(row["vat_treatment"]),
            tuple(stored_string(item) for item in stored_list(row["components"])),
        )
        priced = stored_decimal(row["priced_kwh"])
        amount = stored_decimal(row["amount"])
        if (
            not contract.source
            or not contract.currency
            or contract.vat_treatment not in {"included", "excluded", "not_applicable"}
            or not contract.components
            or len(set(contract.components)) != len(contract.components)
            or not priced.is_finite()
            or priced < 0
            or not amount.is_finite()
            or (priced == 0 and amount != 0)
        ):
            raise ValueError("Invalid saved export amount")
        amounts.append(ExportAmount(contract, priced, amount))
    if (
        len({row.contract for row in amounts}) != len(amounts)
        or sum((row.priced_kwh for row in amounts), Decimal(0)) > observed
    ):
        raise ValueError("Inconsistent export groups or coverage")
    return ExportPeriod(period, observed, tuple(amounts))


class ExportLedger:
    """Book each accepted interval once and retain current/last closed periods."""

    def __init__(self, timezone: tzinfo) -> None:
        self.timezone = timezone
        self.today: ExportPeriod | None = None
        self.this_month: ExportPeriod | None = None
        self.previous_day: ExportPeriod | None = None
        self.previous_month: ExportPeriod | None = None
        self._processed: dict[tuple[str, int], datetime] = {}

    def advance(self, now: datetime) -> bool:
        """Close calendar periods even when the meter has not reported."""
        day = now.astimezone(self.timezone).date().isoformat()
        if self.today is not None and day <= self.today.period:
            return False
        self.previous_day = self.today
        self.today = ExportPeriod(day)
        if self.this_month is None or day[:7] != self.this_month.period:
            self.previous_month = self.this_month
            self.this_month = ExportPeriod(day[:7])
        # Older intervals are rejected by their calendar date after rollover.
        self._processed.clear()
        return True

    def record(self, result: ExportIntervalResult, generation: int) -> bool:
        """Book an immutable valuation, also consuming unpriced intervals."""
        if self.today is None or self.this_month is None:
            return False
        if result.start.utcoffset() is None or result.end.utcoffset() is None:
            return False
        start, end = result.start.astimezone(UTC), result.end.astimezone(UTC)
        if (
            start >= end
            or start.astimezone(self.timezone).date().isoformat() != self.today.period
            or (end - timedelta(microseconds=1))
            .astimezone(self.timezone)
            .date()
            .isoformat()
            != self.today.period
            or type(generation) is not int
            or generation < 0
            or not result.source
            or not result.exported_kwh.is_finite()
            or result.exported_kwh < 0
            or not result.priced_kwh.is_finite()
            or result.priced_kwh < 0
        ):
            return False
        key = result.source, generation
        if (previous := self._processed.get(key)) is not None and start < previous:
            return False
        booking = None
        if result.amount is not None:
            if (
                not result.amount.is_finite()
                or result.priced_kwh != result.exported_kwh
                or result.reason != "priced"
                or not result.currency
                or not result.vat_treatment
                or not result.components
            ):
                return False
            booking = ExportAmount(
                ExportContract(
                    result.source,
                    generation,
                    result.currency,
                    result.vat_treatment,
                    result.components,
                ),
                result.priced_kwh,
                result.amount,
            )
        elif result.priced_kwh != 0:
            return False
        try:
            day = _add(self.today, result.exported_kwh, booking)
            month = _add(self.this_month, result.exported_kwh, booking)
        except ArithmeticError, ValueError:
            return False
        self.today, self.this_month = day, month
        self._processed[key] = end
        return True

    def as_dict(self) -> dict[str, object]:
        """Keep totals and replay protection in the same JSON checkpoint."""
        return {
            "version": 1,
            "timezone": str(self.timezone),
            "today": _period_data(self.today),
            "this_month": _period_data(self.this_month),
            "previous_day": _period_data(self.previous_day),
            "previous_month": _period_data(self.previous_month),
            "processed": [
                {"source": source, "generation": generation, "end": end.isoformat()}
                for (source, generation), end in sorted(self._processed.items())
            ],
        }

    @classmethod
    def from_dict(cls, value: object) -> ExportLedger:
        """Validate saved amounts and their matching replay/calendar state."""
        data = stored_record(value)
        if type(data["version"]) is not int or data["version"] != 1:
            raise ValueError("Unsupported export ledger version")
        ledger = cls(ZoneInfo(stored_string(data["timezone"])))
        ledger.today = _restore_period(data["today"])
        ledger.this_month = _restore_period(data["this_month"], monthly=True)
        ledger.previous_day = _restore_period(data["previous_day"])
        ledger.previous_month = _restore_period(data["previous_month"], monthly=True)
        if (
            (ledger.today is None) != (ledger.this_month is None)
            or (
                ledger.today is not None
                and ledger.this_month is not None
                and (
                    ledger.today.period[:7] != ledger.this_month.period
                    or ledger.today.observed_kwh > ledger.this_month.observed_kwh
                )
            )
            or (
                ledger.previous_day is not None
                and (
                    ledger.today is None
                    or ledger.previous_day.period >= ledger.today.period
                )
            )
            or (
                ledger.previous_month is not None
                and (
                    ledger.this_month is None
                    or ledger.previous_month.period >= ledger.this_month.period
                )
            )
        ):
            raise ValueError("Inconsistent export calendar periods")
        for raw in stored_list(data["processed"]):
            marker = stored_record(raw)
            source = stored_string(marker["source"])
            key = source, _generation(marker["generation"])
            end = datetime.fromisoformat(stored_string(marker["end"]))
            if end.utcoffset() is None:
                raise ValueError("Naive export booking marker")
            end = end.astimezone(UTC)
            if (
                not source
                or key in ledger._processed
                or ledger.today is None
                or (end - timedelta(microseconds=1))
                .astimezone(ledger.timezone)
                .date()
                .isoformat()
                != ledger.today.period
            ):
                raise ValueError("Invalid export booking marker")
            ledger._processed[key] = end
        if ledger.today is not None and (
            (ledger.today.observed_kwh > 0 and not ledger._processed)
            or any(
                (row.contract.source, row.contract.generation) not in ledger._processed
                for row in ledger.today.amounts
            )
        ):
            raise ValueError("Export totals are missing their booking markers")
        return ledger
