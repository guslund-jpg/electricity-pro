"""Validation tests for the published dashboard examples."""

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
import pytest
from homeassistant.helpers.template import Template


DASHBOARD_EXAMPLES = Path(__file__).parents[1] / "examples" / "dashboards"
MONTHLY_TOTAL = "sensor.electricity_pro_total_cost_estimate_this_month"


def _language(path, english, swedish):
    """Select the expected user-facing assertion for each maintained example."""
    return swedish if path.stem.endswith("-sv") else english


def _monthly_cost_note(hass, path):
    dashboard = yaml.safe_load(path.read_text())
    note = next(
        card["content"]
        for card in _walk(dashboard)
        if isinstance(card, dict)
        and card.get("type") == "markdown"
        and MONTHLY_TOTAL in card["content"]
    )
    return Template(note, hass).async_render(parse_result=False)


@pytest.mark.parametrize("coverage", ["partial", "unverified", "tracked"])
async def test_dashboard_coverage_notes_render(hass, coverage) -> None:
    """Render both dashboards against real HA templates and representative states."""
    hass.states.async_set(
        "sensor.electricity_pro_cost_today",
        "0.48",
        {
            "source": "local_estimate",
            "priced_energy_kwh": "0.2",
        },
    )
    hass.states.async_set(
        "sensor.electricity_pro_cost_this_month",
        "0.48",
        {
            "source": "local_estimate",
            "priced_energy_kwh": "0.2",
        },
    )
    hass.states.async_set(
        "sensor.electricity_pro_consumption_weighted_average_price_today",
        "2.97",
        {
            "source": "local_estimate",
            "priced_energy_kwh": "0.18",
        },
    )
    hass.states.async_set(
        "sensor.electricity_pro_energy_this_month",
        "0.55",
        {
            "coverage": coverage,
            "tracking_started_at": "2026-09-14T12:00:00+00:00",
        },
    )
    for path in DASHBOARD_EXAMPLES.glob("*.yaml"):
        dashboard = yaml.safe_load(path.read_text())
        cards = [
            item
            for item in _walk(dashboard)
            if isinstance(item, dict) and item.get("type") == "markdown"
        ]
        rendered = "\n".join(
            str(Template(card["content"], hass).async_render(parse_result=False))
            for card in cards
        )
        assert (
            _language(
                path, "Partial supplier estimate", "Delvis beräknad elhandelskostnad"
            )
            in rendered
        )
        assert "0.2" in rendered
        assert (
            _language(
                path, "Cost & coverage details", "Om kostnader och mätningens täckning"
            )
            in rendered
        )
        assert (
            _language(path, "Partial monthly energy", "Delvis uppmätt månadsenergi")
            in rendered
        ) == (coverage == "partial")
        assert (
            _language(path, "Unverified monthly energy", "Ej verifierad månadsenergi")
            in rendered
        ) == (coverage == "unverified")
        names = {
            item.get("name") for item in _walk(dashboard) if isinstance(item, dict)
        }
        assert _language(path, "Supplier cost today", "Elhandelskostnad i dag") in names
        assert (
            _language(
                path, "Supplier cost this month", "Elhandelskostnad den här månaden"
            )
            in names
        )
        assert _language(path, "Cost today", "Kostnad i dag") not in names
        entity_cards = [
            item["entity"]
            for item in _walk(dashboard)
            if isinstance(item, dict)
            and item.get("type") in {"tile", "custom:mushroom-entity-card"}
        ]
        for suffix in ("today", "this_month"):
            assert entity_cards.index(
                "sensor.electricity_pro_total_cost_estimate_" + suffix
            ) < entity_cards.index("sensor.electricity_pro_cost_" + suffix)


async def test_household_dashboard_notes_explain_missing_fixed_fees(hass) -> None:
    hass.states.async_set(
        "sensor.electricity_pro_total_cost_estimate_today",
        "2",
        {
            "missing_components": ["fixed_supplier_fee", "fixed_grid_fee"],
        },
    )
    for path in DASHBOARD_EXAMPLES.glob("*.yaml"):
        dashboard = yaml.safe_load(path.read_text())
        rendered = "\n".join(
            Template(item["content"], hass).async_render(parse_result=False)
            for item in _walk(dashboard)
            if isinstance(item, dict) and item.get("type") == "markdown"
        )
        assert (
            _language(
                path,
                "fixed supplier fee, fixed grid fee",
                "fast elhandelsavgift, fast elnätsavgift",
            )
            in rendered
        )
        assert (
            _language(
                path,
                "Demand/other unconfigured charges excluded",
                "Effektavgifter och andra ej konfigurerade avgifter ingår inte",
            )
            in rendered
        )


@pytest.mark.parametrize("split", [False, True], ids=["legacy", "split"])
@pytest.mark.parametrize(
    ("state", "fixed_fees", "missing", "expected_fixed"),
    [
        (
            "275",
            "35",
            ["fixed_grid_fee"],
            (
                "Known fixed fees so far** 35.00 EUR",
                "Kända fasta avgifter hittills** 35,00 EUR",
            ),
        ),
        (
            "240",
            "0",
            [],
            (
                "Known fixed fees so far** 0.00 EUR",
                "Kända fasta avgifter hittills** 0,00 EUR",
            ),
        ),
        (
            "240",
            "0",
            ["fixed_supplier_fee", "fixed_grid_fee"],
            (
                "Fixed fees so far** Not available",
                "Fasta avgifter hittills** Uppgift saknas",
            ),
        ),
        ("unavailable", "35", ["fixed_grid_fee"], None),
    ],
    ids=["one-missing-fee", "known-zero", "both-missing-fees", "unavailable"],
)
async def test_monthly_dashboard_cost_breakdown(
    hass, state, fixed_fees, missing, expected_fixed, split
) -> None:
    """Render the breakdown without confusing missing amounts with zero."""
    attributes = {
        "variable_cost": "240",
        "accrued_fixed_fees": fixed_fees,
        "unit_of_measurement": "EUR",
        "priced_energy_kwh": "160",
        "missing_components": missing,
    }
    supplier = None if "fixed_supplier_fee" in missing else fixed_fees
    grid = None if "fixed_grid_fee" in missing else "0"
    if split:
        attributes["accrued_fixed_fee_breakdown"] = {"supplier": supplier, "grid": grid}
        attributes["variable_cost_breakdown"] = None
    hass.states.async_set(MONTHLY_TOTAL, state, attributes)
    for path in DASHBOARD_EXAMPLES.glob("*.yaml"):
        rendered = _monthly_cost_note(hass, path)
        assert (
            _language(path, "Breakdown not yet available", "Uppdelning saknas ännu")
            in rendered
        ) == (state != "unavailable")
        assert "kWh with a breakdown" not in rendered
        assert "kWh med uppdelning" not in rendered
        show_missing_note = bool(missing) and (not split or state == "unavailable")
        assert (
            _language(path, "**Missing:**", "**Saknas:**") in rendered
        ) == show_missing_note
        if expected_fixed is None:
            assert "EUR" not in rendered
            assert "160.0 kWh" not in rendered
            assert (
                _language(
                    path, "Fixed supplier fee so far", "Fast elhandelsavgift hittills"
                )
                not in rendered
            )
        else:
            assert (
                _language(
                    path, "Variable cost** 240.00 EUR", "Rörlig kostnad** 240,00 EUR"
                )
                in rendered
            )
            if split:
                labels_and_amounts = (
                    (
                        "Fixed supplier fee so far",
                        "Fast elhandelsavgift hittills",
                        supplier,
                    ),
                    ("Fixed grid fee so far", "Fast elnätsavgift hittills", grid),
                )
                for en, sv, fee in labels_and_amounts:
                    amount = (
                        _language(path, "Not available", "Uppgift saknas")
                        if fee is None
                        else _language(path, f"{fee}.00 EUR", f"{fee},00 EUR")
                    )
                    assert f"**{_language(path, en, sv)}** {amount}" in rendered
            else:
                assert _language(path, *expected_fixed) in rendered
            assert (
                _language(path, "160.0 kWh priced", "160.0 kWh prissatta") in rendered
            )


async def test_monthly_dashboard_itemizes_only_known_vat(hass):
    hass.states.async_set(
        MONTHLY_TOTAL,
        "4.20",
        {
            "variable_cost": "4.20",
            "accrued_fixed_fees": "0",
            "unit_of_measurement": "SEK",
            "variable_cost_breakdown": {
                "display": {"total": "4.20", "lines": {"market_energy": "4.20"}},
                "vat_display": {
                    "total": "4.20",
                    "lines": {
                        "market_energy": "2.95",
                        "market_energy_excluding_vat": "1.00",
                        "vat": "0.25",
                    },
                },
                "priced_energy_kwh": "2",
            },
        },
    )
    for path in DASHBOARD_EXAMPLES.glob("*.yaml"):
        rendered = _monthly_cost_note(hass, path)
        assert (
            _language(
                path,
                "- Spot energy (excl. VAT) 1.00 SEK",
                "- Spotpris (exkl. moms) 1,00 SEK",
            )
            in rendered
        )
        assert (
            _language(path, "- Spot energy 2.95 SEK", "- Spotpris 2,95 SEK") in rendered
        )
        assert (
            _language(
                path,
                "- VAT on specified items 0.25 SEK",
                "- Moms på specificerade poster 0,25 SEK",
            )
            in rendered
        )
        assert (
            _language(path, "**Variable cost** 4.20 SEK", "**Rörlig kostnad** 4,20 SEK")
            in rendered
        )


@pytest.mark.parametrize("adjustment", ["-0.01", "+0.01", None])
async def test_monthly_dashboard_shows_total_estimate_rounding(hass, adjustment):
    lines = {"variable": "633.09", "supplier": "15.26", "grid": "186.83"}
    total = Decimal("835.18") + Decimal(adjustment or 0)
    if adjustment is not None:
        lines["rounding_adjustment"] = adjustment
    hass.states.async_set(
        MONTHLY_TOTAL,
        str(total),
        {
            "variable_cost": "633.09",
            "accrued_fixed_fees": "202.09",
            "accrued_fixed_fee_breakdown": {"supplier": "15.26", "grid": "186.83"},
            "monthly_cost_display": {"total": str(total), "lines": lines},
            "unit_of_measurement": "SEK",
        },
    )
    for path in DASHBOARD_EXAMPLES.glob("*.yaml"):
        rendered = _monthly_cost_note(hass, path)
        label = _language(
            path, "Total estimate rounding", "Avrundning av totalestimatet"
        )
        if adjustment is None:
            assert label not in rendered
        else:
            amount = _language(path, adjustment, adjustment.replace(".", ","))
            assert any(
                line.strip().startswith(f"**{label}** {amount} SEK")
                for line in rendered.splitlines()
            )
            assert (
                _language(
                    path,
                    f"**Total estimate** {total} SEK",
                    f"**Totalestimat** {str(total).replace('.', ',')} SEK",
                )
                in rendered
            )


@pytest.mark.parametrize(
    ("rows", "covered"),
    [
        (
            (
                (
                    "supplier_price",
                    "52.00",
                    "Combined supplier price",
                    "Samlat elhandelspris",
                ),
                ("energy_tax", "18.00", "Energy tax", "Energiskatt"),
                (
                    "variable_grid_fee",
                    "9.00",
                    "Variable grid fee",
                    "Rörlig elnätsavgift",
                ),
                (
                    "unallocated_cost",
                    "20.00",
                    "Earlier unsplit cost",
                    "Äldre ospecificerad kostnad",
                ),
                ("rounding_adjustment", "+0.02", "Rounding", "Avrundning"),
            ),
            "60",
        ),
        (
            (
                ("market_energy", "-4.00", "Spot energy", "Spotpris"),
                ("supplier_markup", "0.00", "Supplier markup", "Elhandelspåslag"),
            ),
            "80",
        ),
        (
            (
                (
                    "bundled_price",
                    "52.00",
                    "Combined variable price",
                    "Samlat rörligt pris",
                ),
            ),
            "80",
        ),
    ],
    ids=["partial-breakdown", "separate-rates", "complete-price"],
)
async def test_monthly_dashboard_shows_variable_lines_and_coverage(hass, rows, covered):
    lines = {key: amount for key, amount, _, _ in rows}
    total = str(sum(map(Decimal, lines.values())))
    hass.states.async_set(
        MONTHLY_TOTAL,
        total,
        {
            "variable_cost": total,
            "variable_cost_breakdown": {
                "display": {"total": total, "lines": lines},
                "priced_energy_kwh": covered,
            },
            "accrued_fixed_fees": "0",
            "unit_of_measurement": "EUR",
            "priced_energy_kwh": "80",
        },
    )
    for path in DASHBOARD_EXAMPLES.glob("*.yaml"):
        rendered = _monthly_cost_note(hass, path)
        assert (
            _language(
                path,
                f"Variable cost** {total} EUR",
                f"Rörlig kostnad** {total.replace('.', ',')} EUR",
            )
            in rendered
        )
        assert (
            _language(
                path,
                f"80.0 kWh priced, of which {covered}.0 kWh with a breakdown",
                f"80.0 kWh prissatta, varav {covered}.0 kWh med uppdelning",
            )
            in rendered
        )
        assert [
            line.strip() for line in rendered.splitlines() if line.startswith("- ")
        ] == [
            _language(
                path, f"- {en} {amount} EUR", f"- {sv} {amount.replace('.', ',')} EUR"
            )
            for _, amount, en, sv in rows
        ]


async def test_cost_notes_remain_compact_and_prioritize_household_coverage(
    hass,
) -> None:
    """Keep the normal household summaries short instead of repeating the guide."""
    for suffix in ("today", "this_month"):
        hass.states.async_set(
            "sensor.electricity_pro_total_cost_estimate_" + suffix,
            "25",
            {
                "variable_cost": "20",
                "accrued_fixed_fees": "5",
                "accrued_fixed_fee_breakdown": {"supplier": "3", "grid": "2"},
                "unit_of_measurement": "EUR",
                "priced_energy_kwh": "2.09",
                "missing_components": [],
            },
        )
        hass.states.async_set(
            "sensor.electricity_pro_cost_" + suffix,
            "4",
            {
                "source": "local_estimate",
                "priced_energy_kwh": "1.23",
            },
        )
    hass.states.async_set(
        "sensor.electricity_pro_energy_this_month",
        "2.47",
        {
            "coverage": "partial",
            "tracking_started_at": "2026-09-14T21:08:00+02:00",
        },
    )
    for path in DASHBOARD_EXAMPLES.glob("*.yaml"):
        dashboard = yaml.safe_load(path.read_text())
        notes = [
            item
            for item in _walk(dashboard)
            if isinstance(item, dict)
            and item.get("type") == "markdown"
            and "docs/guides/costs-and-pricing.md" in item.get("content", "")
        ]
        assert len(notes) >= 2
        for note in notes:
            text = Template(note["content"], hass).async_render(parse_result=False)
            assert _language(path, "2.09 kWh priced", "2.09 kWh prissatta") in text
            assert "1.23" not in text
            assert len(text.split()) <= 55
            assert "docs/guides/costs-and-pricing.md" in text


async def test_dashboard_notes_do_not_call_external_costs_local_estimates(hass) -> None:
    """Absent attributes and provider totals render without misleading warnings."""
    hass.states.async_set("sensor.electricity_pro_cost_today", "50")
    for path in DASHBOARD_EXAMPLES.glob("*.yaml"):
        dashboard = yaml.safe_load(path.read_text())
        for card in _walk(dashboard):
            if isinstance(card, dict) and card.get("type") == "markdown":
                rendered = Template(card["content"], hass).async_render(
                    parse_result=False
                )
                assert (
                    _language(path, "Partial estimate", "Delvis beräknad kostnad")
                    not in rendered
                )
                assert (
                    _language(
                        path,
                        "Partial supplier estimate",
                        "Delvis beräknad elhandelskostnad",
                    )
                    not in rendered
                )
                assert (
                    _language(
                        path, "Unverified monthly energy", "Ej verifierad månadsenergi"
                    )
                    not in rendered
                )


def _walk(value: Any) -> Iterator[Any]:
    """Yield every nested value from a YAML document."""
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_dashboard_condition_state_not_is_scalar() -> None:
    """Home Assistant conditional cards require one state_not value."""
    for dashboard_path in DASHBOARD_EXAMPLES.glob("*.yaml"):
        dashboard = yaml.safe_load(dashboard_path.read_text(encoding="utf-8"))
        invalid = [
            item
            for item in _walk(dashboard)
            if isinstance(item, dict)
            and "state_not" in item
            and not isinstance(item["state_not"], str)
        ]
        assert not invalid, f"{dashboard_path.name} contains invalid state_not values"


def test_standard_dashboard_covers_core_measurements_and_insights() -> None:
    """Standard dashboard should cover the core product without custom cards."""
    dashboard = yaml.safe_load(
        (DASHBOARD_EXAMPLES / "electricity-pro.yaml").read_text(encoding="utf-8")
    )
    entity_ids = {
        item["entity"]
        for item in _walk(dashboard)
        if isinstance(item, dict) and isinstance(item.get("entity"), str)
    }

    assert {
        "sensor.electricity_pro_current_power",
        "sensor.electricity_pro_current_market_price",
        "sensor.electricity_pro_current_supplier_price",
        "sensor.electricity_pro_effective_price",
        "sensor.electricity_pro_current_cost_rate",
        "sensor.electricity_pro_energy_today",
        "sensor.electricity_pro_cost_today",
        "sensor.electricity_pro_consumption_weighted_average_price_today",
        "sensor.electricity_pro_average_power_today",
        "sensor.electricity_pro_peak_power_today",
        "sensor.electricity_pro_peak_power_time_today",
        "sensor.electricity_pro_energy_this_month",
        "sensor.electricity_pro_cost_this_month",
        "sensor.electricity_pro_consumption_timing_score_yesterday",
        "binary_sensor.electricity_pro_good_time_to_use_electricity",
    } <= entity_ids

    assert not {
        str(item.get("type")) for item in _walk(dashboard) if isinstance(item, dict)
    } & {"custom:mushroom-template-card", "custom:apexcharts-card"}

    advice_tiles = {
        item["card"]["name"]: item
        for item in _walk(dashboard)
        if isinstance(item, dict)
        and item.get("type") == "conditional"
        and isinstance(item.get("card"), dict)
        and item["card"].get("name")
        in {"Good time to use electricity", "Wait for a better price"}
    }
    assert set(advice_tiles) == {
        "Good time to use electricity",
        "Wait for a better price",
    }
    for tile in advice_tiles.values():
        assert tile["card"]["entity"] == "sensor.electricity_pro_effective_price"
    assert (
        advice_tiles["Good time to use electricity"]["conditions"][0]["state"] == "on"
    )
    assert advice_tiles["Wait for a better price"]["conditions"][0]["state"] == "off"


@pytest.mark.parametrize("path", sorted(DASHBOARD_EXAMPLES.glob("*.yaml")))
def test_dashboard_tabs_group_daily_price_and_electrical_cards(path: Path) -> None:
    """Users can find the same kinds of cards in each localized layout."""
    views = yaml.safe_load(path.read_text(encoding="utf-8"))["views"]
    assert [view["path"] for view in views] == ["overview", "trends", "details"]
    assert [view["title"] for view in views] == _language(
        path,
        ["Overview", "Prices and Trends", "Electrical Details"],
        ["Översikt", "Priser och trender", "Eldetaljer"],
    )
    overview, trends, details = [set(_walk_entity_ids(view)) for view in views]
    assert {
        "sensor.electricity_pro_current_power",
        "sensor.electricity_pro_effective_price",
        "sensor.electricity_pro_current_cost_rate",
        "sensor.electricity_pro_energy_today",
        "sensor.electricity_pro_total_cost_estimate_today",
    } <= overview
    assert {
        "sensor.electricity_pro_cheapest_1h_window_start",
        "sensor.electricity_pro_current_market_price",
        MONTHLY_TOTAL,
    } <= trends
    assert {
        "sensor.electricity_pro_peak_power_time_today",
        "sensor.electricity_pro_monthly_peak_hour_consumption",
        "sensor.electricity_pro_current_l1",
        "sensor.electricity_pro_voltage_l3",
    } <= details
    assert MONTHLY_TOTAL not in overview | details
    electrical_cards = [
        card
        for card in views[2]["cards"]
        if card["type"] not in {"heading", "custom:mushroom-title-card"}
    ]
    assert "sensor.electricity_pro_current_l1" in _walk_entity_ids(electrical_cards[0])
    assert "sensor.electricity_pro_peak_power_today" in _walk_entity_ids(
        electrical_cards[1]
    )
    power_charts = [
        view["path"]
        for view in views
        for card in _walk(view)
        if isinstance(card, dict)
        and card.get("type") in {"history-graph", "custom:apexcharts-card"}
        and "sensor.electricity_pro_current_power" in _walk_entity_ids(card)
    ]
    assert power_charts and set(power_charts) == {"details"}
    assert all(
        "sensor.electricity_pro_current_power" in _walk_entity_ids(card)
        for card in electrical_cards[-len(power_charts) :]
    )


def _walk_entity_ids(value: Any) -> Iterator[str]:
    for item in _walk(value):
        if isinstance(item, dict) and isinstance(item.get("entity"), str):
            yield item["entity"]


def test_enhanced_dashboard_live_header_precision() -> None:
    """Enhanced live charts use readable power and price precision."""
    dashboard = yaml.safe_load(
        (DASHBOARD_EXAMPLES / "electricity-pro-enhanced.yaml").read_text(
            encoding="utf-8"
        )
    )
    series_by_entity = {
        series["entity"]: series
        for item in _walk(dashboard)
        if isinstance(item, dict) and isinstance(item.get("series"), list)
        for series in item["series"]
        if isinstance(series, dict) and "entity" in series
    }

    assert (
        series_by_entity["sensor.electricity_pro_current_power"]["float_precision"] == 0
    )
    for entity_id in (
        "sensor.electricity_pro_current_market_price",
        "sensor.electricity_pro_current_supplier_price",
        "sensor.electricity_pro_effective_price",
    ):
        assert series_by_entity[entity_id]["float_precision"] == 2


def test_enhanced_dashboard_advice_formats_effective_price_to_two_decimals() -> None:
    """Enhanced advice card should not expose raw effective-price precision."""
    dashboard = yaml.safe_load(
        (DASHBOARD_EXAMPLES / "electricity-pro-enhanced.yaml").read_text(
            encoding="utf-8"
        )
    )
    advice_card = next(
        item
        for item in _walk(dashboard)
        if isinstance(item, dict)
        and item.get("type") == "custom:mushroom-template-card"
        and item.get("entity")
        == "binary_sensor.electricity_pro_good_time_to_use_electricity"
    )

    assert "'%.2f' | format" in advice_card["secondary"]


def test_enhanced_dashboard_spot_price_presentation() -> None:
    """Enhanced dashboard compares and previews provider-independent prices."""
    dashboard = yaml.safe_load(
        (DASHBOARD_EXAMPLES / "electricity-pro-enhanced.yaml").read_text(
            encoding="utf-8"
        )
    )
    charts = [
        item
        for item in _walk(dashboard)
        if isinstance(item, dict) and item.get("type") == "custom:apexcharts-card"
    ]

    comparison = next(
        chart
        for chart in charts
        if chart.get("header", {}).get("title") == "Spot, supplier, and effective price"
    )
    assert comparison["yaxis"][0]["min"] == "~0"
    assert [series["entity"] for series in comparison["series"]] == [
        "sensor.electricity_pro_current_market_price",
        "sensor.electricity_pro_current_supplier_price",
        "sensor.electricity_pro_effective_price",
    ]

    forecast = next(
        chart
        for chart in charts
        if chart.get("header", {}).get("title") == "Spot price forecast"
    )
    assert forecast["graph_span"] == "50h"
    assert forecast["span"] == {"start": "day"}
    assert forecast["yaxis"][0]["min"] == "~0"
    assert forecast["update_delay"] == "3s"
    # Interval polling can leave ApexCharts 2.2.3 busy before initialization.
    # Keep the forecast on the default entity-driven update path.
    assert "update_interval" not in forecast
    assert forecast["now"]["show"] is True
    assert forecast["apex_config"]["chart"] == {
        "animations": {"enabled": False},
        "redrawOnParentResize": True,
        "redrawOnWindowResize": True,
    }
    assert forecast["series"][0]["curve"] == "stepline"
    assert forecast["series"][0]["show"]["in_header"] == "before_now"
    assert "entity.attributes.forecast" in forecast["series"][0]["data_generator"]


def test_enhanced_dashboard_phase_current_gauges_share_20a_scale() -> None:
    """Phase-current gauges should use one comparable example scale."""
    dashboard = yaml.safe_load(
        (DASHBOARD_EXAMPLES / "electricity-pro-enhanced.yaml").read_text(
            encoding="utf-8"
        )
    )
    cards_by_entity = {
        item["entity"]: item
        for item in _walk(dashboard)
        if isinstance(item, dict)
        and item.get("type") == "gauge"
        and str(item.get("entity", "")).startswith("sensor.electricity_pro_current_l")
    }

    expected_entities = {
        "sensor.electricity_pro_current_l1",
        "sensor.electricity_pro_current_l2",
        "sensor.electricity_pro_current_l3",
    }
    assert cards_by_entity.keys() == expected_entities
    for card in cards_by_entity.values():
        assert card["min"] == 0
        assert card["max"] == 20
        assert card["needle"] is True
        assert card["severity"] == {"green": 0, "yellow": 14, "red": 18}
