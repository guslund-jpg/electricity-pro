"""Supplier section boundaries through Home Assistant's real flow manager."""

import pytest
from homeassistant import config_entries
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from tests.flow_helpers import (
    confirm_production,
    confirm_grid,
    start_grid,
    TIBBER_CONTRACT,
    confirm_market,
    confirm_measurements,
    confirm_supplier,
    form_values,
    start_supplier,
)

DOMAIN = "electricity_pro"
MARKET = "forecast_nordpool_config_entry"


async def start_setup(hass, profile, forecast=False, contract=True):
    if forecast:
        native = MockConfigEntry(
            domain="nordpool", data={"areas": ["SE3"], "currency": "SEK"}
        )
        native.add_to_hass(hass)
    if profile == "tibber":
        tibber = MockConfigEntry(domain="tibber")
        tibber.add_to_hass(hass)
        device = dr.async_get(hass).async_get_or_create(
            config_entry_id=tibber.entry_id, identifiers={("tibber", "home")}
        )
        for key in ["power", "accumulated_cost"] + (
            ["electricity_price"] if contract else []
        ):
            er.async_get(hass).async_get_or_create(
                "sensor",
                "tibber",
                key,
                device_id=device.id,
                translation_key=key,
                suggested_object_id=f"tibber_{key}",
            )
    manager = hass.config_entries.flow
    result = await manager.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await manager.async_configure(result["flow_id"], {"setup_method": profile})
    result = await confirm_measurements(manager, result)
    result = await confirm_market(manager, result)
    return manager, result


async def open_supplier(hass, profile="custom", data=None, options=None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "source_profile": profile,
            "power_entity": "sensor.power",
            **(TIBBER_CONTRACT if profile == "tibber" else {}),
            **(data or {}),
        },
        options=options or {},
    )
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    result = await start_supplier(manager, entry.entry_id)
    return entry, manager, result


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize("forecast", [False, True])
async def test_setup_reviews_supplier_before_grid_without_redeclaring_tibber(
    hass, freezer, profile, forecast
):
    freezer.move_to("2026-11-07T12:00:00Z")
    manager, result = await start_setup(hass, profile, forecast)
    assert result["step_id"] == (
        "supplier_tibber" if profile == "tibber" else "supplier"
    )
    fields = {key.schema for key in result["data_schema"].schema}
    assert (
        not {
            "power_entity",
            MARKET,
            "grid_fee_per_kwh",
            "energy_tax_per_kwh",
            "good_price_mode",
        }
        & fields
    )
    if profile == "tibber":
        assert (
            not {
                "price_entity",
                "pricing_strategy",
                "price_included_components",
                "price_vat_treatment",
            }
            & fields
        )
        assert bool("estimate_supplier_markup" in fields) == forecast
        assert (
            "sensor.tibber_electricity_price"
            in result["description_placeholders"]["price_source"]
        )
    if forecast:
        assert form_values(result)["price_vat_rate"] == 25
    elif profile == "tibber":
        assert fields == {"fixed_supplier_fee_monthly"}
    result = await confirm_supplier(manager, result, {"fixed_supplier_fee_monthly": 0})
    assert result["step_id"] == "grid"
    result = await confirm_grid(manager, result)
    if result.get("step_id") == "energy_flows":
        result = await confirm_production(manager, result)
    assert result["step_id"] == ("tibber_settings" if profile == "tibber" else "manual")
    fields = {key.schema for key in result["data_schema"].schema}
    assert (
        not {
            "price_entity",
            "price_vat_rate",
            "supplier_markup_per_kwh",
            "fixed_supplier_fee_monthly",
        }
        & fields
    )
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    assert result["data"]["fixed_supplier_fee_monthly"] == 0
    if forecast:
        assert result["data"]["price_vat_rate"] == 25
    if profile == "tibber":
        assert result["data"]["price_vat_treatment"] == "included"
        assert result["data"]["price_included_components"] == [
            "market_energy",
            "supplier_markup",
        ]


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_supplier_save_preserves_other_sections_and_explicit_zero(hass, profile):
    data = {
        "grid_fee_per_kwh": 0.5,
        "energy_tax_per_kwh": 0.4,
        "energy_entity": "sensor.energy",
        "energy_source_type": "lifetime",
        "production_power_entity": "sensor.production",
        "good_price_threshold": 1.5,
        MARKET: None,
        "forecast_price_area": None,
        "supplier_markup_per_kwh": 0.119,
        "price_vat_rate": 0,
        "accumulated_cost_today_entity": "sensor.cost",
        "fixed_supplier_fee_monthly": 49,
    }
    options = {"fixed_grid_fee_monthly": 0, "good_price_mode": "adaptive"}
    entry, manager, result = await open_supplier(hass, profile, data, options)
    result = await confirm_supplier(manager, result, {"fixed_supplier_fee_monthly": 0})
    assert result["type"] == "create_entry"
    assert entry.options["fixed_supplier_fee_monthly"] == 0
    assert entry.options["price_vat_rate"] == 0
    assert entry.options["supplier_markup_per_kwh"] == 0.119
    assert entry.options["accumulated_cost_today_entity"] == "sensor.cost"
    assert entry.options["fixed_grid_fee_monthly"] == 0
    assert entry.options["good_price_mode"] == "adaptive"
    assert "grid_fee_per_kwh" not in entry.options
    assert entry.data["energy_entity"] == "sensor.energy"
    assert entry.data["production_power_entity"] == "sensor.production"
    # Saving the remaining section must not overwrite supplier-owned bindings.
    result = await start_grid(manager, entry.entry_id)
    result = await confirm_grid(manager, result, {"grid_fee_per_kwh": 0.6})
    if result.get("step_id") == "energy_flows":
        result = await confirm_production(manager, result)
    assert result["type"] == "create_entry"
    assert entry.options["fixed_supplier_fee_monthly"] == 0
    assert entry.options["price_vat_rate"] == 0
    assert entry.options["supplier_markup_per_kwh"] == 0.119


async def test_cleared_price_and_cost_override_original_data(hass):
    data = {
        **TIBBER_CONTRACT,
        "accumulated_cost_today_entity": "sensor.cost",
        "price_vat_rate": 0,
        "supplier_markup_per_kwh": 0.119,
        "fixed_supplier_fee_monthly": 49,
    }
    entry, manager, result = await open_supplier(hass, data=data)
    result = await confirm_supplier(
        manager,
        result,
        {
            "price_entity": None,
            "accumulated_cost_today_entity": None,
            "fixed_supplier_fee_monthly": None,
            "supplier_markup_per_kwh": None,
        },
    )
    assert result["type"] == "create_entry"
    for key in (
        "price_entity",
        "accumulated_cost_today_entity",
        "pricing_strategy",
        "price_included_components",
        "price_vat_treatment",
        "price_completeness",
        "fixed_supplier_fee_monthly",
        "supplier_markup_per_kwh",
    ):
        assert key in entry.options and entry.options[key] is None
    result = await start_supplier(manager, entry.entry_id)
    assert "price_entity" not in form_values(result)
    assert "accumulated_cost_today_entity" not in form_values(result)


@pytest.mark.parametrize("forecast", [False, True])
async def test_tibber_hidden_forecast_values_and_current_price_are_preserved(
    hass, forecast
):
    source = None
    if forecast:
        native = MockConfigEntry(
            domain="nordpool", data={"areas": ["FI"], "currency": "EUR"}
        )
        native.add_to_hass(hass)
        source = native.entry_id
    entry, manager, result = await open_supplier(
        hass,
        "tibber",
        {
            MARKET: source,
            "supplier_markup_per_kwh": 0,
            "price_vat_rate": 0,
        },
    )
    fields = {key.schema for key in result["data_schema"].schema}
    assert ("price_vat_rate" in fields) == forecast
    result = await confirm_supplier(manager, result)
    assert entry.options["price_vat_rate"] == 0
    assert entry.options["supplier_markup_per_kwh"] == 0
    assert entry.options["price_entity"] == "sensor.price"
    assert entry.options["price_vat_treatment"] == "included"


async def test_price_errors_retain_edits_and_cancel_does_not_save(hass):
    entry, manager, result = await open_supplier(hass)
    result = await confirm_supplier(
        manager,
        result,
        {
            "price_entity": "sensor.price",
            "pricing_strategy": "market_price_plus_tariff",
            "price_included_components": [],
            "price_vat_treatment": "excluded",
            "price_vat_rate": 0,
            "fixed_supplier_fee_monthly": 49,
            "supplier_markup_per_kwh": 0.119,
        },
    )
    assert result["errors"] == {"base": "pricing_metadata_required"}
    assert form_values(result)["fixed_supplier_fee_monthly"] == 49
    assert not entry.options
    manager.async_abort(result["flow_id"])
    result = await start_supplier(manager, entry.entry_id)
    assert "price_entity" not in form_values(result)
    result = await confirm_supplier(
        manager,
        result,
        {
            "price_entity": "sensor.price",
            "pricing_strategy": "market_price_plus_tariff",
            "price_included_components": [],
            "price_vat_treatment": "excluded",
            "price_vat_rate": 0,
            "fixed_supplier_fee_monthly": 49,
        },
    )
    result = await confirm_supplier(
        manager, result, {"price_included_components": ["market_energy"]}
    )
    assert result["type"] == "create_entry"
    assert entry.options["fixed_supplier_fee_monthly"] == 49
    assert entry.options["price_completeness"] == "partial"


@pytest.mark.parametrize("field", ["price_entity", "accumulated_cost_today_entity"])
async def test_integration_outputs_cannot_be_supplier_sources(hass, field):
    entry, manager, result = await open_supplier(hass)
    # Registry changes while the form is open must not bypass save-time validation.
    own = er.async_get(hass).async_get_or_create("sensor", DOMAIN, "own")
    result = await confirm_supplier(manager, result, {field: own.entity_id})
    assert result["errors"][field] == "electricity_pro_source"
    assert not entry.options


@pytest.mark.parametrize(
    "field", ["price_vat_rate", "supplier_markup_per_kwh", "fixed_supplier_fee_monthly"]
)
async def test_nonfinite_amount_is_rejected_without_saving(hass, field):
    entry, manager, result = await open_supplier(hass)
    result = await confirm_supplier(manager, result, {field: float("nan")})
    assert result["errors"][field] == "invalid_supplier_amount"
    assert not entry.options


async def test_incomplete_tibber_declarations_can_be_repaired(hass):
    entry, manager, result = await open_supplier(
        hass, "tibber", {"price_included_components": None}
    )
    assert result["step_id"] == "supplier"
    result = await confirm_supplier(
        manager,
        result,
        {"price_included_components": ["market_energy", "supplier_markup"]},
    )
    assert result["type"] == "create_entry"
    assert entry.options["price_vat_treatment"] == "included"


async def test_changed_provider_does_not_hide_live_price_declarations(hass):
    external = er.async_get(hass).async_get_or_create("sensor", "nordpool", "price")
    entry, manager, result = await open_supplier(
        hass, "tibber", {"price_entity": external.entity_id}
    )
    assert result["step_id"] == "supplier"
    assert "price_entity" in form_values(result)
    result = await confirm_supplier(
        manager,
        result,
        {
            "pricing_strategy": "market_price_plus_tariff",
            "price_included_components": ["market_energy"],
            "price_vat_treatment": "excluded",
            "price_vat_rate": 0,
        },
    )
    assert result["type"] == "create_entry"
    assert entry.options["price_vat_treatment"] == "excluded"


async def test_supplier_reload_preserves_live_prices_totals_and_registry(
    hass, setup_electricity_pro
):
    entry = await setup_electricity_pro(
        energy_value="3.5", price_value="1.2", accumulated_cost_today_value="4.2"
    )
    ids = [
        "sensor.electricity_pro_current_power",
        "sensor.electricity_pro_current_price",
        "sensor.electricity_pro_current_supplier_price",
        "sensor.electricity_pro_energy_today",
        "sensor.electricity_pro_cost_today",
    ]
    before = {entity_id: hass.states.get(entity_id).state for entity_id in ids}
    registry = er.async_get(hass)
    identities = {entity_id: registry.async_get(entity_id).id for entity_id in ids}
    manager = hass.config_entries.options
    result = await start_supplier(manager, entry.entry_id)
    result = await confirm_supplier(manager, result)
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert {entity_id: hass.states.get(entity_id).state for entity_id in ids} == before
    assert {
        entity_id: registry.async_get(entity_id).id for entity_id in ids
    } == identities


async def test_meter_only_tibber_uses_explicit_custom_supplier_inputs(hass):
    manager, result = await start_setup(hass, "tibber", contract=False)
    assert result["step_id"] == "supplier"
    assert "accumulated_cost_today_entity" not in form_values(result)
    result = await confirm_supplier(
        manager,
        result,
        {
            "price_entity": "sensor.other_supplier",
            "pricing_strategy": "supplier_contracted_price",
            "price_included_components": ["market_energy", "supplier_markup"],
            "price_vat_treatment": "included",
        },
    )
    assert result["step_id"] == "grid"
    result = await confirm_grid(manager, result)
    if result.get("step_id") == "energy_flows":
        result = await confirm_production(manager, result)
    assert result["step_id"] == "manual"
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    assert result["data"].get("source_profile") != "tibber"
    assert result["data"]["price_entity"] == "sensor.other_supplier"
