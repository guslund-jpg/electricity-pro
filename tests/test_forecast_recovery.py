"""Recover forecast entities through HA's normal setup and timer lifecycle."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState, ConfigFlow
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_set_domains_to_be_loaded, async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    async_fire_time_changed,
    mock_config_flow,
    mock_integration,
    mock_platform,
)

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.forecast import ForecastInterval
from custom_components.electricity_pro.pricing import (
    PriceComponent,
    PriceComponentScope,
    PriceCompleteness,
    PricingMetadata,
    PricingStrategy,
    VatTreatment,
)

START = datetime(2026, 11, 20, 10, tzinfo=UTC)
WINDOW = START + timedelta(hours=1)
ENTITY = "sensor.electricity_pro_next_inexpensive_1h_window_start"
FETCH = "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date"


@pytest.fixture
def forecast_entry(hass, freezer):
    """A complete live price and comparable forecast with a fixed threshold."""
    freezer.move_to(START)
    hass.states.async_set("sensor.power", "1000", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.price", "0.80", {"unit_of_measurement": "SEK/kWh"})
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "power_entity": "sensor.power",
            "price_entity": "sensor.price",
            "pricing_strategy": "external_complete_price",
            "price_included_components": [
                component.value for component in PriceComponent
            ],
            "price_vat_treatment": "included",
            "price_completeness": "complete",
            "good_price_threshold": 0.65,
            "forecast_nordpool_config_entry": "nordpool-entry-id",
            "forecast_price_area": "SE3",
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def intervals():
    """A future one-hour window that qualifies under the configured threshold."""
    return [
        ForecastInterval(
            start=WINDOW,
            end=WINDOW + timedelta(hours=1),
            market_price=Decimal("0.60"),
            currency="SEK",
            area="SE3",
            pricing_metadata=PricingMetadata(
                strategy=PricingStrategy.EXTERNAL_COMPLETE_PRICE,
                scope=PriceComponentScope(
                    frozenset(PriceComponent), vat=VatTreatment.INCLUDED
                ),
                completeness=PriceCompleteness.COMPLETE,
            ),
        )
    ]


@pytest.mark.parametrize("configured", [True, False])
async def test_startup_orders_optional_nordpool_before_first_forecast(
    hass, forecast_entry, intervals, configured
):
    """Wait for a configured native entry without loading an unused dependency."""
    native_setup = AsyncMock(return_value=True)
    mock_integration(
        hass,
        MockModule("nordpool", async_setup_entry=native_setup),
        top_level_files=set(),
    )
    mock_platform(hass, "nordpool.config_flow")
    native = None
    domains = {DOMAIN}
    if configured:
        native = MockConfigEntry(domain="nordpool", data={})
        native.add_to_hass(hass)
        domains.add("nordpool")
        hass.config_entries.async_update_entry(
            forecast_entry,
            data={
                **forecast_entry.data,
                "forecast_nordpool_config_entry": native.entry_id,
            },
        )
    async_set_domains_to_be_loaded(hass, domains)

    async def fetch_when_ready(*args, **kwargs):
        if native is not None:
            assert native.state is ConfigEntryState.LOADED
        else:
            native_setup.assert_not_awaited()
            assert "nordpool" not in hass.config.components
        return intervals

    with (
        mock_config_flow("nordpool", ConfigFlow),
        patch(FETCH, AsyncMock(side_effect=fetch_when_ready)),
    ):
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
    assert forecast_entry.state is ConfigEntryState.LOADED
    assert hass.states.get(ENTITY).state == WINDOW.isoformat()


@pytest.mark.parametrize(
    "previous", ["new", "enabled", "integration_disabled", "user_disabled"]
)
@pytest.mark.parametrize("initial_result", ["error", "empty"])
async def test_first_forecast_retry_recovers_entity_without_manual_reload(
    hass, freezer, forecast_entry, intervals, previous, initial_result
):
    """A failed initial fetch must not require a reload or replace existing IDs."""
    entry = forecast_entry
    registry = er.async_get(hass)
    unique_id = f"{entry.entry_id}_next_inexpensive_1h_window_start"
    entity_id = ENTITY
    original = None
    if previous != "new":
        original = registry.async_get_or_create(
            "sensor",
            DOMAIN,
            unique_id,
            config_entry=entry,
            suggested_object_id="my_next_cheap_hour",
            disabled_by={
                "integration_disabled": er.RegistryEntryDisabler.INTEGRATION,
                "user_disabled": er.RegistryEntryDisabler.USER,
            }.get(previous),
        )
        entity_id = original.entity_id
    first = (
        HomeAssistantError("Nord Pool is not ready")
        if initial_result == "error"
        else []
    )
    fetch = AsyncMock(side_effect=[first, intervals])
    with patch(FETCH, fetch):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        if previous == "enabled":
            assert registry.async_get(entity_id).disabled_by is None

        freezer.move_to(START + timedelta(minutes=15))
        async_fire_time_changed(hass, START + timedelta(minutes=15))
        # HA interval callbacks are background jobs. Finish the retry before
        # removing the mocked native action, regardless of event-loop timing.
        await hass.async_block_till_done(wait_background_tasks=True)

    assert fetch.await_count == 2
    registered = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert registered == entity_id
    current = registry.async_get(entity_id)
    if original is not None:
        assert current.id == original.id
        assert current.unique_id == original.unique_id
    if previous == "user_disabled":
        assert current.disabled_by is er.RegistryEntryDisabler.USER
        assert hass.states.get(entity_id) is None
        return
    assert current.disabled_by is None
    assert hass.states.get(entity_id).state == WINDOW.isoformat()
    identity = (current.id, current.unique_id, current.device_id)

    # Repeated source/coordinator updates must not add another copy.
    for _ in range(2):
        entry.runtime_data.async_set_updated_data(entry.runtime_data.data)
        await hass.async_block_till_done()
    assert sum(row.unique_id == unique_id for row in registry.entities.values()) == 1

    with patch(FETCH, AsyncMock(return_value=intervals)):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    current = registry.async_get(entity_id)
    assert (current.id, current.unique_id, current.device_id) == identity
    assert hass.states.get(entity_id).state == WINDOW.isoformat()


async def test_expired_forecast_recovers_without_disabling_existing_entity(
    hass, freezer, forecast_entry, intervals
):
    """A later missing delivery day withholds advice but keeps the entity."""
    with patch(FETCH, AsyncMock(return_value=intervals)):
        assert await hass.config_entries.async_setup(forecast_entry.entry_id)
        await hass.async_block_till_done()
    registry = er.async_get(hass)
    original = registry.async_get(ENTITY)
    assert hass.states.get(ENTITY).state == WINDOW.isoformat()

    next_day = START + timedelta(days=1)
    freezer.move_to(next_day)
    with patch(
        FETCH, AsyncMock(side_effect=HomeAssistantError("Nord Pool is offline"))
    ):
        async_fire_time_changed(hass, next_day)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(ENTITY).state == "unavailable"
    assert registry.async_get(ENTITY).disabled_by is None

    recovered = [
        replace(
            row, start=row.start + timedelta(days=1), end=row.end + timedelta(days=1)
        )
        for row in intervals
    ]
    retry_at = next_day + timedelta(minutes=15)
    freezer.move_to(retry_at)
    with patch(FETCH, AsyncMock(return_value=recovered)):
        async_fire_time_changed(hass, retry_at)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(ENTITY).state == (WINDOW + timedelta(days=1)).isoformat()
    assert registry.async_get(ENTITY).id == original.id


async def test_unloaded_entry_cannot_add_entity_on_late_forecast(
    hass, forecast_entry, intervals
):
    """Unloading while waiting removes the late-registration listener."""
    with patch(
        FETCH, AsyncMock(side_effect=HomeAssistantError("Nord Pool is not ready"))
    ):
        assert await hass.config_entries.async_setup(forecast_entry.entry_id)
        await hass.async_block_till_done()
    coordinator = forecast_entry.runtime_data
    assert await hass.config_entries.async_unload(forecast_entry.entry_id)
    await hass.async_block_till_done()
    with patch(FETCH, AsyncMock(return_value=intervals)):
        await coordinator._async_forecast_tick(START)  # noqa: SLF001
        await hass.async_block_till_done()
    assert hass.states.get(ENTITY) is None
    assert (
        er.async_get(hass).async_get_entity_id(
            "sensor",
            DOMAIN,
            f"{forecast_entry.entry_id}_next_inexpensive_1h_window_start",
        )
        is None
    )
