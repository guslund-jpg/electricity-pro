"""Forward-only, checkpoint-acknowledged export sensor publication."""

from collections import deque
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, tzinfo
from decimal import Decimal, DecimalException
from zoneinfo import ZoneInfo

from .export_ledger import ExportPeriod
from .history_storage import stored_list, stored_record, stored_string


@dataclass(frozen=True, slots=True)
class ExportStatistics:
    """One calendar-period value and the coverage saved alongside it."""

    period: ExportPeriod
    timezone: str
    currency: str | None
    history_started_at: datetime

    @property
    def last_reset(self) -> datetime:
        day = self.period.period
        if len(day) == 7:
            day += "-01"
        return datetime.combine(
            date.fromisoformat(day), time(), ZoneInfo(self.timezone)
        ).astimezone(UTC)

    @property
    def reason(self) -> str:
        declarations = {
            (row.contract.currency, row.contract.vat_treatment, row.contract.components)
            for row in self.period.amounts
        }
        if not declarations:
            return "waiting_for_priced_interval"
        if len(declarations) != 1:
            return "mixed_declarations"
        if next(iter(declarations))[0] != self.currency:
            return "currency_changed"
        try:
            amount = sum((row.amount for row in self.period.amounts), Decimal(0))
        except DecimalException:
            return "invalid_amount"
        if not amount.is_finite():
            return "invalid_amount"
        return "partial"

    @property
    def amount(self) -> Decimal | None:
        if self.reason != "partial":
            return None
        return sum((row.amount for row in self.period.amounts), Decimal(0))

    @property
    def priced_kwh(self) -> Decimal:
        return sum((row.priced_kwh for row in self.period.amounts), Decimal(0))

    def zero_baseline(self) -> ExportStatistics:
        """Let Recorder count the first new amount from an explicit baseline."""
        return replace(
            self,
            period=replace(
                self.period,
                observed_kwh=Decimal(0),
                amounts=tuple(
                    replace(row, amount=Decimal(0), priced_kwh=Decimal(0))
                    for row in self.period.amounts
                ),
            ),
        )

    def attributes(self) -> dict[str, object]:
        """Format energy for display and derive coverage before rounding."""
        observed = self.period.observed_kwh
        return {
            "period": self.period.period,
            "timezone": self.timezone,
            "coverage": "partial",
            "reason": self.reason,
            "observed_export_kwh": format(observed, ".3f"),
            "priced_export_kwh": format(self.priced_kwh, ".3f"),
            "unpriced_export_kwh": format(observed - self.priced_kwh, ".3f"),
            "pricing_coverage_percent": str(self.priced_kwh * 100 / observed)
            if observed > 0
            else None,
            "history_started_at": self.history_started_at.isoformat(),
            "timestamp_provenance": "ha_receipt",
            "price_declarations": [
                {
                    "source_entity": row.contract.source,
                    "meter_generation": row.contract.generation,
                    "currency": row.contract.currency,
                    "vat_treatment": row.contract.vat_treatment,
                    "included_components": list(row.contract.components),
                }
                for row in self.period.amounts
            ],
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "period": self.period.as_dict(),
            "timezone": self.timezone,
            "currency": self.currency,
            "history_started_at": self.history_started_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, value: object, *, monthly: bool) -> ExportStatistics:
        data = stored_record(value)
        timezone = stored_string(data["timezone"])
        ZoneInfo(timezone)
        started = datetime.fromisoformat(stored_string(data["history_started_at"]))
        currency = (
            stored_string(data["currency"]) if data["currency"] is not None else None
        )
        if started.utcoffset() is None or currency == "":
            raise ValueError("Invalid export publication metadata")
        return cls(
            ExportPeriod.from_dict(data["period"], monthly=monthly),
            timezone,
            currency,
            started,
        )


class ExportHistory:
    """Keep closing periods ahead of new resets and pin the series currency."""

    def __init__(
        self, timezone: tzinfo, started_at: datetime, *, monthly: bool
    ) -> None:
        self.timezone = str(timezone)
        self.monthly = monthly
        self.started_at = started_at.astimezone(UTC)
        self.currency: str | None = None
        self.saved: ExportStatistics | None = None
        self._pending: deque[ExportStatistics] = deque()

    def _snapshot(self, period: ExportPeriod) -> ExportStatistics:
        currencies = {row.contract.currency for row in period.amounts}
        if self.currency is None and len(currencies) == 1:
            self.currency = next(iter(currencies))
        return ExportStatistics(period, self.timezone, self.currency, self.started_at)

    def initialize(self, period: ExportPeriod | None) -> None:
        """Use existing checkpointed bookings as the new series' start balance."""
        if period is not None:
            self.saved = self._snapshot(period)
            self._pending.append(self.saved)

    def update(self, period: ExportPeriod | None) -> None:
        if period is None:
            return
        new = self._snapshot(period)
        current = self._pending[-1] if self._pending else None
        if current is not None and new.last_reset < current.last_reset:
            return
        if current is None or new.last_reset != current.last_reset:
            if current is not None and current == self.saved:
                self._pending.pop()
            self._pending.append(new)
        else:
            self._pending[-1] = new

    @property
    def checkpoint(self) -> ExportStatistics | None:
        return self._pending[0] if self._pending else None

    @property
    def dirty(self) -> bool:
        return len(self._pending) > 1 or self.checkpoint != self.saved

    def confirm(self, saved: ExportStatistics) -> bool:
        self.saved = saved
        if len(self._pending) > 1 and self.checkpoint == saved:
            self._pending.popleft()
            return True
        return False

    def as_list(self) -> list[dict[str, object]]:
        return [snapshot.as_dict() for snapshot in self._pending]

    def restore(self, value: object) -> None:
        snapshots = [
            ExportStatistics.from_dict(item, monthly=self.monthly)
            for item in stored_list(value)
        ]
        currencies = {
            snapshot.currency for snapshot in snapshots if snapshot.currency is not None
        }
        if (
            not snapshots
            or len(currencies) > 1
            or any(snapshot.timezone != self.timezone for snapshot in snapshots)
            or any(
                snapshot.history_started_at != snapshots[0].history_started_at
                for snapshot in snapshots
            )
            or any(
                later.last_reset <= earlier.last_reset
                for earlier, later in zip(snapshots, snapshots[1:], strict=False)
            )
        ):
            raise ValueError("Invalid export publication periods")
        self.currency = next(iter(currencies), None)
        self.started_at = snapshots[0].history_started_at
        self.saved = snapshots[0]
        self._pending.extend(snapshots)
