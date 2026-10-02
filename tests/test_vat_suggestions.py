"""Country hints and confirmed VAT rates must not become silent tax assumptions."""

from datetime import date, timedelta
import json
from pathlib import Path

import pytest
from homeassistant import config_entries
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.config_flow import _entity_schema, _tibber_settings_schema, _tibber_forecast_pricing_schema
from custom_components.electricity_pro.vat_suggestions import RULES, VERIFIED_ON, country_hint, vat_rule


@pytest.mark.parametrize(("areas", "selected", "expected"), [
    (["SE1"], None, "SE"), (["DK2"], None, "DK"), (["FI"], None, "FI"),
    (["NO4"], None, "NO"), (["NO1", "NO4"], None, "NO"),
    (["SE3", "FI"], None, None), (["SE3", "FI"], "FI", "FI"),
    (["SE3"], "FI", None), (["EE"], None, None), ([], None, None),
    (["SE3", "unknown"], None, None), (["SE99"], None, None),
])
def test_country_hint(areas, selected, expected):
    assert country_hint(areas, selected) == expected


@pytest.mark.parametrize(("country", "context", "rate"), [
    ("SE", "standard", 25), ("DK", "standard", 25), ("FI", "standard", 25.5),
    ("NO", "north_household", 0), ("NO", "other_household", 25),
    ("IS", "general", 24), ("IS", "heating", 11),
])
def test_verified_rules_and_date_boundaries(country, context, rate):
    rule = vat_rule(country, context, VERIFIED_ON)
    assert rule.rate == rate
    assert rule.source.startswith("https://")
    assert vat_rule(country, context, rule.effective_from - timedelta(days=1)) is None
    assert vat_rule(country, context, rule.effective_from) == rule
    assert vat_rule(country, context, VERIFIED_ON + timedelta(days=366)) == rule
    assert vat_rule(country, context, VERIFIED_ON + timedelta(days=367)) is None


def test_unknown_context_never_infers_exemption():
    assert vat_rule("NO", "standard", VERIFIED_ON) is None
    assert vat_rule("NO", "NO4", VERIFIED_ON) is None
    assert vat_rule("IS", "standard", VERIFIED_ON) is None
    assert vat_rule("unknown", "standard", VERIFIED_ON) is None
    assert vat_rule("FI", "standard", date(2024, 8, 31)) is None


def test_assistance_visibility_and_translations():
    assert "suggest_vat_rate" in {k.schema for k in _entity_schema().schema}
    assert "suggest_vat_rate" in {k.schema for k in _tibber_forecast_pricing_schema({}).schema}
    assert "suggest_vat_rate" not in {k.schema for k in _tibber_settings_schema().schema}
    root = Path(__file__).resolve().parents[1] / "custom_components/electricity_pro"
    strings = json.loads((root / "strings.json").read_text())
    english = json.loads((root / "translations/en.json").read_text())
    for flow in ("config", "options"):
        for step in ("vat_country", "vat_context", "vat_review"):
            assert strings[flow]["step"][step] == english[flow]["step"][step]
        assert strings[flow]["step"]["tibber_forecast_pricing"]["data"]["price_vat_rate"] == "VAT to add to Nord Pool forecasts (%)"


async def start(hass, profile, **data):
    entry = MockConfigEntry(domain="electricity_pro", data={
        "source_profile": profile, "power_entity": "sensor.power", **data,
    })
    entry.add_to_hass(hass)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    return entry, flow


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_automatic_hint_requires_confirmation(hass, freezer, profile):
    freezer.move_to("2026-10-02T12:00:00Z")
    nordpool = MockConfigEntry(domain="nordpool", data={"areas": ["FI"], "currency": "SEK"})
    nordpool.add_to_hass(hass)
    entry, flow = await start(hass, profile)
    submit = hass.config_entries.options.async_configure
    values = {"forecast_nordpool_config_entry": nordpool.entry_id}
    if profile == "custom":
        values["power_entity"] = "sensor.power"
    flow = await submit(flow["flow_id"], values)
    if profile == "tibber":
        assert flow["step_id"] == "tibber_forecast_pricing"
        flow = await submit(flow["flow_id"], {})
    assert flow["step_id"] == "vat_country"
    assert flow["description_placeholders"]["hint"] == "FI"
    assert not entry.options
    flow = await submit(flow["flow_id"], {"vat_country": "FI"})
    assert flow["step_id"] == "vat_review"
    schema_values = flow["data_schema"]({})
    assert schema_values["price_vat_rate"] == 25.5
    assert not entry.options
    flow = await submit(flow["flow_id"], {"price_vat_rate": 25.5, "use_vat_suggestion": True})
    assert flow["type"] == "create_entry"
    assert flow["data"]["price_vat_rate"] == 25.5
    assert "suggest_vat_rate" not in flow["data"]
    assert "vat_country" not in flow["data"]


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize("saved", [0, 17.2, 25])
async def test_saved_rates_unchanged_on_source_change(hass, profile, saved):
    nordpool = MockConfigEntry(domain="nordpool", data={"areas": ["FI"], "currency": "EUR"})
    nordpool.add_to_hass(hass)
    _, flow = await start(hass, profile, price_vat_rate=saved)
    submit = hass.config_entries.options.async_configure
    values = {"forecast_nordpool_config_entry": nordpool.entry_id}
    if profile == "custom":
        values.update(power_entity="sensor.power", price_vat_rate=saved)
    flow = await submit(flow["flow_id"], values)
    if profile == "tibber":
        assert flow["step_id"] == "tibber_forecast_pricing"
        flow = await submit(flow["flow_id"], {"price_vat_rate": saved})
    assert flow["type"] == "create_entry"
    assert flow["data"]["price_vat_rate"] == saved


@pytest.mark.parametrize("accept", [False, True])
async def test_non_nordpool_override_or_decline(hass, freezer, accept):
    freezer.move_to("2026-10-02T12:00:00Z")
    _, flow = await start(hass, "custom", price_vat_rate=0)
    submit = hass.config_entries.options.async_configure
    flow = await submit(flow["flow_id"], {"power_entity": "sensor.power", "price_vat_rate": 0, "suggest_vat_rate": True})
    assert flow["description_placeholders"]["hint"] == "No unambiguous Nord Pool area"
    flow = await submit(flow["flow_id"], {"vat_country": "SE"})
    assert float(flow["description_placeholders"]["previous"]) == 0
    flow = await submit(flow["flow_id"], {"price_vat_rate": 12.3, "use_vat_suggestion": accept})
    assert flow["type"] == "create_entry"
    assert flow["data"]["price_vat_rate"] == (12.3 if accept else 0)


@pytest.mark.parametrize(("country", "context", "rate"), [("NO", "north_household", 0), ("NO", "other_household", 25), ("IS", "general", 24), ("IS", "heating", 11)])
async def test_exception_context_required(hass, freezer, country, context, rate):
    freezer.move_to("2026-10-02T12:00:00Z")
    flow = await hass.config_entries.flow.async_init("electricity_pro", context={"source": config_entries.SOURCE_USER})
    submit = hass.config_entries.flow.async_configure
    flow = await submit(flow["flow_id"], {"setup_method": "custom"})
    flow = await submit(flow["flow_id"], {"power_entity": "sensor.power", "suggest_vat_rate": True})
    flow = await submit(flow["flow_id"], {"vat_country": country})
    assert flow["step_id"] == "vat_context"
    assert flow["data_schema"]({})["vat_context"] == "manual"
    flow = await submit(flow["flow_id"], {"vat_context": context})
    assert flow["data_schema"]({})["price_vat_rate"] == rate
    flow = await submit(flow["flow_id"], {"price_vat_rate": rate, "use_vat_suggestion": True})
    assert flow["data"]["price_vat_rate"] == rate


async def test_expired_rule_allows_manual_escape(hass, freezer):
    freezer.move_to("2028-10-02T12:00:00Z")
    _, flow = await start(hass, "custom", price_vat_rate=17)
    submit = hass.config_entries.options.async_configure
    flow = await submit(flow["flow_id"], {"power_entity": "sensor.power", "suggest_vat_rate": True})
    flow = await submit(flow["flow_id"], {"vat_country": "SE"})
    assert "price_vat_rate" not in flow["data_schema"]({})
    flow = await submit(flow["flow_id"], {"use_vat_suggestion": False})
    assert flow["data"]["price_vat_rate"] == 17
