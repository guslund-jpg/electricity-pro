"""Characterize the completed timing result at the coordinator boundary."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import CONF_POWER_ENTITY, DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.timing_score import TimingScoreUnavailableReason

_RESULT_KEY = "consumption_timing_score_yesterday"
_WARNING = "Ignoring invalid persisted timing score result"
_DAY = date(2026, 8, 24)
_LEGACY_RESULT = {
    "period_start": "2026-08-24",
    "result": {
        "score": "88",
        "unavailable_reason": None,
        "coverage_percent": "98.50",
        "energy_kwh": "12.300",
        "consumption_weighted_price": "-0.750",
        "time_weighted_price": "1.250",
        "price_variation_percent": "40.00",
        "rating": "well_timed",
    },
}


async def _coordinator(hass):
    """Create an independent runtime in the established local timezone."""
    await hass.config.async_set_time_zone("Europe/Stockholm")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_POWER_ENTITY: "sensor.test_power"},
        entry_id="completed-timing-contract",
    )
    return ElectricityProCoordinator(hass, entry)


async def _restore(coordinator, stored):
    """Read the legacy JSON through the actual statistics restoration path."""
    with patch.object(coordinator._store, "async_load", AsyncMock(return_value=stored)):
        await coordinator._async_restore_statistics()


def _fill_day(coordinator, day):
    """Consume only in the cheapest quarter of a real local day."""
    timezone = coordinator._local_timezone
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone).astimezone(UTC)
    end = datetime.combine(
        day + timedelta(days=1), datetime.min.time(), tzinfo=timezone
    ).astimezone(UTC)
    quarter = (end - start) / 4
    for index in range(4):
        coordinator._timing_buckets.add_segment(
            start=start + index * quarter,
            end=start + (index + 1) * quarter,
            power_w=Decimal(4000) if index == 0 else Decimal(0),
            effective_price=Decimal(index + 1),
        )
    return start, end


@pytest.mark.parametrize(
    ("day", "hours"),
    [(date(2026, 3, 29), 23), (_DAY, 24), (date(2026, 10, 25), 25)],
)
async def test_completed_timing_uses_real_local_day_duration(hass, day, hours):
    """DST must preserve full coverage, real energy and the agreed score."""
    coordinator = await _coordinator(hass)
    _fill_day(coordinator, day)

    coordinator._finalize_timing_day(day)

    result_day, result = coordinator.timing_score_yesterday
    assert result_day == day
    assert result.score == Decimal(88)
    assert result.coverage_percent == Decimal(100)
    assert result.energy_kwh == Decimal(hours)
    assert result.consumption_weighted_price == Decimal(1)
    assert result.time_weighted_price == Decimal("2.5")
    assert result.price_variation_percent == Decimal(120)
    payload = coordinator._statistics_data()[_RESULT_KEY]
    assert set(payload) == {"period_start", "result"}
    assert payload["period_start"] == day.isoformat()
    assert payload["result"] == result.as_dict()


@pytest.mark.parametrize(
    ("gap", "reason"),
    [
        (timedelta(hours=23), TimingScoreUnavailableReason.INSUFFICIENT_COVERAGE),
        (timedelta(minutes=90), TimingScoreUnavailableReason.LONG_DATA_GAP),
    ],
)
async def test_completed_timing_preserves_partial_day_reasons(hass, gap, reason):
    """Coverage and longest-gap guards must retain their distinct reasons."""
    coordinator = await _coordinator(hass)
    start = datetime(2026, 8, 24, tzinfo=coordinator._local_timezone)
    coordinator._timing_buckets.add_segment(
        start=start,
        end=start + timedelta(days=1) - gap,
        power_w=Decimal(1000),
        effective_price=Decimal(1),
    )

    coordinator._finalize_timing_day(_DAY)

    assert coordinator.timing_score_yesterday[1].score is None
    assert coordinator.timing_score_yesterday[1].unavailable_reason is reason
    assert (
        coordinator._statistics_data()[_RESULT_KEY]["result"]["unavailable_reason"]
        == reason
    )


@pytest.mark.parametrize("available", [True, False])
async def test_completed_timing_restores_legacy_json_exactly(hass, available):
    """Old Decimal strings, negative prices and unavailable results round-trip."""
    coordinator = await _coordinator(hass)
    payload = json.loads(json.dumps(_LEGACY_RESULT))
    if not available:
        payload["result"].update(
            score=None,
            unavailable_reason="insufficient_coverage",
            consumption_weighted_price=None,
            time_weighted_price=None,
            price_variation_percent=None,
            rating=None,
        )
    assert coordinator.timing_score_yesterday is None
    assert _RESULT_KEY not in coordinator._statistics_data()

    await _restore(coordinator, {_RESULT_KEY: payload})

    assert coordinator.timing_score_yesterday[0] == _DAY
    assert coordinator._statistics_data()[_RESULT_KEY] == payload
    if available:
        assert coordinator.timing_score_yesterday[
            1
        ].consumption_weighted_price == Decimal("-0.750")


@pytest.mark.parametrize(
    "stored", [{}, {_RESULT_KEY: None}, {_RESULT_KEY: []}, {_RESULT_KEY: "bad"}]
)
async def test_completed_timing_ignores_absent_or_non_record_state(
    hass, caplog, stored
):
    """These outer shapes do not clear an existing result or emit its warning."""
    coordinator = await _coordinator(hass)
    await _restore(coordinator, {_RESULT_KEY: _LEGACY_RESULT})

    await _restore(coordinator, stored)

    assert coordinator._statistics_data()[_RESULT_KEY] == _LEGACY_RESULT
    assert _WARNING not in caplog.text


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"period_start": "2026-08-24"},
        {"period_start": "bad", "result": _LEGACY_RESULT["result"]},
        {"period_start": 20260824, "result": _LEGACY_RESULT["result"]},
        {"period_start": "2026-08-24", "result": {}},
        {
            "period_start": "2026-08-24",
            "result": {**_LEGACY_RESULT["result"], "score": "NaN"},
        },
    ],
)
async def test_completed_timing_invalid_record_clears_result_and_warns(
    hass, caplog, payload
):
    """Existing caught parse failures discard both date and result."""
    coordinator = await _coordinator(hass)
    await _restore(coordinator, {_RESULT_KEY: _LEGACY_RESULT})

    await _restore(coordinator, {_RESULT_KEY: payload})

    assert coordinator.timing_score_yesterday is None
    assert _RESULT_KEY not in coordinator._statistics_data()
    assert caplog.text.count(_WARNING) == 1


@pytest.mark.parametrize("path", ["midnight", "restart"])
async def test_completed_timing_keeps_existing_no_observation_policy(hass, path):
    """Rollover records an empty day; restart without yesterday's buckets does not."""
    coordinator = await _coordinator(hass)
    await _restore(coordinator, {_RESULT_KEY: _LEGACY_RESULT})
    today = _DAY + timedelta(days=2)
    if path == "restart":
        coordinator._finalize_restored_timing_days(today)
        assert coordinator._statistics_data()[_RESULT_KEY] == _LEGACY_RESULT
    else:
        midnight = datetime.combine(
            today, datetime.min.time(), tzinfo=coordinator._local_timezone
        )
        with patch.object(coordinator, "_schedule_statistics_save"):
            coordinator._async_daily_rollover(midnight)
        day, result = coordinator.timing_score_yesterday
        assert day == today - timedelta(days=1)
        assert result.coverage_percent == Decimal(0)
        assert (
            result.unavailable_reason
            is TimingScoreUnavailableReason.INSUFFICIENT_COVERAGE
        )


@pytest.mark.parametrize("path", ["midnight", "restart"])
async def test_completed_timing_finalizes_before_discarding_export_marker(hass, path):
    """Both lifecycle paths must use yesterday's marker before retaining today."""
    coordinator = await _coordinator(hass)
    start, end = _fill_day(coordinator, _DAY)
    coordinator._base_load_buckets.add_segment(
        start=start, end=start + timedelta(minutes=5), power_w=Decimal(-100)
    )
    coordinator._timing_buckets.add_segment(
        start=end,
        end=end + timedelta(minutes=15),
        power_w=Decimal(1000),
        effective_price=Decimal(1),
    )
    if path == "restart":
        stored = json.loads(json.dumps(coordinator._statistics_data()))
        coordinator = await _coordinator(hass)
        await _restore(coordinator, stored)
        coordinator._finalize_restored_timing_days(_DAY + timedelta(days=1))
        coordinator._finalize_restored_base_load_days(_DAY + timedelta(days=1))
    else:
        with patch.object(coordinator, "_schedule_statistics_save") as save:
            coordinator._async_daily_rollover(end)
        save.assert_called_once_with(immediate=True)

    day, result = coordinator.timing_score_yesterday
    assert day == _DAY
    assert result.coverage_percent == Decimal(100)
    assert (
        result.unavailable_reason
        is TimingScoreUnavailableReason.UNSUPPORTED_BIDIRECTIONAL_POWER
    )
    assert not coordinator._timing_buckets.intervals_for_date(_DAY)
    assert not coordinator._base_load_buckets.bidirectional_observed(_DAY)
    assert coordinator._timing_buckets.intervals_for_date(_DAY + timedelta(days=1))
