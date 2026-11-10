"""Exercise shared Measurements screens through Home Assistant's flow manager."""

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN
from tests.flow_helpers import (
    confirm_review,
    confirm_supplier,
    confirm_grid,
    confirm_production,
)


def form_values(result):
    values = {}
    for marker in result["data_schema"].schema:
        description = marker.description or {}
        if description.get("suggested_value") is not None:
            values[marker.schema] = description["suggested_value"]
    return values


def add_tibber(hass, price=True):
    entry = MockConfigEntry(domain="tibber")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("tibber", "home")},
        name="My meter",
    )
    registry = er.async_get(hass)
    for key in ["power", "accumulated_consumption"] + (
        ["electricity_price"] if price else []
    ):
        registry.async_get_or_create(
            "sensor",
            "tibber",
            key,
            device_id=device.id,
            translation_key=key,
            suggested_object_id=f"test_{key}",
        )


async def start_setup(hass, profile):
    manager = hass.config_entries.flow
    result = await manager.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    return manager, await manager.async_configure(
        result["flow_id"], {"setup_method": profile}
    )


async def start_options(hass, profile="custom", **data):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"power_entity": "sensor.old_power", "source_profile": profile, **data},
        options={"fixed_grid_fee_monthly": 0, "supplier_markup_per_kwh": 0.119},
    )
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    menu = await manager.async_init(entry.entry_id)
    assert menu["type"] == FlowResultType.MENU
    assert list(menu["menu_options"]) == [
        "measurements",
        "market_prices",
        "supplier",
        "grid",
        *(["billed_demand_charge"] if data.get("energy_entity") else []),
        "energy_flows",
        "insights",
        "overview",
    ]
    result = await manager.async_configure(
        menu["flow_id"], {"next_step_id": "measurements"}
    )
    return entry, manager, result


async def test_custom_setup_moves_measurements_out_of_remaining_settings(hass):
    manager, result = await start_setup(hass, "custom")
    assert result["step_id"] == "measurements"
    assert {key.schema for key in result["data_schema"].schema} == {
        "power_entity",
        "energy_entity",
        "advanced_measurements",
    }
    result = await manager.async_configure(
        result["flow_id"], {"power_entity": "sensor.power"}
    )
    assert result["step_id"] == "market_prices"
    result = await manager.async_configure(result["flow_id"], {})
    assert result["step_id"] == "supplier"
    result = await confirm_supplier(manager, result)
    result = await confirm_grid(manager, result)
    if result.get("step_id") == "energy_flows":
        result = await confirm_production(manager, result)
    assert result["step_id"] == "insights"
    assert "power_entity" not in {key.schema for key in result["data_schema"].schema}
    result = await manager.async_configure(result["flow_id"], {})
    result = await confirm_review(manager, result)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["power_entity"] == "sensor.power"


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize("price", [False, True])
async def test_supported_meter_suggestions_do_not_require_supplier_price(
    hass, profile, price
):
    add_tibber(hass, price)
    manager, result = await start_setup(hass, profile)
    assert result["step_id"] == "measurements"
    values = form_values(result)
    assert values["power_entity"] == "sensor.test_power"
    assert values["energy_entity"] == "sensor.test_accumulated_consumption"
    assert "My meter" in result["description_placeholders"]["sources"]
    result = await manager.async_configure(result["flow_id"], values)
    assert result["step_id"] == "market_prices"
    result = await manager.async_configure(result["flow_id"], {})
    result = await confirm_supplier(manager, result)
    result = await confirm_grid(manager, result)
    if result.get("step_id") == "energy_flows":
        result = await confirm_production(manager, result)
    assert result["step_id"] == "insights"
    result = await manager.async_configure(result["flow_id"], {})
    result = await confirm_review(manager, result)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["energy_source_type"] == "daily"


async def test_unknown_energy_period_is_confirmed_after_source_selection(hass):
    manager, result = await start_setup(hass, "custom")
    result = await manager.async_configure(
        result["flow_id"],
        {"power_entity": "sensor.power", "energy_entity": "sensor.energy"},
    )
    assert result["step_id"] == "measurement_energy"
    result = await manager.async_configure(
        result["flow_id"], {"energy_source_type": "lifetime"}
    )
    assert result["step_id"] == "market_prices"
    result = await manager.async_configure(result["flow_id"], {})
    result = await confirm_supplier(manager, result)
    result = await confirm_grid(manager, result)
    if result.get("step_id") == "energy_flows":
        result = await confirm_production(manager, result)
    result = await manager.async_configure(result["flow_id"], {})
    result = await confirm_review(manager, result)
    assert result["data"]["energy_entity"] == "sensor.energy"
    assert result["data"]["energy_source_type"] == "lifetime"


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_measurement_save_keeps_unrelated_settings_and_explicit_zero(
    hass, profile
):
    entry, manager, result = await start_options(
        hass,
        profile,
        energy_entity="sensor.energy",
        energy_source_type="lifetime",
        price_entity="sensor.price",
        production_energy_entity="sensor.production",
        current_l1_entity="sensor.phase_one",
    )
    result = await manager.async_configure(
        result["flow_id"],
        {
            "power_entity": "sensor.new_power",
            "energy_entity": "sensor.energy",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    saved = {**entry.data, **result["data"]}
    assert saved["power_entity"] == "sensor.new_power"
    assert saved["energy_source_type"] == "lifetime"
    assert saved["fixed_grid_fee_monthly"] == 0
    assert saved["supplier_markup_per_kwh"] == 0.119
    assert saved["price_entity"] == "sensor.price"
    assert saved["production_energy_entity"] == "sensor.production"
    assert saved["current_l1_entity"] == "sensor.phase_one"


async def test_measurement_clears_override_old_data_and_cancel_is_atomic(hass):
    entry, manager, result = await start_options(
        hass, energy_entity="sensor.energy", current_l1_entity="sensor.phase_one"
    )
    previous = dict(entry.options)
    result = await manager.async_configure(
        result["flow_id"],
        {"power_entity": "sensor.power", "energy_entity": "sensor.other_energy"},
    )
    assert result["step_id"] == "measurement_energy"
    assert dict(entry.options) == previous
    manager.async_abort(result["flow_id"])
    assert dict(entry.options) == previous
    result = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "measurements"}
    )
    result = await manager.async_configure(
        result["flow_id"], {"power_entity": "sensor.power", "advanced_measurements": {}}
    )
    assert result["data"]["energy_entity"] is None
    assert result["data"]["current_l1_entity"] is None


async def test_measurement_rejects_own_outputs_and_wrong_units(hass):
    entry, manager, result = await start_options(hass)
    own = er.async_get(hass).async_get_or_create("sensor", DOMAIN, "own")
    result = await manager.async_configure(
        result["flow_id"], {"power_entity": own.entity_id}
    )
    assert result["errors"]["power_entity"] == "electricity_pro_source"
    hass.states.async_set("sensor.wrong", "12", {"unit_of_measurement": "kWh"})
    result = await manager.async_configure(
        result["flow_id"], {"power_entity": "sensor.wrong"}
    )
    assert result["errors"]["power_entity"] == "invalid_measurement_source"
    assert "power_entity" not in entry.options


async def test_measurement_cannot_reuse_optional_flow_source(hass):
    _, manager, result = await start_options(
        hass, production_power_entity="sensor.production"
    )
    result = await manager.async_configure(
        result["flow_id"], {"power_entity": "sensor.production"}
    )
    assert result["errors"]["power_entity"] == "invalid_flow_source"


async def test_loaded_entry_keeps_readings_totals_and_registry_on_measurement_save(
    hass, setup_electricity_pro
):
    entry = await setup_electricity_pro(
        energy_value="3.5",
        price_value="1.2",
        accumulated_cost_today_value="4.2",
        energy_source_type="daily",
    )
    ids = [
        "sensor.electricity_pro_current_power",
        "sensor.electricity_pro_energy_today",
        "sensor.electricity_pro_cost_today",
    ]
    before = {entity_id: hass.states.get(entity_id).state for entity_id in ids}
    registry = er.async_get(hass)
    identities = {entity_id: registry.async_get(entity_id).id for entity_id in ids}
    manager = hass.config_entries.options
    result = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "measurements"}
    )
    result = await manager.async_configure(
        result["flow_id"],
        {
            "power_entity": "sensor.test_power",
            "energy_entity": "sensor.test_energy",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert {entity_id: hass.states.get(entity_id).state for entity_id in ids} == before
    assert {
        entity_id: registry.async_get(entity_id).id for entity_id in ids
    } == identities


async def test_advanced_energy_period_can_be_corrected_without_changing_source(hass):
    _, manager, result = await start_options(hass, energy_entity="sensor.energy")
    result = await manager.async_configure(
        result["flow_id"],
        {
            "power_entity": "sensor.old_power",
            "energy_entity": "sensor.energy",
            "advanced_measurements": {"energy_source_type": "lifetime"},
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["energy_source_type"] == "lifetime"


async def test_generic_energy_sensor_without_device_class_is_selectable(hass):
    hass.states.async_set("sensor.generic_energy", "12", {"unit_of_measurement": "kWh"})
    manager, result = await start_setup(hass, "custom")
    energy_selector = next(
        value
        for key, value in result["data_schema"].schema.items()
        if key.schema == "energy_entity"
    )
    assert "device_class" not in energy_selector.config
    result = await manager.async_configure(
        result["flow_id"],
        {"power_entity": "sensor.power", "energy_entity": "sensor.generic_energy"},
    )
    assert result["step_id"] == "measurement_energy"


async def test_legacy_invalid_energy_period_keeps_its_effective_daily_semantics(hass):
    _, manager, result = await start_options(
        hass, energy_entity="sensor.energy", energy_source_type="legacy_unknown"
    )
    result = await manager.async_configure(
        result["flow_id"],
        {
            "power_entity": "sensor.old_power",
            "energy_entity": "sensor.energy",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["energy_source_type"] == "daily"


async def test_temporarily_unavailable_existing_sources_can_be_retained(hass):
    hass.states.async_set("sensor.old_power", "unavailable")
    hass.states.async_set("sensor.energy", "unavailable")
    _, manager, result = await start_options(
        hass, energy_entity="sensor.energy", energy_source_type="lifetime"
    )
    result = await manager.async_configure(
        result["flow_id"],
        {"power_entity": "sensor.old_power", "energy_entity": "sensor.energy"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["energy_source_type"] == "lifetime"
