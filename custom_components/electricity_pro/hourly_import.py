"""Normalize and retain measured hourly grid import."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timedelta, tzinfo
from decimal import Decimal

from .demand_charge import HourlyImportBlock
from .history_storage import stored_record, stored_string


def hourly_import_block(
    value: str, attributes: Mapping[str, object]
) -> HourlyImportBlock | None:
    """Read the measurement and its own interval from a sensor report."""
    unit = attributes.get("unit_of_measurement")
    if unit not in ("Wh", "kWh"):
        return None
    try:
        energy = Decimal(value)
        if unit == "Wh":
            energy /= 1000
        return HourlyImportBlock(
            datetime.fromisoformat(stored_string(attributes.get("interval_start"))),
            datetime.fromisoformat(stored_string(attributes.get("interval_end"))),
            energy,
        )
    except ValueError, ArithmeticError:
        return None


class HourlyImportHistory:
    """Keep two local months of measurements for one source and meter."""

    def __init__(self, source: str, meter: str, timezone: tzinfo) -> None:
        self.source = source
        self._timezone = timezone
        self._scope = {"source": source, "meter": meter, "timezone": str(timezone)}
        # None is a conflict, distinct from a missing report or a measured zero.
        self._blocks: dict[datetime, HourlyImportBlock | None] = {}

    @property
    def blocks(self) -> tuple[HourlyImportBlock, ...]:
        """Return usable blocks in UTC order."""
        return tuple(
            block for _, block in sorted(self._blocks.items()) if block is not None
        )

    def _oldest_date(self, now: datetime) -> date:
        month = now.astimezone(self._timezone).date().replace(day=1)
        return (month - timedelta(days=1)).replace(day=1)

    def _accepts(self, block: HourlyImportBlock, now: datetime) -> bool:
        start = block.start.astimezone(self._timezone)
        end = block.end.astimezone(self._timezone)
        return (
            block.end <= now
            and start.date() >= self._oldest_date(now)
            and not any(
                (
                    start.minute,
                    start.second,
                    start.microsecond,
                    end.minute,
                    end.second,
                    end.microsecond,
                )
            )
        )

    def retain(self, now: datetime) -> None:
        """Discard blocks and conflicts older than the previous local month."""
        oldest = self._oldest_date(now)
        self._blocks = {
            start: block
            for start, block in self._blocks.items()
            if start.astimezone(self._timezone).date() >= oldest
        }

    def observe(self, block: HourlyImportBlock, now: datetime) -> bool:
        """Add a closed block or mark a conflicting report as unusable."""
        if not self._accepts(block, now):
            return False
        if block.start in self._blocks:
            previous = self._blocks[block.start]
            if previous is None or previous == block:
                return False
            self._blocks[block.start] = None
        else:
            self._blocks[block.start] = block
        return True

    def restore(self, value: object, now: datetime) -> None:
        """Restore matching records, leaving malformed or expired hours as gaps."""
        record = stored_record(value)
        if record.get("scope") != self._scope:
            return
        for start_text, amount in stored_record(record.get("blocks")).items():
            try:
                start = datetime.fromisoformat(start_text)
                block = HourlyImportBlock(
                    start,
                    start + timedelta(hours=1),
                    Decimal(stored_string(amount))
                    if amount is not None
                    else Decimal(0),
                )
            except ValueError, ArithmeticError:
                continue
            if amount is None:
                if self._accepts(block, now):
                    self._blocks[block.start] = None
            else:
                self.observe(block, now)

    def as_dict(self) -> dict[str, object]:
        """Save the scope and one exact value or conflict marker per UTC hour."""
        return {
            "scope": self._scope,
            "blocks": {
                start.isoformat(): str(block.energy_kwh) if block is not None else None
                for start, block in sorted(self._blocks.items())
            },
        }
