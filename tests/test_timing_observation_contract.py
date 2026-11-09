"""Characterize live timing observations at the coordinator boundary."""

import json
from dataclasses import replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_POWER_ENTITY,
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_ENTITY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICING_STRATEGY,
    DOMAIN,
)
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.pricing import (
    PriceCompleteness,
    PriceComponent,
    PricingStrategy,
    VatTreatment,
)
from custom_components.electricity_pro.timing_score import TimingScoreUnavailableReason

_DAY = date(2026, 8, 24)


async def _coordinator(hass):
    """Create a local runtime with a declared, VAT-inclusive complete price."""
    await hass.config.async_set_time_zone("Europe/Stockholm")
    hass.states.async_set("sensor.test_power", "600", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.test_price", "1", {"unit_of_measurement": "SEK/kWh"})
    return ElectricityProCoordinator(
        hass,
        MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_POWER_ENTITY: "sensor.test_power",
                CONF_PRICE_ENTITY: "sensor.test_price",
                CONF_PRICING_STRATEGY: PricingStrategy.EXTERNAL_COMPLETE_PRICE,
                CONF_PRICE_INCLUDED_COMPONENTS: list(PriceComponent),
                CONF_PRICE_VAT_TREATMENT: VatTreatment.INCLUDED,
                CONF_PRICE_COMPLETENESS: PriceCompleteness.COMPLETE,
            },
            entry_id="timing-observation-contract",
        ),
    )


def _update(coordinator, now, power="600", price="1", *, observed=False):
    """Supply normalized readings while retaining real effective-price calculation."""
    inputs = coordinator._provider.read()
    return coordinator._update_timing_history(
        replace(
            inputs,
            readings=replace(
                inputs.readings,
                current_power=Decimal(power) if power is not None else None,
                current_price=Decimal(price) if price is not None else None,
            ),
        ),
        now,
        power_observed=observed,
    )


def _intervals(coordinator, day=_DAY):
    return coordinator._timing_buckets.intervals_for_date(day)


async def test_timing_observation_closes_previous_power_and_price_before_replacing(
    hass,
):
    """Fractional/negative prices must price their own preceding intervals only."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, 0, 12, tzinfo=coordinator._local_timezone)
    assert not _update(coordinator, start, "600", "-0.1000", observed=True)
    assert _update(
        coordinator, start + timedelta(minutes=4), "1200", "0.2500", observed=True
    )
    assert not _update(coordinator, start + timedelta(minutes=8), "999", "0.9000")

    assert [
        (i.energy_kwh, i.effective_price, i.covered_duration)
        for i in _intervals(coordinator)
    ] == [
        (Decimal("0.03"), Decimal("-0.1000"), timedelta(minutes=3)),
        (Decimal("0.09"), Decimal("0.18"), timedelta(minutes=5)),
    ]


async def test_timing_observation_price_updates_do_not_renew_held_power(hass):
    """Price-only updates change future price but cannot prolong power coverage."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, tzinfo=coordinator._local_timezone)
    flags = [
        _update(coordinator, start, observed=True),
        _update(coordinator, start + timedelta(minutes=5), "999", "2"),
        _update(coordinator, start + timedelta(minutes=20), "999", "3"),
        _update(coordinator, start + timedelta(minutes=25), "999", "4"),
    ]

    assert flags == [False, False, False, False]
    intervals = _intervals(coordinator)
    assert len(intervals) == 1
    assert intervals[0].energy_kwh == Decimal("0.1")
    assert intervals[0].effective_price == Decimal("1.5")
    assert intervals[0].covered_duration == timedelta(minutes=10)


@pytest.mark.parametrize(
    ("elapsed_seconds", "covered_seconds"), [(599, 599), (600, 600), (601, 600)]
)
async def test_timing_observation_preserves_exact_hold_boundary(
    hass, elapsed_seconds, covered_seconds
):
    """The existing ten-minute expiry controls coverage and the quarter signal."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, 0, 10, tzinfo=coordinator._local_timezone)
    _update(coordinator, start, observed=True)

    assert _update(coordinator, start + timedelta(seconds=elapsed_seconds))

    assert sum(
        (i.covered_duration for i in _intervals(coordinator)), timedelta(0)
    ) == timedelta(seconds=covered_seconds)


async def test_timing_observation_missing_price_leaves_gap_without_backfill(hass):
    """Returning prices apply from their observation, using still-fresh power."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, tzinfo=coordinator._local_timezone)
    _update(coordinator, start, observed=True)
    _update(coordinator, start + timedelta(minutes=2), price=None)
    _update(coordinator, start + timedelta(minutes=4), price="2")
    _update(coordinator, start + timedelta(minutes=6), price="2")

    (interval,) = _intervals(coordinator)
    assert interval.energy_kwh == Decimal("0.04")
    assert interval.effective_price == Decimal("1.5")
    assert interval.covered_duration == timedelta(minutes=4)
    assert coordinator._timing_buckets.longest_uncovered_gap(
        _DAY, day_start=start, day_end=start + timedelta(minutes=6)
    ) == timedelta(minutes=2)


@pytest.mark.parametrize(
    ("power", "observed", "minutes", "energy"),
    [
        (None, True, 5, "0.05"),
        ("-100", True, 5, "0.05"),
        ("0", True, 10, "0.05"),
        (None, False, 10, "0.1"),
        ("-100", False, 10, "0.1"),
    ],
)
async def test_timing_observation_preserves_missing_negative_and_zero_power(
    hass, power, observed, minutes, energy
):
    """Only explicit source observations replace or invalidate the held power."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, tzinfo=coordinator._local_timezone)
    _update(coordinator, start, observed=True)
    _update(coordinator, start + timedelta(minutes=5), power, observed=observed)
    _update(coordinator, start + timedelta(minutes=10))

    (interval,) = _intervals(coordinator)
    assert interval.energy_kwh == Decimal(energy)
    assert interval.effective_price == Decimal(1)
    assert interval.covered_duration == timedelta(minutes=minutes)


async def test_timing_observation_equal_timestamp_retains_new_values_without_duration(
    hass,
):
    """Repeated timestamps add no coverage, but replace the power/price sample."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, tzinfo=coordinator._local_timezone)
    _update(coordinator, start, "600", "1", observed=True)
    assert not _update(coordinator, start, "1200", "2", observed=True)
    assert not _intervals(coordinator)
    _update(coordinator, start + timedelta(minutes=5), "999", "3")

    (interval,) = _intervals(coordinator)
    assert interval.energy_kwh == Decimal("0.1")
    assert interval.effective_price == Decimal(2)
    assert interval.covered_duration == timedelta(minutes=5)


async def test_timing_observation_rollover_finalizes_before_retaining_new_day(hass):
    """A held sample can span midnight while yesterday finalizes before pruning."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, 23, 58, tzinfo=coordinator._local_timezone)
    _update(coordinator, start, observed=True)
    with patch.object(coordinator, "_schedule_statistics_save") as save:
        coordinator._async_daily_rollover(start + timedelta(minutes=2))
    save.assert_called_once_with(immediate=True)
    result_day, result = coordinator.timing_score_yesterday
    assert result_day == _DAY
    assert result.energy_kwh == Decimal("0.02")
    assert (
        result.unavailable_reason is TimingScoreUnavailableReason.INSUFFICIENT_COVERAGE
    )
    assert not _intervals(coordinator)

    _update(coordinator, start + timedelta(minutes=4))

    (interval,) = _intervals(coordinator, date(2026, 8, 25))
    assert interval.energy_kwh == Decimal("0.02")
    assert interval.effective_price == Decimal(1)
    assert interval.covered_duration == timedelta(minutes=2)


async def test_timing_observation_restart_restores_json_without_replaying_live_sample(
    hass,
):
    """Saved history survives while live power and price require new observations."""
    original = await _coordinator(hass)
    start = datetime(2026, 8, 24, tzinfo=original._local_timezone)
    _update(original, start, observed=True)
    _update(original, start + timedelta(minutes=5))
    stored = json.loads(json.dumps(original._statistics_data()))
    restored = await _coordinator(hass)
    with patch.object(restored._store, "async_load", AsyncMock(return_value=stored)):
        await restored._async_restore_statistics()

    assert not _update(restored, start + timedelta(minutes=15), price="2")
    assert (
        restored._statistics_data()["consumption_timing_buckets"]
        == stored["consumption_timing_buckets"]
    )
    assert set(restored._statistics_data()) == set(stored)
    _update(restored, start + timedelta(minutes=15), price="2", observed=True)
    assert not _update(restored, start + timedelta(minutes=20), price="3")
    assert [
        (i.energy_kwh, i.effective_price, i.covered_duration)
        for i in _intervals(restored)
    ] == [
        (Decimal("0.05"), Decimal(1), timedelta(minutes=5)),
        (Decimal("0.05"), Decimal(2), timedelta(minutes=5)),
    ]


async def test_timing_observation_price_calculation_keeps_existing_update_order(hass):
    """If calculation raises, prior coverage/new power are kept and old price remains."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, tzinfo=coordinator._local_timezone)
    _update(coordinator, start, observed=True)
    with (
        patch(
            "custom_components.electricity_pro.coordinator.calculate_declared_effective_price",
            side_effect=RuntimeError("calculation failed"),
        ),
        pytest.raises(RuntimeError, match="calculation failed"),
    ):
        _update(coordinator, start + timedelta(minutes=5), "1200", "3", observed=True)
    _update(coordinator, start + timedelta(minutes=10), "999", "2")

    (interval,) = _intervals(coordinator)
    assert interval.energy_kwh == Decimal("0.15")
    assert interval.effective_price == Decimal(1)
    assert interval.covered_duration == timedelta(minutes=10)
