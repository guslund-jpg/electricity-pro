"""Tests for pure forecast insight calculations."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from custom_components.electricity_pro.forecast import ForecastInterval
from custom_components.electricity_pro.forecast_insights import (
    find_cheapest_continuous_window,
    find_next_inexpensive_1h_window,
    find_price_direction,
)
from custom_components.electricity_pro.pricing import (
    PriceComponent,
    PriceComponentScope,
    PricingMetadata,
    PricingStrategy,
)


def _interval(
    start: datetime,
    *,
    minutes: int,
    market_price: str,
    currency: str = "SEK",
    area: str = "SE3",
) -> ForecastInterval:
    """Create a normalized forecast interval for tests."""
    return ForecastInterval(
        start=start,
        end=start + timedelta(minutes=minutes),
        market_price=Decimal(market_price),
        currency=currency,
        area=area,
        published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
    )


def test_find_cheapest_continuous_window_for_one_hour_quarter_hour_intervals() -> None:
    """The cheapest 1-hour window should be selected from quarter-hour data."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=15, market_price="0.80"),
        _interval(datetime(2026, 8, 13, 10, 15, tzinfo=UTC), minutes=15, market_price="0.70"),
        _interval(datetime(2026, 8, 13, 10, 30, tzinfo=UTC), minutes=15, market_price="0.60"),
        _interval(datetime(2026, 8, 13, 10, 45, tzinfo=UTC), minutes=15, market_price="0.50"),
        _interval(datetime(2026, 8, 13, 11, 0, tzinfo=UTC), minutes=15, market_price="0.30"),
        _interval(datetime(2026, 8, 13, 11, 15, tzinfo=UTC), minutes=15, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 11, 30, tzinfo=UTC), minutes=15, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 11, 45, tzinfo=UTC), minutes=15, market_price="0.20"),
    ]

    result = find_cheapest_continuous_window(
        intervals,
        now=now,
        duration_minutes=60,
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 11, 0, tzinfo=UTC)
    assert result.end == datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    assert result.interval_count == 4
    assert result.average_market_price == Decimal("0.225")
    assert result.average_effective_price == Decimal("0.225")


def test_find_cheapest_continuous_window_for_two_hours_hourly_intervals() -> None:
    """The cheapest 2-hour window should be selected from hourly data."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.80"),
        _interval(datetime(2026, 8, 13, 11, 0, tzinfo=UTC), minutes=60, market_price="0.30"),
        _interval(datetime(2026, 8, 13, 12, 0, tzinfo=UTC), minutes=60, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 13, 0, tzinfo=UTC), minutes=60, market_price="0.60"),
    ]

    result = find_cheapest_continuous_window(
        intervals,
        now=now,
        duration_minutes=120,
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 11, 0, tzinfo=UTC)
    assert result.end == datetime(2026, 8, 13, 13, 0, tzinfo=UTC)
    assert result.interval_count == 2
    assert result.average_market_price == Decimal("0.25")


def test_find_cheapest_continuous_window_tie_breaks_to_earliest_start() -> None:
    """Equal-price windows should prefer the earliest start."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.40"),
        _interval(datetime(2026, 8, 13, 11, 0, tzinfo=UTC), minutes=60, market_price="0.40"),
        _interval(datetime(2026, 8, 13, 12, 0, tzinfo=UTC), minutes=60, market_price="0.40"),
    ]

    result = find_cheapest_continuous_window(
        intervals,
        now=now,
        duration_minutes=120,
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    assert result.end == datetime(2026, 8, 13, 12, 0, tzinfo=UTC)


def test_find_cheapest_continuous_window_sorts_input() -> None:
    """Window selection should not depend on provider payload ordering."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 12, 0, tzinfo=UTC), minutes=60, market_price="0.10"),
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 11, 0, tzinfo=UTC), minutes=60, market_price="0.20"),
    ]

    result = find_cheapest_continuous_window(
        intervals,
        now=now,
        duration_minutes=120,
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 11, 0, tzinfo=UTC)
    assert result.average_market_price == Decimal("0.15")


def test_find_cheapest_continuous_window_rejects_gap() -> None:
    """A gap should prevent forming a continuous window across it."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.40"),
        _interval(datetime(2026, 8, 13, 12, 0, tzinfo=UTC), minutes=60, market_price="0.20"),
    ]

    result = find_cheapest_continuous_window(
        intervals,
        now=now,
        duration_minutes=120,
    )

    assert result is None


def test_find_cheapest_continuous_window_rejects_overlap() -> None:
    """An overlap should invalidate the window calculation."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.40"),
        _interval(datetime(2026, 8, 13, 10, 30, tzinfo=UTC), minutes=60, market_price="0.20"),
    ]

    result = find_cheapest_continuous_window(
        intervals,
        now=now,
        duration_minutes=120,
    )

    assert result is None


def test_find_cheapest_continuous_window_uses_weighted_average() -> None:
    """The returned average should be duration-weighted."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=15, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 10, 15, tzinfo=UTC), minutes=45, market_price="0.60"),
    ]

    result = find_cheapest_continuous_window(
        intervals,
        now=now,
        duration_minutes=60,
        grid_fee_per_kwh=Decimal("0.10"),
        energy_tax_per_kwh=Decimal("0.45"),
        supplier_markup_per_kwh=Decimal("0.08"),
    )

    assert result is not None
    assert result.average_market_price == Decimal("0.50")
    assert result.average_effective_price == Decimal("1.13")
    assert PriceComponent.ENERGY_TAX in result.pricing_metadata.scope.included
    assert PriceComponent.SUPPLIER_MARKUP in result.pricing_metadata.scope.included


def test_forecast_supplier_markup_is_not_added_twice() -> None:
    """A forecast source that includes markup should retain its supplied value."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    interval = replace(
        _interval(now, minutes=60, market_price="0.88"),
        pricing_metadata=PricingMetadata(
            strategy=PricingStrategy.SUPPLIER_CONTRACTED_PRICE,
            scope=PriceComponentScope(
                frozenset(
                    {PriceComponent.MARKET_ENERGY, PriceComponent.SUPPLIER_MARKUP}
                )
            ),
        ),
    )

    result = find_cheapest_continuous_window(
        [interval],
        now=now,
        duration_minutes=60,
        supplier_markup_per_kwh=Decimal("0.08"),
    )

    assert result is not None
    assert result.average_scheduling_price == Decimal("0.88")


def test_find_cheapest_window_applies_grid_fee_for_each_interval() -> None:
    """A time-varying grid fee should affect which forecast window is cheapest."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(now, minutes=60, market_price="0.10"),
        _interval(now + timedelta(hours=1), minutes=60, market_price="0.20"),
    ]

    result = find_cheapest_continuous_window(
        intervals,
        now=now,
        duration_minutes=60,
        grid_fee_at=lambda at: Decimal("0.30") if at == now else Decimal("0.05"),
    )

    assert result is not None
    assert result.start == now + timedelta(hours=1)
    assert result.average_market_price == Decimal("0.20")
    assert result.average_effective_price == Decimal("0.25")


def test_find_cheapest_continuous_window_excludes_currently_started_interval() -> None:
    """Upcoming windows should not start from a partially elapsed interval."""
    now = datetime(2026, 8, 13, 10, 10, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=15, market_price="0.10"),
        _interval(datetime(2026, 8, 13, 10, 15, tzinfo=UTC), minutes=15, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 10, 30, tzinfo=UTC), minutes=15, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 10, 45, tzinfo=UTC), minutes=15, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 11, 0, tzinfo=UTC), minutes=15, market_price="0.20"),
    ]

    result = find_cheapest_continuous_window(
        intervals,
        now=now,
        duration_minutes=60,
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 10, 15, tzinfo=UTC)


def test_find_price_direction_rising_for_active_and_next_interval() -> None:
    """Price direction should be rising when the next interval is more expensive."""
    now = datetime(2026, 8, 13, 10, 10, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=15, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 10, 15, tzinfo=UTC), minutes=15, market_price="0.30"),
    ]

    result = find_price_direction(intervals, now=now)

    assert result is not None
    assert result.direction == "rising"
    assert result.delta == Decimal("0.10")


def test_find_price_direction_includes_grid_fee_transition() -> None:
    """Price direction should include a tariff change between intervals."""
    now = datetime(2026, 8, 13, 10, 10, tzinfo=UTC)
    start = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(start, minutes=15, market_price="0.30"),
        _interval(start + timedelta(minutes=15), minutes=15, market_price="0.30"),
    ]

    result = find_price_direction(
        intervals,
        now=now,
        grid_fee_at=lambda at: Decimal("0.10") if at == start else Decimal("0.25"),
    )

    assert result is not None
    assert result.direction == "rising"
    assert result.delta == Decimal("0.15")


def test_find_price_direction_falling_for_active_and_next_interval() -> None:
    """Price direction should be falling when the next interval is cheaper."""
    now = datetime(2026, 8, 13, 10, 10, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=15, market_price="0.40"),
        _interval(datetime(2026, 8, 13, 10, 15, tzinfo=UTC), minutes=15, market_price="0.20"),
    ]

    result = find_price_direction(intervals, now=now)

    assert result is not None
    assert result.direction == "falling"
    assert result.delta == Decimal("-0.20")


def test_find_price_direction_stable_for_equal_prices() -> None:
    """Price direction should be stable when the compared prices are equal."""
    now = datetime(2026, 8, 13, 10, 10, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=15, market_price="0.25"),
        _interval(datetime(2026, 8, 13, 10, 15, tzinfo=UTC), minutes=15, market_price="0.25"),
    ]

    result = find_price_direction(intervals, now=now)

    assert result is not None
    assert result.direction == "stable"
    assert result.delta == Decimal("0.00")


def test_find_price_direction_uses_first_two_future_intervals_without_active_one() -> None:
    """Future intervals should be compared when there is no active interval."""
    now = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 11, 0, tzinfo=UTC), minutes=60, market_price="0.50"),
    ]

    result = find_price_direction(intervals, now=now)

    assert result is not None
    assert result.direction == "rising"
    assert result.current_start == datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    assert result.next_start == datetime(2026, 8, 13, 11, 0, tzinfo=UTC)


def test_find_price_direction_returns_none_when_fewer_than_two_intervals_exist() -> None:
    """At least two usable intervals are required for price direction."""
    result = find_price_direction(
        [_interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.20")],
        now=datetime(2026, 8, 13, 9, 0, tzinfo=UTC),
    )

    assert result is None


def test_find_price_direction_returns_none_on_overlap() -> None:
    """Overlapping intervals should invalidate price direction."""
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 10, 30, tzinfo=UTC), minutes=60, market_price="0.30"),
    ]

    result = find_price_direction(
        intervals,
        now=datetime(2026, 8, 13, 10, 10, tzinfo=UTC),
    )

    assert result is None


def test_find_next_inexpensive_1h_window_returns_earliest_qualifying_window() -> None:
    """The first window at or below threshold should be returned."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.80"),
        _interval(datetime(2026, 8, 13, 11, 0, tzinfo=UTC), minutes=60, market_price="0.50"),
        _interval(datetime(2026, 8, 13, 12, 0, tzinfo=UTC), minutes=60, market_price="0.30"),
    ]

    result = find_next_inexpensive_1h_window(
        intervals,
        now=now,
        threshold=Decimal("0.55"),
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 11, 0, tzinfo=UTC)
    assert result.end == datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    assert result.duration_minutes == 60
    assert result.interval_count == 1
    assert result.average_effective_price == Decimal("0.50")
    assert result.threshold == Decimal("0.55")


def test_find_next_inexpensive_1h_window_returns_none_when_none_qualify() -> None:
    """None should be returned when every upcoming window exceeds the threshold."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.80"),
        _interval(datetime(2026, 8, 13, 11, 0, tzinfo=UTC), minutes=60, market_price="0.70"),
    ]

    result = find_next_inexpensive_1h_window(
        intervals,
        now=now,
        threshold=Decimal("0.60"),
    )

    assert result is None


def test_find_next_inexpensive_1h_window_qualifies_on_exact_threshold() -> None:
    """A window exactly equal to the threshold should qualify."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.50"),
    ]

    result = find_next_inexpensive_1h_window(
        intervals,
        now=now,
        threshold=Decimal("0.50"),
    )

    assert result is not None
    assert result.average_effective_price == Decimal("0.50")


def test_find_next_inexpensive_1h_window_uses_effective_price_for_comparison() -> None:
    """The threshold comparison should use the effective price including adjustments."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.40"),
        _interval(datetime(2026, 8, 13, 11, 0, tzinfo=UTC), minutes=60, market_price="0.30"),
    ]

    # With grid_fee=0.15, effective prices are 0.55 and 0.45; threshold 0.50 skips first
    result = find_next_inexpensive_1h_window(
        intervals,
        now=now,
        threshold=Decimal("0.50"),
        grid_fee_per_kwh=Decimal("0.15"),
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 11, 0, tzinfo=UTC)
    assert result.average_effective_price == Decimal("0.45")
    assert result.average_market_price == Decimal("0.30")


def test_find_next_inexpensive_1h_window_quarter_hour_intervals() -> None:
    """The function should compose four 15-min intervals into a qualifying 1h window."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    # All four first intervals are 0.90; the second four are 0.20.
    # Starting at 10:45 gives avg (0.90+0.20+0.20+0.20)/4=0.375, which already qualifies.
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=15, market_price="0.90"),
        _interval(datetime(2026, 8, 13, 10, 15, tzinfo=UTC), minutes=15, market_price="0.90"),
        _interval(datetime(2026, 8, 13, 10, 30, tzinfo=UTC), minutes=15, market_price="0.90"),
        _interval(datetime(2026, 8, 13, 10, 45, tzinfo=UTC), minutes=15, market_price="0.90"),
        _interval(datetime(2026, 8, 13, 11, 0, tzinfo=UTC), minutes=15, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 11, 15, tzinfo=UTC), minutes=15, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 11, 30, tzinfo=UTC), minutes=15, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 11, 45, tzinfo=UTC), minutes=15, market_price="0.20"),
    ]

    result = find_next_inexpensive_1h_window(
        intervals,
        now=now,
        threshold=Decimal("0.50"),
    )

    assert result is not None
    # 10:45 window: (0.90+0.20+0.20+0.20)/4 = 0.375 ≤ 0.50 — earliest qualifying
    assert result.start == datetime(2026, 8, 13, 10, 45, tzinfo=UTC)
    assert result.end == datetime(2026, 8, 13, 11, 45, tzinfo=UTC)
    assert result.interval_count == 4


def test_find_next_inexpensive_1h_window_excludes_past_intervals() -> None:
    """Intervals starting before now should not be considered."""
    now = datetime(2026, 8, 13, 11, 5, tzinfo=UTC)
    intervals = [
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.10"),
        _interval(datetime(2026, 8, 13, 11, 0, tzinfo=UTC), minutes=60, market_price="0.10"),
        _interval(datetime(2026, 8, 13, 12, 0, tzinfo=UTC), minutes=60, market_price="0.30"),
    ]

    result = find_next_inexpensive_1h_window(
        intervals,
        now=now,
        threshold=Decimal("0.50"),
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 12, 0, tzinfo=UTC)


def test_find_next_inexpensive_1h_window_returns_none_on_empty_intervals() -> None:
    """An empty interval list should return None."""
    result = find_next_inexpensive_1h_window(
        [],
        now=datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
        threshold=Decimal("1.00"),
    )

    assert result is None


def test_find_cheapest_continuous_window_skips_overlapping_start_finds_later_valid_window() -> None:
    """An overlap at an early start should not prevent finding a valid later window."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        # A and B overlap — any window starting at A or B cannot complete cleanly
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.50"),
        _interval(datetime(2026, 8, 13, 10, 30, tzinfo=UTC), minutes=60, market_price="0.50"),
        # C and D are contiguous and form a valid 2h window
        _interval(datetime(2026, 8, 13, 12, 0, tzinfo=UTC), minutes=60, market_price="0.30"),
        _interval(datetime(2026, 8, 13, 13, 0, tzinfo=UTC), minutes=60, market_price="0.30"),
    ]

    result = find_cheapest_continuous_window(
        intervals,
        now=now,
        duration_minutes=120,
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    assert result.end == datetime(2026, 8, 13, 14, 0, tzinfo=UTC)
    assert result.interval_count == 2


def test_find_cheapest_continuous_window_gap_before_valid_window_returns_later_result() -> None:
    """A gap early in the list should not prevent finding a valid window later."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        # Lone interval — cannot form a 2h window by itself
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.20"),
        # Gap here (missing 11:00–12:00)
        _interval(datetime(2026, 8, 13, 12, 0, tzinfo=UTC), minutes=60, market_price="0.40"),
        _interval(datetime(2026, 8, 13, 13, 0, tzinfo=UTC), minutes=60, market_price="0.40"),
    ]

    result = find_cheapest_continuous_window(
        intervals,
        now=now,
        duration_minutes=120,
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    assert result.end == datetime(2026, 8, 13, 14, 0, tzinfo=UTC)


def test_find_price_direction_skips_overlapping_pair_finds_next_clean_pair() -> None:
    """An overlapping pair should be skipped; the next clean pair should be used."""
    # now is inside C so the A/B overlap pair and the B/C gap pair are both bypassed
    now = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    intervals = [
        # A and B overlap — this pair is invalid
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 10, 30, tzinfo=UTC), minutes=60, market_price="0.30"),
        # C and D are a clean contiguous pair; now falls inside C
        _interval(datetime(2026, 8, 13, 12, 0, tzinfo=UTC), minutes=60, market_price="0.20"),
        _interval(datetime(2026, 8, 13, 13, 0, tzinfo=UTC), minutes=60, market_price="0.50"),
    ]

    result = find_price_direction(intervals, now=now)

    assert result is not None
    assert result.direction == "rising"
    assert result.current_start == datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    assert result.next_start == datetime(2026, 8, 13, 13, 0, tzinfo=UTC)


def test_find_next_inexpensive_1h_window_skips_overlapping_start_finds_later_valid_window() -> None:
    """An overlap at an early start should not prevent finding a qualifying window later."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        # A and B overlap — cannot form a 1h window starting at A
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=60, market_price="0.80"),
        _interval(datetime(2026, 8, 13, 10, 30, tzinfo=UTC), minutes=60, market_price="0.80"),
        # C is a valid 1h interval at or below threshold
        _interval(datetime(2026, 8, 13, 12, 0, tzinfo=UTC), minutes=60, market_price="0.40"),
    ]

    result = find_next_inexpensive_1h_window(
        intervals,
        now=now,
        threshold=Decimal("0.50"),
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    assert result.end == datetime(2026, 8, 13, 13, 0, tzinfo=UTC)
    assert result.average_effective_price == Decimal("0.40")


def test_find_next_inexpensive_1h_window_gap_before_valid_window_returns_later_result() -> None:
    """A gap early in the list should not prevent finding a qualifying window later."""
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    intervals = [
        # Pair with a gap — neither alone forms a 1h window (each is 30 min)
        _interval(datetime(2026, 8, 13, 10, 0, tzinfo=UTC), minutes=30, market_price="0.80"),
        # Gap here (missing 10:30–11:00)
        _interval(datetime(2026, 8, 13, 11, 0, tzinfo=UTC), minutes=30, market_price="0.80"),
        # A clean contiguous pair forming a 1h window below threshold
        _interval(datetime(2026, 8, 13, 12, 0, tzinfo=UTC), minutes=30, market_price="0.40"),
        _interval(datetime(2026, 8, 13, 12, 30, tzinfo=UTC), minutes=30, market_price="0.40"),
    ]

    result = find_next_inexpensive_1h_window(
        intervals,
        now=now,
        threshold=Decimal("0.50"),
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    assert result.end == datetime(2026, 8, 13, 13, 0, tzinfo=UTC)
    assert result.interval_count == 2


# ---------------------------------------------------------------------------
# Timezone-aware and DST edge-case coverage
# ---------------------------------------------------------------------------


def test_find_cheapest_continuous_window_with_stockholm_tz_aware_datetimes() -> None:
    """Window selection works correctly when intervals carry a non-UTC local timezone."""
    import zoneinfo

    tz = zoneinfo.ZoneInfo("Europe/Stockholm")
    # Four 15-minute intervals starting at 10:00 local time (UTC+2 in summer)
    t0 = datetime(2026, 8, 13, 10, 0, tzinfo=tz)
    intervals = [
        _interval(t0, minutes=15, market_price="0.80"),
        _interval(t0 + timedelta(minutes=15), minutes=15, market_price="0.70"),
        _interval(t0 + timedelta(minutes=30), minutes=15, market_price="0.60"),
        _interval(t0 + timedelta(minutes=45), minutes=15, market_price="0.50"),
    ]

    result = find_cheapest_continuous_window(
        intervals,
        now=t0,
        duration_minutes=60,
    )

    assert result is not None
    assert result.start == t0
    assert result.duration_minutes == 60
    assert result.interval_count == 4


def test_find_cheapest_continuous_window_dst_spring_forward_adjacent_slots() -> None:
    """On a DST spring-forward day two adjacent UTC slots still form a valid window.

    In Europe/Stockholm, clocks spring forward at 02:00 → 03:00 on the last
    Sunday of March (2025-03-30).  Nord Pool publishes UTC-based intervals, so
    adjacent UTC hours are always contiguous regardless of local clock changes.
    The slot 01:00–02:00 UTC+1 ends at the same UTC instant as 03:00+02:00
    begins.  A 2-hour window that spans this DST boundary must form correctly
    when the tzinfo objects carry explicit fixed offsets (as produced by
    dt_util.parse_datetime from ISO strings with offsets).
    """
    from datetime import timezone

    tz_plus1 = timezone(timedelta(hours=1))
    tz_plus2 = timezone(timedelta(hours=2))
    # 01:00+01:00 → 02:00+01:00 is 00:00–01:00 UTC
    # 03:00+02:00 → 04:00+02:00 is 01:00–02:00 UTC — directly adjacent
    slot_before = datetime(2025, 3, 30, 1, 0, tzinfo=tz_plus1)
    slot_after  = datetime(2025, 3, 30, 3, 0, tzinfo=tz_plus2)
    intervals = [
        ForecastInterval(
            start=slot_before,
            end=slot_before + timedelta(hours=1),   # 02:00+01:00 = 01:00 UTC
            market_price=Decimal("0.20"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2025, 3, 29, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=slot_after,                        # 03:00+02:00 = 01:00 UTC
            end=slot_after + timedelta(hours=1),
            market_price=Decimal("0.30"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2025, 3, 29, 11, 0, tzinfo=UTC),
        ),
    ]

    # The two 1-hour slots are UTC-adjacent and must form a valid 2h window.
    result = find_cheapest_continuous_window(
        intervals,
        now=slot_before,
        duration_minutes=120,
    )

    assert result is not None
    assert result.interval_count == 2
    assert result.duration_minutes == 120
    assert result.start == slot_before


def test_find_cheapest_continuous_window_dst_fall_back_extra_hour() -> None:
    """On a DST fall-back day the extra hour produces 25 contiguous intervals.

    In Europe/Stockholm, clocks fall back at 03:00 → 02:00 on the last Sunday
    of October.  Nord Pool publishes an interval for each UTC hour, so the local
    day has 25 hourly slots.  A 3-hour window request over those slots must work
    correctly on actual interval boundaries without assuming 24 slots.
    """
    import zoneinfo
    from datetime import UTC as _UTC

    # 2025-10-26 is the fall-back day for Europe/Stockholm.
    # Build 25 contiguous UTC-based hourly intervals covering the full day.
    # Prices fall steadily — the cheapest 3h window is at the end (22:00–01:00 UTC).
    published = datetime(2025, 10, 25, 11, 0, tzinfo=_UTC)
    intervals = []
    for hour in range(25):
        start = datetime(2025, 10, 25, 23, 0, tzinfo=_UTC) + timedelta(hours=hour)
        intervals.append(
            ForecastInterval(
                start=start,
                end=start + timedelta(hours=1),
                market_price=Decimal(str(round(1.00 - hour * 0.04, 2))),
                currency="SEK",
                area="SE3",
                published_at=published,
            )
        )

    # now = first interval start; cheapest 3h = last 3 intervals (hours 22–24)
    now = intervals[0].start
    result = find_cheapest_continuous_window(
        intervals,
        now=now,
        duration_minutes=180,
    )

    assert result is not None
    assert result.interval_count == 3
    assert result.start == intervals[22].start
    assert result.end == intervals[24].end
    assert result.duration_minutes == 180


def test_find_price_direction_across_dst_spring_forward_boundary() -> None:
    """Price direction resolves correctly for intervals that straddle a DST transition.

    Nord Pool uses ISO timestamps with explicit UTC offsets.  When intervals on a
    spring-forward day are expressed with their respective local offsets (+01:00
    before the transition, +02:00 after), 'now' inside the first interval should
    correctly yield a rising direction comparing the pre-transition and
    post-transition slots.
    """
    from datetime import timezone

    tz_plus1 = timezone(timedelta(hours=1))
    tz_plus2 = timezone(timedelta(hours=2))
    slot_before = datetime(2025, 3, 30, 1, 0, tzinfo=tz_plus1)   # 00:00 UTC
    slot_after  = datetime(2025, 3, 30, 3, 0, tzinfo=tz_plus2)   # 01:00 UTC

    first = ForecastInterval(
        start=slot_before,
        end=slot_before + timedelta(hours=1),   # 02:00+01:00 = 01:00 UTC
        market_price=Decimal("0.30"),
        currency="SEK",
        area="SE3",
        published_at=datetime(2025, 3, 29, 11, 0, tzinfo=UTC),
    )
    second = ForecastInterval(
        start=slot_after,                        # 03:00+02:00 = 01:00 UTC
        end=slot_after + timedelta(hours=1),
        market_price=Decimal("0.50"),
        currency="SEK",
        area="SE3",
        published_at=datetime(2025, 3, 29, 11, 0, tzinfo=UTC),
    )

    now = slot_before + timedelta(minutes=15)
    result = find_price_direction([first, second], now=now)

    assert result is not None
    assert result.direction == "rising"
    assert result.current_start == slot_before
    assert result.next_start == slot_after


def test_find_next_inexpensive_1h_window_uses_interval_boundaries_not_fixed_indexes() -> None:
    """The 1h window must be assembled from real interval end-to-start continuity.

    A data set where intervals have heterogeneous durations (30 min then 15 min)
    verifies that the 60-minute accumulation uses actual boundaries and minutes,
    not positional slot assumptions.
    """
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    # 30+15+15 = 60 minutes exactly — qualifies
    intervals = [
        ForecastInterval(
            start=datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 10, 30, tzinfo=UTC),
            market_price=Decimal("0.20"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 10, 30, tzinfo=UTC),
            end=datetime(2026, 8, 13, 10, 45, tzinfo=UTC),
            market_price=Decimal("0.20"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 10, 45, tzinfo=UTC),
            end=datetime(2026, 8, 13, 11, 0, tzinfo=UTC),
            market_price=Decimal("0.20"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
    ]

    result = find_next_inexpensive_1h_window(
        intervals,
        now=now,
        threshold=Decimal("0.50"),
    )

    assert result is not None
    assert result.start == datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    assert result.end == datetime(2026, 8, 13, 11, 0, tzinfo=UTC)
    assert result.interval_count == 3
    assert result.duration_minutes == 60
