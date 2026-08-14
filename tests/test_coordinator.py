"""Tests for coordinator forecast runtime behavior."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_FORECAST_CURRENCY,
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FORECAST_PRICE_AREA,
    CONF_POWER_ENTITY,
    DOMAIN,
)
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.forecast import ForecastInterval
from custom_components.electricity_pro.forecast_insights import (
    ForecastDirectionInsight,
    ForecastWindowInsight,
)


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """Create a minimal config entry for coordinator tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_FORECAST_PRICE_AREA: "SE3",
            CONF_FORECAST_CURRENCY: "SEK",
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: "nordpool-entry-id",
        },
        entry_id="test-entry-id",
    )


async def test_async_start_stores_forecast_intervals(
    hass,
    mock_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coordinator startup should retrieve and store today's forecast intervals."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    mock_entry.add_to_hass(hass)

    forecast_intervals = [
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 20, 15, tzinfo=UTC),
            market_price=Decimal("0.59104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 15, tzinfo=UTC),
            end=datetime(2026, 8, 13, 20, 30, tzinfo=UTC),
            market_price=Decimal("0.69104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 30, tzinfo=UTC),
            end=datetime(2026, 8, 13, 20, 45, tzinfo=UTC),
            market_price=Decimal("0.79104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 45, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            market_price=Decimal("0.89104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 15, tzinfo=UTC),
            market_price=Decimal("0.99104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 21, 15, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 30, tzinfo=UTC),
            market_price=Decimal("1.09104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 21, 30, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 45, tzinfo=UTC),
            market_price=Decimal("1.19104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 21, 45, tzinfo=UTC),
            end=datetime(2026, 8, 13, 22, 0, tzinfo=UTC),
            market_price=Decimal("1.29104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 22, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 22, 15, tzinfo=UTC),
            market_price=Decimal("1.39104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 22, 15, tzinfo=UTC),
            end=datetime(2026, 8, 13, 22, 30, tzinfo=UTC),
            market_price=Decimal("1.49104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 22, 30, tzinfo=UTC),
            end=datetime(2026, 8, 13, 22, 45, tzinfo=UTC),
            market_price=Decimal("1.59104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 22, 45, tzinfo=UTC),
            end=datetime(2026, 8, 13, 23, 0, tzinfo=UTC),
            market_price=Decimal("1.69104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 23, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 23, 15, tzinfo=UTC),
            market_price=Decimal("1.79104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 23, 15, tzinfo=UTC),
            end=datetime(2026, 8, 13, 23, 30, tzinfo=UTC),
            market_price=Decimal("1.89104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 23, 30, tzinfo=UTC),
            end=datetime(2026, 8, 13, 23, 45, tzinfo=UTC),
            market_price=Decimal("1.99104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 23, 45, tzinfo=UTC),
            end=datetime(2026, 8, 14, 0, 0, tzinfo=UTC),
            market_price=Decimal("2.09104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
    ]

    async_get = AsyncMock(return_value=forecast_intervals)
    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        async_get,
    )

    coordinator = ElectricityProCoordinator(hass, mock_entry)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 20, 1, tzinfo=UTC),
    ):
        await coordinator.async_start()

    assert coordinator.forecast_intervals == forecast_intervals
    async_get.assert_awaited_once()
    assert async_get.await_args.kwargs["config_entry_id"] == "nordpool-entry-id"
    assert async_get.await_args.kwargs["area"] == "SE3"
    assert async_get.await_args.kwargs["currency"] == "SEK"
    assert isinstance(coordinator.cheapest_1h_window, ForecastWindowInsight)
    assert coordinator.cheapest_1h_window.start == datetime(2026, 8, 13, 20, 15, tzinfo=UTC)
    assert coordinator.cheapest_1h_window.end == datetime(2026, 8, 13, 21, 15, tzinfo=UTC)
    assert isinstance(coordinator.cheapest_2h_window, ForecastWindowInsight)
    assert coordinator.cheapest_2h_window.start == datetime(2026, 8, 13, 20, 15, tzinfo=UTC)
    assert coordinator.cheapest_2h_window.end == datetime(2026, 8, 13, 22, 15, tzinfo=UTC)
    assert isinstance(coordinator.cheapest_3h_window, ForecastWindowInsight)
    assert coordinator.cheapest_3h_window.start == datetime(2026, 8, 13, 20, 15, tzinfo=UTC)
    assert coordinator.cheapest_3h_window.end == datetime(2026, 8, 13, 23, 15, tzinfo=UTC)
    assert isinstance(coordinator.price_direction, ForecastDirectionInsight)
    assert coordinator.price_direction.direction == "rising"


async def test_async_start_keeps_empty_forecast_intervals_on_retrieval_failure(
    hass,
    mock_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coordinator startup should keep an empty forecast state on retrieval failure."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    mock_entry.add_to_hass(hass)

    async_get = AsyncMock(side_effect=ValueError("bad forecast response"))
    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        async_get,
    )

    coordinator = ElectricityProCoordinator(hass, mock_entry)
    await coordinator.async_start()

    assert coordinator.forecast_intervals == []
    assert coordinator.cheapest_1h_window is None
    assert coordinator.cheapest_2h_window is None
    assert coordinator.cheapest_3h_window is None
    assert coordinator.price_direction is None
    async_get.assert_awaited_once()


async def test_async_start_caches_next_inexpensive_1h_window_when_threshold_configured(
    hass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coordinator should cache the next inexpensive 1h window when a good price threshold is set."""
    from custom_components.electricity_pro.forecast_insights import NextInexpensive1hWindowInsight

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_FORECAST_PRICE_AREA: "SE3",
            CONF_FORECAST_CURRENCY: "SEK",
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: "nordpool-entry-id",
            "good_price_threshold": 0.70,
        },
        entry_id="test-entry-id-threshold",
    )
    hass.states.async_set("sensor.test_power", "1000", {"unit_of_measurement": "W"})
    entry.add_to_hass(hass)

    forecast_intervals = [
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            market_price=Decimal("0.90"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 22, 0, tzinfo=UTC),
            market_price=Decimal("0.60"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 22, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 23, 0, tzinfo=UTC),
            market_price=Decimal("0.50"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
    ]

    async_get = AsyncMock(return_value=forecast_intervals)
    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        async_get,
    )

    coordinator = ElectricityProCoordinator(hass, entry)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 20, 1, tzinfo=UTC),
    ):
        await coordinator.async_start()

    assert isinstance(coordinator.next_inexpensive_1h_window, NextInexpensive1hWindowInsight)
    assert coordinator.next_inexpensive_1h_window.start == datetime(2026, 8, 13, 21, 0, tzinfo=UTC)
    assert coordinator.next_inexpensive_1h_window.end == datetime(2026, 8, 13, 22, 0, tzinfo=UTC)
    assert coordinator.next_inexpensive_1h_window.threshold == Decimal("0.70")


async def test_async_start_next_inexpensive_1h_window_none_without_threshold(
    hass,
    mock_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coordinator should leave next_inexpensive_1h_window as None when no threshold is configured."""
    hass.states.async_set("sensor.test_power", "1000", {"unit_of_measurement": "W"})
    mock_entry.add_to_hass(hass)

    forecast_intervals = [
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            market_price=Decimal("0.30"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
    ]

    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        AsyncMock(return_value=forecast_intervals),
    )

    coordinator = ElectricityProCoordinator(hass, mock_entry)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 19, 0, tzinfo=UTC),
    ):
        await coordinator.async_start()

    assert coordinator.next_inexpensive_1h_window is None


async def test_recalculate_forecast_insights_returns_none_when_now_is_past_all_intervals(
    hass,
    mock_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Insights should all be None when 'now' has advanced past every stored interval.

    This is the expected stale-data behavior: as time moves forward the coordinator
    does not have a refresh mechanism that automatically fetches new intervals, so
    if 'now' lands beyond the last stored interval end, every insight returns None
    rather than exposing an expired window.
    """
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    mock_entry.add_to_hass(hass)

    forecast_intervals = [
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            market_price=Decimal("0.30"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 22, 0, tzinfo=UTC),
            market_price=Decimal("0.40"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
    ]

    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        AsyncMock(return_value=forecast_intervals),
    )

    coordinator = ElectricityProCoordinator(hass, mock_entry)

    # Start with 'now' well after the last interval end (22:00 UTC).
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 14, 6, 0, tzinfo=UTC),
    ):
        await coordinator.async_start()

    # Intervals are stored but all are in the past relative to 'now'.
    assert coordinator.forecast_intervals == forecast_intervals
    assert coordinator.cheapest_1h_window is None
    assert coordinator.cheapest_2h_window is None
    assert coordinator.cheapest_3h_window is None
    assert coordinator.next_inexpensive_1h_window is None
    assert coordinator.price_direction is None
