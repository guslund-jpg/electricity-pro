"""Tests for coordinator forecast runtime behavior."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import CONF_POWER_ENTITY, DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.forecast import ForecastInterval


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """Create a minimal config entry for coordinator tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={CONF_POWER_ENTITY: "sensor.test_power"},
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
            start=datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 10, 15, tzinfo=UTC),
            market_price=Decimal("0.59104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        )
    ]

    async_get = AsyncMock(return_value=forecast_intervals)
    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        async_get,
    )

    coordinator = ElectricityProCoordinator(hass, mock_entry)
    await coordinator.async_start()

    assert coordinator.forecast_intervals == forecast_intervals
    async_get.assert_awaited_once()


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
    async_get.assert_awaited_once()
