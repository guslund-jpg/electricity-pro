"""Execute the shipped one-shot example through real Home Assistant scripts."""

import asyncio
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from homeassistant.setup import async_setup_component
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.electricity_pro.pricing import (
    PriceComponent, PriceComponentScope, PriceCompleteness,
    PricingMetadata, PricingStrategy, VatTreatment,
)

PACKAGE = Path(__file__).parents[1] / "examples/automations/one_shot_window.yaml"
SOURCE = "sensor.electricity_pro_cheapest_2h_window_start"
REQUEST = "script.ep_window_request"


async def settle(hass):
    """Drain ready callbacks without awaiting a deliberately long-running script."""
    for _ in range(30):
        await asyncio.sleep(0)


@pytest.fixture
async def example(hass, freezer):
    freezer.move_to("2026-10-31T10:00:00+00:00")
    package = yaml.safe_load(PACKAGE.read_text())
    notifications = async_mock_service(hass, "persistent_notification", "create")
    assert await async_setup_component(hass, "script", {"script": package["script"]})
    assert await async_setup_component(hass, "automation", {"automation": package["automation"]})
    await hass.async_start()
    await settle(hass)
    return package, notifications


def publish(hass, *, hours=2, start=None, price="1.50", **attributes):
    start = start or dt_util.utcnow() + timedelta(minutes=15)
    attrs = {
        "device_class": "timestamp",
        "window_end": (start + timedelta(hours=hours)).isoformat(),
        "window_duration_minutes": hours * 60,
        "average_scheduling_price": price,
        "currency": "SEK",
        "price_area": "SE3",
        "price_components": ["market_energy", "supplier_markup", "grid_fee", "energy_tax"],
        "vat_treatment": "included",
        "price_completeness": "partial",
        # This is optional in real insight attributes; do not invent freshness.
        "published_at": None,
        **attributes,
    }
    hass.states.async_set(SOURCE, start.isoformat(), attrs)
    return start


async def request(hass, **overrides):
    await hass.services.async_call("script", "turn_on", {
        "entity_id": REQUEST,
        "variables": {
            "window_entity": SOURCE,
            "expected_currency": "SEK",
            "price_limit": 2,
            **overrides,
        },
    }, blocking=False)
    await settle(hass)


async def advance(hass, freezer, instant):
    freezer.move_to(instant)
    async_fire_time_changed(hass, dt_util.utcnow())
    await settle(hass)


def dispatched(notifications):
    return [c for c in notifications if c.data["title"] in (
        "Electricity Pro — your selected window starts now",
        "Electricity Pro — appliance DRY RUN",
    )]


@pytest.mark.parametrize("hours", [1, 2, 3])
@pytest.mark.parametrize("appliance", [False, True])
async def test_one_shot_and_natural_window_rollover(hass, freezer, example, hours, appliance):
    _, notifications = example
    start = publish(hass, hours=hours)
    await request(hass, appliance_start=appliance)
    assert hass.states.get(REQUEST).state == "on"
    # Same request again while waiting is ignored, not queued.
    await request(hass, appliance_start=appliance)
    assert len(notifications) == 1
    # At the boundary the insight legitimately moves to a later window.
    freezer.move_to(start)
    publish(hass, hours=hours, start=start + timedelta(hours=4), price="1.90")
    await advance(hass, freezer, start)
    assert hass.states.get(REQUEST).state == "off"
    assert len(dispatched(notifications)) == 1
    result = dispatched(notifications)[0].data
    assert ("DRY RUN" in result["title"]) == appliance
    assert "1.50" in result["message"] or "1.5" in result["message"]
    assert not hass.services.has_service("switch", "turn_on")
    await advance(hass, freezer, start + timedelta(minutes=5))
    assert len(dispatched(notifications)) == 1


@pytest.mark.parametrize("mutation", [
    {"price": "2.1"}, {"price": "1.4"}, {"currency": "EUR"}, {"price_area": "SE4"},
    {"window_duration_minutes": 60}, {"window_end": "2026-10-31T14:15:00+00:00"},
    {"price_components": ["market_energy"]}, {"vat_treatment": "excluded"},
    {"price_completeness": "complete"}, {"price": "nan"},
])
async def test_revisions_cancel_not_reschedule(hass, example, mutation):
    _, notifications = example
    start = publish(hass)
    await request(hass)
    publish(hass, start=start, **mutation)
    await settle(hass)
    assert hass.states.get(REQUEST).state == "off"
    assert notifications[-1].data["title"].endswith("window cancelled")
    assert not dispatched(notifications)


@pytest.mark.parametrize("state", ["unavailable", "unknown", "invalid", "rescheduled"])
async def test_source_loss_or_new_start_cancels(hass, example, state):
    _, notifications = example
    start = publish(hass)
    await request(hass)
    if state == "rescheduled":
        publish(hass, start=start + timedelta(minutes=15))
    else:
        hass.states.async_set(SOURCE, state)
    await settle(hass)
    assert hass.states.get(REQUEST).state == "off"
    assert not dispatched(notifications)


@pytest.mark.parametrize("overrides", [
    {"expected_currency": "EUR"}, {"price_limit": 1}, {"price_limit": "nan"},
    {"price_limit": "inf"}, {"window_entity": "sensor.missing"},
])
async def test_invalid_request_is_refused(hass, example, overrides):
    _, notifications = example
    publish(hass)
    await request(hass, **overrides)
    assert hass.states.get(REQUEST).state == "off"
    assert notifications[-1].data["title"].endswith("request refused")


@pytest.mark.parametrize("seconds", [-60, 0, 59, 86401])
async def test_expired_or_distant_requests_refused(hass, example, seconds):
    _, notifications = example
    publish(hass, start=dt_util.utcnow() + timedelta(seconds=seconds))
    await request(hass)
    assert hass.states.get(REQUEST).state == "off"
    assert not dispatched(notifications)


async def test_negative_prices_and_offset_timestamps(hass, freezer, example):
    _, notifications = example
    # Both duplicated local hours on DST fall-back have distinct instants.
    freezer.move_to("2026-10-25T00:00:00Z")
    start = dt_util.parse_datetime("2026-10-25T02:15:00+02:00")
    publish(hass, start=start, price="-0.5")
    await request(hass, price_limit=-0.1)
    freezer.move_to(start)
    publish(hass, start=start, price="-0.5")
    await advance(hass, freezer, start)
    assert len(dispatched(notifications)) == 1


async def test_stale_source_refused_at_arm_and_cancels_wait(hass, freezer, example):
    _, notifications = example
    start = publish(hass)
    await advance(hass, freezer, dt_util.utcnow() + timedelta(minutes=6))
    await request(hass)
    assert hass.states.get(REQUEST).state == "off"
    publish(hass, start=start)
    await request(hass)
    assert hass.states.get(REQUEST).state == "on"
    await advance(hass, freezer, dt_util.utcnow() + timedelta(minutes=6))
    assert hass.states.get(REQUEST).state == "off"
    assert not dispatched(notifications)


async def test_explicit_cancel_and_rearm(hass, freezer, example):
    _, notifications = example
    start = publish(hass)
    await request(hass)
    await hass.services.async_call("script", "ep_window_cancel", blocking=True)
    assert hass.states.get(REQUEST).state == "off"
    await request(hass)
    assert hass.states.get(REQUEST).state == "on"
    freezer.move_to(start)
    publish(hass, start=start)
    await advance(hass, freezer, start)
    assert len(dispatched(notifications)) == 1
    # Once consumed, that same past/current window cannot be armed again.
    await request(hass)
    assert len(dispatched(notifications)) == 1


async def test_missed_start_has_no_catch_up(hass, freezer, example):
    _, notifications = example
    start = publish(hass)
    await request(hass)
    freezer.move_to(start + timedelta(seconds=31))
    publish(hass, start=start)
    await advance(hass, freezer, dt_util.utcnow())
    assert hass.states.get(REQUEST).state == "off"
    assert not dispatched(notifications)


async def test_reload_cancels_pending_script_and_never_replays(hass, freezer, example):
    package, notifications = example
    start = publish(hass)
    await request(hass)
    with patch("homeassistant.config.async_hass_config_yaml",
               new=AsyncMock(return_value={"script": package["script"]})):
        await hass.services.async_call("script", "reload", blocking=True)
    await settle(hass)
    assert hass.states.get(REQUEST).state == "off"
    freezer.move_to(start)
    publish(hass, start=start)
    await advance(hass, freezer, start)
    assert not dispatched(notifications)


async def test_shutdown_aborts_pending_request(hass, example):
    _, notifications = example
    publish(hass)
    await request(hass)
    await hass.async_stop()
    assert not dispatched(notifications)


async def test_fresh_install_does_not_schedule_anything(hass, example):
    _, notifications = example
    publish(hass)
    await settle(hass)
    assert hass.states.get(REQUEST).state == "off"
    assert not notifications


async def test_accepts_actual_electricity_pro_sensor_contract(hass, example, setup_electricity_pro):
    _, notifications = example
    start = dt_util.utcnow() + timedelta(minutes=15)
    await setup_electricity_pro(
        forecast_nordpool_config_entry="test_nordpool",
        forecast_price_area="SE3",
        forecast_currency="SEK",
        forecast_intervals=[{
            "start": (start + timedelta(hours=i)).isoformat(),
            "end": (start + timedelta(hours=i + 1)).isoformat(),
            "price": 1500,
        } for i in range(3)],
    )
    state = hass.states.get(SOURCE)
    assert state is not None
    assert state.attributes["published_at"] is None
    await request(hass)
    assert hass.states.get(REQUEST).state == "on"
    assert notifications[-1].data["title"].endswith("one window armed")
    await hass.services.async_call("script", "ep_window_cancel", blocking=True)


async def test_next_inexpensive_reminder_uses_actual_sensor(hass, freezer, example, setup_electricity_pro):
    _, notifications = example
    source = "sensor.electricity_pro_next_inexpensive_1h_window_start"
    start = dt_util.utcnow() + timedelta(minutes=15)
    await setup_electricity_pro(
        price_value="1.50", good_price_threshold=2.0,
        price_completeness=PriceCompleteness.COMPLETE,
        forecast_pricing_metadata=PricingMetadata(
            strategy=PricingStrategy.EXTERNAL_COMPLETE_PRICE,
            scope=PriceComponentScope(frozenset(PriceComponent), vat=VatTreatment.INCLUDED),
            completeness=PriceCompleteness.COMPLETE,
        ),
        forecast_nordpool_config_entry="test_nordpool",
        forecast_price_area="SE3", forecast_currency="SEK",
        forecast_intervals=[{
            "start": (start + timedelta(hours=i)).isoformat(),
            "end": (start + timedelta(hours=i + 1)).isoformat(),
            "price": 1500,
        } for i in range(3)],
    )
    state = hass.states.get(source)
    assert state is not None and state.state != "unavailable"
    assert state.attributes["window_duration_minutes"] == 60
    assert float(state.attributes["threshold"]) == 2.0
    await request(hass, window_entity=source, appliance_start=False)
    assert hass.states.get(REQUEST).state == "on"
    freezer.move_to(start)
    # Refresh the report at dispatch, independently of forecast fetch timing.
    hass.states.async_set(source, state.state, dict(state.attributes))
    await advance(hass, freezer, start)
    assert len(dispatched(notifications)) == 1
    assert dispatched(notifications)[0].data["title"].endswith("starts now")
    assert hass.states.get(REQUEST).state == "off"


async def test_next_inexpensive_revision_cancels_reminder(hass, example):
    _, notifications = example
    source = "sensor.electricity_pro_next_inexpensive_1h_window_start"
    start = publish(hass, hours=1)
    attrs = dict(hass.states.get(SOURCE).attributes)
    attrs["threshold"] = "2.00"
    hass.states.async_set(source, start.isoformat(), attrs)
    await request(hass, window_entity=source, appliance_start=False)
    assert hass.states.get(REQUEST).state == "on"
    hass.states.async_set(source, "unavailable")
    await settle(hass)
    assert hass.states.get(REQUEST).state == "off"
    assert not dispatched(notifications)


async def test_revision_during_arm_notification_is_not_missed(hass, example):
    _, notifications = example
    start = publish(hass)

    async def notify(call):
        notifications.append(call)
        if call.data["title"].endswith("one window armed"):
            publish(hass, start=start, price="1.9")

    hass.services.async_register("persistent_notification", "create", notify)
    await request(hass)
    assert hass.states.get(REQUEST).state == "off"
    assert not dispatched(notifications)


@pytest.mark.parametrize("change", ["unavailable", "stale"])
async def test_loss_at_dispatch_cancels(hass, freezer, example, change):
    _, notifications = example
    start = publish(hass)
    await request(hass, appliance_start=True)
    freezer.move_to(start)
    if change == "unavailable":
        hass.states.async_set(SOURCE, "unavailable")
    await advance(hass, freezer, start)
    assert hass.states.get(REQUEST).state == "off"
    assert not dispatched(notifications)


async def test_repeated_unchanged_reports_do_not_look_stale(hass, freezer, example):
    _, notifications = example
    start = publish(hass)
    await request(hass)
    initial_changed = hass.states.get(SOURCE).last_changed
    freezer.move_to(dt_util.utcnow() + timedelta(minutes=4))
    publish(hass, start=start)
    assert hass.states.get(SOURCE).last_changed == initial_changed
    assert hass.states.get(SOURCE).last_reported > initial_changed
    await advance(hass, freezer, dt_util.utcnow())
    assert hass.states.get(REQUEST).state == "on"
    await hass.services.async_call("script", "ep_window_cancel", blocking=True)
    assert not dispatched(notifications)


async def test_failed_device_action_is_not_retried(hass, freezer, example):
    start = publish(hass)
    failed_action = AsyncMock(side_effect=HomeAssistantError("Device response uncertain"))
    hass.services.async_register("script", "ep_window_appliance_action", failed_action)
    # Await the direct script call so the expected device error is consumed by
    # this test rather than left as an unhandled background service exception.
    running = asyncio.create_task(hass.services.async_call(
        "script", "ep_window_request", {
            "window_entity": SOURCE, "expected_currency": "SEK",
            "price_limit": 2, "appliance_start": True,
        }, blocking=True,
    ))
    await settle(hass)
    freezer.move_to(start)
    publish(hass, start=start)
    await advance(hass, freezer, start)
    with pytest.raises(HomeAssistantError, match="Device response uncertain"):
        await running
    assert hass.states.get(REQUEST).state == "off"
    assert failed_action.call_count == 1
    await advance(hass, freezer, start + timedelta(minutes=1))
    await request(hass, appliance_start=True)
    assert failed_action.call_count == 1
