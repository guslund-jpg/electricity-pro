"""Pure forecast insight calculations for Electricity Pro."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Callable

from .forecast import ForecastInterval
from .calculations import vat_inclusive_price
from .pricing import (
    VatTreatment,
    PriceComponent,
    PriceComponentScope,
    PricingMetadata,
)

GridFeeAt = Callable[[datetime], Decimal | None]
PRICE_TREND_RELATIVE_TOLERANCE = Decimal("0.02")


@dataclass(frozen=True, slots=True)
class NextInexpensive1hWindowInsight:
    """The earliest comparable 1-hour window at or below the threshold."""

    start: datetime
    end: datetime
    duration_minutes: int
    interval_count: int
    average_market_price: Decimal
    average_scheduling_price: Decimal
    threshold: Decimal
    currency: str
    area: str
    published_at: datetime | None
    pricing_metadata: PricingMetadata

    @property
    def average_effective_price(self) -> Decimal:
        """Return the legacy internal alias for compatibility."""
        return self.average_scheduling_price


@dataclass(frozen=True, slots=True)
class ForecastWindowInsight:
    """A selected continuous future price window."""

    start: datetime
    end: datetime
    duration_minutes: int
    interval_count: int
    average_market_price: Decimal
    average_scheduling_price: Decimal
    currency: str
    area: str
    published_at: datetime | None
    pricing_metadata: PricingMetadata

    @property
    def average_effective_price(self) -> Decimal:
        """Return the legacy internal alias for compatibility."""
        return self.average_scheduling_price


@dataclass(frozen=True, slots=True)
class ForecastDirectionInsight:
    """A comparison of scheduling-price averages over two elapsed hours."""

    direction: str
    current_start: datetime
    current_end: datetime
    next_start: datetime
    next_end: datetime
    current_scheduling_price: Decimal
    next_scheduling_price: Decimal
    delta: Decimal
    stable_tolerance: Decimal
    currency: str
    area: str
    published_at: datetime | None
    pricing_metadata: PricingMetadata

    @property
    def current_effective_price(self) -> Decimal:
        """Return the legacy internal alias for compatibility."""
        return self.current_scheduling_price

    @property
    def next_effective_price(self) -> Decimal:
        """Return the legacy internal alias for compatibility."""
        return self.next_scheduling_price


def find_cheapest_continuous_window(
    intervals: list[ForecastInterval],
    *,
    now: datetime,
    duration_minutes: int,
    grid_fee_per_kwh: Decimal | None = None,
    grid_fee_at: GridFeeAt | None = None,
    energy_tax_per_kwh: Decimal | None = None,
    supplier_markup_per_kwh: Decimal | None = None,
) -> ForecastWindowInsight | None:
    """Return the cheapest upcoming continuous window with the exact duration."""
    if any(
        vat_inclusive_price(i.market_price, i.pricing_metadata) is None
        for i in intervals
    ):
        return None
    upcoming = sorted(
        (interval for interval in intervals if interval.start >= now),
        key=lambda interval: interval.start,
    )
    best_window: ForecastWindowInsight | None = None

    for start_index, start_interval in enumerate(upcoming):
        window = [start_interval]
        total_minutes = start_interval.resolution_minutes

        for interval in upcoming[start_index + 1 :]:
            previous = window[-1]
            if interval.start < previous.end:
                break
            if interval.start != previous.end or total_minutes >= duration_minutes:
                break
            window.append(interval)
            total_minutes += interval.resolution_minutes

        if total_minutes != duration_minutes:
            continue

        if any(
            interval.currency != start_interval.currency or interval.area != start_interval.area
            for interval in window[1:]
        ):
            continue

        average_market_price = _average_market_price(window)
        average_scheduling_price = _average_scheduling_price(
            window,
            grid_fee_per_kwh=grid_fee_per_kwh,
            grid_fee_at=grid_fee_at,
            energy_tax_per_kwh=energy_tax_per_kwh,
            supplier_markup_per_kwh=supplier_markup_per_kwh,
        )
        candidate = ForecastWindowInsight(
            start=window[0].start,
            end=window[-1].end,
            duration_minutes=duration_minutes,
            interval_count=len(window),
            average_market_price=average_market_price,
            average_scheduling_price=average_scheduling_price,
            currency=window[0].currency,
            area=window[0].area,
            published_at=window[0].published_at,
            pricing_metadata=_scheduling_price_metadata(
                window[0],
                _has_grid_fee(
                    window[0].start,
                    grid_fee_per_kwh=grid_fee_per_kwh,
                    grid_fee_at=grid_fee_at,
                ),
                energy_tax_per_kwh is not None,
                supplier_markup_per_kwh is not None,
            ),
        )
        if best_window is None or (candidate.average_scheduling_price, candidate.start, candidate.average_market_price) < (
            best_window.average_scheduling_price,
            best_window.start,
            best_window.average_market_price,
        ):
            best_window = candidate

    return best_window


def find_price_direction(
    intervals: list[ForecastInterval],
    *,
    now: datetime,
    grid_fee_per_kwh: Decimal | None = None,
    grid_fee_at: GridFeeAt | None = None,
    energy_tax_per_kwh: Decimal | None = None,
    supplier_markup_per_kwh: Decimal | None = None,
    grid_fee_change_times: tuple[datetime, ...] = (),
) -> ForecastDirectionInsight | None:
    """Compare [now, +1h) with [+1h, +2h), requiring comparable full coverage.

    Arithmetic uses UTC elapsed time, including partial source intervals. A
    variable tariff callback must supply any intra-interval change boundaries.
    Consistently partial bill-component scope is allowed; missing time is not.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Price trend requires a timezone-aware timestamp")
    start = now.astimezone(UTC)
    middle = start + timedelta(hours=1)
    end = middle + timedelta(hours=1)
    relevant = sorted(
        (
            i
            for i in intervals
            if i.end.astimezone(UTC) > start and i.start.astimezone(UTC) < end
        ),
        key=lambda i: i.start.astimezone(UTC),
    )
    if not relevant:
        return None
    first = relevant[0]
    cursor = start
    weighted = [Decimal(0), Decimal(0)]
    metadata: PricingMetadata | None = None
    boundaries = {middle, *(t.astimezone(UTC) for t in grid_fee_change_times)}
    for interval in relevant:
        left = max(start, interval.start.astimezone(UTC))
        right = min(end, interval.end.astimezone(UTC))
        if (
            left != cursor
            or right <= left
            or interval.currency != first.currency
            or interval.area != first.area
            or interval.pricing_metadata != first.pricing_metadata
            or vat_inclusive_price(interval.market_price, interval.pricing_metadata)
            is None
        ):
            return None
        points = [left, *sorted(t for t in boundaries if left < t < right), right]
        for segment_start, segment_end in zip(points, points[1:]):
            # Evaluate once so the price and its declared component scope agree.
            fee = (
                grid_fee_at(segment_start)
                if grid_fee_at is not None
                else grid_fee_per_kwh
            )
            if any(
                value is not None and not value.is_finite()
                for value in (fee, energy_tax_per_kwh, supplier_markup_per_kwh)
            ):
                return None
            segment_metadata = _scheduling_price_metadata(
                interval,
                fee is not None,
                energy_tax_per_kwh is not None,
                supplier_markup_per_kwh is not None,
            )
            if metadata is not None and segment_metadata != metadata:
                return None
            metadata = segment_metadata
            price = _scheduling_price(
                interval.market_price,
                pricing_metadata=interval.pricing_metadata,
                at=segment_start,
                grid_fee_per_kwh=fee,
                grid_fee_at=None,
                energy_tax_per_kwh=energy_tax_per_kwh,
                supplier_markup_per_kwh=supplier_markup_per_kwh,
            )
            if not price.is_finite():
                return None
            seconds = Decimal(str((segment_end - segment_start).total_seconds()))
            weighted[0 if segment_start < middle else 1] += price * seconds
        cursor = right
    if cursor != end or metadata is None:
        return None
    current, following = (value / Decimal(3600) for value in weighted)
    delta = following - current
    tolerance = max(abs(current), abs(following)) * PRICE_TREND_RELATIVE_TOLERANCE
    direction = (
        "stable" if abs(delta) <= tolerance else "rising" if delta > 0 else "falling"
    )
    return ForecastDirectionInsight(
        direction=direction,
        current_start=start,
        current_end=middle,
        next_start=middle,
        next_end=end,
        current_scheduling_price=current,
        next_scheduling_price=following,
        delta=delta,
        stable_tolerance=tolerance,
        currency=first.currency,
        area=first.area,
        published_at=(
            min(i.published_at for i in relevant if i.published_at is not None)
            if all(i.published_at is not None for i in relevant)
            else None
        ),
        pricing_metadata=metadata,
    )


def _scheduling_price(
    market_price: Decimal,
    *,
    pricing_metadata: PricingMetadata,
    at: datetime,
    grid_fee_per_kwh: Decimal | None,
    grid_fee_at: GridFeeAt | None,
    energy_tax_per_kwh: Decimal | None,
    supplier_markup_per_kwh: Decimal | None,
) -> Decimal:
    """Return the market-derived scheduling price with configured adjustments."""
    grid_fee = grid_fee_at(at) if grid_fee_at is not None else grid_fee_per_kwh
    grid_adjustment = (
        Decimal("0")
        if pricing_metadata.scope.includes(PriceComponent.VARIABLE_GRID_FEE)
        else grid_fee or Decimal("0")
    )
    tax_adjustment = (
        Decimal("0")
        if pricing_metadata.scope.includes(PriceComponent.ENERGY_TAX)
        else energy_tax_per_kwh or Decimal("0")
    )
    markup_adjustment = (
        Decimal("0")
        if pricing_metadata.scope.includes(PriceComponent.SUPPLIER_MARKUP)
        else supplier_markup_per_kwh or Decimal("0")
    )
    gross_price = vat_inclusive_price(market_price, pricing_metadata)
    if gross_price is None:
        raise ValueError("Scheduling requires a known VAT-inclusive price")
    return (
        gross_price
        + grid_adjustment
        + tax_adjustment
        + markup_adjustment
    )


def _average_market_price(window: list[ForecastInterval]) -> Decimal:
    """Return the duration-weighted average market price for a window."""
    total_minutes = sum(interval.resolution_minutes for interval in window)
    weighted_sum = sum(
        interval.market_price * interval.resolution_minutes for interval in window
    )
    return weighted_sum / Decimal(total_minutes)


def _average_scheduling_price(
    window: list[ForecastInterval],
    *,
    grid_fee_per_kwh: Decimal | None,
    grid_fee_at: GridFeeAt | None,
    energy_tax_per_kwh: Decimal | None,
    supplier_markup_per_kwh: Decimal | None,
) -> Decimal:
    """Return the duration-weighted average scheduling price for a window."""
    total_minutes = sum(interval.resolution_minutes for interval in window)
    weighted_sum = sum(
        _scheduling_price(
            interval.market_price,
            pricing_metadata=interval.pricing_metadata,
            at=interval.start,
            grid_fee_per_kwh=grid_fee_per_kwh,
            grid_fee_at=grid_fee_at,
            energy_tax_per_kwh=energy_tax_per_kwh,
            supplier_markup_per_kwh=supplier_markup_per_kwh,
        )
        * interval.resolution_minutes
        for interval in window
    )
    return weighted_sum / Decimal(total_minutes)


def find_next_inexpensive_1h_window(
    intervals: list[ForecastInterval],
    *,
    now: datetime,
    threshold: Decimal,
    grid_fee_per_kwh: Decimal | None = None,
    grid_fee_at: GridFeeAt | None = None,
    energy_tax_per_kwh: Decimal | None = None,
    supplier_markup_per_kwh: Decimal | None = None,
    price_is_comparable: bool = True,
) -> NextInexpensive1hWindowInsight | None:
    """Return the earliest comparable 1-hour window at or below threshold."""
    if any(
        vat_inclusive_price(i.market_price, i.pricing_metadata) is None
        for i in intervals
    ):
        return None
    if not price_is_comparable:
        return None
    upcoming = sorted(
        (interval for interval in intervals if interval.start >= now),
        key=lambda interval: interval.start,
    )

    for start_index, start_interval in enumerate(upcoming):
        window = [start_interval]
        total_minutes = start_interval.resolution_minutes

        for interval in upcoming[start_index + 1 :]:
            previous = window[-1]
            if interval.start < previous.end:
                break
            if interval.start != previous.end or total_minutes >= 60:
                break
            window.append(interval)
            total_minutes += interval.resolution_minutes

        if total_minutes != 60:
            continue

        if any(
            interval.currency != start_interval.currency or interval.area != start_interval.area
            for interval in window[1:]
        ):
            continue

        average_scheduling_price = _average_scheduling_price(
            window,
            grid_fee_per_kwh=grid_fee_per_kwh,
            grid_fee_at=grid_fee_at,
            energy_tax_per_kwh=energy_tax_per_kwh,
            supplier_markup_per_kwh=supplier_markup_per_kwh,
        )
        if average_scheduling_price > threshold:
            continue

        return NextInexpensive1hWindowInsight(
            start=window[0].start,
            end=window[-1].end,
            duration_minutes=60,
            interval_count=len(window),
            average_market_price=_average_market_price(window),
            average_scheduling_price=average_scheduling_price,
            threshold=threshold,
            currency=window[0].currency,
            area=window[0].area,
            published_at=window[0].published_at,
            pricing_metadata=_scheduling_price_metadata(
                window[0],
                _has_grid_fee(
                    window[0].start,
                    grid_fee_per_kwh=grid_fee_per_kwh,
                    grid_fee_at=grid_fee_at,
                ),
                energy_tax_per_kwh is not None,
                supplier_markup_per_kwh is not None,
            ),
        )

    return None


def _has_grid_fee(
    at: datetime,
    *,
    grid_fee_per_kwh: Decimal | None,
    grid_fee_at: GridFeeAt | None,
) -> bool:
    """Return whether the scheduling price includes a grid fee."""
    return (
        grid_fee_at(at) if grid_fee_at is not None else grid_fee_per_kwh
    ) is not None


def _scheduling_price_metadata(
    interval: ForecastInterval,
    includes_grid_fee: bool,
    includes_energy_tax: bool,
    includes_supplier_markup: bool,
) -> PricingMetadata:
    """Return component metadata for a derived forecast scheduling price."""
    included = set(interval.pricing_metadata.scope.included)
    if includes_grid_fee:
        included.add(PriceComponent.VARIABLE_GRID_FEE)
    if includes_energy_tax:
        included.add(PriceComponent.ENERGY_TAX)
    if includes_supplier_markup:
        included.add(PriceComponent.SUPPLIER_MARKUP)
    return PricingMetadata(
        strategy=interval.pricing_metadata.strategy,
        scope=PriceComponentScope(
            included=frozenset(included),
            vat=VatTreatment.INCLUDED,
        ),
        completeness=interval.pricing_metadata.completeness,
    )
