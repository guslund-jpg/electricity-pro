"""Keep Enhanced Clean's concise presentation on existing entity contracts."""

from collections import Counter
import copy
import json
from pathlib import Path

import pytest
import yaml


DASHBOARDS = Path(__file__).parents[1] / "examples" / "dashboards"
PREFIX = "sensor.electricity_pro_"
FLOW_ENTITIES = {
    PREFIX + channel + "_" + period
    for channel in ("production", "grid_export", "household_energy")
    for period in ("today", "this_month")
}
COMPENSATION = {
    PREFIX + "export_compensation_" + period for period in ("today", "this_month")
}
SHORT_NAMES = (
    FLOW_ENTITIES
    | COMPENSATION
    | {
        PREFIX + channel + "_" + period
        for channel in ("energy", "cost", "total_cost_estimate")
        for period in ("today", "this_month")
    }
    | {PREFIX + "consumption_weighted_average_price_today"}
)


@pytest.fixture(params=["", "-sv"], ids=["en", "sv"])
def examples(request):
    suffix = request.param
    return suffix, *(
        yaml.safe_load(
            (DASHBOARDS / f"electricity-pro-enhanced{variant}{suffix}.yaml").read_text()
        )
        for variant in ("", "-clean")
    )


def leaves(config, states=None):
    """Read actual cards, keeping conditions and optional frontend visibility.

    Series records are properties of a chart, not additional cards. Missing
    frontend states behave as unknown; the examples use state/and/or guards.
    """

    def matches(condition):
        kind = condition["condition"]
        if kind == "or":
            return any(matches(child) for child in condition["conditions"])
        if kind == "and":
            return all(matches(child) for child in condition["conditions"])
        assert kind == "state"
        return states.get(condition["entity"], "unknown") != condition["state_not"]

    def cards(card, guards=()):
        if card["type"] == "conditional":
            conditions = card["conditions"]
            if states is None or all(matches(condition) for condition in conditions):
                yield from cards(card["card"], guards + (conditions,))
        elif "cards" in card:
            for child in card["cards"]:
                yield from cards(child, guards)
        elif card["type"] not in {"markdown", "custom:mushroom-title-card"}:
            yield card, guards

    for view in config["views"]:
        for card in view["cards"]:
            for item, guards in cards(card):
                yield view["path"], item, guards


def operational_cards(config):
    result = []
    for view, card, guards in leaves(config):
        value = copy.deepcopy(card)
        entity = value.get("entity")
        if entity in SHORT_NAMES:
            value.pop("name", None)
        if entity in FLOW_ENTITIES:
            value.pop("vertical", None)
        if entity in COMPENSATION:
            value.pop("layout", None)
        if (
            value["type"] == "custom:apexcharts-card"
            and value.get("graph_span") == "24h"
        ):
            if any(
                row.get("entity") == PREFIX + "current_power" for row in value["series"]
            ):
                value["header"].pop("title", None)
        result.append(json.dumps([view, value, guards], sort_keys=True))
    return Counter(result)


def test_clean_retains_all_enhanced_values_chart_code_and_visibility(examples):
    _, original, clean = examples
    assert operational_cards(clean) == operational_cards(original)
    assert sum(operational_cards(clean).values()) == 52
    assert (
        sum(card["type"] == "custom:apexcharts-card" for _, card, _ in leaves(clean))
        == 5
    )
    assert [view["path"] for view in clean["views"]] == [
        "overview",
        "prices",
        "energy",
        "details",
    ]


def test_clean_has_compact_period_groups_and_no_explanatory_cards(examples):
    suffix, _, clean = examples

    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    assert clean["title"] == "Electricity Pro Enhanced Clean"
    assert all(
        card.get("type") != "markdown" and "subtitle" not in card
        for card in walk(clean)
    )
    energy = next(view for view in clean["views"] if view["path"] == "energy")
    groups = [card for card in energy["cards"] if card["type"] == "grid"]
    assert [len(card["cards"]) for card in groups] == [8, 7]
    assert all(card["columns"] == 2 and not card["square"] for card in groups)
    for index, group in enumerate(groups):
        period = "today" if index == 0 else "this_month"
        entities = {
            card.get("entity")
            for _, card, _ in leaves({"views": [{"path": "energy", "cards": [group]}]})
        }
        assert {
            PREFIX + name + "_" + period
            for name in (
                "energy",
                "total_cost_estimate",
                "cost",
                "grid_export",
                "export_compensation",
            )
        } <= entities
    for _, card, _ in leaves(clean):
        entity = card.get("entity")
        if entity in FLOW_ENTITIES:
            assert ("(delvis)" if suffix else "(partial)") in card["name"]
            assert card["vertical"] is True
            assert card["tap_action"] == {"action": "more-info"}
        if entity in COMPENSATION or entity in {
            PREFIX + "total_cost_estimate_" + p for p in ("today", "this_month")
        }:
            assert ("(ca)" if suffix else "(est.)") in card["name"]


@pytest.mark.parametrize("channel", ["production", "grid_export", "household"])
@pytest.mark.parametrize("periods", [("power",), ("today", "this_month")])
@pytest.mark.parametrize("state", [None, "unknown", "unavailable", "0", "1.5"])
def test_clean_independent_energy_and_power_sources_keep_zero_and_outages(
    examples, channel, periods, state
):
    _, _, clean = examples

    def entity(period):
        suffix = (
            ("demand_power" if period == "power" else "energy_" + period)
            if channel == "household"
            else period
        )
        return PREFIX + channel + "_" + suffix

    states = {entity(period): state for period in periods if state is not None}
    shown = {card.get("entity") for _, card, _ in leaves(clean, states)}
    channels = FLOW_ENTITIES | {
        PREFIX + name
        for name in ("production_power", "grid_export_power", "household_demand_power")
    }
    assert shown & channels == (
        set(states) if state not in (None, "unknown") else set()
    )


@pytest.mark.parametrize("period", ["today", "this_month"])
@pytest.mark.parametrize(
    "state", [None, "unknown", "unavailable", "0", "-0.40", "1.25"]
)
async def test_clean_export_amounts_read_signed_sensor_state_without_fallback(
    hass, examples, period, state
):
    _, _, clean = examples
    amount = PREFIX + "export_compensation_" + period
    energy = PREFIX + "grid_export_" + period
    hass.states.async_set(energy, "0")
    if state is not None:
        hass.states.async_set(amount, state, {"unit_of_measurement": "EUR"})
    states = {entity.entity_id: entity.state for entity in hass.states.async_all()}
    cards = [
        card for _, card, _ in leaves(clean, states) if card.get("entity") == amount
    ]
    assert bool(cards) == (state not in (None, "unknown", "unavailable"))
    if cards:
        assert cards[0]["type"] == "custom:mushroom-entity-card"
        assert cards[0]["layout"] == "vertical"
        assert cards[0]["tap_action"] == {"action": "more-info"}
        assert hass.states.get(cards[0]["entity"]).state == state
        assert (
            hass.states.get(cards[0]["entity"]).attributes["unit_of_measurement"]
            == "EUR"
        )
        assert not any(
            key in cards[0]
            for key in ("state", "content", "primary", "secondary", "unit")
        )


def test_clean_new_day_hides_missing_amount_and_keeps_month(examples):
    _, _, clean = examples
    daily, monthly = [
        PREFIX + "export_compensation_" + period for period in ("today", "this_month")
    ]
    states = {daily: "unavailable", monthly: "25.12"}
    visible = {card.get("entity") for _, card, _ in leaves(clean, states)}
    assert daily not in visible and monthly in visible
    states[daily] = "0"
    visible = {card.get("entity") for _, card, _ in leaves(clean, states)}
    assert {daily, monthly} <= visible
