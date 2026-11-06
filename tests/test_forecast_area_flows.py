"""Characterize Nord Pool area selection through setup and options flows."""

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN


async def start_flow(hass, profile, options, data=None, saved_options=None):
    """Enter the real flow manager with a minimal custom or discovered home."""
    if options:
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "power_entity": "sensor.power",
                "source_profile": profile,
                **(data or {}),
            },
            options=saved_options or {},
        )
        entry.add_to_hass(hass)
        manager = hass.config_entries.options
        return entry, manager, await manager.async_init(entry.entry_id)
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
    result = await manager.async_configure(result["flow_id"], {"setup_method": profile})
    return None, manager, result


async def submit(manager, result, values):
    """Confirm Tibber pricing when offered before the area decision."""
    fields = {key.schema for key in result["data_schema"].schema}
    values = {
        key: value
        for key, value in {"price_vat_rate": 25, **values}.items()
        if key in fields and value is not None
    }
    result = await manager.async_configure(result["flow_id"], values)
    if result.get("step_id") == "tibber_forecast_pricing":
        result = await manager.async_configure(
            result["flow_id"], {"price_vat_rate": 25, "supplier_markup_per_kwh": 0}
        )
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
    nordpool = MockConfigEntry(domain="nordpool", data={"areas": areas})
    nordpool.add_to_hass(hass)
    entry, manager, result = await start_flow(hass, profile, options)
    submitted = {
        "power_entity": "sensor.power",
        "forecast_nordpool_config_entry": nordpool.entry_id,
        "fixed_grid_fee_monthly": 0,
    }
    result = await submit(manager, result, submitted)
    if areas == ["SE3", "SE4"]:
        assert result["step_id"] == "forecast_area"
        selector = next(iter(result["data_schema"].schema.values()))
        assert selector.config["options"] == ["SE3", "SE4"]
        if entry:
            assert entry.options == {}
        result = await manager.async_configure(
            result["flow_id"], {"forecast_price_area": "SE4"}
        )
        assert result["data"]["forecast_price_area"] == "SE4"
    else:
        assert "forecast_price_area" not in result["data"]
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["forecast_nordpool_config_entry"] == nordpool.entry_id
    assert result["data"]["fixed_grid_fee_monthly"] == 0


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
    nordpool = MockConfigEntry(domain="nordpool", data={"areas": ["SE3", "SE4"]})
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
        assert result["step_id"] == "forecast_area"
        assert dict(entry.data) == original_data
        assert dict(entry.options) == original_options
        manager.async_abort(result["flow_id"])
        assert dict(entry.options) == original_options
        result = await manager.async_init(entry.entry_id)
        result = await submit(
            manager,
            result,
            {
                "power_entity": "sensor.power",
                "forecast_nordpool_config_entry": nordpool.entry_id,
            },
        )
        assert result["step_id"] == "forecast_area"
        result = await manager.async_configure(
            result["flow_id"], {"forecast_price_area": "SE3"}
        )
        assert result["data"]["forecast_price_area"] == "SE3"
    else:
        # Preserve the existing path-specific options payloads in this refactor.
        if profile == "tibber":
            assert result["data"]["forecast_price_area"] == saved_options.get(
                "forecast_price_area", "SE4"
            )
        else:
            assert "forecast_price_area" not in result["data"]
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert dict(entry.data) == original_data


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_options_omitted_forecast_binding(hass, profile):
    """Preserve each track's existing default/clear behaviour for omitted input."""
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
    expected = "old" if profile == "custom" else None
    assert result["data"]["forecast_nordpool_config_entry"] == expected
    assert "forecast_price_area" not in result["data"]
    assert entry.options["forecast_nordpool_config_entry"] == expected
