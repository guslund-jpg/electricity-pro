"""Characterize delivery-date cache and publication boundaries in the coordinator."""

import asyncio
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.forecast import ForecastInterval

_DAY = date(2026, 8, 24)
_RETRIEVE = "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date"


def _series(day, price="-0.1250"):
    """Use a partial but valid delivery series with exact signed Decimal prices."""
    start = datetime.combine(day, time(), tzinfo=UTC)
    return [
        ForecastInterval(
            start=start + timedelta(hours=hour),
            end=start + timedelta(hours=hour + 1),
            market_price=Decimal(price),
            currency="SEK",
            area="SE3",
        )
        for hour in range(2)
    ]


async def _coordinator(hass):
    await hass.config.async_set_time_zone("UTC")
    return ElectricityProCoordinator(
        hass,
        MockConfigEntry(
            domain=DOMAIN,
            data={
                "power_entity": "sensor.power",
                "forecast_nordpool_config_entry": "nordpool-id",
            },
            entry_id="forecast-cache-contract",
        ),
    )


async def _refresh(subject, day, intervals):
    with patch(_RETRIEVE, AsyncMock(return_value=intervals)):
        return await subject._async_refresh_forecast_intervals(day, market_today=day)


async def test_forecast_cache_replaces_only_target_date_and_preserves_raw_intervals(
    hass,
):
    """A sorted/deduplicated publication retains other dates and input identities."""
    subject = await _coordinator(hass)
    tomorrow = _DAY + timedelta(days=1)
    other = _series(tomorrow)
    first = _series(_DAY)
    assert await _refresh(subject, tomorrow, other)
    assert await _refresh(subject, _DAY, first)
    assert subject.forecast_intervals == first + other
    old_publication = subject.forecast_intervals
    replacement = _series(_DAY, "0.234500")
    duplicate = replace(replacement[0])
    incoming = [replacement[1], replacement[0], duplicate]

    assert await _refresh(subject, _DAY, incoming)

    assert subject.forecast_intervals == replacement + other
    assert subject.forecast_intervals is not old_publication
    assert old_publication == first + other
    assert subject.forecast_intervals[0] is replacement[0]
    assert subject.forecast_intervals[-1] is other[-1]
    assert str(subject.forecast_intervals[0].market_price) == "0.234500"
    assert incoming == [replacement[1], replacement[0], duplicate]


@pytest.mark.parametrize(
    "fault", ["conflict", "overlap", "currency", "area", "metadata"]
)
async def test_forecast_cache_invalid_replacement_preserves_every_date_and_publication(
    hass, fault
):
    """A rejected candidate must not corrupt either the published or dated cache."""
    subject = await _coordinator(hass)
    tomorrow = _DAY + timedelta(days=1)
    first, other = _series(_DAY), _series(tomorrow)
    assert await _refresh(subject, _DAY, first)
    assert await _refresh(subject, tomorrow, other)
    published = subject.forecast_intervals
    response = subject.market_price_forecast_response
    if fault == "conflict":
        incoming = [*first, replace(first[0], market_price=Decimal(9))]
    elif fault == "overlap":
        incoming = [
            first[0],
            replace(first[1], start=first[0].start + timedelta(minutes=30)),
        ]
    elif fault == "currency":
        incoming = [replace(i, currency="EUR") for i in first]
    elif fault == "area":
        incoming = [replace(i, area="SE4") for i in first]
    else:
        incoming = [
            replace(
                i, pricing_metadata=replace(i.pricing_metadata, vat_rate=Decimal(25))
            )
            for i in first
        ]

    assert not await _refresh(subject, _DAY, incoming)

    assert subject.forecast_intervals is published
    assert subject.market_price_forecast_response == response
    # Refreshing the other date also checks that rejected data did not enter
    # the dated cache and poison the next aggregate validation.
    assert await _refresh(subject, tomorrow, other)
    assert subject.forecast_intervals == first + other


async def test_forecast_cache_replacement_excludes_previous_target_metadata(hass):
    """Replacing the only date can replace its metadata without mixing old rows."""
    subject = await _coordinator(hass)
    original = _series(_DAY)
    assert await _refresh(subject, _DAY, original)
    replacement = [
        replace(i, currency="EUR", area="SE4") for i in _series(_DAY, "0.75")
    ]

    assert await _refresh(subject, _DAY, replacement)

    assert subject.forecast_intervals == replacement
    assert subject.market_price_forecast_response["currency"] == "EUR"
    assert subject.market_price_forecast_response["area"] == "SE4"


async def test_forecast_cache_pruning_keeps_publication_during_pending_fetch(
    hass, freezer
):
    """Discarding dated entries must not publish before the awaited refresh ends."""
    subject = await _coordinator(hass)
    previous = _series(_DAY)
    assert await _refresh(subject, _DAY, previous)
    published = subject.forecast_intervals
    response = subject.market_price_forecast_response
    tomorrow = _DAY + timedelta(days=1)
    now = datetime.combine(tomorrow, time(8), tzinfo=UTC)
    freezer.move_to(now)
    entered, release = asyncio.Event(), asyncio.Event()

    async def fetch(*args, **kwargs):
        entered.set()
        await release.wait()
        return _series(kwargs["target_date"])

    with patch(_RETRIEVE, AsyncMock(side_effect=fetch)) as retrieve:
        task = asyncio.create_task(subject._async_forecast_tick(now))
        try:
            await asyncio.wait_for(entered.wait(), timeout=5)
            assert subject.forecast_intervals is published
            assert subject.market_price_forecast_response == response
        finally:
            release.set()
            await task
    assert [call.kwargs["target_date"] for call in retrieve.await_args_list] == [
        tomorrow
    ]
    assert subject.forecast_intervals == _series(tomorrow)
    assert subject.forecast_intervals is not published
    assert published == previous


async def test_forecast_cache_rebuild_failure_clears_only_publication_and_can_recover(
    hass, freezer, caplog
):
    """Existing defensive rebuilding clears the series while retaining dated entries."""
    subject = await _coordinator(hass)
    prices = _series(_DAY)
    assert await _refresh(subject, _DAY, prices)
    published = subject.forecast_intervals
    # The original cache retains the retrieved list, while publication has its
    # own list. Preserve that behavior and its defensive rebuild policy.
    prices.append(replace(prices[0], market_price=Decimal(9)))
    subject._rebuild_forecast_intervals()
    assert subject.forecast_intervals == []
    assert published == _series(_DAY)
    assert "Unable to publish market-price forecast series" in caplog.text

    now = datetime.combine(_DAY, time(8), tzinfo=UTC)
    freezer.move_to(now)
    with patch(_RETRIEVE, AsyncMock()) as retrieve:
        await subject._async_forecast_tick(now)
    retrieve.assert_not_awaited()
    assert subject.forecast_intervals == []
    assert await _refresh(subject, _DAY, _series(_DAY))
    assert subject.forecast_intervals == _series(_DAY)
