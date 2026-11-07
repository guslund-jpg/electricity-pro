"""Grid configuration boundaries through Home Assistant's flow manager."""

import pytest
from homeassistant import config_entries
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.grid_config import GRID_KEYS
from tests.flow_helpers import (
    confirm_review,
    confirm_production,
    TIBBER_CONTRACT,
    confirm_grid,
    confirm_market,
    confirm_measurements,
    confirm_supplier,
    form_values,
    start_grid,
    start_settings,
)

DOMAIN = "electricity_pro"
TARIFF = {
    "grid_fee_per_kwh": 0.125,
    "grid_fee_high_per_kwh": 0.25,
    "grid_fee_high_start": "22:30",
    "grid_fee_high_end": "06:15",
    "grid_fee_high_season_start": "11-01",
    "grid_fee_high_season_end": "03-31",
    "grid_fee_workday_entity": "binary_sensor.workday",
    "energy_tax_per_kwh": 0.4,
    "fixed_grid_fee_monthly": 0,
}


async def open_grid(hass, profile="custom", data=None, options=None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "source_profile": profile,
            "power_entity": "sensor.power",
            **(TIBBER_CONTRACT if profile == "tibber" else {}),
            **(data or {}),
        },
        options=options or {},
    )
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    return entry, manager, await start_grid(manager, entry.entry_id)


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_setup_grid_after_supplier_before_insights(hass, profile):
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
    result = await confirm_supplier(manager, result, {"fixed_supplier_fee_monthly": 49})
    assert result["step_id"] == "grid"
    assert form_values(result) == {"grid_mode": "unconfigured"}
    result = await confirm_grid(manager, result, TARIFF)
    if result.get("step_id") == "energy_flows":
        result = await confirm_production(manager, result)
    assert result["step_id"] == "insights"
    assert not set(GRID_KEYS) & {key.schema for key in result["data_schema"].schema}
    result = await manager.async_configure(result["flow_id"], {})
    result = await confirm_review(manager, result)
    assert result["type"] == "create_entry"
    assert {key: result["data"][key] for key in GRID_KEYS} == TARIFF
    assert result["data"]["fixed_supplier_fee_monthly"] == 49
    assert "grid_mode" not in result["data"]


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize(
    ("charges", "mode"),
    [
        ({}, "unconfigured"),
        ({"grid_fee_high_start": "bad"}, "unconfigured"),
        ({"energy_tax_per_kwh": 0}, "constant"),
        ({"fixed_grid_fee_monthly": 0}, "constant"),
        ({"grid_fee_per_kwh": 0}, "constant"),
        ({"grid_fee_high_per_kwh": 0, "grid_fee_per_kwh": 0}, "time_of_use"),
        (TARIFF, "time_of_use"),
    ],
)
async def test_infer_modes_preserve_zero_and_only_owned_keys(
    hass, profile, charges, mode
):
    entry, manager, result = await open_grid(
        hass,
        profile,
        data={
            "energy_entity": "sensor.energy",
            "price_vat_rate": 0,
            "supplier_markup_per_kwh": 0.119,
            **charges,
        },
        options={
            "good_price_mode": "adaptive",
            "production_power_entity": "sensor.production",
        },
    )
    original = dict(entry.data)
    assert form_values(result)["grid_mode"] == mode
    assert (
        not {"price_entity", "price_vat_rate", "good_price_mode", "power_entity"}
        & result["data_schema"].schema.keys()
    )
    result = await confirm_grid(manager, result)
    assert result["type"] == "create_entry"
    assert dict(entry.data) == original
    assert entry.options["good_price_mode"] == "adaptive"
    assert entry.options["production_power_entity"] == "sensor.production"
    assert "price_vat_rate" not in entry.options
    assert "grid_mode" not in entry.options
    if mode == "unconfigured":
        assert all(entry.options[key] is None for key in GRID_KEYS)
    else:
        for key, value in charges.items():
            assert entry.options[key] == value
    # Insight/optional-flow saves retain all grid values, including None and zero.
    saved_grid = {key: entry.options[key] for key in GRID_KEYS}
    result = await start_settings(manager, entry.entry_id)
    assert not set(GRID_KEYS) & result["data_schema"].schema.keys()
    result = await manager.async_configure(result["flow_id"], form_values(result))
    assert result["type"] == "create_entry"
    assert {key: entry.options[key] for key in GRID_KEYS} == saved_grid


@pytest.mark.parametrize("mode", ["constant", "unconfigured"])
async def test_mode_change_drafts_then_clears_inactive_tariff(hass, mode):
    entry, manager, result = await open_grid(hass, data=TARIFF)
    saved_data = dict(entry.data)
    result = await manager.async_configure(
        result["flow_id"], {**form_values(result), "grid_mode": mode}
    )
    if mode == "constant":
        assert result["step_id"] == "grid"
        assert not entry.options
        assert "grid_fee_high_per_kwh" not in result["data_schema"].schema
        result = await confirm_grid(manager, result)
        if result.get("step_id") == "energy_flows":
            result = await confirm_production(manager, result)
        assert entry.options["grid_fee_per_kwh"] == 0.125
        assert entry.options["fixed_grid_fee_monthly"] == 0
    else:
        assert all(entry.options[key] is None for key in GRID_KEYS)
    assert result["type"] == "create_entry"
    assert dict(entry.data) == saved_data
    assert entry.options["grid_fee_high_per_kwh"] is None
    assert entry.options["grid_fee_workday_entity"] is None
    reopened = await start_grid(manager, entry.entry_id)
    assert form_values(reopened)["grid_mode"] == mode


async def test_clear_visible_amount_overrides_setup_but_retains_zero(hass):
    entry, manager, result = await open_grid(hass, data=TARIFF)
    result = await confirm_grid(manager, result, {"energy_tax_per_kwh": None})
    assert result["type"] == "create_entry"
    assert entry.options["energy_tax_per_kwh"] is None
    assert entry.options["fixed_grid_fee_monthly"] == 0
    result = await start_grid(manager, entry.entry_id)
    assert "energy_tax_per_kwh" not in form_values(result)
    result = await confirm_grid(manager, result)
    assert result["data"]["energy_tax_per_kwh"] is None


@pytest.mark.parametrize("cancel", [False, True])
async def test_retry_keeps_values_and_explicit_clear_until_save_or_cancel(hass, cancel):
    entry, manager, result = await open_grid(hass, data=TARIFF)
    result = await confirm_grid(
        manager, result, {"grid_fee_high_start": "bad", "energy_tax_per_kwh": None}
    )
    assert result["errors"] == {"base": "invalid_grid_tariff"}
    assert not entry.options
    shown = form_values(result)
    assert "energy_tax_per_kwh" not in shown
    assert shown["grid_fee_workday_entity"] == "binary_sensor.workday"
    assert shown["fixed_grid_fee_monthly"] == 0
    result = await confirm_grid(manager, result, {"grid_fee_high_start": "still-bad"})
    assert result["errors"] == {"base": "invalid_grid_tariff"}
    if cancel:
        manager.async_abort(result["flow_id"])
        assert not entry.options
        result = await start_grid(manager, entry.entry_id)
        assert form_values(result)["energy_tax_per_kwh"] == 0.4
        assert form_values(result)["grid_fee_high_start"] == "22:30"
    else:
        result = await confirm_grid(manager, result, {"grid_fee_high_start": "21:30"})
        if result.get("step_id") == "energy_flows":
            result = await confirm_production(manager, result)
        assert result["type"] == "create_entry"
        assert entry.options["energy_tax_per_kwh"] is None
        assert entry.options["grid_fee_high_start"] == "21:30"


@pytest.mark.parametrize(
    "field",
    [
        "grid_fee_per_kwh",
        "energy_tax_per_kwh",
        "fixed_grid_fee_monthly",
        "grid_fee_high_per_kwh",
    ],
)
async def test_nonfinite_amount_does_not_save(hass, field):
    entry, manager, result = await open_grid(hass, data=TARIFF)
    result = await confirm_grid(manager, result, {field: float("nan")})
    assert result["errors"] == {field: "invalid_grid_amount"}
    assert not entry.options


@pytest.mark.parametrize(
    "changes",
    [
        {"grid_fee_high_start": "06:15"},
        {"grid_fee_high_season_start": "02-30"},
        {"grid_fee_high_end": None},
        {"grid_fee_high_season_end": "13-01"},
    ],
)
async def test_invalid_schedule_never_saves_and_cleared_time_stays_blank(hass, changes):
    entry, manager, result = await open_grid(hass, data=TARIFF)
    result = await confirm_grid(manager, result, changes)
    assert result["errors"] == {"base": "invalid_grid_tariff"}
    assert not entry.options
    if changes.get("grid_fee_high_end", "not-cleared") is None:
        assert "grid_fee_high_end" not in form_values(result)


async def test_empty_single_rate_requires_amount_or_explicit_unconfigured(hass):
    entry, manager, result = await open_grid(hass)
    result = await confirm_grid(manager, result, {"grid_mode": "constant"})
    assert result["errors"] == {"base": "grid_amount_required"}
    assert not entry.options
    result = await confirm_grid(manager, result, {"fixed_grid_fee_monthly": 0})
    assert result["type"] == "create_entry"
    assert entry.options["grid_fee_per_kwh"] is None
    assert entry.options["fixed_grid_fee_monthly"] == 0


async def test_enable_high_low_reviews_fields_and_does_not_invent_rates(hass):
    entry, manager, result = await open_grid(hass, data={"energy_tax_per_kwh": 0})
    result = await manager.async_configure(
        result["flow_id"], {**form_values(result), "grid_mode": "time_of_use"}
    )
    assert result["step_id"] == "grid"
    assert not result["errors"]
    shown = form_values(result)
    assert shown["energy_tax_per_kwh"] == 0
    assert shown["grid_fee_high_start"] == "06:00"
    assert "grid_fee_per_kwh" not in shown
    assert "grid_fee_high_per_kwh" not in shown
    assert not entry.options
    result = await confirm_grid(manager, result)
    assert result["errors"] == {
        "grid_fee_per_kwh": "grid_rate_required",
        "grid_fee_high_per_kwh": "grid_rate_required",
    }
    manager.async_abort(result["flow_id"])
    result = await start_grid(manager, entry.entry_id)
    assert form_values(result)["grid_mode"] == "constant"
    assert not entry.options


async def test_grid_reload_preserves_live_values_totals_and_entity_identity(
    hass, setup_electricity_pro
):
    entry = await setup_electricity_pro(
        energy_value="3.5", price_value="1.2", accumulated_cost_today_value="4.2"
    )
    ids = [
        "sensor.electricity_pro_current_power",
        "sensor.electricity_pro_current_price",
        "sensor.electricity_pro_current_supplier_price",
        "sensor.electricity_pro_energy_today",
        "sensor.electricity_pro_cost_today",
    ]
    before = {key: hass.states.get(key).state for key in ids}
    registry = er.async_get(hass)
    identities = {key: registry.async_get(key).id for key in ids}
    manager = hass.config_entries.options
    result = await start_grid(manager, entry.entry_id)
    result = await confirm_grid(manager, result)
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert {key: hass.states.get(key).state for key in ids} == before
    assert {key: registry.async_get(key).id for key in ids} == identities
