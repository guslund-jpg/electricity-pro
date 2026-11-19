"""Connect accepted export increments to their saved fixed-price periods."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from .export_compensation import FixedExportPrice, calculate_export_compensation
from .export_price_config import ExportPriceTerms, parse_export_price_terms
from .history_storage import stored_list, stored_record, stored_string

if TYPE_CHECKING:
    from .energy_flows import FlowCounter
    from .flow_sources import FlowReading


@dataclass(frozen=True, slots=True)
class ExportIntervalResult:
    """The latest observed interval, with explicit pricing and receipt times."""

    source: str
    start: datetime
    end: datetime
    exported_kwh: Decimal
    priced_kwh: Decimal = Decimal(0)
    amount: Decimal | None = None
    amount_per_kwh: Decimal | None = None
    currency: str | None = None
    vat_treatment: str | None = None
    components: tuple[str, ...] = ()
    reason: str = "no_single_price_period"
    timestamp_provenance: str = "ha_receipt"


def _price_interval(
    source: str,
    start: datetime,
    end: datetime,
    exported_kwh: Decimal,
    periods: object,
) -> ExportIntervalResult:
    """Use exactly one overlapping period, requiring full interval coverage."""
    result = ExportIntervalResult(source, start, end, exported_kwh)
    candidates: list[tuple[FixedExportPrice, ExportPriceTerms]] = []
    try:
        for raw in stored_list(periods):
            period = stored_record(raw)
            if period.get("meter") != source:
                continue
            terms, errors = parse_export_price_terms(
                source,
                stored_string(period["amount_per_kwh"]),
                stored_string(period["currency"]),
                stored_string(period["vat_treatment"]),
                [stored_string(item) for item in stored_list(period["components"])],
            )
            if errors or terms is None:
                raise ValueError("Invalid saved export terms")
            valid_from = datetime.fromisoformat(stored_string(period["valid_from"]))
            valid_until = (
                datetime.fromisoformat(stored_string(period["valid_until"]))
                if period["valid_until"] is not None
                else None
            )
            if valid_from.utcoffset() is None or (
                valid_until is not None and valid_until.utcoffset() is None
            ):
                raise ValueError("Naive export-price validity")
            valid_from = valid_from.astimezone(UTC)
            if valid_until is not None:
                valid_until = valid_until.astimezone(UTC)
                if valid_until <= valid_from:
                    raise ValueError("Invalid export-price period")
            if valid_from < end and (valid_until is None or valid_until > start):
                candidates.append(
                    (
                        FixedExportPrice(
                            Decimal(terms["amount_per_kwh"]), valid_from, valid_until
                        ),
                        terms,
                    )
                )
    except KeyError, ValueError, TypeError, ArithmeticError:
        return replace(result, reason="invalid_price_periods")
    if len(candidates) != 1:
        return result
    price, terms = candidates[0]
    amount = calculate_export_compensation(exported_kwh, start, end, price)
    if amount is None:
        return replace(result, reason="interval_not_priced")
    return replace(
        result,
        priced_kwh=exported_kwh,
        amount=amount,
        amount_per_kwh=price.amount_per_kwh,
        currency=terms["currency"],
        vat_treatment=terms["vat_treatment"],
        components=tuple(terms["components"]),
        reason="priced",
    )


class ExportObservation:
    """Price each new accepted report once, with a fresh baseline on startup."""

    def __init__(self, started_at: datetime) -> None:
        self.result: ExportIntervalResult | None = None
        self._started_at = started_at.astimezone(UTC)
        self._scope: tuple[str | None, int, date] | None = None
        self._previous: FlowReading | None = None

    def update(
        self,
        reading: FlowReading,
        counter: FlowCounter,
        now: datetime,
        periods: object,
        *,
        accepted: bool,
    ) -> None:
        """Consume the counter's decision while keeping report-time provenance."""
        scope = reading.source, counter.generation, now.date()
        if scope != self._scope:
            self._scope = scope
            self._previous = None
            self.result = None
        if (
            not accepted
            or reading.source is None
            or reading.value is None
            or reading.observed_at is None
        ):
            self.result = None
            return
        end = reading.observed_at.astimezone(UTC)
        if end < self._started_at:
            self.result = None
            return
        previous = self._previous
        if previous is not None and previous.observed_at is not None:
            start = previous.observed_at.astimezone(UTC)
            if end <= start:
                return
        self._previous = reading
        self.result = None
        delta = counter.last_increment
        if previous is None or previous.observed_at is None or delta is None:
            return
        # The increment must start at the same high-water reading as its time.
        if reading.value - delta != previous.value:
            return
        self.result = _price_interval(
            reading.source,
            previous.observed_at.astimezone(UTC),
            end,
            delta,
            periods,
        )
