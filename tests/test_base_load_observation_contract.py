"""Characterize live base-load observations before moving their ownership."""

import json
from dataclasses import replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import CONF_POWER_ENTITY, DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator


async def _coordinator(hass):
    """Create a price-independent runtime in the established local timezone."""
    await hass.config.async_set_time_zone("Europe/Stockholm")
    return ElectricityProCoordinator(
        hass,
        MockConfigEntry(
            domain=DOMAIN,
            data={CONF_POWER_ENTITY: "sensor.test_power"},
            entry_id="base-load-observation-contract",
        ),
    )


def _update(coordinator, now, power="600", *, observed=False, bidirectional=False):
    """Supply normalized provider readings to the existing update boundary."""
    inputs = coordinator._provider.read()
    return coordinator._update_base_load_history(
        replace(
            inputs,
            readings=replace(
                inputs.readings,
                current_power=Decimal(power) if power is not None else None,
                current_power_bidirectional=bidirectional,
            ),
        ),
        now,
        power_observed=observed,
    )


def _intervals(coordinator, day=date(2026, 8, 24)):
    return coordinator._base_load_buckets.intervals_for_date(day)


async def test_base_load_observation_weights_previous_power_and_closes_quarter(hass):
    """A fresh power sample closes the preceding sample before replacing it."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, 0, 12, tzinfo=coordinator._local_timezone)

    assert not _update(coordinator, start, "100.1", observed=True)
    assert _update(coordinator, start + timedelta(minutes=4), "200.3", observed=True)
    assert not _update(coordinator, start + timedelta(minutes=8), "999", observed=False)

    intervals = _intervals(coordinator)
    assert [(item.mean_power_w, item.covered_duration) for item in intervals] == [
        (Decimal("100.1"), timedelta(minutes=3)),
        (Decimal("180.26"), timedelta(minutes=5)),
    ]


async def test_base_load_observation_quiet_updates_do_not_renew_expired_power(hass):
    """Only explicit power observations renew the ten-minute hold."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, tzinfo=coordinator._local_timezone)
    flags = [
        _update(coordinator, start, observed=True),
        _update(coordinator, start + timedelta(minutes=5), "900"),
        _update(coordinator, start + timedelta(minutes=20), "900"),
        _update(coordinator, start + timedelta(minutes=25), "300", observed=True),
        _update(coordinator, start + timedelta(minutes=30), "999"),
    ]

    assert flags == [False, False, False, False, True]
    assert [
        (item.mean_power_w, item.covered_duration) for item in _intervals(coordinator)
    ] == [
        (Decimal(600), timedelta(minutes=10)),
        (Decimal(300), timedelta(minutes=5)),
    ]
    assert coordinator._base_load_buckets.longest_uncovered_gap(
        start.date(), day_start=start, day_end=start + timedelta(minutes=30)
    ) == timedelta(minutes=15)


@pytest.mark.parametrize(
    ("elapsed_seconds", "covered_seconds"), [(599, 599), (600, 600), (601, 600)]
)
async def test_base_load_observation_preserves_exact_hold_boundary(
    hass, elapsed_seconds, covered_seconds
):
    """Coverage ends at the same ten-minute limit on either side of expiry."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, 0, 10, tzinfo=coordinator._local_timezone)
    _update(coordinator, start, observed=True)

    assert _update(coordinator, start + timedelta(seconds=elapsed_seconds))

    assert sum(
        (item.covered_duration for item in _intervals(coordinator)), timedelta(0)
    ) == timedelta(seconds=covered_seconds)


@pytest.mark.parametrize("observed", [False, True])
async def test_base_load_observation_missing_power_only_invalidates_on_source_event(
    hass, observed
):
    """An explicit unavailable sample clears the held power after closing it."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, tzinfo=coordinator._local_timezone)
    _update(coordinator, start, observed=True)
    _update(coordinator, start + timedelta(minutes=5), None, observed=observed)
    _update(coordinator, start + timedelta(minutes=10), None)

    intervals = _intervals(coordinator)
    assert len(intervals) == 1
    assert intervals[0].mean_power_w == Decimal(600)
    assert intervals[0].covered_duration == timedelta(minutes=5 if observed else 10)


@pytest.mark.parametrize(
    ("power", "bidirectional", "marked", "closed"),
    [
        ("-100", False, True, True),
        (None, True, True, True),
        ("600", True, True, True),
        ("0", False, False, True),
        (None, False, False, False),
    ],
)
async def test_base_load_observation_preserves_export_zero_and_missing_samples(
    hass, power, bidirectional, marked, closed
):
    """Export marks the day without positive coverage; zero still contributes."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, 0, 14, tzinfo=coordinator._local_timezone)
    _update(coordinator, start, power, observed=True, bidirectional=bidirectional)

    assert _update(coordinator, start + timedelta(minutes=2)) is closed
    assert coordinator._base_load_buckets.bidirectional_observed(start.date()) is marked
    intervals = _intervals(coordinator)
    if power == "0":
        assert sum(
            (item.covered_duration for item in intervals), timedelta(0)
        ) == timedelta(minutes=2)
        assert all(item.mean_power_w == 0 for item in intervals)
    else:
        assert not intervals


@pytest.mark.parametrize("power", ["600", "-100"])
async def test_base_load_observation_splits_local_midnight_without_pruning(hass, power):
    """Both dates retain their coverage or export markers for lifecycle callers."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, 23, 58, tzinfo=coordinator._local_timezone)
    _update(coordinator, start, power, observed=True)

    assert _update(coordinator, start + timedelta(minutes=4))

    for day in (date(2026, 8, 24), date(2026, 8, 25)):
        assert coordinator._base_load_buckets.bidirectional_observed(day) is (
            power == "-100"
        )
        intervals = _intervals(coordinator, day)
        if power == "600":
            assert len(intervals) == 1
            assert intervals[0].covered_duration == timedelta(minutes=2)
            assert intervals[0].mean_power_w == Decimal(600)
        else:
            assert not intervals


async def test_base_load_observation_equal_timestamp_replaces_without_coverage(hass):
    """Repeated timestamps add no duration but the newest observation is retained."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, tzinfo=coordinator._local_timezone)
    _update(coordinator, start, "100", observed=True)
    assert not _update(coordinator, start, "200", observed=True)
    assert not _intervals(coordinator)

    _update(coordinator, start + timedelta(minutes=5))

    assert _intervals(coordinator)[0].mean_power_w == Decimal(200)
    assert _intervals(coordinator)[0].covered_duration == timedelta(minutes=5)


async def test_base_load_observation_restart_restores_buckets_without_replaying_live_sample(
    hass,
):
    """Existing JSON restores history, while the open observation remains transient."""
    original = await _coordinator(hass)
    start = datetime(2026, 8, 24, tzinfo=original._local_timezone)
    _update(original, start, observed=True)
    _update(original, start + timedelta(minutes=5))
    stored = json.loads(json.dumps(original._statistics_data()))
    restored = await _coordinator(hass)
    with patch.object(restored._store, "async_load", AsyncMock(return_value=stored)):
        await restored._async_restore_statistics()

    assert not _update(restored, start + timedelta(minutes=15))
    assert (
        restored._statistics_data()["base_load_buckets"] == stored["base_load_buckets"]
    )
    assert set(restored._statistics_data()) == set(stored)
    _update(restored, start + timedelta(minutes=15), "300", observed=True)
    assert not _update(restored, start + timedelta(minutes=20))
    assert [
        (item.mean_power_w, item.covered_duration) for item in _intervals(restored)
    ] == [
        (Decimal(600), timedelta(minutes=5)),
        (Decimal(300), timedelta(minutes=5)),
    ]
