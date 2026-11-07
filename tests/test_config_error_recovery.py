"""Recover configuration errors without discarding form or follow-up choices."""

from math import isnan

import pytest
import probatio as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from tests.flow_helpers import (
    confirm_production,
    start_settings,
    configure_settings,
    confirm_measurements,
    confirm_market,
    confirm_supplier,
    confirm_grid,
)

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
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "power_entity": "sensor.old_power",
                "source_profile": profile,
                "adaptive_price_ceiling": 2.5,
            },
            options={"fixed_grid_fee_monthly": 600, "adaptive_price_ceiling": 2.2},
        )
        entry.add_to_hass(hass)
        return (
            entry,
            hass.config_entries.options,
            await start_settings(hass.config_entries.options, entry.entry_id),
        )
    if profile == "tibber":
        tibber = MockConfigEntry(domain="tibber")
        tibber.add_to_hass(hass)
        device = dr.async_get(hass).async_get_or_create(
            config_entry_id=tibber.entry_id,
            identifiers={("tibber", "home")},
        )
        for name in ("power", "electricity_price"):
            er.async_get(hass).async_get_or_create(
                "sensor",
                "tibber",
                name,
                device_id=device.id,
                translation_key=name,
            )
    manager = hass.config_entries.flow
    result = await manager.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await configure_settings(manager, result, {"setup_method": profile})
    result = await confirm_measurements(manager, result)
    result = await confirm_market(manager, result)
    result = await confirm_supplier(manager, result)
    result = await confirm_grid(manager, result)
    if result.get("step_id") == "energy_flows":
        result = await confirm_production(manager, result)
    return None, manager, result


@pytest.mark.parametrize("options", [False, True], ids=["setup", "options"])
@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_repeated_error_preserves_displayed_values(hass, profile, options):
    """Retry the displayed form, changing only the invalid field, then save."""
    entry, manager, result = await start(hass, profile, options)
    original_keys = set(result["data_schema"].schema)
    original_options = dict(entry.options) if entry else None
    original_data = dict(entry.data) if entry else None
    submitted = {
        **form_values(result),
        "good_price_mode": "adaptive",
        "adaptive_target_percentile": 37,
        "adaptive_price_ceiling": 1.7,
    }
    submitted["adaptive_price_ceiling"] = float("nan")
    result = await configure_settings(manager, result, submitted)
    assert result["errors"] == {"base": "invalid_good_price_settings"}
    assert set(result["data_schema"].schema) == original_keys
    shown = form_values(result)
    for key, value in submitted.items():
        if key == "adaptive_price_ceiling":
            assert isnan(shown[key])
        else:
            assert shown[key] == value
    if profile == "tibber":
        assert (
            not {"price_entity", "price_vat_rate", "supplier_markup_per_kwh"}
            & shown.keys()
        )
        if not options:
            assert result["description_placeholders"]["power_entity"]
    if entry:
        assert dict(entry.options) == original_options
        assert dict(entry.data) == original_data

    # Another error after clearing an optional field must not resurrect it.
    shown.pop("adaptive_price_ceiling", None)
    shown["adaptive_target_percentile"] = float("nan")
    result = await configure_settings(manager, result, shown)
    assert result["errors"] == {"base": "invalid_good_price_settings"}
    shown = form_values(result)
    assert "adaptive_price_ceiling" not in shown
    shown["adaptive_target_percentile"] = 37
    result = await configure_settings(manager, result, shown)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"].get("adaptive_price_ceiling") is None
    if entry:
        # Explicit None must override the original setup data, not fall back to it.
        assert (
            entry.options.get(
                "adaptive_price_ceiling", entry.data["adaptive_price_ceiling"]
            )
            is None
        )
    assert result["data"]["adaptive_target_percentile"] == 37


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_insight_save_does_not_validate_or_repair_other_sections(hass, profile):
    entry, manager, result = await start(hass, profile, True)
    saved = {
        **entry.options,
        "production_power_entity": "sensor.old_power",
        "grid_export_power_entity": "sensor.old_power",
        "flow_storage_presence": "present",
        "flow_compatibility_enabled": False,
        "household_energy_entity": None,
    }
    hass.config_entries.async_update_entry(entry, options=saved)
    fields = {marker.schema for marker in result["data_schema"].schema}
    assert not set((*FLOW_KEYS, *COMPATIBILITY_KEYS, "configure_energy_flows")) & fields
    result = await configure_settings(manager, result, form_values(result))
    assert result["type"] == FlowResultType.CREATE_ENTRY
    for key in (*FLOW_KEYS, *COMPATIBILITY_KEYS):
        if key in saved:
            assert result["data"][key] == saved[key]
