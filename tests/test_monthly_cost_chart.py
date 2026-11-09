"""Exercise the published Enhanced chart and its coverage note in both languages."""

import json
import shutil
import subprocess
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from homeassistant.helpers.template import Template

from custom_components.electricity_pro.monthly_cost_archive import (
    MonthlyVariableCostArchive,
    monthly_cost_chart_rows,
)
from custom_components.electricity_pro.pricing import VariableCostComponent

ENTITY = "sensor.electricity_pro_monthly_variable_cost_history"
DASHBOARDS = Path(__file__).parents[1] / "examples" / "dashboards"


@pytest.fixture
def chart_rows():
    archive = MonthlyVariableCostArchive()
    for (start_month, start_day, end_month, end_day), kwh, amounts in (
        ((8, 1, 9, 1), 40, {VariableCostComponent.BUNDLED_PRICE: "14"}),
        (
            (9, 15, 9, 30),
            20,
            {
                VariableCostComponent.MARKET_ENERGY: "-3",
                VariableCostComponent.SUPPLIER_MARKUP: "0",
            },
        ),
        ((11, 1, 11, 2), 3, {VariableCostComponent.SUPPLIER_PRICE: "7"}),
    ):
        archive.record(
            datetime(2026, start_month, start_day, tzinfo=UTC),
            datetime(2026, end_month, end_day, tzinfo=UTC),
            "SEK",
            Decimal(kwh),
            tuple(
                (component, Decimal(amount)) for component, amount in amounts.items()
            ),
        )
    return monthly_cost_chart_rows(archive.months, date(2026, 11, 2))


@pytest.fixture(params=["en", "sv"])
def chart_cards(request):
    suffix = "-sv" if request.param == "sv" else ""
    dashboard = yaml.safe_load(
        (DASHBOARDS / f"electricity-pro-enhanced{suffix}.yaml").read_text()
    )
    trends = next(view for view in dashboard["views"] if view["path"] == "trends")
    block = next(
        card
        for card in trends["cards"]
        if card["type"] == "conditional"
        and card["conditions"][0].get("entity") == ENTITY
    )
    assert block["conditions"] == [
        {"condition": "state", "entity": ENTITY, "state_not": "unavailable"},
        {"condition": "state", "entity": ENTITY, "state_not": "unknown"},
    ]
    chart, coverage = block["card"]["cards"]
    return request.param, chart, coverage


async def test_monthly_chart_coverage_labels(hass, chart_cards, chart_rows):
    language, _, note = chart_cards
    hass.states.async_set(
        ENTITY, "7", {"months": chart_rows, "unit_of_measurement": "SEK"}
    )
    text = Template(note["content"], hass).async_render(parse_result=False)
    rows = [line for line in text.splitlines() if line.startswith("| 2026-")]
    assert [line.split("|")[1].strip() for line in rows] == [
        "2026-08",
        "2026-09",
        "2026-11",
    ]
    labels = (
        ("Full month", "Partial coverage", "To date")
        if language == "en"
        else ("Hel månad", "Delvis täckt", "Hittills")
    )
    assert [line.split("|")[2].strip() for line in rows] == list(labels)
    assert [Decimal(line.split("|")[3].strip().replace(",", ".")) for line in rows] == [
        40,
        20,
        3,
    ]


def test_monthly_chart_series_keep_zero_negative_and_missing_distinct(
    chart_cards, chart_rows
):
    _, chart, _ = chart_cards
    assert chart["stacked"] and chart["all_series_config"]["type"] == "column"
    assert chart["apex_config"]["tooltip"]["hideEmptySeries"] is False
    assert all(series["entity"] == ENTITY for series in chart["series"])
    assert len(chart_rows) == 12 and chart_rows[0]["month"] == "2025-12"
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to execute the ApexCharts data generators")
    payload = {
        "series": chart["series"],
        "months": chart_rows,
        "tooltip": chart["apex_config"]["tooltip"]["custom"].removeprefix("EVAL:"),
    }
    result = subprocess.run(
        [
            node,
            "-e",
            """
const { series, months, tooltip } = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const entity = { attributes: { months } };
const points = series.map(item => new Function('entity', item.data_generator)(entity));
const document = { createElement: () => ({children: [], style: {}, append(child) { this.children.push(child); }}) };
const w = {
  globals: { seriesX: points.map(item => item.map(([timestamp]) => timestamp)) },
  config: { series, tooltip: { y: { formatter: value => `<strong>${value} SEK</strong>` } } },
};
const render = new Function('document', `return (${tooltip})`)(document);
const info = render({series: points.map(item => item.map(([, value]) => value)), dataPointIndex: 9, w});
process.stdout.write(JSON.stringify({points, info: info.children.map(child => child.textContent)}));
""",
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    output = json.loads(result.stdout)
    points = output["points"]
    assert output["info"] == [
        "2026-09",
        f"{chart['series'][0]['name']}: -3 SEK",
        f"{chart['series'][1]['name']}: 0 SEK",
    ]
    assert [[value for _, value in series[-4:]] for series in points] == [
        [None, -3, None, None],
        [None, 0, None, None],
        [None, None, None, 7],
        [14, None, None, None],
        [None, None, None, None],
        [None, None, None, None],
    ]
    expected_dates = [
        int(
            datetime.fromisoformat(row["month"] + "-15T12:00:00+00:00").timestamp()
            * 1000
        )
        for row in chart_rows
    ]
    assert all(
        [timestamp for timestamp, _ in series] == expected_dates for series in points
    )
