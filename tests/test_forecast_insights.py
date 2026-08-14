"""Tests for pure forecast insight calculations."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from custom_components.electricity_pro.forecast import ForecastInterval
from custom_components.electricity_pro.forecast_insights import (
    find_cheapest_continuous_window,
    find_next_inexpensive_1h_window,
    find_price_direction,
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
        tax_per_kwh=Decimal("0.05"),
    )

    assert result is not None
    assert result.average_market_price == Decimal("0.50")
    assert result.average_effective_price == Decimal("0.65")


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
