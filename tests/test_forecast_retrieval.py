"""Market-clock scheduling, publication retries and non-destructive caching."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
import logging
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.forecast import ForecastInterval
from custom_components.electricity_pro.nordpool import NORDPOOL_TIME_ZONE, forecast_delivery_dates

MARKET = ZoneInfo(NORDPOOL_TIME_ZONE)
RETRIEVE = "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date"
LOGGER = "custom_components.electricity_pro.coordinator"


def market_day(day):
    """Real UTC boundaries for a 23-, 24- or 25-hour market delivery day."""
    start = datetime.combine(day, time(), MARKET).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time(), MARKET).astimezone(UTC)
    return [ForecastInterval(
        start=start + timedelta(hours=offset), end=start + timedelta(hours=offset + 1),
        market_price=Decimal("0.5"), currency="SEK", area="SE3",
    ) for offset in range(int((end - start).total_seconds() // 3600))]


def coordinator(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={
        "power_entity": "sensor.power", "forecast_nordpool_config_entry": "nordpool-id",
    })
    entry.add_to_hass(hass)
    return ElectricityProCoordinator(hass, entry)


@pytest.mark.parametrize("zone", ["UTC", "Europe/Stockholm", "Europe/Helsinki"])
@pytest.mark.parametrize("day", [date(2026, 1, 15), date(2026, 7, 15),
                                 date(2026, 3, 29), date(2026, 10, 25)])
async def test_startup_and_tick_share_market_gate(hass, freezer, zone, day):
    await hass.config.async_set_time_zone(zone)
    before = datetime.combine(day, time(12, 59), MARKET)
    freezer.move_to(before)
    fetch = AsyncMock(side_effect=lambda *args, **kw: market_day(kw["target_date"]))
    expected = ([day - timedelta(days=1)] if zone == "Europe/Helsinki" else []) + [day]
    with patch(RETRIEVE, fetch):
        first = coordinator(hass)
        await first.async_start()
        assert [call.kwargs["target_date"] for call in fetch.await_args_list] == expected
        fetch.reset_mock()
        at_gate = datetime.combine(day, time(13), MARKET)
        freezer.move_to(at_gate)
        await first._async_forecast_tick(at_gate.astimezone(UTC))
        assert [call.kwargs["target_date"] for call in fetch.await_args_list] == [day + timedelta(days=1)]
        fetch.reset_mock()
        restarted = coordinator(hass)
        await restarted.async_start()
        assert [call.kwargs["target_date"] for call in fetch.await_args_list] == expected + [day + timedelta(days=1)]
        assert first.forecast_intervals == restarted.forecast_intervals


@pytest.mark.parametrize(("zone", "stamp", "expected"), [
    ("UTC", "2026-07-14T22:15:00+00:00", [date(2026, 7, 14), date(2026, 7, 15)]),
    ("Europe/Helsinki", "2026-07-14T21:15:00+00:00", [date(2026, 7, 14), date(2026, 7, 15)]),
    ("Europe/Stockholm", "2026-07-14T22:15:00+00:00", [date(2026, 7, 15)]),
])
def test_delivery_date_is_not_the_installation_date(zone, stamp, expected):
    assert list(forecast_delivery_dates(
        datetime.fromisoformat(stamp), local_timezone=ZoneInfo(zone), market_timezone=MARKET
    )) == expected


@pytest.mark.parametrize(("day", "hours"), [(date(2026, 3, 29), 23), (date(2026, 10, 25), 25)])
async def test_dst_delivery_days_retain_actual_utc_intervals(hass, freezer, day, hours):
    await hass.config.async_set_time_zone("Europe/Stockholm")
    freezer.move_to(datetime.combine(day, time(8), MARKET))
    prices = market_day(day)
    assert len(prices) == hours
    with patch(RETRIEVE, AsyncMock(return_value=prices)):
        subject = coordinator(hass)
        await subject.async_start()
    assert subject.forecast_intervals == prices


async def test_late_publication_retries_quietly_then_stops_on_success(hass, freezer, caplog):
    await hass.config.async_set_time_zone("UTC")
    caplog.set_level(logging.DEBUG, logger=LOGGER)
    day = date(2026, 7, 15)
    tomorrow = day + timedelta(days=1)
    fetch = AsyncMock(side_effect=lambda *args, **kw: market_day(day) if kw["target_date"] == day else [])
    freezer.move_to("2026-07-15T11:00:00+00:00")
    with patch(RETRIEVE, fetch):
        subject = coordinator(hass)
        await subject.async_start()
        for stamp in ("2026-07-15T11:15:00+00:00", "2026-07-15T18:00:00+00:00"):
            freezer.move_to(stamp)
            await subject._async_forecast_tick(datetime.fromisoformat(stamp))
        assert [call.kwargs["target_date"] for call in fetch.await_args_list] == [day, tomorrow, tomorrow, tomorrow]
        assert tomorrow not in subject._forecast_intervals_by_date
        assert not [r for r in caplog.records if r.name == LOGGER and r.levelno >= logging.WARNING]
        assert "future delivery date" in caplog.text
        fetch.side_effect = None
        fetch.return_value = market_day(tomorrow)
        freezer.move_to("2026-07-15T18:15:00+00:00")
        await subject._async_forecast_tick(datetime(2026, 7, 15, 18, 15, tzinfo=UTC))
        fetch.reset_mock()
        await subject._async_forecast_tick(datetime(2026, 7, 15, 18, 30, tzinfo=UTC))
        fetch.assert_not_awaited()
        # Market midnight in UTC still needs the previous date for the local day.
        await subject._async_forecast_tick(datetime(2026, 7, 15, 22, 15, tzinfo=UTC))
        assert day in subject._forecast_intervals_by_date
        await subject._async_forecast_tick(datetime(2026, 7, 16, 0, 15, tzinfo=UTC))
        assert day not in subject._forecast_intervals_by_date
        assert subject.forecast_intervals == market_day(tomorrow)


async def test_empty_date_becomes_warning_when_delivery_day_arrives(hass, freezer, caplog):
    await hass.config.async_set_time_zone("Europe/Stockholm")
    freezer.move_to("2026-07-15T21:45:00+00:00")
    with patch(RETRIEVE, AsyncMock(return_value=[])):
        subject = coordinator(hass)
        await subject._async_forecast_tick(datetime(2026, 7, 15, 21, 45, tzinfo=UTC))
        caplog.clear()
        await subject._async_forecast_tick(datetime(2026, 7, 15, 22, 0, tzinfo=UTC))
        await subject._async_forecast_tick(datetime(2026, 7, 15, 22, 15, tzinfo=UTC))
    warnings = [r for r in caplog.records if r.name == LOGGER and r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "2026-07-16" in warnings[0].message
    assert "no forecast intervals" in warnings[0].message


@pytest.mark.parametrize("error", [
    HomeAssistantError("action unavailable"), TimeoutError("network timeout"),
    ValueError("malformed intervals"),
    ServiceValidationError(translation_domain="nordpool", translation_key="authentication_error"),
    ServiceValidationError(translation_domain="nordpool", translation_key="connection_error"),
])
async def test_real_failures_warn_without_erasing_valid_cache(hass, caplog, error):
    subject = coordinator(hass)
    day = date(2026, 7, 15)
    tomorrow = day + timedelta(days=1)
    prices = market_day(tomorrow)
    with patch(RETRIEVE, AsyncMock(return_value=prices)):
        assert await subject._async_refresh_forecast_intervals(tomorrow, market_today=day)
    caplog.clear()
    with patch(RETRIEVE, AsyncMock(side_effect=error)):
        for _ in range(2):
            assert not await subject._async_refresh_forecast_intervals(tomorrow, market_today=day)
    warnings = [r for r in caplog.records if r.name == LOGGER and r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "Unable to refresh" in warnings[0].message
    assert subject.forecast_intervals == prices
    assert subject._forecast_intervals_by_date[tomorrow] == prices
    with patch(RETRIEVE, AsyncMock(return_value=prices)):
        assert await subject._async_refresh_forecast_intervals(tomorrow, market_today=day)
    assert tomorrow not in subject._forecast_failures


async def test_empty_and_conflicting_refreshes_preserve_cached_series(hass):
    subject = coordinator(hass)
    day = date(2026, 7, 15)
    prices = market_day(day)
    with patch(RETRIEVE, AsyncMock(return_value=prices)):
        await subject._async_refresh_forecast_intervals(day, market_today=day)
    conflict = ForecastInterval(start=prices[0].start, end=prices[0].end,
                                market_price=Decimal(9), currency="SEK", area="SE3")
    for response in ([], [*prices, conflict]):
        with patch(RETRIEVE, AsyncMock(return_value=response)):
            assert not await subject._async_refresh_forecast_intervals(day, market_today=day)
        assert subject.forecast_intervals == prices
    with patch(RETRIEVE, AsyncMock(return_value=[])):
        assert not await subject._async_refresh_forecast_intervals(day, market_today=day - timedelta(days=1))
    assert subject.forecast_intervals == prices
