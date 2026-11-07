"""Follow shared configuration sections in settings-focused tests."""

import probatio as vol

from custom_components.electricity_pro.measurement_config import (
    ADVANCED_MEASUREMENTS,
    MEASUREMENT_KEYS,
)
from custom_components.electricity_pro.market_config import MARKET_KEYS
from custom_components.electricity_pro.supplier_config import SUPPLIER_KEYS

TIBBER_CONTRACT = {
    "price_entity": "sensor.price",
    "pricing_strategy": "supplier_contracted_price",
    "price_included_components": ["market_energy", "supplier_markup"],
    "price_vat_treatment": "included",
    "price_completeness": "partial",
}


def form_values(result):
    """Model accepting the visible suggestions and defaults."""
    values = {}
    for marker in result["data_schema"].schema:
        default = marker.default() if callable(marker.default) else vol.UNDEFINED
        value = (marker.description or {}).get("suggested_value", default)
        if value is not vol.UNDEFINED and value is not None:
            values[marker.schema] = value
    return values


async def start_settings(manager, entry_id):
    """Open the remaining grid/insight form through the Configure menu."""
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


async def start_supplier(manager, entry_id):
    """Open the supplier section without editing a different section."""
    result = await manager.async_init(entry_id)
    return await manager.async_configure(
        result["flow_id"], {"next_step_id": "supplier"}
    )


async def confirm_supplier(manager, result, values=None):
    """Accept displayed supplier values, optionally changing or clearing some."""
    submitted = form_values(result)
    fields = {marker.schema for marker in result["data_schema"].schema}
    for key, value in (values or {}).items():
        if key not in fields:
            continue
        if value is None:
            submitted.pop(key, None)
        else:
            submitted[key] = value
    return await manager.async_configure(result["flow_id"], submitted)


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
    if result.get("step_id") in ("supplier", "supplier_tibber"):
        result = await confirm_supplier(manager, result, values)
        if result.get("step_id") not in ("init", "manual", "tibber_settings"):
            return result
    if result.get("step_id") in ("init", "manual", "tibber_settings"):
        values = {
            key: value
            for key, value in values.items()
            if key
            not in (
                *MEASUREMENT_KEYS,
                *MARKET_KEYS,
                *SUPPLIER_KEYS,
                "suggest_vat_rate",
                "estimate_supplier_markup",
            )
        }
    result = await manager.async_configure(result["flow_id"], values)
    if result.get("step_id") in ("manual", "tibber_settings") and not result.get(
        "errors"
    ):
        return await manager.async_configure(result["flow_id"], {})
    return result
