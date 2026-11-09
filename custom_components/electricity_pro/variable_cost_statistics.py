"""Forward-only monthly cost snapshots for Home Assistant Recorder."""

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from .cost_ledger import VariableCostSummary
from .history_storage import stored_decimal, stored_list, stored_record, stored_string
from .pricing import EffectivePriceBreakdown, VariableCostComponent


@dataclass(frozen=True, slots=True)
class VariableCostStatistics:
    """The signed amounts for one calendar month and one currency."""

    last_reset: datetime
    currency: str
    amounts: tuple[tuple[VariableCostComponent, Decimal], ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "last_reset": self.last_reset.isoformat(),
            "currency": self.currency,
            "amounts": {key.value: str(value) for key, value in self.amounts},
        }

    @classmethod
    def from_dict(cls, value: object) -> "VariableCostStatistics":
        data = stored_record(value)
        last_reset = datetime.fromisoformat(stored_string(data["last_reset"]))
        currency = stored_string(data["currency"])
        amounts = tuple(
            (VariableCostComponent(key), stored_decimal(amount))
            for key, amount in stored_record(data["amounts"]).items()
        )
        if (
            last_reset.utcoffset() is None
            or not currency
            or any(not amount.is_finite() for _, amount in amounts)
        ):
            raise ValueError("Invalid variable cost statistics")
        return cls(last_reset, currency, amounts)


class VariableCostHistory:
    """Accumulate new ledger deltas and checkpoint closing periods in order."""

    def __init__(self) -> None:
        self._pending: deque[VariableCostStatistics] = deque()
        self.saved: VariableCostStatistics | None = None

    def restore(self, value: object) -> None:
        periods = [
            VariableCostStatistics.from_dict(period) for period in stored_list(value)
        ]
        if not periods or any(
            following.currency != earlier.currency
            or following.last_reset <= earlier.last_reset
            for earlier, following in zip(periods, periods[1:])
        ):
            raise ValueError("Invalid variable cost statistics periods")
        self.saved = periods[0]
        self._pending.extend(periods)

    def as_list(self) -> list[dict[str, object]]:
        return [period.as_dict() for period in self._pending]

    @property
    def checkpoint(self) -> VariableCostStatistics | None:
        return self._pending[0] if self._pending else None

    @property
    def dirty(self) -> bool:
        return len(self._pending) > 1 or self.checkpoint != self.saved

    def update(
        self,
        now: datetime,
        currency: str | None,
        price: EffectivePriceBreakdown | None,
        before: VariableCostSummary | None,
        after: VariableCostSummary | None,
    ) -> None:
        """Include only newly booked costs, with a zero for each known rate."""
        current = self._pending[-1] if self._pending else None
        if currency is None or (current is None and price is None):
            return
        if current is not None and currency != current.currency:
            return
        last_reset = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0, fold=0
        ).astimezone(UTC)
        if current is not None and last_reset < current.last_reset:
            return
        if current is None or last_reset != current.last_reset:
            # A closing month must reach Recorder before the next reset.
            if current is not None and current == self.saved:
                self._pending.pop()
            current = VariableCostStatistics(last_reset, currency)
            self._pending.append(current)

        amounts = dict(current.amounts)
        if price is not None:
            for key, _ in price.components:
                amounts.setdefault(key, Decimal(0))
        if after is not None:
            previous = dict(before.components) if before is not None else {}
            for key, amount in after.components:
                delta = amount - previous.get(key, Decimal(0))
                if delta or key not in previous:
                    amounts[key] = amounts.get(key, Decimal(0)) + delta
        self._pending[-1] = VariableCostStatistics(
            last_reset, currency, tuple(amounts.items())
        )

    def confirm(self, saved: VariableCostStatistics) -> bool:
        """Retire a closing month only after its latest amounts were written."""
        self.saved = saved
        if len(self._pending) > 1 and self.checkpoint == saved:
            self._pending.popleft()
            return True
        return False
