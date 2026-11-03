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
