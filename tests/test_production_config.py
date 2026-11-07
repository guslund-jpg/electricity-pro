"""Shared production section through actual setup, options and entry reloads."""

from decimal import Decimal

import pytest
from homeassistant import config_entries
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.flow_sources import FLOW_KEYS
from custom_components.electricity_pro.production_config import PRODUCTION_KEYS
from tests.flow_helpers import (
    confirm_grid,
    confirm_market,
    confirm_measurements,
    confirm_production,
    confirm_supplier,
    form_values,
    open_production_sources,
    start_production,
)

DOMAIN = "electricity_pro"


def source(hass, entity_id="sensor.production", quantity="power", value="100"):
    hass.states.async_set(
        entity_id,
        value,
        {
            "device_class": quantity,
            "unit_of_measurement": "W" if quantity == "power" else "kWh",
        },
    )


async def setup_section(hass, profile):
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
    result = await confirm_supplier(manager, result, {"fixed_supplier_fee_monthly": 0})
    result = await confirm_grid(manager, result, {"grid_fee_per_kwh": 0})
    assert result["step_id"] == "energy_flows"
    return manager, result


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_import_only_setup_skips_sources_and_installation_questions(
    hass, profile
):
    manager, result = await setup_section(hass, profile)
    assert form_values(result) == {"configure_energy_flows": False}
    assert len(result["data_schema"].schema) == 1
    result = await manager.async_configure(
        result["flow_id"], {"configure_energy_flows": False}
    )
    assert result["step_id"] == ("manual" if profile == "custom" else "tibber_settings")
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    assert all(result["data"][key] is None for key in FLOW_KEYS)
    assert result["data"]["flow_storage_presence"] == "unknown"
    assert result["data"]["flow_generation_presence"] == "unknown"
    assert result["data"]["grid_fee_per_kwh"] == 0
    assert result["data"]["fixed_supplier_fee_monthly"] == 0
    assert "configure_energy_flows" not in result["data"]


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize("key", FLOW_KEYS)
async def test_each_source_can_be_reviewed_during_both_setup_paths(hass, profile, key):
    source(hass, "sensor.optional", "power" if "_power_" in key else "energy")
    manager, result = await setup_section(hass, profile)
    result = await confirm_production(
        manager, result, {key: "sensor.optional", "confirm_flow_semantics": True}
    )
    assert result["step_id"] == "flow_compatibility"
    fields = {marker.schema for marker in result["data_schema"].schema}
    phases = {field for field in fields if field.endswith("phase_convention")}
    assert phases == (
        {key.replace("_entity", "_phase_convention")} if "_power_" in key else set()
    )
    assert form_values(result)["flow_storage_presence"] == "unknown"
    assert form_values(result)["flow_compatibility_enabled"] is False
    result = await manager.async_configure(result["flow_id"], {})
    assert result["step_id"] in ("manual", "tibber_settings")
    assert not set(PRODUCTION_KEYS) & result["data_schema"].schema.keys()
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    assert result["data"][key] == "sensor.optional"
    assert result["data"]["flow_storage_presence"] == "unknown"
    assert "confirm_flow_semantics" not in result["data"]


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_retries_and_review_are_atomic_and_do_not_touch_other_sections(
    hass, profile, cancel
):
    source(hass)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "source_profile": profile,
            "power_entity": "sensor.import",
            "grid_fee_per_kwh": 0.125,
            "price_vat_rate": 0,
            "energy_entity": "sensor.import_energy",
        },
        options={
            "flow_storage_presence": "present",
            "supplier_markup_per_kwh": 0.119,
            "good_price_mode": "adaptive",
        },
    )
    entry.add_to_hass(hass)
    original_data, original_options = dict(entry.data), dict(entry.options)
    manager = hass.config_entries.options
    result = await start_production(manager, entry.entry_id)
    result = await open_production_sources(manager, result)
    result = await confirm_production(
        manager,
        result,
        {"production_power_entity": "sensor.missing", "confirm_flow_semantics": True},
    )
    assert result["errors"]["production_power_entity"] == "invalid_flow_source"
    assert form_values(result)["confirm_flow_semantics"] is True
    assert dict(entry.options) == original_options
    result = await confirm_production(
        manager, result, {"production_power_entity": "sensor.production"}
    )
    assert result["step_id"] == "flow_compatibility"
    result = await manager.async_configure(
        result["flow_id"],
        {"flow_generation_presence": "absent", "flow_storage_presence": "absent"},
    )
    assert result["errors"] == {"flow_generation_presence": "contradictory_topology"}
    assert form_values(result)["flow_storage_presence"] == "absent"
    assert dict(entry.options) == original_options
    assert dict(entry.data) == original_data
    if cancel:
        manager.async_abort(result["flow_id"])
        result = await start_production(manager, entry.entry_id)
        assert form_values(result) == {"configure_energy_flows": False}
        assert dict(entry.options) == original_options
    else:
        result = await manager.async_configure(
            result["flow_id"], {"flow_generation_presence": "present"}
        )
        assert result["type"] == "create_entry"
        assert entry.options["flow_storage_presence"] == "absent"
        assert entry.options["production_power_entity"] == "sensor.production"
        assert entry.options["supplier_markup_per_kwh"] == 0.119
        assert entry.options["good_price_mode"] == "adaptive"
        assert dict(entry.data) == original_data


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_disable_clears_bindings_and_diagnostic_but_remembers_hardware_facts(
    hass, profile
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "source_profile": profile,
            "power_entity": "sensor.import",
            "production_power_entity": "sensor.old",
            "production_energy_entity": "sensor.energy",
            "flow_compatibility_enabled": True,
            "flow_generation_presence": "present",
            "flow_storage_presence": "present",
            "production_power_phase_convention": "gross_directional",
        },
    )
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    result = await start_production(manager, entry.entry_id)
    assert form_values(result)["configure_energy_flows"] is True
    result = await manager.async_configure(
        result["flow_id"], {"configure_energy_flows": False}
    )
    assert result["type"] == "create_entry"
    assert all(entry.options[key] is None for key in FLOW_KEYS)
    assert entry.options["flow_compatibility_enabled"] is False
    assert entry.options["production_power_phase_convention"] == "unknown"
    assert entry.options["flow_generation_presence"] == "present"
    assert entry.options["flow_storage_presence"] == "present"
    result = await start_production(manager, entry.entry_id)
    assert form_values(result) == {"configure_energy_flows": False}


async def test_cancel_after_replacing_a_source_preserves_original_conventions(hass):
    source(hass, "sensor.new")
    source(hass, "sensor.export")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "power_entity": "sensor.import",
            "production_power_entity": "sensor.old",
            "grid_export_power_entity": "sensor.export",
            "production_power_phase_convention": "gross_directional",
            "grid_export_power_phase_convention": "net_across_phases",
            "flow_generation_presence": "present",
        },
    )
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    result = await start_production(manager, entry.entry_id)
    result = await confirm_production(
        manager,
        result,
        {"production_power_entity": "sensor.new", "confirm_flow_semantics": True},
    )
    assert result["step_id"] == "flow_compatibility"
    shown = form_values(result)
    assert shown["production_power_phase_convention"] == "unknown"
    assert shown["grid_export_power_phase_convention"] == "net_across_phases"
    manager.async_abort(result["flow_id"])
    assert not entry.options
    assert entry.data["production_power_phase_convention"] == "gross_directional"


async def test_own_section_does_not_validate_or_repair_an_unrelated_price_source(hass):
    source(hass)
    own = er.async_get(hass).async_get_or_create("sensor", DOMAIN, "old-price-output")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"power_entity": "sensor.import", "price_entity": own.entity_id},
    )
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    result = await start_production(manager, entry.entry_id)
    result = await confirm_production(
        manager,
        result,
        {
            "production_power_entity": "sensor.production",
            "confirm_flow_semantics": True,
        },
    )
    assert result["step_id"] == "flow_compatibility"
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    assert "price_entity" not in entry.options
    assert entry.data["price_entity"] == own.entity_id


async def test_unchanged_section_save_reloads_without_resetting_counters_or_ids(
    hass, setup_electricity_pro
):
    for key in FLOW_KEYS:
        source(hass, f"sensor.test_{key}", "power" if "_power_" in key else "energy")
    entry = await setup_electricity_pro(
        include_flow_sources=True,
        energy_value="3.5",
        price_value="1.2",
        accumulated_cost_today_value="4.2",
    )
    for key in FLOW_KEYS:
        if "_energy_" in key:
            source(hass, f"sensor.test_{key}", "energy", "101")
    await hass.async_block_till_done()
    ids = [
        "sensor.electricity_pro_current_power",
        "sensor.electricity_pro_current_price",
        "sensor.electricity_pro_energy_today",
        "sensor.electricity_pro_cost_today",
        "sensor.electricity_pro_production_today",
        "sensor.electricity_pro_grid_export_today",
        "sensor.electricity_pro_household_energy_today",
    ]
    before = {key: hass.states.get(key).state for key in ids}
    for key in ids[-3:]:
        assert Decimal(before[key]) == 1
    registry = er.async_get(hass)
    identities = {key: registry.async_get(key).id for key in ids}
    manager = hass.config_entries.options
    result = await start_production(manager, entry.entry_id)
    result = await confirm_production(manager, result, {"confirm_flow_semantics": True})
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert {key: hass.states.get(key).state for key in ids} == before
    assert {key: registry.async_get(key).id for key in ids} == identities
