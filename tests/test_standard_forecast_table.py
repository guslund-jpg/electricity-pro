"""Render Standard's native forecast table without custom frontend cards."""

from pathlib import Path

from homeassistant.helpers.template import Template
import pytest
import yaml


SOURCE = "sensor.electricity_pro_current_market_price"
DASHBOARDS = Path(__file__).parents[1] / "examples" / "dashboards"


@pytest.fixture(params=["electricity-pro.yaml", "electricity-pro-sv.yaml"])
def forecast_card(request):
    data = yaml.safe_load((DASHBOARDS / request.param).read_text())
    prices = next(view for view in data["views"] if view["path"] == "prices")
    group = next(
        card
        for card in prices["cards"]
        if card.get("type") == "conditional"
        and card["card"].get("type") == "markdown"
        and SOURCE in card["card"]["content"]
    )
    assert group["conditions"] == [
        {"condition": "state", "entity": SOURCE, "state_not": "unknown"}
    ]
    return group["card"], request.param.endswith("-sv.yaml")


def interval(start, end, price):
    return {"start": start, "end": end, "price": price}


def set_forecast(hass, rows, *, state="0", currency="SEK", vat="excluded"):
    hass.states.async_set(
        SOURCE,
        state,
        {
            "forecast": rows,
            "currency": currency,
            "price_area": "SE3",
            "vat_treatment": vat,
        },
    )


def render(hass, card):
    return Template(card["content"], hass).async_render(parse_result=False)


async def test_native_forecast_keeps_quarters_zero_negative_and_gaps(
    hass, freezer, forecast_card
):
    card, swedish = forecast_card
    await hass.config.async_set_time_zone("Europe/Stockholm")
    freezer.move_to("2026-11-28T12:07:00+00:00")
    set_forecast(
        hass,
        [
            interval("2026-11-28T11:45:00Z", "2026-11-28T12:00:00Z", 99),
            interval("2026-11-28T12:00:00Z", "2026-11-28T12:15:00Z", 0),
            interval("2026-11-28T12:15:00Z", "2026-11-28T12:30:00Z", -0.2),
            interval("2026-11-28T12:45:00Z", "2026-11-28T13:00:00Z", 1.23456),
            interval("bad", "2026-11-28T13:15:00Z", 2),
            interval("2026-11-28T13:00:00Z", "2026-11-28T13:15:00Z", "unknown"),
        ],
    )
    text = render(hass, card)
    assert "<details>" in text and "<summary>" in text and "<table>" in text
    assert "3 pågående/kommande" in text if swedish else "3 current/upcoming" in text
    assert text.count("<tr>") == 4  # Three intervals plus the header.
    assert "13:00 +0100–13:15 +0100" in text
    assert "13:15 +0100–13:30 +0100" in text
    assert "13:45 +0100–14:00 +0100" in text
    assert "13:30 +0100–13:45 +0100" not in text
    for amount in ("0.0000", "-0.2000", "1.2346"):
        assert (amount.replace(".", ",") if swedish else amount) in text
    assert "99.0000" not in text and "99,0000" not in text
    assert "SEK/kWh" in text and "SE3" in text


@pytest.mark.parametrize("state", [None, "unknown", "unavailable", "0"])
async def test_native_forecast_does_not_invent_missing_data(
    hass, freezer, forecast_card, state
):
    card, swedish = forecast_card
    freezer.move_to("2026-11-28T12:07:00+00:00")
    if state is not None:
        set_forecast(
            hass,
            [interval("2026-11-28T12:00:00Z", "2026-11-28T12:15:00Z", 0)],
            state=state,
        )
    text = render(hass, card)
    assert ("<table>" in text) == (state == "0")
    message = (
        "Ingen publicerad prognos"
        if swedish
        else "No published current or upcoming forecast"
    )
    assert (message in text) == (state != "0")


@pytest.mark.parametrize("rows,currency", [([], "SEK"), (None, "SEK"), ([], None)])
async def test_native_forecast_handles_absent_series(
    hass, forecast_card, rows, currency
):
    card, _ = forecast_card
    set_forecast(hass, rows, currency=currency)
    assert "<table>" not in render(hass, card)


@pytest.mark.parametrize("vat", ["excluded", "included", "unknown"])
async def test_native_forecast_declares_vat_without_adjusting_prices(
    hass, freezer, forecast_card, vat
):
    card, swedish = forecast_card
    freezer.move_to("2026-11-28T12:07:00+00:00")
    set_forecast(
        hass, [interval("2026-11-28T12:00:00Z", "2026-11-28T12:15:00Z", 0.5)], vat=vat
    )
    text = render(hass, card)
    labels = {
        "excluded": ("VAT excluded.", "Moms ingår inte."),
        "included": ("VAT included.", "Moms ingår."),
        "unknown": ("VAT treatment unknown.", "Momshantering okänd."),
    }
    assert labels[vat][swedish] in text
    assert ("0,5000" if swedish else "0.5000") in text


async def test_native_forecast_distinguishes_repeated_autumn_hour(
    hass, freezer, forecast_card
):
    card, _ = forecast_card
    await hass.config.async_set_time_zone("Europe/Stockholm")
    freezer.move_to("2026-10-24T23:59:00+00:00")
    set_forecast(
        hass,
        [
            interval("2026-10-25T00:00:00Z", "2026-10-25T00:15:00Z", 0),
            interval("2026-10-25T01:00:00Z", "2026-10-25T01:15:00Z", -0.1),
        ],
    )
    text = render(hass, card)
    assert "02:00 +0200–02:15 +0200" in text
    assert "02:00 +0100–02:15 +0100" in text
    assert text.count("<tr>") == 3
