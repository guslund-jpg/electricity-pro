"""Guided setup/options keep complete translations and interpolation contracts."""

from collections import Counter
import json
from pathlib import Path
import re
from string import Formatter

import pytest


ROOT = Path(__file__).resolve().parents[1] / "custom_components/electricity_pro"
# Retained caller-compatibility screens, reviewed separately in #446.
# All other source keys, including future guided steps/errors, require Swedish.
LEGACY_CONFIG_STEPS = {
    ("config", "step", "manual"),
    ("config", "step", "tibber_settings"),
}


def _string_leaves(value, path=()):
    for key, item in value.items():
        if isinstance(item, dict):
            yield from _string_leaves(item, (*path, key))
        elif isinstance(item, str):
            yield (*path, key), item


def _guided_strings(filename, flow):
    resource = json.loads((ROOT / filename).read_text(encoding="utf-8"))
    return {
        key: text
        for key, text in _string_leaves(resource)
        if key[0] == flow and key[:3] not in LEGACY_CONFIG_STEPS
    }


def _placeholders(text):
    return Counter(
        (field, spec, conversion)
        for _, field, spec, conversion in Formatter().parse(text)
        if field is not None
    )


@pytest.mark.parametrize("flow", ["config", "options"])
def test_swedish_guided_flow_has_all_source_keys(flow):
    """New guided fields/errors must not silently fall back to English."""
    source = _guided_strings("strings.json", flow)
    swedish = _guided_strings("translations/sv.json", flow)
    missing = sorted(".".join(key) for key in source.keys() - swedish.keys())
    assert not missing, f"Missing Swedish strings: {missing}"
    assert all(swedish[key].strip() for key in source), "Blank Swedish string"


@pytest.mark.parametrize("flow", ["config", "options"])
def test_swedish_guided_flow_preserves_placeholders_and_links(flow):
    """Formatting fields, their counts/specifiers and link targets stay intact."""
    source = _guided_strings("strings.json", flow)
    swedish = _guided_strings("translations/sv.json", flow)
    for key, text in source.items():
        translated = swedish[key]
        assert _placeholders(translated) == _placeholders(text), ".".join(key)
        assert re.findall(r"\[[^\]]*\]\(([^)]+)\)", translated) == re.findall(
            r"\[[^\]]*\]\(([^)]+)\)", text
        ), ".".join(key)


@pytest.mark.parametrize("flow", ["config", "options"])
@pytest.mark.parametrize(
    ("step", "values"),
    [
        (
            "tibber_markup_review",
            {"count": "4", "area": "SE3", "spread": "0,01", "currency": "SEK"},
        ),
        ("vat_country", {"hint": "SE"}),
        (
            "vat_review",
            {
                "context": "Svenskt hushåll",
                "previous": "0",
                "verified": "2026-11-01",
                "source": "https://example.test/vat",
            },
        ),
    ],
)
def test_swedish_guided_descriptions_render(flow, step, values):
    """Tibber and VAT values, including a prior zero and source URL, survive."""
    strings = _guided_strings("translations/sv.json", flow)
    rendered = strings[(flow, "step", step, "description")].format(**values)
    assert all(value in rendered for value in values.values())
    assert not _placeholders(rendered)
    if "source" in values:
        assert f"]({values['source']})" in rendered


@pytest.mark.parametrize("flow", ["config", "options"])
def test_english_flow_matches_default(flow):
    root = Path(__file__).resolve().parents[1] / "custom_components/electricity_pro"
    default = json.loads((root / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((root / "translations/en.json").read_text(encoding="utf-8"))
    assert default[flow] == english[flow]


@pytest.mark.parametrize(
    "filename", ["strings.json", "translations/en.json", "translations/sv.json"]
)
@pytest.mark.parametrize("flow", ["config", "options"])
@pytest.mark.parametrize("step", ["measurements", "measurement_energy"])
def test_measurement_readings_start_in_a_separate_markdown_list(filename, flow, step):
    """The introduction must end before the first source bullet begins."""
    root = Path(__file__).resolve().parents[1] / "custom_components/electricity_pro"
    strings = json.loads((root / filename).read_text(encoding="utf-8"))
    sources = "- sensor.power · 600 W\n- sensor.energy · 12 kWh"
    rendered = strings[flow]["step"][step]["description"].format(sources=sources)
    assert rendered.splitlines()[-3:] == ["", *sources.splitlines()]
