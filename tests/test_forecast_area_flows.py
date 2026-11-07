"""Characterize Nord Pool area selection through setup and options flows."""

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from tests.flow_helpers import (
    confirm_production,
    start_market,
    start_supplier,
    confirm_supplier,
    confirm_grid,
    configure_settings,
    confirm_measurements,
)

from custom_components.electricity_pro.const import DOMAIN


async def start_flow(hass, profile, options, data=None, saved_options=None):
    """Enter the real flow manager with a minimal custom or discovered home."""
    if options:
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "power_entity": "sensor.power",
                "source_profile": profile,
                "fixed_grid_fee_monthly": 0,
                **(data or {}),
            },
            options=saved_options or {},
        )
        entry.add_to_hass(hass)
        manager = hass.config_entries.options
        return entry, manager, await start_market(manager, entry.entry_id)
    if profile == "tibber":
        tibber = MockConfigEntry(domain="tibber")
        tibber.add_to_hass(hass)
        device = dr.async_get(hass).async_get_or_create(
            config_entry_id=tibber.entry_id,
            identifiers={("tibber", "home")},
        )
        for key in ("power", "electricity_price"):
            er.async_get(hass).async_get_or_create(
                "sensor", "tibber", key, device_id=device.id, translation_key=key
            )
    manager = hass.config_entries.flow
    result = await manager.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await configure_settings(manager, result, {"setup_method": profile})
    result = await confirm_measurements(manager, result)
    return None, manager, result


async def submit(manager, result, values):
    """Select market inputs on their own screen before the pricing forms."""
    result = await manager.async_configure(
        result["flow_id"],
        {
            key: value
            for key, value in values.items()
            if key in ("forecast_nordpool_config_entry", "forecast_price_area")
            and value is not None
        },
    )
    return result


async def finish_setup(manager, result):
    if result.get("step_id") in ("supplier", "supplier_tibber"):
        result = await confirm_supplier(
            manager, result, {"price_vat_rate": 25, "supplier_markup_per_kwh": 0}
        )
    if result.get("step_id") == "grid":
        result = await confirm_grid(manager, result, {"fixed_grid_fee_monthly": 0})
        if result.get("step_id") == "energy_flows":
            result = await confirm_production(manager, result)
    if result.get("step_id") in ("insights", "insights_adaptive"):
        result = await manager.async_configure(result["flow_id"], {})
    return result


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize("options", [False, True], ids=["setup", "options"])
@pytest.mark.parametrize(
    "areas",
    [["SE3", "SE4"], ["SE3"], [], None, "SE3"],
    ids=["multiple", "single", "empty", "null", "not-list"],
)
async def test_area_prompt_depends_on_source_metadata(hass, profile, options, areas):
    """Ask only for a multi-area list and preserve the pending settings."""
    nordpool = MockConfigEntry(
        domain="nordpool", data={"areas": areas, "currency": "SEK"}
    )
    nordpool.add_to_hass(hass)
    entry, manager, result = await start_flow(hass, profile, options)
    submitted = {
        "power_entity": "sensor.power",
        "forecast_nordpool_config_entry": nordpool.entry_id,
        "fixed_grid_fee_monthly": 0,
    }
    result = await submit(manager, result, submitted)
    if areas == ["SE3", "SE4"]:
        assert result["step_id"] == "market_area"
        selector = next(iter(result["data_schema"].schema.values()))
        assert selector.config["options"] == ["SE3", "SE4"]
        if entry:
            assert entry.options == {}
        result = await manager.async_configure(
            result["flow_id"], {"forecast_price_area": "SE4"}
        )
    elif areas != ["SE3"]:
        assert result["errors"] == {
            "forecast_nordpool_config_entry": "invalid_market_source"
        }
        assert not entry or not entry.options
        manager.async_abort(result["flow_id"])
        return
    result = await finish_setup(manager, result) if not options else result
    if areas == ["SE3", "SE4"]:
        assert result["data"]["forecast_price_area"] == "SE4"
    if areas == ["SE3"]:
        assert not result["data"].get("forecast_price_area")
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["forecast_nordpool_config_entry"] == nordpool.entry_id
    assert (entry.options if entry else result["data"]).get(
        "fixed_grid_fee_monthly", 0
    ) == 0


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize(
    ("saved_options", "switch_entry", "prompt"),
    [
        ({}, False, False),
        ({"forecast_price_area": "SE3"}, False, False),
        ({"forecast_price_area": None}, False, True),
        ({"forecast_price_area": "FI"}, False, True),
        ({}, True, True),
    ],
    ids=["data", "options", "cleared", "invalid", "changed-source"],
)
async def test_options_reuse_area_only_for_same_source(
    hass, profile, saved_options, switch_entry, prompt
):
    """Respect saved precedence, explicit clearing and a changed forecast entry."""
    nordpool = MockConfigEntry(
        domain="nordpool", data={"areas": ["SE3", "SE4"], "currency": "SEK"}
    )
    nordpool.add_to_hass(hass)
    entry, manager, result = await start_flow(
        hass,
        profile,
        True,
        data={
            "forecast_nordpool_config_entry": "old-entry"
            if switch_entry
            else nordpool.entry_id,
            "forecast_price_area": "SE4",
        },
        saved_options=saved_options,
    )
    original_data, original_options = dict(entry.data), dict(entry.options)
    result = await submit(
        manager,
        result,
        {
            "power_entity": "sensor.power",
            "forecast_nordpool_config_entry": nordpool.entry_id,
        },
    )
    if prompt:
        assert result["step_id"] == "market_area"
        assert dict(entry.data) == original_data
        assert dict(entry.options) == original_options
        manager.async_abort(result["flow_id"])
        assert dict(entry.options) == original_options
        result = await start_market(manager, entry.entry_id)
        result = await submit(
            manager,
            result,
            {
                "power_entity": "sensor.power",
                "forecast_nordpool_config_entry": nordpool.entry_id,
            },
        )
        assert result["step_id"] == "market_area"
        result = await manager.async_configure(
            result["flow_id"], {"forecast_price_area": "SE3"}
        )
        assert result["data"]["forecast_price_area"] == "SE3"
    else:
        assert result["data"]["forecast_price_area"] == saved_options.get(
            "forecast_price_area", "SE4"
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert dict(entry.data) == original_data


async def test_custom_options_keep_area_override_across_repeated_saves(hass):
    """An unrelated save must keep the user's area instead of reverting to setup."""
    nordpool = MockConfigEntry(
        domain="nordpool", data={"areas": ["SE3", "SE4"], "currency": "SEK"}
    )
    nordpool.add_to_hass(hass)
    entry, manager, result = await start_flow(
        hass,
        "custom",
        True,
        data={
            "forecast_nordpool_config_entry": nordpool.entry_id,
            "forecast_price_area": "SE4",
        },
        saved_options={"forecast_price_area": "SE3"},
    )
    manager.async_abort(result["flow_id"])
    for fee in (49, 60):
        result = await start_supplier(manager, entry.entry_id)
        result = await configure_settings(
            manager,
            result,
            {
                "power_entity": "sensor.power",
                "forecast_nordpool_config_entry": nordpool.entry_id,
                "fixed_supplier_fee_monthly": fee,
            },
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert entry.options["forecast_price_area"] == "SE3"
        assert entry.options["fixed_supplier_fee_monthly"] == fee
        assert entry.data["forecast_price_area"] == "SE4"


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_options_omitted_forecast_binding(hass, profile):
    """Clearing the market screen disables either track without resurrecting data."""
    entry, manager, result = await start_flow(
        hass,
        profile,
        True,
        data={"forecast_nordpool_config_entry": "old", "forecast_price_area": "SE4"},
    )
    result = await submit(
        manager,
        result,
        {"power_entity": "sensor.power", "forecast_nordpool_config_entry": None},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    expected = None
    assert result["data"]["forecast_nordpool_config_entry"] == expected
    assert result["data"]["forecast_price_area"] is None
    assert entry.options["forecast_nordpool_config_entry"] == expected
