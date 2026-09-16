"""Visibility and truthful presentation for the optional dashboard groups."""

from pathlib import Path

import pytest
import yaml
from homeassistant.helpers.template import Template


DASHBOARDS = Path(__file__).parents[1] / "examples" / "dashboards"
CHANNELS = ("production", "grid_export")
PERIODS = ("power", "today", "this_month")


def matches(conditions, states):
    """Evaluate the state/or subset used here, with missing = unknown.

    Mirrors HA frontend checkStateCondition/checkOrCondition, rather than
    backend automation conditions (which have different missing-state rules).
    """
    def check(condition):
        if condition["condition"] == "or":
            return any(check(child) for child in condition["conditions"])
        assert condition["condition"] == "state"
        assert set(condition) == {"condition", "entity", "state_not"}
        return states.get(condition["entity"], "unknown") != condition["state_not"]

    return all(check(condition) for condition in conditions)


def visible_tiles(card, states):
    if card["type"] == "conditional":
        return visible_tiles(card["card"], states) if matches(card["conditions"], states) else []
    if card["type"] == "tile":
        return [card]
    return [tile for child in card.get("cards", []) for tile in visible_tiles(child, states)]


@pytest.fixture(params=["electricity-pro.yaml", "electricity-pro-enhanced.yaml"])
def groups(request):
    dashboard = yaml.safe_load((DASHBOARDS / request.param).read_text())
    overview = next(view for view in dashboard["views"] if view["title"] == "Overview")
    result = {}
    for channel in CHANNELS:
        groups = [
            card for card in overview["cards"]
            if card.get("type") == "conditional"
            and card.get("card", {}).get("type") == "vertical-stack"
            and f"sensor.electricity_pro_{channel}_power" in str(card["conditions"])
        ]
        assert len(groups) == 1
        result[channel] = groups[0]
    return result


@pytest.mark.parametrize("state", [None, "unknown", "0", "1.5", "unavailable"])
@pytest.mark.parametrize("periods", [("power",), ("today", "this_month"), PERIODS])
@pytest.mark.parametrize("channel", CHANNELS)
def test_groups_handle_absence_zero_outages_and_independent_sources(groups, state, periods, channel):
    states = {
        f"sensor.electricity_pro_{channel}_{period}": state
        for period in periods if state is not None
    }
    tiles = [tile for group in groups.values() for tile in visible_tiles(group, states)]
    expected = set(states) if state not in (None, "unknown") else set()
    assert {tile["entity"] for tile in tiles} == expected
    assert matches(groups[channel]["conditions"], states) == bool(expected)
    other = "grid_export" if channel == "production" else "production"
    assert not matches(groups[other]["conditions"], states)


async def test_notes_are_partial_only_for_energy_and_do_not_infer_origin(hass, groups):
    for channel, group in groups.items():
        note = group["card"]["cards"][0]
        assert note["type"] == "markdown"
        for energy_configured in (False, True):
            if energy_configured:
                hass.states.async_set(f"sensor.electricity_pro_{channel}_today", "unavailable")
            text = Template(note["content"], hass).async_render(parse_result=False)
            assert ("Partial energy totals" in text) == energy_configured
            assert "Flow details" in text
            assert len(text.split()) < 55
            if channel == "production":
                assert "excluding battery discharge" in text
            else:
                assert "may include a battery" in text
                assert "solar export" not in text.lower()


def test_both_channels_visible_without_new_dependencies_or_calculations(groups):
    states = {
        f"sensor.electricity_pro_{channel}_{period}": "0"
        for channel in CHANNELS for period in PERIODS
    }
    tiles = [tile for group in groups.values() for tile in visible_tiles(group, states)]
    assert len(tiles) == 6
    for tile in tiles:
        assert tile["type"] == "tile"
        assert tile["tap_action"] == {"action": "more-info"}
        assert "(partial)" in tile["name"] or tile["entity"].endswith("_power")
    for group in groups.values():
        assert "custom:" not in str(group)
        assert "float" not in str(group)
        assert "revenue" not in str(group)
