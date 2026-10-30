"""Recover configuration errors without discarding form or follow-up choices."""

from math import isnan

import pytest
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.flow_sources import FLOW_KEYS
from custom_components.electricity_pro.flow_compatibility import COMPATIBILITY_KEYS


def form_values(result):
    """Model submitting the displayed suggestions/defaults, not hidden fields."""
    values = {}
    for marker in result["data_schema"].schema:
        description = marker.description or {}
        default = marker.default() if callable(marker.default) else vol.UNDEFINED
        value = description.get("suggested_value", default)
        if value is not vol.UNDEFINED and value is not None:
            values[marker.schema] = value
    return values


async def start(hass, profile, options):
    """Enter either setup track or its options through HA's flow manager."""
    if options:
        entry = MockConfigEntry(domain=DOMAIN, data={
            "power_entity": "sensor.old_power", "source_profile": profile,
            "adaptive_price_ceiling": 2.5,
        }, options={"fixed_grid_fee_monthly": 600, "adaptive_price_ceiling": 2.2})
        entry.add_to_hass(hass)
        return entry, hass.config_entries.options, await hass.config_entries.options.async_init(entry.entry_id)
    if profile == "tibber":
        tibber = MockConfigEntry(domain="tibber")
        tibber.add_to_hass(hass)
        device = dr.async_get(hass).async_get_or_create(
            config_entry_id=tibber.entry_id, identifiers={("tibber", "home")},
        )
        for name in ("power", "electricity_price"):
            er.async_get(hass).async_get_or_create(
                "sensor", "tibber", name, device_id=device.id, translation_key=name,
            )
    manager = hass.config_entries.flow
    result = await manager.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await manager.async_configure(result["flow_id"], {"setup_method": profile})
    return None, manager, result


@pytest.mark.parametrize("options", [False, True], ids=["setup", "options"])
@pytest.mark.parametrize(("profile", "error"), [
    ("custom", "tariff"), ("tibber", "tariff"),
    ("custom", "good_time"), ("tibber", "good_time"),
    ("custom", "source"), ("custom", "pricing"),
])
async def test_repeated_error_preserves_displayed_values(hass, profile, options, error):
    """Retry the displayed form, changing only the invalid field, then save."""
    entry, manager, result = await start(hass, profile, options)
    original_keys = set(result["data_schema"].schema)
    original_options = dict(entry.options) if entry else None
    original_data = dict(entry.data) if entry else None
    submitted = {
        **form_values(result),
        "grid_fee_per_kwh": 0,
        "fixed_grid_fee_monthly": 0,
        "fixed_supplier_fee_monthly": 49,
        "good_price_mode": "adaptive",
        "adaptive_target_percentile": 37,
        "adaptive_price_ceiling": 1.7,
        "grid_fee_high_start": "07:30",
    }
    if profile == "custom":
        submitted.update(power_entity="sensor.new_power", price_vat_rate=0)
    expected = {"base": {
        "tariff": "invalid_grid_tariff", "good_time": "invalid_good_price_settings",
        "pricing": "pricing_metadata_required",
    }.get(error)}
    if error == "tariff":
        submitted["grid_fee_high_start"] = "bad-time"
    elif error == "good_time":
        submitted["adaptive_price_ceiling"] = float("nan")
    elif error == "pricing":
        submitted.update(price_entity="sensor.price", pricing_strategy="market_price_plus_tariff",
                         price_vat_treatment="excluded", price_included_components=[])
    else:
        # Create after the form so server-side ownership validation catches it.
        own = er.async_get(hass).async_get_or_create("sensor", DOMAIN, "own")
        submitted["power_entity"] = own.entity_id
        expected = {"power_entity": "electricity_pro_source"}
    result = await manager.async_configure(result["flow_id"], submitted)
    assert result["errors"] == expected
    assert set(result["data_schema"].schema) == original_keys
    shown = form_values(result)
    for key, value in submitted.items():
        if key == "adaptive_price_ceiling" and error == "good_time":
            assert isnan(shown[key])
        else:
            assert shown[key] == value
    if profile == "tibber":
        assert not {"price_entity", "price_vat_rate", "supplier_markup_per_kwh"} & shown.keys()
        if not options:
            assert result["description_placeholders"]["power_entity"]
    if entry:
        assert dict(entry.options) == original_options
        assert dict(entry.data) == original_data

    # Another error after clearing an optional field must not resurrect it.
    shown.pop("adaptive_price_ceiling", None)
    shown["grid_fee_high_start"] = "still-bad"
    if error == "source":
        shown["power_entity"] = "sensor.new_power"
    result = await manager.async_configure(result["flow_id"], shown)
    assert result["errors"] == {"base": "invalid_grid_tariff"}
    shown = form_values(result)
    assert "adaptive_price_ceiling" not in shown
    assert shown["fixed_grid_fee_monthly"] == 0
    shown["grid_fee_high_start"] = "07:30"
    if error == "pricing":
        shown["price_included_components"] = ["market_energy"]
    result = await manager.async_configure(result["flow_id"], shown)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["fixed_grid_fee_monthly"] == 0
    assert result["data"].get("adaptive_price_ceiling") is None
    if entry:
        # Explicit None must override the original setup data, not fall back to it.
        assert entry.options.get("adaptive_price_ceiling", entry.data["adaptive_price_ceiling"]) is None
    assert result["data"]["adaptive_target_percentile"] == 37


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_follow_up_choices_survive_main_form_errors(hass, profile, cancel):
    """Keep confirmed hidden bindings/clears/declarations until save or cancel."""
    entry, manager, result = await start(hass, profile, True)
    hass.config_entries.async_update_entry(entry, options={
        **entry.options, "grid_export_power_entity": "sensor.old_export",
        "flow_storage_presence": "present",
    })
    saved = dict(entry.options)
    hass.states.async_set("sensor.production", "100", {
        "device_class": "power", "unit_of_measurement": "W",
    })
    submitted = {**form_values(result), "configure_energy_flows": True,
                 "grid_fee_high_start": "invalid"}
    result = await manager.async_configure(result["flow_id"], submitted)
    assert result["step_id"] == "energy_flows"
    result = await manager.async_configure(result["flow_id"], {
        "production_power_entity": "sensor.missing", "confirm_flow_semantics": True,
        "configure_flow_compatibility": True,
    })
    assert result["errors"]["production_power_entity"] == "invalid_flow_source"
    shown = form_values(result)
    assert shown["confirm_flow_semantics"] is True
    assert shown["configure_flow_compatibility"] is True
    assert "grid_export_power_entity" not in shown
    shown["production_power_entity"] = "sensor.production"
    result = await manager.async_configure(result["flow_id"], shown)
    assert result["step_id"] == "flow_compatibility"
    result = await manager.async_configure(result["flow_id"], {
        **form_values(result), "flow_generation_presence": "absent",
        "flow_storage_presence": "absent", "flow_compatibility_enabled": False,
        "production_power_phase_convention": "net_across_phases",
    })
    assert result["errors"] == {"flow_generation_presence": "contradictory_topology"}
    shown = form_values(result)
    assert shown["flow_compatibility_enabled"] is False
    assert shown["flow_storage_presence"] == "absent"
    shown["flow_generation_presence"] = "present"
    result = await manager.async_configure(result["flow_id"], shown)
    assert result["step_id"] == "init"
    assert result["errors"] == {"base": "invalid_grid_tariff"}
    assert dict(entry.options) == saved
    assert "configure_energy_flows" in result["data_schema"].schema
    assert not set((*FLOW_KEYS, *COMPATIBILITY_KEYS)) & result["data_schema"].schema.keys()
    shown = form_values(result)
    shown["grid_fee_high_start"] = "another-error"
    result = await manager.async_configure(result["flow_id"], shown)
    assert result["errors"] == {"base": "invalid_grid_tariff"}
    if cancel:
        manager.async_abort(result["flow_id"])
        assert dict(entry.options) == saved
        # A fresh attempt must not inherit the cancelled source draft.
        result = await manager.async_init(entry.entry_id)
        result = await manager.async_configure(result["flow_id"], form_values(result))
        assert result["data"]["grid_export_power_entity"] == "sensor.old_export"
        assert "production_power_entity" not in result["data"]
        return
    shown = form_values(result)
    shown["grid_fee_high_start"] = "08:00"
    result = await manager.async_configure(result["flow_id"], shown)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["production_power_entity"] == "sensor.production"
    assert result["data"]["grid_export_power_entity"] is None
    assert result["data"]["flow_storage_presence"] == "absent"
    assert result["data"]["flow_compatibility_enabled"] is False
    assert result["data"]["production_power_phase_convention"] == "net_across_phases"


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_source_error_keeps_follow_up_available(hass, profile):
    """A source conflict can still be corrected through the optional form."""
    entry, manager, result = await start(hass, profile, True)
    hass.config_entries.async_update_entry(entry, options={
        **entry.options, "production_power_entity": "sensor.old_power",
        "grid_export_power_entity": "sensor.old_power",
    })
    saved = dict(entry.options)
    submitted = {**form_values(result), "fixed_supplier_fee_monthly": 0}
    result = await manager.async_configure(result["flow_id"], submitted)
    assert result["errors"] == {"base": "invalid_flow_source"}
    assert dict(entry.options) == saved
    shown = form_values(result)
    assert shown["fixed_supplier_fee_monthly"] == 0
    shown["configure_energy_flows"] = True
    result = await manager.async_configure(result["flow_id"], shown)
    assert result["step_id"] == "energy_flows"
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["production_power_entity"] is None
    assert result["data"]["fixed_supplier_fee_monthly"] == 0
