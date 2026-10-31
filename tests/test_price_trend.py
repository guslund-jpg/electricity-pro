"""Rolling two-hour price-trend contract, independent of HA state."""

from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from custom_components.electricity_pro.forecast import (
    ForecastInterval,
    NORDPOOL_MARKET_PRICE_METADATA,
)
from custom_components.electricity_pro.forecast_insights import find_price_direction
from custom_components.electricity_pro.grid_tariff import HighLowGridTariff
from custom_components.electricity_pro.pricing import (
    PriceComponent,
    PriceComponentScope,
    VatTreatment,
)

NOW = datetime(2026, 10, 31, 23, tzinfo=UTC)
STOCKHOLM = ZoneInfo("Europe/Stockholm")


def interval(start=NOW, minutes=60, price="1", **kwargs):
    """Build a VAT-resolved interval with exact elapsed boundaries."""
    return ForecastInterval(
        start=start,
        end=start + timedelta(minutes=minutes),
        market_price=Decimal(price),
        currency="SEK",
        area="SE3",
        pricing_metadata=replace(NORDPOOL_MARKET_PRICE_METADATA, vat_rate=Decimal(0)),
        **kwargs,
    )


def test_quarter_hour_noise_does_not_define_hourly_trend():
    """The next quarter rises, but the next-hour average falls."""
    series = [
        interval(NOW + timedelta(minutes=15 * n), 15, str(p))
        for n, p in enumerate([2, 3, 1, 2, 1, 2, 0, 1])
    ]
    result = find_price_direction(series, now=NOW)
    assert result is not None
    assert result.direction == "falling"
    assert result.current_scheduling_price == 2
    assert result.next_scheduling_price == 1
    assert result.delta == -1
    assert result.current_start == NOW
    assert result.next_end == NOW + timedelta(hours=2)


def test_clips_partial_intervals_at_now_hour_split_and_end():
    """Weight actual seconds, not interval counts or rounded minutes."""
    series = [
        interval(NOW, price="0.2"),
        interval(NOW + timedelta(hours=1), price="0.6"),
        interval(NOW + timedelta(hours=2), price="0.1"),
    ]
    now = NOW + timedelta(minutes=7, seconds=30)
    result = find_price_direction(series, now=now)
    assert result is not None
    assert result.current_start == now
    assert result.current_scheduling_price == Decimal("0.25")
    assert result.next_scheduling_price == Decimal("0.5375")


def test_mixed_resolutions_and_forecast_revisions():
    """Mixed durations weight correctly; a later revision is not cached here."""
    series = [
        interval(NOW, 30, "1"),
        interval(NOW + timedelta(minutes=30), 15, "2"),
        interval(NOW + timedelta(minutes=45), 15, "4"),
        interval(NOW + timedelta(hours=1), 60, "3"),
    ]
    result = find_price_direction(list(reversed(series)), now=NOW)
    assert result is not None
    assert result.current_scheduling_price == 2
    assert result.direction == "rising"
    revised = [*series[:-1], replace(series[-1], market_price=Decimal(1))]
    result = find_price_direction(revised, now=NOW)
    assert result is not None and result.direction == "falling"
    assert series[-1].market_price == 3


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ("0.98", "1", "stable"),
        ("1", "0.98", "stable"),
        ("0.9799", "1", "rising"),
        ("1", "0.9799", "falling"),
        ("-1", "-0.98", "stable"),
        ("-2", "-3", "falling"),
        ("-3", "-2", "rising"),
        ("-0.01", "0.01", "rising"),
        ("0", "0", "stable"),
        ("0", "0.000001", "rising"),
    ],
)
@pytest.mark.parametrize("scale", [Decimal(1), Decimal("0.1")])
def test_relative_tolerance_is_symmetric_signed_and_currency_scale_independent(
    first, second, expected, scale
):
    series = [
        interval(price=str(Decimal(first) * scale)),
        interval(NOW + timedelta(hours=1), price=str(Decimal(second) * scale)),
    ]
    result = find_price_direction(series, now=NOW)
    assert result is not None and result.direction == expected
    assert result.stable_tolerance == max(
        abs(Decimal(first)), abs(Decimal(second))
    ) * scale * Decimal("0.02")


@pytest.mark.parametrize(
    "fault",
    [
        "gap",
        "overlap",
        "duplicate",
        "short",
        "no_current",
        "area",
        "currency",
        "vat",
        "scope",
    ],
)
def test_incomplete_or_incomparable_horizon_is_unavailable(fault):
    first = interval()
    second = interval(NOW + timedelta(hours=1))
    if fault in ("gap", "overlap"):
        second = replace(
            second, start=second.start + timedelta(seconds=1 if fault == "gap" else -1)
        )
    elif fault == "short":
        second = replace(second, end=second.end - timedelta(microseconds=1))
    elif fault == "no_current":
        first = replace(first, start=first.start + timedelta(seconds=1))
    elif fault in ("area", "currency"):
        second = replace(second, **{fault: "OTHER"})
    elif fault == "vat":
        second = replace(second, pricing_metadata=NORDPOOL_MARKET_PRICE_METADATA)
    elif fault == "scope":
        second = replace(
            second,
            pricing_metadata=replace(
                second.pricing_metadata,
                scope=PriceComponentScope(
                    frozenset(
                        {PriceComponent.MARKET_ENERGY, PriceComponent.SUPPLIER_MARKUP}
                    ),
                    VatTreatment.INCLUDED,
                ),
            ),
        )
    series = [first, second]
    if fault == "duplicate":
        series.append(replace(second, market_price=Decimal(4)))
    assert find_price_direction(series, now=NOW) is None


def test_outside_horizon_unknown_vat_does_not_poison_valid_coverage():
    series = [
        interval(),
        interval(NOW + timedelta(hours=1)),
        replace(
            interval(NOW + timedelta(hours=3)),
            pricing_metadata=NORDPOOL_MARKET_PRICE_METADATA,
        ),
    ]
    assert find_price_direction(series, now=NOW) is not None


def test_vat_markup_and_tax_are_applied_once():
    series = [
        replace(
            interval(NOW, 120),
            pricing_metadata=replace(
                NORDPOOL_MARKET_PRICE_METADATA, vat_rate=Decimal("25")
            ),
        )
    ]
    result = find_price_direction(
        series,
        now=NOW,
        supplier_markup_per_kwh=Decimal("0.1"),
        grid_fee_per_kwh=Decimal("0.2"),
        energy_tax_per_kwh=Decimal("0.45"),
    )
    assert result is not None and result.current_scheduling_price == 2
    included = replace(
        series[0], market_price=Decimal(2), pricing_metadata=result.pricing_metadata
    )
    result = find_price_direction(
        [included],
        now=NOW,
        supplier_markup_per_kwh=Decimal("0.1"),
        grid_fee_per_kwh=Decimal("0.2"),
        energy_tax_per_kwh=Decimal("0.45"),
    )
    assert result is not None and result.next_scheduling_price == 2


@pytest.mark.parametrize("fee", [None, Decimal("NaN"), Decimal("Infinity")])
def test_missing_tariff_scope_or_nonfinite_adjustment_is_unavailable(fee):
    assert (
        find_price_direction(
            [interval(NOW, 120)],
            now=NOW,
            grid_fee_at=lambda t: Decimal(1) if t < NOW + timedelta(hours=1) else fee,
        )
        is None
    )


def tariff(**kwargs):
    return HighLowGridTariff(
        low_fee_per_kwh=Decimal(0),
        high_fee_per_kwh=Decimal(2),
        high_season_start=(1, 1),
        high_season_end=(12, 31),
        high_weekdays=frozenset(range(7)),
        **kwargs,
    )


def test_tariff_change_inside_hourly_forecast_and_hour_split():
    schedule = tariff(high_start_time=time(1, 30), high_end_time=time(3))
    result = find_price_direction(
        [interval(NOW, 180, "1")],
        now=NOW,
        grid_fee_at=lambda t: schedule.fee_at(t.astimezone(STOCKHOLM)),
        grid_fee_change_times=schedule.change_boundaries(
            NOW, NOW + timedelta(hours=2), STOCKHOLM
        ),
    )
    assert result is not None
    assert result.current_scheduling_price == 1  # local 00:00–01:00
    assert result.next_scheduling_price == 2  # local 01:00–02:00, fee rises at 01:30


def test_midnight_excluded_date_tariff_boundary():
    schedule = tariff(
        high_start_time=time(22),
        high_end_time=time(6),
        excluded_dates=frozenset({date(2026, 11, 1)}),
    )
    start = NOW - timedelta(hours=1)  # local Oct 31 23:00
    result = find_price_direction(
        [interval(start, 120)],
        now=start,
        grid_fee_at=lambda t: schedule.fee_at(t.astimezone(STOCKHOLM)),
        grid_fee_change_times=schedule.change_boundaries(
            start, start + timedelta(hours=2), STOCKHOLM
        ),
    )
    assert result is not None
    assert result.current_scheduling_price == 3 and result.next_scheduling_price == 1


@pytest.mark.parametrize(
    "start",
    [datetime(2026, 3, 29, 0, tzinfo=UTC), datetime(2026, 10, 25, 0, tzinfo=UTC)],
)
def test_dst_uses_two_elapsed_hours_and_real_tariff_transitions(start):
    schedule = tariff(high_start_time=time(2, 15), high_end_time=time(3, 30))
    # A single long UTC interval converted to the SAME ZoneInfo at both ends.
    source = interval(start, 120)
    source = replace(
        source,
        start=source.start.astimezone(STOCKHOLM),
        end=source.end.astimezone(STOCKHOLM),
    )
    result = find_price_direction(
        [source],
        now=start.astimezone(STOCKHOLM),
        grid_fee_at=lambda t: schedule.fee_at(t.astimezone(STOCKHOLM)),
        grid_fee_change_times=schedule.change_boundaries(
            start, start + timedelta(hours=2), STOCKHOLM
        ),
    )
    assert result is not None
    assert result.next_end - result.current_start == timedelta(hours=2)
    if start.month == 3:
        assert result.current_scheduling_price == 1
        assert result.next_scheduling_price == 2  # jump to 03:00, high until 03:30
    else:
        assert result.current_scheduling_price == Decimal("2.5")
        assert result.next_scheduling_price == Decimal("2.5")  # repeated 02:15 boundary


def test_naive_now_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        find_price_direction([], now=NOW.replace(tzinfo=None))
