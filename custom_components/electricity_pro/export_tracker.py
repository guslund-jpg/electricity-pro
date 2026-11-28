"""Own export observation, booking and checkpointed publication state."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, tzinfo
from typing import TYPE_CHECKING

from .export_ledger import ExportLedger
from .export_observation import ExportIntervalResult, ExportObservation
from .export_statistics import ExportHistory, ExportStatistics
from .history_storage import stored_list, stored_record

if TYPE_CHECKING:
    from .energy_flows import FlowCounter
    from .flow_sources import FlowReading

_LEDGER = "export_ledger"
_STATISTICS = "export_statistics"


class ExportTracker:
    """Keep export state together while HA owns writes, timers and delivery."""

    def __init__(self, timezone: tzinfo, utcnow: Callable[[], datetime]) -> None:
        self._timezone = timezone
        self._observation = ExportObservation(utcnow())
        self._ledger = ExportLedger(timezone)
        self._ledger_paused = False
        self._inactive_ledger: object = None
        self._histories = {
            period: ExportHistory(timezone, utcnow(), monthly=period == "this_month")
            for period in ("today", "this_month")
        }
        self._recorded: dict[str, ExportStatistics] = {}
        self._publication_paused = False
        self._inactive_statistics: object = None

    @property
    def ledger(self) -> ExportLedger:
        """Return the booking ledger without transferring its ownership."""
        return self._ledger

    @property
    def result(self) -> ExportIntervalResult | None:
        return self._observation.result

    @property
    def paused(self) -> bool:
        return self._ledger_paused or self._publication_paused

    @property
    def recorded_statistics(self) -> Mapping[str, ExportStatistics]:
        return self._recorded

    def advance(self, now: datetime) -> bool:
        return self._ledger.advance(now) if not self._ledger_paused else False

    def observe(
        self,
        reading: FlowReading,
        counter: FlowCounter,
        now: datetime,
        periods: object,
        *,
        accepted: bool,
    ) -> bool:
        """Keep transient pricing available even when saved booking is paused."""
        self._observation.update(reading, counter, now, periods, accepted=accepted)
        if not self._ledger_paused and self.result is not None:
            return self._ledger.record(self.result, counter.generation)
        return False

    def update_history(self, *, source_configured: bool) -> bool:
        """Queue current periods without publishing unacknowledged amounts."""
        changed = False
        if not self.paused and source_configured:
            for period, export_period in (
                ("today", self._ledger.today),
                ("this_month", self._ledger.this_month),
            ):
                history = self._histories[period]
                history.update(export_period)
                changed |= history.dirty
        return changed

    def restore(
        self, stored: Mapping[str, object], *, source_configured: bool
    ) -> tuple[str, ...]:
        """Restore existing keys, preserving incompatible checkpoints verbatim."""
        warnings = []
        if _LEDGER in stored:
            try:
                ledger = ExportLedger.from_dict(stored[_LEDGER])
                if str(ledger.timezone) != str(self._timezone):
                    raise ValueError("Export ledger timezone changed")
                self._ledger = ledger
            except KeyError, ValueError, TypeError, ArithmeticError:
                self._ledger_paused = True
                self._inactive_ledger = stored[_LEDGER]
                warnings.append(
                    "Pausing export booking with an incompatible ledger checkpoint"
                )

        if _STATISTICS in stored:
            try:
                for period, raw in stored_record(stored[_STATISTICS]).items():
                    self._histories[period].restore(raw)
                self._recorded = {
                    period: history.saved
                    for period, history in self._histories.items()
                    if history.saved is not None
                }
            except KeyError, ValueError, TypeError, ArithmeticError:
                self._publication_paused = True
                self._inactive_statistics = stored[_STATISTICS]
                warnings.append("Pausing export publication with an invalid checkpoint")
        if not self.paused and source_configured:
            for period, export_period in (
                ("today", self._ledger.today),
                ("this_month", self._ledger.this_month),
            ):
                history = self._histories[period]
                if history.checkpoint is None:
                    history.initialize(export_period)
                if history.saved is not None:
                    self._recorded[period] = history.saved
        return tuple(warnings)

    def as_dict(self) -> dict[str, object]:
        """Keep both persisted sections in their existing order and format."""
        return {
            _LEDGER: self._inactive_ledger
            if self._ledger_paused
            else self._ledger.as_dict(),
            _STATISTICS: self._inactive_statistics
            if self._publication_paused
            else {
                period: history.as_list()
                for period, history in self._histories.items()
                if history.checkpoint is not None
            },
        }

    def confirm_saved(
        self,
        data: Mapping[str, object],
        *,
        publish: Callable[[], None],
        schedule_save: Callable[[bool], None],
    ) -> None:
        """Deliver each acknowledged state before requesting the next write."""
        if self.paused:
            return
        for period, raw in stored_record(data.get(_STATISTICS, {})).items():
            history = self._histories[period]
            saved = ExportStatistics.from_dict(
                stored_list(raw)[0], monthly=period == "this_month"
            )
            finished = history.confirm(saved)
            previous = self._recorded.get(period)
            if previous != saved:
                if saved.amount is not None and (
                    previous is None or previous.amount is None
                ):
                    self._recorded[period] = saved.zero_baseline()
                    publish()
                self._recorded[period] = saved
                publish()
            if history.dirty:
                schedule_save(finished)
