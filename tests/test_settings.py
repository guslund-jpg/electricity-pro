"""Tests for the shared, normalization-free saved settings overlay."""

from types import MappingProxyType

import pytest

from custom_components.electricity_pro.settings import resolve_settings


@pytest.mark.parametrize("value", [None, 0, False, "", [], {}, "replacement"])
def test_explicit_options_override_data(value):
    """Falsey options must not resurrect a prior setting."""
    data = MappingProxyType({"key": "old", "data_only": 1})
    options = MappingProxyType({"key": value, "options_only": 2})
    assert resolve_settings(data, options) == {
        "key": value, "data_only": 1, "options_only": 2,
    }
    assert data["key"] == "old"
    assert options["key"] == value


def test_missing_keys_remain_missing_and_none_remains_present():
    """Defaults and presence-based entity creation remain caller decisions."""
    result = resolve_settings({"cleared": 1}, {"cleared": None})
    assert "cleared" in result
    assert result.get("cleared", "default") is None
    assert "missing" not in result
    assert result.get("missing", "default") == "default"


def test_fresh_shallow_mapping_without_nested_merge():
    """Do not mutate inputs, deep-copy values or cache subsequent reads."""
    nested = {"new": 2}
    data = {"key": {"old": 1}, "unchanged": [1]}
    options = {"key": nested}
    first = resolve_settings(data, options)
    second = resolve_settings(data, options)
    assert first == second
    assert first is not second
    assert first["key"] is nested
    assert first["unchanged"] is data["unchanged"]
    first["added"] = True
    assert "added" not in second and "added" not in data and "added" not in options
    options["key"] = None
    assert resolve_settings(data, options)["key"] is None
    assert second["key"] is nested
