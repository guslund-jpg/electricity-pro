"""Follow shared configuration sections in settings-focused tests."""

import probatio as vol

from custom_components.electricity_pro.measurement_config import (
    ADVANCED_MEASUREMENTS,
    MEASUREMENT_KEYS,
)
from custom_components.electricity_pro.market_config import MARKET_KEYS
from custom_components.electricity_pro.supplier_config import SUPPLIER_KEYS
from custom_components.electricity_pro.grid_config import GRID_KEYS, grid_mode
from custom_components.electricity_pro.production_config import PRODUCTION_KEYS
from custom_components.electricity_pro.flow_sources import FLOW_KEYS

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
    """Open the shared insight form through the Configure menu."""
    result = await manager.async_init(entry_id)
    return await manager.async_configure(
        result["flow_id"], {"next_step_id": "insights"}
    )


async def select_insight_method(manager, result, mode):
    """Reveal the chosen method's controls without saving the entry."""
    submitted = form_values(result)
    if mode == submitted["good_price_mode"]:
        return result
    return await manager.async_configure(
        result["flow_id"], {**submitted, "good_price_mode": mode}
    )


async def confirm_insights(manager, result, values=None):
    """Review a method change, then accept only its visible values."""
    values = values or {}
    previous_mode = form_values(result)["good_price_mode"]
    next_mode = values.get("good_price_mode", previous_mode)
    if next_mode != previous_mode:
        result = await select_insight_method(manager, result, next_mode)
        if result.get("errors"):
            return result
    submitted = form_values(result)
    fields = {marker.schema for marker in result["data_schema"].schema}
    for key, value in values.items():
        if key in fields:
            if value is None:
                submitted.pop(key, None)
            else:
                submitted[key] = value
    return await manager.async_configure(result["flow_id"], submitted)


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


async def start_grid(manager, entry_id):
    """Open grid charges through the section menu."""
    result = await manager.async_init(entry_id)
    return await manager.async_configure(result["flow_id"], {"next_step_id": "grid"})


async def start_production(manager, entry_id):
    """Open the dedicated optional-source section."""
    result = await manager.async_init(entry_id)
    return await manager.async_configure(
        result["flow_id"], {"next_step_id": "energy_flows"}
    )


async def open_production_sources(manager, result):
    """Reveal source fields if they are not already displayed."""
    if form_values(result)["configure_energy_flows"]:
        return result
    return await manager.async_configure(
        result["flow_id"], {"configure_energy_flows": True}
    )


async def confirm_production(manager, result, values=None):
    """Accept visible source suggestions, optionally changing or clearing them."""
    values = values or {}
    submitted = form_values(result)
    enabled = values.get(
        "configure_energy_flows",
        submitted["configure_energy_flows"]
        or any(values.get(key) for key in FLOW_KEYS),
    )
    if enabled != submitted["configure_energy_flows"]:
        result = await manager.async_configure(
            result["flow_id"], {**submitted, "configure_energy_flows": enabled}
        )
        if result.get("step_id") != "energy_flows":
            return result
        submitted = form_values(result)
    fields = {marker.schema for marker in result["data_schema"].schema}
    for key, value in values.items():
        if key in fields:
            if value is None:
                submitted.pop(key, None)
            else:
                submitted[key] = value
    return await manager.async_configure(result["flow_id"], submitted)


async def confirm_grid(manager, result, values=None):
    """Select the tariff, then submit the fields actually displayed for it."""
    values = values or {}
    submitted = form_values(result)
    mode = values.get("grid_mode", submitted["grid_mode"])
    if "grid_mode" not in values and mode == "unconfigured":
        mode = grid_mode(values)
    if mode != submitted["grid_mode"]:
        result = await manager.async_configure(
            result["flow_id"], {**submitted, "grid_mode": mode}
        )
        if result.get("step_id") != "grid":
            return result
        submitted = form_values(result)
    fields = {marker.schema for marker in result["data_schema"].schema}
    for key, value in values.items():
        if key not in fields:
            continue
        if value is None:
            submitted.pop(key, None)
        else:
            submitted[key] = value
    return await manager.async_configure(result["flow_id"], submitted)


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
    if result.get("step_id") in ("insights", "insights_adaptive"):
        return await confirm_insights(manager, result, values)
    if result.get("step_id") == "flow_compatibility":
        fields = {marker.schema for marker in result["data_schema"].schema}
        values = {key: value for key, value in values.items() if key in fields}
    if result.get("step_id") == "energy_flows":
        fields = {marker.schema for marker in result["data_schema"].schema}
        return await manager.async_configure(
            result["flow_id"],
            {
                "configure_energy_flows": form_values(result)["configure_energy_flows"],
                **{key: value for key, value in values.items() if key in fields},
            },
        )
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
        if result.get("step_id") != "grid":
            return result
    if result.get("step_id") == "grid":
        result = await confirm_grid(manager, result, values)
        if result.get("step_id") == "grid":
            return result
    if result.get("step_id") == "energy_flows":
        result = await confirm_production(manager, result, values)
        if result.get("step_id") in ("energy_flows", "flow_compatibility"):
            return result
    if result.get("step_id") in ("insights", "insights_adaptive"):
        return await confirm_insights(manager, result, values)
    if result.get("step_id") in ("init", "manual", "tibber_settings"):
        values = {
            key: value
            for key, value in values.items()
            if key
            not in (
                *MEASUREMENT_KEYS,
                *MARKET_KEYS,
                *SUPPLIER_KEYS,
                *GRID_KEYS,
                *PRODUCTION_KEYS,
                "configure_energy_flows",
                "confirm_flow_semantics",
                "grid_mode",
                "suggest_vat_rate",
                "estimate_supplier_markup",
            )
        }
    result = await manager.async_configure(result["flow_id"], values)
    if result.get("step_id") == "grid" and not result.get("errors"):
        result = await confirm_grid(manager, result)
    if result.get("step_id") == "energy_flows" and not result.get("errors"):
        result = await confirm_production(manager, result)
    if result.get("step_id") in ("insights", "insights_adaptive") and not result.get(
        "errors"
    ):
        return await confirm_insights(manager, result)
    if result.get("step_id") in ("manual", "tibber_settings") and not result.get(
        "errors"
    ):
        return await manager.async_configure(result["flow_id"], {})
    return result
