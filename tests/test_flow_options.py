"""Optional flow settings stay separate from import and Tibber fast-track."""

import pytest
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN, CONF_POWER_ENTITY, CONF_SOURCE_PROFILE
from custom_components.electricity_pro.flow_sources import FLOW_KEYS, CONF_CONFIGURE_FLOWS


async def start_options(hass, profile="custom", **settings):
    entry = MockConfigEntry(domain=DOMAIN, data={
        CONF_POWER_ENTITY: "sensor.import_power",
        CONF_SOURCE_PROFILE: profile,
        **settings,
    })
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return entry, result


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_opt_in_and_preserve_bindings_on_normal_save(hass, profile):
    entry, result = await start_options(hass, profile, production_energy_entity="sensor.production")
    keys = {key.schema for key in result["data_schema"].schema}
    assert not keys.intersection(FLOW_KEYS)
    assert CONF_CONFIGURE_FLOWS in keys
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        **({CONF_POWER_ENTITY: "sensor.import_power"} if profile == "custom" else {}),
    })
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["production_energy_entity"] == "sensor.production"
    assert CONF_CONFIGURE_FLOWS not in result["data"]


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_optional_sources_confirm_save_and_clear(hass, profile):
    hass.states.async_set("sensor.production", "100", {
        "device_class": "energy", "unit_of_measurement": "kWh",
    })
    entry, result = await start_options(hass, profile)
    submission = {
        CONF_CONFIGURE_FLOWS: True,
        **({CONF_POWER_ENTITY: "sensor.import_power"} if profile == "custom" else {}),
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], submission)
    assert result["step_id"] == "energy_flows"
    assert "production_energy_entity" not in entry.options
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "production_energy_entity": "sensor.production",
    })
    assert result["errors"]["base"] == "confirm_flow_semantics"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "production_energy_entity": "sensor.production", "confirm_flow_semantics": True,
    })
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["production_energy_entity"] == "sensor.production"
    assert "confirm_flow_semantics" not in result["data"]
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], submission)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert all(result["data"][key] is None for key in FLOW_KEYS)


@pytest.mark.parametrize("kind", ["own", "duplicate", "import", "unit", "class", "missing"])
async def test_invalid_sources_rejected(hass, kind):
    entry, result = await start_options(hass)
    source = "sensor.production"
    if kind == "own":
        entity = er.async_get(hass).async_get_or_create(
            "sensor", DOMAIN, "own", config_entry=entry,
        )
        source = entity.entity_id
    if kind == "import":
        source = "sensor.import_power"
    if kind != "missing":
        hass.states.async_set(source, "100", {
            "device_class": "energy" if kind == "class" else "power",
            "unit_of_measurement": "MW" if kind == "unit" else "W",
        })
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        CONF_POWER_ENTITY: "sensor.import_power", CONF_CONFIGURE_FLOWS: True,
    })
    submission = {
        "production_power_entity": source, "confirm_flow_semantics": True,
        **({"grid_export_power_entity": source} if kind == "duplicate" else {}),
    }
    if kind == "own":
        with pytest.raises(InvalidData):
            await hass.config_entries.options.async_configure(result["flow_id"], submission)
        from custom_components.electricity_pro.config_flow import _source_input_errors
        assert _source_input_errors(hass, submission)["production_power_entity"] == "electricity_pro_source"
        return
    result = await hass.config_entries.options.async_configure(result["flow_id"], submission)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]
    assert not entry.options


async def test_import_change_cannot_reuse_saved_flow(hass):
    _, result = await start_options(hass, production_power_entity="sensor.production")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        CONF_POWER_ENTITY: "sensor.production",
    })
    assert result["errors"]["base"] == "invalid_flow_source"


async def test_cancel_does_not_write_partial_settings(hass):
    entry, result = await start_options(hass)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        CONF_POWER_ENTITY: "sensor.import_power", CONF_CONFIGURE_FLOWS: True,
    })
    hass.config_entries.options.async_abort(result["flow_id"])
    assert not entry.options
