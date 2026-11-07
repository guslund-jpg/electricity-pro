"""Shared insight configuration through HA flows and loaded-entry reloads."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import InvalidData
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.binary_sensor import async_setup_entry
from custom_components.electricity_pro.insight_config import INSIGHT_KEYS
from custom_components.electricity_pro.pricing import PriceCompleteness
from tests.flow_helpers import (
    confirm_grid,
    confirm_insights,
    confirm_market,
    confirm_measurements,
    confirm_production,
    confirm_supplier,
    form_values,
    select_insight_method,
    start_settings,
)

DOMAIN = "electricity_pro"
FIXED = "good_price_threshold"
MODE = "good_price_mode"
TARGET = "adaptive_target_percentile"
CEILING = "adaptive_price_ceiling"
GOOD_TIME = "binary_sensor.electricity_pro_good_time_to_use_electricity"


async def open_setup(hass, profile):
    if profile == "tibber":
        native = MockConfigEntry(domain="tibber")
        native.add_to_hass(hass)
        device = dr.async_get(hass).async_get_or_create(
            config_entry_id=native.entry_id, identifiers={("tibber", "home")}
        )
        for key in ("power", "electricity_price"):
            er.async_get(hass).async_get_or_create(
                "sensor", "tibber", key, translation_key=key, device_id=device.id
            )
    manager = hass.config_entries.flow
    result = await manager.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await manager.async_configure(result["flow_id"], {"setup_method": profile})
    result = await confirm_measurements(manager, result)
    result = await confirm_market(manager, result)
    result = await confirm_supplier(manager, result, {"supplier_markup_per_kwh": 0})
    result = await confirm_grid(manager, result, {"grid_fee_per_kwh": 0})
    result = await confirm_production(manager, result)
    return manager, result


async def open_options(hass, profile="custom", data=None, options=None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "source_profile": profile,
            "power_entity": "sensor.power",
            **(data or {}),
        },
        options=options or {},
    )
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    return entry, manager, await start_settings(manager, entry.entry_id)


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize("mode", ["fixed", "adaptive"])
async def test_setup_uses_same_relevant_controls_after_production(hass, profile, mode):
    manager, result = await open_setup(hass, profile)
    assert result["step_id"] == "insights"
    assert set(result["data_schema"].schema) == {MODE, FIXED}
    result = await select_insight_method(manager, result, mode)
    assert set(result["data_schema"].schema) == (
        set(INSIGHT_KEYS) if mode == "adaptive" else {MODE, FIXED}
    )
    if mode == "adaptive":
        assert form_values(result)[TARGET] == 25
    result = await confirm_insights(
        manager, result, {FIXED: 0, TARGET: 37, CEILING: -0.5}
    )
    assert result["type"] == "create_entry"
    assert result["data"][MODE] == mode
    assert result["data"][FIXED] == 0
    assert result["data"]["grid_fee_per_kwh"] == 0
    if mode == "adaptive":
        assert result["data"][TARGET] == 37
        assert result["data"][CEILING] == -0.5
    else:
        assert CEILING not in result["data"]


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_default_setup_does_not_create_an_unconfigured_good_time_entity(
    hass, profile
):
    manager, result = await open_setup(hass, profile)
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    assert FIXED not in result["data"]
    add_entities = Mock()
    await async_setup_entry(
        hass, MockConfigEntry(domain=DOMAIN, data=result["data"]), add_entities
    )
    add_entities.assert_not_called()


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize("mode", ["fixed", "adaptive"])
async def test_options_only_save_owned_keys_and_keep_inactive_values(
    hass, profile, mode
):
    data = {
        MODE: mode,
        FIXED: 0,
        TARGET: 37,
        CEILING: -0.25,
        "price_entity": "sensor.price",
        "forecast_price_area": "SE4",
        "grid_fee_per_kwh": 0.125,
        "production_power_entity": "sensor.unavailable",
    }
    options = {
        "supplier_markup_per_kwh": 0,
        "household_energy_entity": None,
        "flow_storage_presence": "present",
    }
    entry, manager, result = await open_options(hass, profile, data, options)
    original = dict(entry.data)
    result = await confirm_insights(manager, result)
    assert result["type"] == "create_entry"
    assert dict(entry.data) == original
    assert dict(entry.options) == {
        **options,
        **{key: data[key] for key in INSIGHT_KEYS},
    }


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_method_changes_keep_hidden_values_and_do_not_save_early(
    hass, profile, cancel
):
    data = {MODE: "adaptive", FIXED: 0, TARGET: 37, CEILING: -0.3}
    entry, manager, result = await open_options(hass, profile, data)
    result = await select_insight_method(manager, result, "fixed")
    assert result["step_id"] == "insights"
    assert set(result["data_schema"].schema) == {MODE, FIXED}
    assert not entry.options
    result = await select_insight_method(manager, result, "adaptive")
    assert form_values(result)[TARGET] == 37
    assert form_values(result)[CEILING] == -0.3
    assert form_values(result)[FIXED] == 0
    if cancel:
        manager.async_abort(result["flow_id"])
        assert not entry.options
        result = await start_settings(manager, entry.entry_id)
        assert form_values(result)[MODE] == "adaptive"
    else:
        result = await confirm_insights(manager, result)
        assert result["type"] == "create_entry"
        assert dict(entry.options) == data


@pytest.mark.parametrize("value", [None, 0])
async def test_cleared_fixed_threshold_overrides_setup_and_zero_remains_known(
    hass, value
):
    entry, manager, result = await open_options(
        hass, data={FIXED: 1.5, TARGET: 37, CEILING: 0.8}
    )
    result = await confirm_insights(manager, result, {FIXED: value})
    assert result["type"] == "create_entry"
    assert entry.options[FIXED] is None if value is None else entry.options[FIXED] == 0
    result = await start_settings(manager, entry.entry_id)
    if value is None:
        assert FIXED not in form_values(result)
    else:
        assert form_values(result)[FIXED] == 0
    assert entry.options[TARGET] == 37
    assert entry.options[CEILING] == 0.8


@pytest.mark.parametrize("key", [FIXED, TARGET, CEILING])
async def test_nonfinite_inputs_are_rejected_without_writing(hass, key):
    entry, manager, result = await open_options(
        hass, data={MODE: "adaptive", FIXED: 1, TARGET: 37, CEILING: 2}
    )
    result = await confirm_insights(manager, result, {key: float("nan")})
    assert result["errors"] == {
        key: {
            FIXED: "invalid_insight_threshold",
            TARGET: "invalid_insight_percentile",
            CEILING: "invalid_insight_ceiling",
        }[key]
    }
    assert not entry.options


@pytest.mark.parametrize("target", [1, 100])
async def test_percentile_boundaries_and_zero_ceiling(hass, target):
    entry, manager, result = await open_options(hass, data={MODE: "adaptive"})
    result = await confirm_insights(manager, result, {TARGET: target, CEILING: 0})
    assert result["type"] == "create_entry"
    assert entry.options[TARGET] == target
    assert entry.options[CEILING] == 0


@pytest.mark.parametrize("target", [0, 101])
async def test_out_of_range_percentile_is_rejected_by_the_form(hass, target):
    entry, manager, result = await open_options(hass, data={MODE: "adaptive"})
    with pytest.raises(InvalidData):
        await manager.async_configure(
            result["flow_id"], {MODE: "adaptive", TARGET: target}
        )
    assert not entry.options


async def test_clears_survive_error_retry_and_method_changes(hass):
    entry, manager, result = await open_options(
        hass, data={MODE: "adaptive", FIXED: 2, TARGET: 37, CEILING: 1.5}
    )
    # Real form submission omits cleared optional controls.
    result = await manager.async_configure(
        result["flow_id"], {MODE: "adaptive", TARGET: float("nan")}
    )
    assert result["errors"] == {TARGET: "invalid_insight_percentile"}
    assert FIXED not in form_values(result)
    assert CEILING not in form_values(result)
    assert not entry.options
    result = await manager.async_configure(
        result["flow_id"], {MODE: "fixed", TARGET: 37}
    )
    assert result["step_id"] == "insights"
    assert not entry.options
    result = await select_insight_method(manager, result, "adaptive")
    assert FIXED not in form_values(result)
    assert CEILING not in form_values(result)
    result = await confirm_insights(manager, result)
    assert result["type"] == "create_entry"
    assert entry.options[FIXED] is None
    assert entry.options[CEILING] is None


async def test_invalid_draft_cannot_be_hidden_by_switching_method(hass):
    entry, manager, result = await open_options(
        hass, data={MODE: "adaptive", TARGET: 37}
    )
    result = await manager.async_configure(
        result["flow_id"], {MODE: "fixed", TARGET: 37, CEILING: float("nan")}
    )
    assert result["step_id"] == "insights_adaptive"
    assert result["errors"] == {CEILING: "invalid_insight_ceiling"}
    assert form_values(result)[MODE] == "adaptive"
    assert CEILING in result["data_schema"].schema
    assert not entry.options


async def test_unconfigured_fixed_save_does_not_add_an_empty_entity(
    hass, setup_electricity_pro
):
    entry = await setup_electricity_pro(price_value="1.2", energy_value="3.5")
    assert hass.states.get(GOOD_TIME) is None
    manager = hass.config_entries.options
    result = await start_settings(manager, entry.entry_id)
    result = await confirm_insights(manager, result)
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert FIXED not in entry.options
    assert hass.states.get(GOOD_TIME) is None


@pytest.mark.parametrize("mode", ["fixed", "adaptive"])
async def test_loaded_save_preserves_history_totals_identity_and_existing_fallback(
    hass, freezer, setup_electricity_pro, mode
):
    now = datetime(2026, 11, 7, 12, 30, tzinfo=UTC)
    freezer.move_to(now)
    entry = await setup_electricity_pro(
        energy_value="3.5",
        price_value="1.2",
        accumulated_cost_today_value="4.2",
        grid_fee_per_kwh=0,
        energy_tax_per_kwh=0,
        supplier_markup_per_kwh=0,
        good_price_threshold=2,
        good_price_mode="adaptive",
        adaptive_target_percentile=37,
        adaptive_price_ceiling=0.5,
        price_completeness=PriceCompleteness.COMPLETE,
    )
    # Current runtime deliberately uses the fixed fallback during warm-up,
    # even when its threshold is above the adaptive-only ceiling.
    assert hass.states.get(GOOD_TIME).state == "on"
    assert (
        hass.states.get(GOOD_TIME).attributes["evaluation_method"]
        == "adaptive_fallback"
    )
    history = entry.runtime_data.adaptive_price_history
    history.add_segment(
        start=now.replace(hour=11, minute=0),
        end=now.replace(minute=0),
        effective_price=Decimal("1.1"),
    )
    assert len(history.observations) == 1
    saved_history = history.as_dict()
    ids = [
        "sensor.electricity_pro_current_power",
        "sensor.electricity_pro_current_price",
        "sensor.electricity_pro_energy_today",
        "sensor.electricity_pro_cost_today",
        GOOD_TIME,
    ]
    before = {key: hass.states.get(key).state for key in ids}
    registry = er.async_get(hass)
    identities = {key: registry.async_get(key).id for key in ids}
    manager = hass.config_entries.options
    result = await start_settings(manager, entry.entry_id)
    result = await confirm_insights(manager, result, {MODE: mode})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert {key: hass.states.get(key).state for key in ids} == before
    assert {key: registry.async_get(key).id for key in ids} == identities
    assert entry.runtime_data.adaptive_price_history.as_dict() == saved_history
    assert hass.states.get(GOOD_TIME).attributes["configured_mode"] == mode
