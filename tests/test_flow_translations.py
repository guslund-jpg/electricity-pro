"""The default and English setup forms should give the same instructions."""

import json
from pathlib import Path

import pytest


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
