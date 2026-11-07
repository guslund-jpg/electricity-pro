"""Keep translated dashboard presentation on the same operational contracts."""

import json
from pathlib import Path
import re

from homeassistant.helpers.template import Template
from jinja2 import Environment, nodes
import pytest
import yaml

ROOT = Path(__file__).parents[1]
DASHBOARDS = ROOT / "examples" / "dashboards"
PAIRS = ("electricity-pro", "electricity-pro-enhanced")
PRESENTATION = {
    "title",
    "heading",
    "subtitle",
    "name",
    "label",
    "content",
    "primary",
    "secondary",
}


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def template_contract(value):
    """Protect state reads, branches, assignments and numeric presentation."""
    tree = Environment().parse(value)
    return {
        "assignments": [
            (repr(n.target), repr(n.node)) for n in tree.find_all(nodes.Assign)
        ],
        "conditions": [repr(n.test) for n in tree.find_all((nodes.If, nodes.CondExpr))],
        "reads": [
            repr(n)
            for n in tree.find_all(nodes.Call)
            if isinstance(n.node, nodes.Name)
            and n.node.name
            in ("states", "is_state", "state_attr", "as_datetime", "as_local")
        ],
        "numeric_filters": [
            (n.name, [repr(arg) for arg in n.args])
            for n in tree.find_all(nodes.Filter)
            if n.name in ("float", "round", "format")
        ],
        "links": re.findall(r"https?://[^)\s]+", value),
    }


@pytest.mark.parametrize("name", PAIRS)
def test_language_variants_share_operational_configuration(name):
    english = yaml.safe_load((DASHBOARDS / f"{name}.yaml").read_text())
    swedish = yaml.safe_load((DASHBOARDS / f"{name}-sv.yaml").read_text())

    def compare(en, sv, field=None):
        if isinstance(en, dict):
            assert en.keys() == sv.keys()
            for key in en:
                compare(en[key], sv[key], key)
        elif isinstance(en, list):
            assert len(en) == len(sv)
            for a, b in zip(en, sv, strict=True):
                compare(a, b, field)
        elif field in PRESENTATION and isinstance(en, str):
            if en in ("Electricity Pro", "Electricity Pro Enhanced"):
                assert en == sv
            else:
                assert en != sv, f"Untranslated {field}: {en}"
                assert template_contract(en) == template_contract(sv)
        else:
            # Includes IDs, URLs/paths, conditions, thresholds, JS, colours,
            # visibility, chart precision and custom-card dependencies.
            assert en == sv, field

    compare(english, swedish)


@pytest.mark.parametrize("name", PAIRS)
@pytest.mark.parametrize(
    "missing", [[], ["fixed_supplier_fee", "fixed_grid_fee", "complete_variable_price"]]
)
async def test_swedish_missing_cost_components_render_without_english_keys(
    hass, name, missing
):
    hass.states.async_set(
        "sensor.electricity_pro_total_cost_estimate_today",
        "0",
        {"priced_energy_kwh": "0", "missing_components": missing},
    )
    data = yaml.safe_load((DASHBOARDS / f"{name}-sv.yaml").read_text())
    notes = [
        item["content"]
        for item in walk(data)
        if isinstance(item, dict)
        and item.get("type") == "markdown"
        and "total_cost_estimate_today" in item.get("content", "")
    ]
    assert notes
    for note in notes:
        rendered = str(Template(note, hass).async_render(parse_result=False))
        assert "0.0 kWh prissatta" in rendered
        assert ("Saknas:" in rendered) == bool(missing)
        if missing:
            assert (
                "fast elhandelsavgift, fast elnätsavgift, komplett rörligt elpris"
                in rendered
            )
            assert not any(key in rendered for key in missing)
        assert (
            "Effektavgifter och andra ej konfigurerade avgifter ingår inte" in rendered
        )


@pytest.mark.parametrize(
    ("state", "phrase"),
    [("on", "Bra tillfälle att använda el"), ("off", "Vänta på ett bättre pris")],
)
@pytest.mark.parametrize("price", ["0", "-0.25", "1.234"])
async def test_swedish_enhanced_advice_keeps_state_logic_precision_and_currency(
    hass, state, phrase, price
):
    hass.states.async_set(
        "binary_sensor.electricity_pro_good_time_to_use_electricity", state
    )
    hass.states.async_set(
        "sensor.electricity_pro_effective_price",
        price,
        {"unit_of_measurement": "EUR/kWh"},
    )
    data = yaml.safe_load((DASHBOARDS / "electricity-pro-enhanced-sv.yaml").read_text())
    advice = next(
        item
        for item in walk(data)
        if isinstance(item, dict)
        and item.get("type") == "custom:mushroom-template-card"
    )
    assert (
        Template(advice["primary"], hass).async_render(parse_result=False).strip()
        == phrase
    )
    text = Template(advice["secondary"], hass).async_render(parse_result=False)
    assert "Effektivt elpris:" in text
    assert f"{float(price):.2f}" in text
    assert "EUR/kWh" in text
    assert "SEK" not in text


def test_swedish_price_labels_match_reviewed_entity_translations():
    entities = json.loads(
        (ROOT / "custom_components/electricity_pro/translations/sv.json").read_text()
    )["entity"]["sensor"]
    data = yaml.safe_load((DASHBOARDS / "electricity-pro-enhanced-sv.yaml").read_text())
    price_chart = next(
        item
        for item in walk(data)
        if isinstance(item, dict)
        and item.get("header", {}).get("title")
        == "Spotpris, elhandelspris och effektivt elpris"
    )
    assert [series["name"] for series in price_chart["series"]] == [
        entities[key]["name"]
        for key in ("current_market_price", "current_supplier_price", "effective_price")
    ]
