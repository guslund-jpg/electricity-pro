"""Follow the shared Measurements and options menu in settings-focused tests."""

import probatio as vol

from custom_components.electricity_pro.measurement_config import (
    ADVANCED_MEASUREMENTS,
    MEASUREMENT_KEYS,
)
from custom_components.electricity_pro.market_config import MARKET_KEYS


async def start_settings(manager, entry_id):
    """Open the existing prices/settings form through the Configure menu."""
    result = await manager.async_init(entry_id)
    return await manager.async_configure(
        result["flow_id"], {"next_step_id": "settings"}
    )


async def start_market(manager, entry_id):
    """Open the shared market section without saving another section."""
    result = await manager.async_init(entry_id)
    return await manager.async_configure(
        result["flow_id"], {"next_step_id": "market_prices"}
    )


async def confirm_market(manager, result, values=None):
    """Select a forecast source on its own screen in settings-focused tests."""
    values = values or {}
    shown = {
        marker.schema: (marker.description or {}).get("suggested_value")
        for marker in result["data_schema"].schema
    }
    result = await manager.async_configure(
        result["flow_id"],
        {
            key: values.get(key, shown.get(key))
            for key in MARKET_KEYS
            if key in shown and values.get(key, shown.get(key)) is not None
        },
    )
    if result.get("step_id") == "market_area" and values.get("forecast_price_area"):
        result = await manager.async_configure(
            result["flow_id"], {"forecast_price_area": values["forecast_price_area"]}
        )
    return result


async def confirm_measurements(manager, result, values=None):
    """Confirm the preceding meter selection for a test of a later screen."""
    values = values or {}
    shown = {}
    for marker in result["data_schema"].schema:
        suggestion = (marker.description or {}).get("suggested_value", vol.UNDEFINED)
        if suggestion is not vol.UNDEFINED and suggestion is not None:
            shown[marker.schema] = suggestion
    submitted = {
        "power_entity": values.get(
            "power_entity", shown.get("power_entity", "sensor.power")
        ),
    }
    if "energy_entity" in values or "energy_entity" in shown:
        submitted["energy_entity"] = values.get(
            "energy_entity", shown.get("energy_entity")
        )
    advanced = {key: values[key] for key in ADVANCED_MEASUREMENTS if key in values}
    if advanced:
        submitted["advanced_measurements"] = advanced
    result = await manager.async_configure(result["flow_id"], submitted)
    if result.get("step_id") == "measurement_energy":
        result = await manager.async_configure(
            result["flow_id"],
            {"energy_source_type": values.get("energy_source_type", "daily")},
        )
    return result


async def configure_settings(manager, result, values):
    """Submit moved measurement fields on their screen and settings on theirs."""
    if result.get("step_id") == "measurements":
        result = await confirm_measurements(manager, result, values)
        if result.get("step_id") == "measurements":
            return result
    if result.get("step_id") == "market_prices":
        result = await confirm_market(manager, result, values)
        if result.get("step_id") in ("market_prices", "market_area"):
            return result
        if result["type"] == "create_entry":
            return result
    if result.get("step_id") in ("init", "manual", "tibber_settings"):
        values = {
            key: value
            for key, value in values.items()
            if key not in (*MEASUREMENT_KEYS, *MARKET_KEYS)
        }
    return await manager.async_configure(result["flow_id"], values)
