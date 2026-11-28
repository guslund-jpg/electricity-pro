"""Exercise optional export cards and their notes against actual HA templates."""

from pathlib import Path

from homeassistant.helpers.template import Template
import pytest
import yaml


DASHBOARDS = Path(__file__).parents[1] / "examples" / "dashboards"
PREFIX = "sensor.electricity_pro_"
DASHBOARDS_WITH_NOTES = sorted(
    path for path in DASHBOARDS.glob("*.yaml") if "-clean" not in path.stem
)


@pytest.fixture(params=DASHBOARDS_WITH_NOTES, ids=lambda p: p.stem)
def dashboard(request):
    return request.param, yaml.safe_load(request.param.read_text())


def amount_and_note(group, entity):
    """Find money cards independently of the neighboring measured-energy tile."""
    cards = group["card"]["cards"]
    amount = next(c for c in cards if c.get("card", {}).get("entity") == entity)
    note = next(c for c in cards if c["type"] == "markdown" and entity in c["content"])
    return amount, note


@pytest.fixture(params=[("energy", "today"), ("energy", "this_month")])
def export_cards(dashboard, request):
    path, data = dashboard
    view, period = request.param
    entity = f"{PREFIX}export_compensation_{period}"
    cards = next(v["cards"] for v in data["views"] if v["path"] == view)
    group = next(
        c
        for c in cards
        if c["type"] == "conditional" and entity in str(c["conditions"])
    )
    amount, note = amount_and_note(group, entity)
    return path, entity, group, amount, note


def visible(conditions, hass):
    """Evaluate the native frontend state/or subset, including absent = unknown."""

    def check(condition):
        if condition["condition"] == "or":
            return any(check(child) for child in condition["conditions"])
        assert condition["condition"] == "state"
        state = hass.states.get(condition["entity"])
        return (state.state if state is not None else "unknown") != condition[
            "state_not"
        ]

    return all(check(condition) for condition in conditions)


def render(hass, note):
    return " ".join(
        Template(note["content"], hass).async_render(parse_result=False).split()
    )


def attrs(**changes):
    return {
        "unit_of_measurement": "EUR",
        "observed_export_kwh": "3.000",
        "priced_export_kwh": "1.000",
        "source_status": "partial",
        "fixed_export_price_enabled": True,
        **changes,
    }


@pytest.mark.parametrize(
    "state", [None, "unknown", "unavailable", "0", "-0.40", "1.25"]
)
async def test_export_amounts_keep_zero_sign_currency_and_missing_data(
    hass, export_cards, state
):
    path, entity, group, amount, note = export_cards
    sv = path.stem.endswith("-sv")
    # An export energy channel exists even when its compensation is not ready.
    energy = entity.replace("export_compensation", "grid_export")
    hass.states.async_set(energy, "0")
    if state is not None:
        hass.states.async_set(entity, state, attrs())
    assert visible(group["conditions"], hass)
    known = state not in (None, "unknown", "unavailable")
    assert visible(amount["conditions"], hass) == known
    card = amount["card"]
    assert card["entity"] == entity
    assert card["tap_action"] == {"action": "more-info"}
    assert card["type"] == (
        "custom:mushroom-entity-card" if "enhanced" in path.stem else "tile"
    )
    assert card["name"] == (
        "Exportersättning (ca)" if sv else "Export compensation (est.)"
    )
    # Native cards read the signed sensor state and its own currency; no price
    # multiplication, import netting or monetary fallback is performed in YAML.
    assert "SEK" not in str(group)
    assert "float(0)" not in str(group)
    text = render(hass, note)
    assert (("Underlag saknas" if sv else "Data unavailable") in text) == (not known)
    assert (("Delvis täckning" if sv else "Partial coverage") in text) == known
    assert (("Negativ ersättning" if sv else "Negative compensation") in text) == (
        state == "-0.40"
    )
    if known:
        assert hass.states.get(card["entity"]).state == state
        assert (
            hass.states.get(card["entity"]).attributes["unit_of_measurement"] == "EUR"
        )
        assert ("3,000 kWh observerade" if sv else "3.000 kWh observed") in text
        assert ("1,000 kWh prissatta" if sv else "1.000 kWh priced") in text
    else:
        assert "kWh" not in text
        assert "0.00" not in text
        assert "3.000" not in text
    assert (
        "Separat från importkostnaden" if sv else "Separate from import costs"
    ) in text


@pytest.mark.parametrize("source", [None, "unknown", "unavailable", "0"])
async def test_export_visibility_needs_energy_or_booked_amount(
    hass, export_cards, source
):
    _, entity, group, _, _ = export_cards
    # Import, production and export power alone must not reveal money cards.
    for suffix in (
        "energy_today",
        "cost_today",
        "production_today",
        "grid_export_power",
    ):
        hass.states.async_set(PREFIX + suffix, "1")
    if source is not None:
        hass.states.async_set(
            entity.replace("export_compensation", "grid_export"), source
        )
    assert visible(group["conditions"], hass) == (source in ("unavailable", "0"))
    hass.states.async_set(entity, "0", attrs())
    assert visible(group["conditions"], hass)


@pytest.mark.parametrize(
    "changes",
    [
        {"source_status": "invalid_or_missing_source"},
        {"source_status": None},
        {"fixed_export_price_enabled": False},
        {"source_status": "waiting_for_baseline", "fixed_export_price_enabled": False},
    ],
)
async def test_booked_amount_survives_source_gap_and_disabled_price(
    hass, export_cards, changes
):
    path, entity, group, amount, note = export_cards
    sv = path.stem.endswith("-sv")
    hass.states.async_set(entity, "1.25", attrs(**changes))
    assert visible(group["conditions"], hass)
    assert visible(amount["conditions"], hass)
    text = render(hass, note)
    assert ("bokfört belopp visas" if sv else "showing the booked amount") in text
    assert (
        (
            "Exportkällan kan inte bekräftas"
            if sv
            else "export source cannot be confirmed"
        )
        in text
    ) == ("source_status" in changes)
    assert (
        ("Fast exportpris är avstängt" if sv else "Fixed export pricing is off") in text
    ) == (changes.get("fixed_export_price_enabled") is False)


@pytest.mark.parametrize("observed,priced", [("0", "0"), ("3", "3"), (None, "bad")])
async def test_coverage_remains_partial_without_inventing_energy(
    hass, export_cards, observed, priced
):
    path, entity, _, _, note = export_cards
    sv = path.stem.endswith("-sv")
    hass.states.async_set(
        entity, "0", attrs(observed_export_kwh=observed, priced_export_kwh=priced)
    )
    text = render(hass, note)
    assert ("Delvis täckning" if sv else "Partial coverage") in text
    assert "%" not in text
    if observed is None:
        assert (
            "Täckningsunderlag saknas" if sv else "Coverage data unavailable"
        ) in text
        assert "0.000" not in text
        assert "kWh" not in text
    else:
        assert (observed + (",000" if sv else ".000")) in text


async def test_day_rollover_does_not_reuse_month_or_previous_day(hass, dashboard):
    _, data = dashboard
    daily = PREFIX + "export_compensation_today"
    monthly = PREFIX + "export_compensation_this_month"
    hass.states.async_set(daily, "5.12", attrs())
    hass.states.async_set(monthly, "25.12", attrs())
    cards = next(view["cards"] for view in data["views"] if view["path"] == "energy")
    groups = {
        period: next(
            c
            for c in cards
            if c["type"] == "conditional"
            and f"export_compensation_{period}" in str(c["conditions"])
        )
        for period in ("today", "this_month")
    }
    day_amount, day_note = amount_and_note(groups["today"], daily)
    month_amount, month_note = amount_and_note(groups["this_month"], monthly)
    hass.states.async_set(daily, "unavailable")
    assert visible(groups["today"]["conditions"], hass)
    assert not visible(day_amount["conditions"], hass)
    assert visible(month_amount["conditions"], hass)
    assert day_amount["card"]["entity"] == daily
    assert month_amount["card"]["entity"] == monthly
    assert monthly not in day_note["content"]
    assert daily not in month_note["content"]
    assert "5.12" not in render(hass, day_note)
    assert "25.12" not in render(hass, day_note)
    hass.states.async_set(
        daily, "0", attrs(observed_export_kwh="0", priced_export_kwh="0")
    )
    assert visible(day_amount["conditions"], hass)
