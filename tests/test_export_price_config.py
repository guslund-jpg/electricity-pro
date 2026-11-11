"""Configure fixed export prices through the production options flow."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from tests.flow_helpers import confirm_production, form_values, start_production

START = datetime(2026, 11, 11, 11, tzinfo=UTC)
PRICE = {
    "fixed_export_price_enabled": True,
    "export_price_amount": "-0,20",
    "export_price_currency": "sek",
    "export_price_vat_treatment": "excluded",
    "export_price_components": ["supplier_compensation", "variable_deductions"],
}


@pytest.fixture
def entry(hass):
    hass.states.async_set(
        "sensor.export", "100", {"device_class": "energy", "unit_of_measurement": "Wh"}
    )
    entry = MockConfigEntry(
        domain="electricity_pro",
        data={
            "power_entity": "sensor.import",
            "grid_export_energy_entity": "sensor.export",
        },
        options={"grid_fee_per_kwh": 0.12},
    )
    entry.add_to_hass(hass)
    return entry


async def open_price(hass, entry):
    manager = hass.config_entries.options
    result = await start_production(manager, entry.entry_id)
    result = await confirm_production(manager, result, {"confirm_flow_semantics": True})
    assert result["step_id"] == "flow_compatibility"
    result = await manager.async_configure(
        result["flow_id"], {**form_values(result), "edit_fixed_export_price": True}
    )
    assert result["step_id"] == "fixed_export_price"
    assert result["description_placeholders"] == {"export_meter": "sensor.export"}
    return manager, result


async def save_at(manager, result, user_input, instant):
    with patch(
        "custom_components.electricity_pro.config_flow.dt_util.utcnow",
        return_value=instant,
    ):
        return await manager.async_configure(result["flow_id"], user_input)


async def test_price_change_preserves_old_period_and_unchanged_save(hass, entry):
    manager, result = await open_price(hass, entry)
    assert form_values(result) == {"fixed_export_price_enabled": False}
    assert (await save_at(manager, result, PRICE, START))["type"] == "create_entry"
    (first,) = entry.options["export_price_periods"]
    assert first == {
        "meter": "sensor.export",
        "amount_per_kwh": "-0.20",
        "currency": "SEK",
        "vat_treatment": "excluded",
        "components": ["supplier_compensation", "variable_deductions"],
        "valid_from": START.isoformat(),
        "valid_until": None,
    }
    assert entry.options["grid_fee_per_kwh"] == 0.12

    _, result = await open_price(hass, entry)
    assert form_values(result)["export_price_amount"] == "-0.20"
    await save_at(
        manager,
        result,
        {**PRICE, "export_price_amount": "-0.200"},
        START + timedelta(minutes=1),
    )
    assert entry.options["export_price_periods"] == [first]

    _, result = await open_price(hass, entry)
    change = START + timedelta(minutes=5)
    await save_at(manager, result, {**PRICE, "export_price_amount": "0"}, change)
    old, new = entry.options["export_price_periods"]
    assert old == {**first, "valid_until": change.isoformat()}
    assert new == {**first, "amount_per_kwh": "0", "valid_from": change.isoformat()}

    _, result = await open_price(hass, entry)
    await save_at(
        manager,
        result,
        {"fixed_export_price_enabled": False},
        change + timedelta(minutes=1),
    )
    assert entry.options["export_price_periods"] == [
        old,
        {**new, "valid_until": (change + timedelta(minutes=1)).isoformat()},
    ]


async def test_invalid_submission_and_cancellation_save_nothing(hass, entry):
    manager, result = await open_price(hass, entry)
    result = await manager.async_configure(
        result["flow_id"],
        {
            "fixed_export_price_enabled": True,
            "export_price_amount": "NaN",
            "export_price_currency": "ZZZ",
            "export_price_components": ["variable_deductions"],
        },
    )
    assert result["errors"] == {
        "export_price_amount": "invalid_export_price",
        "export_price_currency": "invalid_export_currency",
        "export_price_vat_treatment": "export_vat_required",
        "export_price_components": "export_component_required",
    }
    manager.async_abort(result["flow_id"])
    assert dict(entry.options) == {"grid_fee_per_kwh": 0.12}


async def test_removing_export_register_closes_price_without_deleting_history(
    hass, entry
):
    manager, result = await open_price(hass, entry)
    await save_at(manager, result, PRICE, START)
    (first,) = entry.options["export_price_periods"]
    result = await start_production(manager, entry.entry_id)
    change = START + timedelta(hours=1)
    result = await save_at(manager, result, {"configure_energy_flows": False}, change)
    assert result["type"] == "create_entry"
    assert entry.options["grid_export_energy_entity"] is None
    assert entry.options["export_price_periods"] == [
        {**first, "valid_until": change.isoformat()}
    ]
