"""Opt-in declarations, stable diagnostics and unchanged independent readings."""

from unittest.mock import patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.flow_compatibility import (
    CONF_ENABLED, CONF_GENERATION, CONF_STORAGE, COMPATIBILITY_KEYS,
)

DIAGNOSTIC = "sensor.electricity_pro_flow_power_compatibility"


def source(hass, entity, value):
    hass.states.async_set(entity, str(value), {
        "unit_of_measurement": "W", "device_class": "power",
    })


def entry_data():
    return {
        "power_entity": "sensor.net",
        "production_power_entity": "sensor.production",
        "grid_export_power_entity": "sensor.export",
    }


def declarations():
    return {
        CONF_ENABLED: True, CONF_GENERATION: "present", CONF_STORAGE: "absent",
        "production_power_phase_convention": "net_across_phases",
        "grid_export_power_phase_convention": "net_across_phases",
    }


@pytest.mark.parametrize("mode", ["legacy", "disabled", "unknown", "aligned"])
async def test_diagnostic_opt_in_does_not_affect_measurements(hass, freezer, mode):
    freezer.move_to("2026-09-16T12:00:00+00:00")
    for entity, value in (("sensor.net", -500), ("sensor.production", 1000), ("sensor.export", 500)):
        source(hass, entity, value)
    options = {} if mode == "legacy" else {
        **declarations(), CONF_ENABLED: mode != "disabled",
        CONF_STORAGE: "unknown" if mode == "unknown" else "absent",
    }
    entry = MockConfigEntry(domain=DOMAIN, title="Electricity Pro", data=entry_data(), options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.electricity_pro_current_power").state == "-500"
    assert hass.states.get("sensor.electricity_pro_production_power").state == "1000"
    diagnostic = hass.states.get(DIAGNOSTIC)
    if mode in ("legacy", "disabled"):
        assert diagnostic is None
        return
    assert diagnostic.state == ("unknown_topology" if mode == "unknown" else "aligned")
    assert diagnostic.attributes["complete_balance_available"] is False
    assert diagnostic.attributes["assessment_scope"] == "configured_optional_power_only"
    assert diagnostic.attributes["timestamp_provenance"] == "ha_receipt"
    before = dict(diagnostic.attributes)
    source(hass, "sensor.net", -400)
    await hass.async_block_till_done()
    assert dict(hass.states.get(DIAGNOSTIC).attributes) == before
    if mode == "aligned":
        assert diagnostic.attributes["quality"] == "receipt_time_estimate"
        freezer.move_to("2026-09-16T12:00:31+00:00")
        source(hass, "sensor.production", 1100)
        await hass.async_block_till_done()
        assert hass.states.get(DIAGNOSTIC).state == "time_skew"
        assert hass.states.get("sensor.electricity_pro_production_power").state == "1100"
        assert hass.states.get("sensor.electricity_pro_grid_export_power").state == "500"
        source(hass, "sensor.export", 600)
        await hass.async_block_till_done()
        assert hass.states.get(DIAGNOSTIC).state == "aligned"
        source(hass, "sensor.export", "unavailable")
        await hass.async_block_till_done()
        assert hass.states.get(DIAGNOSTIC).state == "invalid_or_unavailable_source"
        assert hass.states.get("sensor.electricity_pro_production_power").state == "1100"


async def to_compatibility_step(hass, profile="custom", options=None):
    source(hass, "sensor.production", 1000)
    entry = MockConfigEntry(domain=DOMAIN, data={
        "power_entity": "sensor.net", "source_profile": profile,
    }, options=options or {})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    initial_keys = {key.schema for key in result["data_schema"].schema}
    assert not set(COMPATIBILITY_KEYS) & initial_keys
    submission = {"power_entity": "sensor.net"} if profile == "custom" else {}
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        **submission, "configure_energy_flows": True,
    })
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "production_power_entity": "sensor.production", "confirm_flow_semantics": True,
        "configure_flow_compatibility": True,
    })
    assert result["step_id"] == "flow_compatibility"
    return entry, result, submission


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_defaults_confirmation_contradictions_preservation_and_disable(hass, profile):
    entry, result, submission = await to_compatibility_step(hass, profile)
    defaults = result["data_schema"]({})
    assert defaults[CONF_GENERATION] == defaults[CONF_STORAGE] == "unknown"
    assert defaults["production_power_phase_convention"] == "unknown"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        CONF_GENERATION: "absent",
    })
    assert result["errors"][CONF_GENERATION] == "contradictory_topology"
    assert not entry.options
    result = await hass.config_entries.options.async_configure(result["flow_id"], declarations())
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_STORAGE] == "absent"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], submission)
    assert result["data"][CONF_GENERATION] == "present"
    assert result["data"]["production_power_phase_convention"] == "net_across_phases"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        **submission, "configure_energy_flows": True,
    })
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "production_power_entity": "sensor.production", "confirm_flow_semantics": True,
        "configure_flow_compatibility": True,
    })
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        **declarations(), CONF_ENABLED: False,
    })
    assert result["data"][CONF_ENABLED] is False
    assert result["data"]["production_power_entity"] == "sensor.production"


async def test_cancel_does_not_commit_declarations(hass):
    entry, result, _ = await to_compatibility_step(hass)
    hass.config_entries.options.async_abort(result["flow_id"])
    assert not entry.options


async def test_adding_production_requires_correcting_saved_absence(hass):
    source(hass, "sensor.production", 100)
    entry = MockConfigEntry(domain=DOMAIN, data={"power_entity": "sensor.net"}, options={
        CONF_GENERATION: "absent", CONF_STORAGE: "absent", CONF_ENABLED: False,
    })
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "power_entity": "sensor.net", "configure_energy_flows": True,
    })
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "production_power_entity": "sensor.production", "confirm_flow_semantics": True,
    })
    assert result["step_id"] == "flow_compatibility"
    assert entry.options[CONF_GENERATION] == "absent"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        CONF_GENERATION: "present", CONF_STORAGE: "absent", CONF_ENABLED: False,
    })
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["production_power_entity"] == "sensor.production"
    assert result["data"][CONF_ENABLED] is False


async def test_replacing_source_invalidates_only_its_phase_declaration(hass):
    source(hass, "sensor.new_production", 100)
    entry = MockConfigEntry(domain=DOMAIN, data=entry_data(), options=declarations())
    entry.add_to_hass(hass)
    source(hass, "sensor.export", 0)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "power_entity": "sensor.net", "configure_energy_flows": True,
    })
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "production_power_entity": "sensor.new_production",
        "grid_export_power_entity": "sensor.export",
        "confirm_flow_semantics": True,
    })
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["production_power_phase_convention"] == "unknown"
    assert result["data"]["grid_export_power_phase_convention"] == "net_across_phases"


async def test_declaration_changes_do_not_discard_independent_energy_baselines(hass):
    from datetime import UTC, datetime
    from decimal import Decimal
    from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
    data = {**entry_data(), "production_energy_entity": "sensor.production_energy"}
    old = ElectricityProCoordinator(hass, MockConfigEntry(domain=DOMAIN, data=data))
    old._flow_counters["production"].update(Decimal(100), datetime(2026, 9, 16, tzinfo=UTC))
    stored = old._statistics_data()
    new = ElectricityProCoordinator(hass, MockConfigEntry(domain=DOMAIN, data=data, options=declarations()))
    with patch.object(new._store, "async_load", return_value=stored):
        await new._async_restore_statistics()
    assert new._flow_counters["production"].high_water == 100
