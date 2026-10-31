"""Run optional daily notices and humidity simulation with real HA automations."""

import asyncio
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from homeassistant.core import State
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed, async_mock_service, mock_restore_cache,
)

DIRECTORY = Path(__file__).parents[1] / "examples/automations"
DAILY = "automation.ep_daily_window_notice"
WINDOW = "sensor.electricity_pro_cheapest_3h_window_start"
ENABLED = "input_boolean.ep_humidity_example_enabled"
RUNNING = "input_boolean.ep_humidity_simulated_running"
GOOD = "binary_sensor.electricity_pro_good_time_to_use_electricity"
PRICE = "sensor.electricity_pro_effective_price"
HUMIDITY = "sensor.living_room_humidity"


async def settle():
    for _ in range(30):
        await asyncio.sleep(0)


@pytest.fixture
def restored_on():
    return False


@pytest.fixture
async def examples(hass, freezer, restored_on):
    freezer.move_to("2026-10-31T13:59:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    daily = yaml.safe_load((DIRECTORY / "daily_window_notice.yaml").read_text())
    humidity = yaml.safe_load((DIRECTORY / "good_time_humidity_dry_run.yaml").read_text())
    if restored_on:
        mock_restore_cache(hass, [State(entity, "on") for entity in (DAILY, ENABLED, RUNNING)])
    notifications = async_mock_service(hass, "persistent_notification", "create")
    assert await async_setup_component(hass, "input_boolean", humidity)
    assert await async_setup_component(hass, "automation", {
        "automation": daily["automation"] + humidity["automation"],
    })
    await hass.async_start()
    await settle()
    yield notifications
    # Explicitly detach recurring trigger timers before HA fixture shutdown.
    await hass.services.async_call("automation", "turn_off", {
        "entity_id": [DAILY, "automation.ep_humidity_dry_run"],
    }, blocking=True)
    await settle()


def window(hass, *, start=None, **overrides):
    start = start or dt_util.utcnow() + timedelta(hours=1)
    attrs = {
        "window_end": (start + timedelta(hours=3)).isoformat(),
        "window_duration_minutes": 180,
        "average_scheduling_price": "1.25",
        "currency": "SEK",
        "price_area": "SE3",
        **overrides,
    }
    hass.states.async_set(WINDOW, start.isoformat(), attrs)


def inputs(hass, *, good="on", price="1.50", humidity="60", unit="SEK/kWh", humidity_unit="%"):
    hass.states.async_set(GOOD, good)
    hass.states.async_set(PRICE, price, {"unit_of_measurement": unit})
    hass.states.async_set(HUMIDITY, humidity, {"unit_of_measurement": humidity_unit})


async def toggle(hass, entity, on=True):
    domain = entity.split(".")[0]
    await hass.services.async_call(domain, "turn_on" if on else "turn_off",
                                   {"entity_id": entity}, blocking=True)
    await settle()


async def tick(hass, freezer, *, minutes=1, refresh=False):
    freezer.move_to(dt_util.utcnow() + timedelta(minutes=minutes))
    if refresh:
        inputs(hass)
    async_fire_time_changed(hass, dt_util.utcnow())
    await settle()


async def daily_run(hass):
    await hass.services.async_call("automation", "trigger", {
        "entity_id": DAILY, "skip_condition": False,
    }, blocking=True)
    await settle()


async def start_simulation(hass, freezer):
    inputs(hass)
    await toggle(hass, ENABLED)
    await tick(hass, freezer, minutes=5, refresh=True)
    assert hass.states.get(RUNNING).state == "on"


async def test_new_install_is_opt_in(hass, freezer, examples):
    assert hass.states.get(DAILY).state == "off"
    assert hass.states.get(ENABLED).state == "off"
    assert hass.states.get(RUNNING).state == "off"
    window(hass)
    inputs(hass)
    await tick(hass, freezer, minutes=6, refresh=True)
    assert not examples
    assert hass.states.get(RUNNING).state == "off"
    assert not hass.services.has_service("switch", "turn_on")


@pytest.mark.parametrize("restored_on", [True])
async def test_restart_does_not_restore_enabled_or_running(hass, freezer, examples, restored_on):
    assert hass.states.get(DAILY).state == "off"
    assert hass.states.get(ENABLED).state == "off"
    assert hass.states.get(RUNNING).state == "off"
    inputs(hass)
    await tick(hass, freezer, minutes=6, refresh=True)
    assert not examples
    assert hass.states.get(RUNNING).state == "off"


async def test_daily_time_trigger_and_single_snapshot(hass, freezer, examples):
    window(hass, average_scheduling_price="-0.10")
    await toggle(hass, DAILY)
    await tick(hass, freezer)
    assert len(examples) == 1
    assert "best currently available" in examples[0].data["title"]
    message = examples[0].data["message"]
    assert "-0.1 SEK/kWh" in message
    assert "does not confirm" in message
    assert "no job was scheduled or started" in message
    window(hass, average_scheduling_price="1.10")
    await tick(hass, freezer)
    assert len(examples) == 1  # Not repeated on sensor updates.


@pytest.mark.parametrize("attrs", [
    {"currency": "EUR"}, {"average_scheduling_price": "nan"},
    {"average_scheduling_price": "inf"}, {"window_end": "invalid"},
    {"window_duration_minutes": 60}, {"price_area": None},
])
async def test_daily_rejects_invalid_attributes(hass, examples, attrs):
    window(hass, **attrs)
    await daily_run(hass)
    assert examples[-1].data["title"].endswith("notice unavailable")


@pytest.mark.parametrize("invalid", ["missing", "unavailable", "past", "stale", "future_report"])
async def test_daily_rejects_invalid_source(hass, freezer, examples, invalid):
    if invalid == "unavailable":
        hass.states.async_set(WINDOW, "unavailable")
    elif invalid == "past":
        window(hass, start=dt_util.utcnow() - timedelta(minutes=1))
    elif invalid in ("stale", "future_report"):
        window(hass)
        freezer.move_to(dt_util.utcnow() + timedelta(minutes=6 if invalid == "stale" else -1))
    await daily_run(hass)
    assert examples[-1].data["title"].endswith("notice unavailable")


async def test_daily_missing_publication_timestamp_is_not_invented(hass, examples):
    window(hass)  # No published_at or separate average-price entity required.
    await daily_run(hass)
    assert "fresh exchange fetch" in examples[-1].data["message"]
    assert "1.25 SEK/kWh" in examples[-1].data["message"]


async def test_humidity_hysteresis_cooldown_and_only_transition_notices(hass, freezer, examples):
    inputs(hass, humidity="52")
    await toggle(hass, ENABLED)
    await tick(hass, freezer, minutes=5)
    # Humidity changes while Good Time stays on: this must start without a
    # price transition, once the initial off-time has elapsed.
    inputs(hass, humidity="55")
    await settle()
    assert hass.states.get(RUNNING).state == "on"
    assert len(examples) == 1
    inputs(hass, humidity="52")
    await settle()
    assert hass.states.get(RUNNING).state == "on"
    assert len(examples) == 1
    inputs(hass, humidity="50")
    await settle()
    assert hass.states.get(RUNNING).state == "off"
    assert "humidity_low" in examples[-1].data["message"]
    inputs(hass, humidity="60")
    await tick(hass, freezer, minutes=4, refresh=True)
    assert hass.states.get(RUNNING).state == "off"
    await tick(hass, freezer, refresh=True)
    assert hass.states.get(RUNNING).state == "on"
    assert len(examples) == 3


async def test_humidity_initial_cooldown_and_disable(hass, freezer, examples):
    inputs(hass)
    await toggle(hass, ENABLED)
    assert hass.states.get(RUNNING).state == "off"
    await tick(hass, freezer, minutes=4, refresh=True)
    assert hass.states.get(RUNNING).state == "off"
    await tick(hass, freezer, refresh=True)
    assert hass.states.get(RUNNING).state == "on"
    await toggle(hass, ENABLED, False)
    assert hass.states.get(RUNNING).state == "off"
    assert "disabled" in examples[-1].data["message"]


@pytest.mark.parametrize("change,reason", [
    ({"good": "off"}, "not_good_time"),
    ({"good": "unavailable"}, "invalid_or_stale_input"),
    ({"good": "unknown"}, "invalid_or_stale_input"),
    ({"price": "2.01"}, "price_over_limit"),
    ({"price": "nan"}, "invalid_or_stale_input"),
    ({"price": "unavailable"}, "invalid_or_stale_input"),
    ({"unit": "EUR/kWh"}, "invalid_or_stale_input"),
    ({"humidity": "unavailable"}, "invalid_or_stale_input"),
    ({"humidity": "nan"}, "invalid_or_stale_input"),
    ({"humidity": "101"}, "invalid_or_stale_input"),
    ({"humidity": "-1"}, "invalid_or_stale_input"),
    ({"humidity_unit": "W"}, "invalid_or_stale_input"),
])
async def test_humidity_stops_on_bad_data_or_price(hass, freezer, examples, change, reason):
    await start_simulation(hass, freezer)
    inputs(hass, **change)
    await settle()
    assert hass.states.get(RUNNING).state == "off"
    assert reason in examples[-1].data["message"]
    inputs(hass)
    await settle()
    assert hass.states.get(RUNNING).state == "off"  # Recovery still needs cooldown.
    await tick(hass, freezer, minutes=5, refresh=True)
    assert hass.states.get(RUNNING).state == "on"


async def test_humidity_stale_without_state_change(hass, freezer, examples):
    await start_simulation(hass, freezer)
    await tick(hass, freezer, minutes=6)
    assert hass.states.get(RUNNING).state == "off"
    assert "invalid_or_stale_input" in examples[-1].data["message"]


async def test_humidity_unchanged_reports_refresh_age(hass, freezer, examples):
    await start_simulation(hass, freezer)
    changed = hass.states.get(GOOD).last_changed
    for _ in range(3):
        await tick(hass, freezer, minutes=4, refresh=True)
        assert hass.states.get(RUNNING).state == "on"
    assert hass.states.get(GOOD).last_changed == changed
    assert len(examples) == 1


async def test_humidity_reload_event_reconciles_simulation(hass, freezer, examples):
    await start_simulation(hass, freezer)
    # Only the synthetic helper is modified, not a real device.
    hass.states.async_set(GOOD, "off")
    hass.bus.async_fire("automation_reloaded")
    await settle()
    assert hass.states.get(RUNNING).state == "off"


async def test_real_reload_preserves_unchanged_daily_and_humidity_can_reconcile(hass, freezer, examples):
    await start_simulation(hass, freezer)
    await toggle(hass, DAILY)
    # Stop listeners, then change the input so reconciliation after reload and
    # re-enabling must correct the existing simulated running state.
    await toggle(hass, "automation.ep_humidity_dry_run", False)
    inputs(hass, good="off")
    assert hass.states.get(RUNNING).state == "on"
    daily = yaml.safe_load((DIRECTORY / "daily_window_notice.yaml").read_text())
    humidity = yaml.safe_load((DIRECTORY / "good_time_humidity_dry_run.yaml").read_text())
    with patch("homeassistant.config.async_hass_config_yaml", new=AsyncMock(return_value={
        "automation": daily["automation"] + humidity["automation"],
    })):
        await hass.services.async_call("automation", "reload", blocking=True)
    await settle()
    assert hass.states.get(DAILY).state == "on"  # HA keeps unchanged automations.
    # A user-disabled automation remains disabled across reload; re-enable it,
    # and the periodic check must reconcile rather than assume a physical state.
    await toggle(hass, "automation.ep_humidity_dry_run")
    await tick(hass, freezer)
    assert hass.states.get(RUNNING).state == "off"


async def test_humidity_negative_price_allowed_and_ceiling_inclusive(hass, freezer, examples):
    await start_simulation(hass, freezer)
    inputs(hass, price="-1")
    await settle()
    assert hass.states.get(RUNNING).state == "on"
    inputs(hass, price="2.00")
    await settle()
    assert hass.states.get(RUNNING).state == "on"
