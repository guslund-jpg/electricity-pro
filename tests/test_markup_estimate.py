"""Safeguards for the optional, confirmed Tibber forecast addition."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.forecast import ForecastInterval
from custom_components.electricity_pro.markup_estimate import (
    MarkupEstimate, async_estimate_markup, estimate_markup,
)

NOW = datetime(2026, 9, 25, 12, tzinfo=timezone.utc)


def samples(*, negative=False):
    rows, market = [], []
    for index in range(5):
        start = NOW - timedelta(minutes=75 - index * 15)
        price = Decimal(index) / 10 - (1 if negative else 0)
        rows.append({"start_time": start.isoformat(), "price": float(price * Decimal("1.25") + Decimal("0.18"))})
        market.append(ForecastInterval(start, start + timedelta(minutes=15), price, "SEK", "SE3"))
    return rows, market


@pytest.mark.parametrize("negative", [False, True])
def test_exact_pairs_and_negative_spot(negative):
    rows, market = samples(negative=negative)
    result = estimate_markup(rows, market, vat_rate=25, now=NOW)
    assert result.value == Decimal("0.180")
    assert result.count == 4  # No guessed end for the final Tibber point.


@pytest.mark.parametrize("vat", [None, -1, 101, float("nan"), float("inf")])
def test_explicit_valid_vat_required(vat):
    rows, market = samples()
    with pytest.raises(ValueError):
        estimate_markup(rows, market, vat_rate=vat, now=NOW)


def test_zero_vat_is_valid():
    rows, market = samples()
    for row, interval in zip(rows, market):
        row["price"] = float(interval.market_price + Decimal("0.18"))
    assert estimate_markup(rows, market, vat_rate=0, now=NOW).value == Decimal("0.180")


@pytest.mark.parametrize("failure", ["few", "future", "stale", "duplicate", "nan", "variable", "negative", "resolution", "naive"])
def test_refuse_unreliable_comparison(failure):
    rows, market = samples()
    now = NOW
    if failure == "few":
        rows.pop()
    elif failure == "future":
        now -= timedelta(hours=1)
    elif failure == "stale":
        now += timedelta(days=2)
    elif failure == "duplicate":
        rows.append(rows[0])
    elif failure == "nan":
        rows[0]["price"] = float("nan")
    elif failure == "variable":
        rows[0]["price"] += 0.02
    elif failure == "negative":
        for row in rows:
            row["price"] -= 1
    elif failure == "resolution":
        market = [ForecastInterval(market[0].start, market[0].start + timedelta(hours=1), Decimal(0), "SEK", "SE3")]
    elif failure == "naive":
        rows[0]["start_time"] = "2026-09-25T10:45:00"
    with pytest.raises(ValueError):
        estimate_markup(rows, market, vat_rate=25, now=now)


def test_utc_matching_ignores_timestamp_offset():
    rows, market = samples()
    for row in rows:
        row["start_time"] = datetime.fromisoformat(row["start_time"]).astimezone(timezone(timedelta(hours=2))).isoformat()
    assert estimate_markup(rows, market, vat_rate=25, now=NOW).count == 4


async def source(hass):
    tibber = MockConfigEntry(domain="tibber", data={})
    tibber.add_to_hass(hass)
    nordpool = MockConfigEntry(domain="nordpool", data={"areas": ["SE3"], "currency": "SEK"})
    nordpool.add_to_hass(hass)
    entity = er.async_get(hass).async_get_or_create(
        "sensor", "tibber", "home-price", config_entry=tibber,
        translation_key="electricity_price",
    )
    hass.states.async_set(entity.entity_id, "1.43", {"app_nickname": "Home", "unit_of_measurement": "SEK/kWh"})
    return dict(price_entity=entity.entity_id, nordpool_entry_id=nordpool.entry_id, area="SE3", vat_rate=25)


async def test_public_action_adapter(hass):
    args = await source(hass)
    rows, market = samples()
    with (
        patch("custom_components.electricity_pro.markup_estimate.dt_util.now", return_value=NOW),
        patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock(return_value={"prices": {"Home": rows}})) as call,
        patch("custom_components.electricity_pro.markup_estimate.async_get_nordpool_forecast_intervals_for_date", AsyncMock(return_value=market)),
    ):
        result = await async_estimate_markup(hass, **args)
    assert result.value == Decimal("0.180")
    assert call.call_args.args[:2] == ("tibber", "get_prices")


@pytest.mark.parametrize("failure", ["unit", "unavailable", "nickname", "area", "account"])
async def test_adapter_refuses_unverified_metadata(hass, failure):
    args = await source(hass)
    state = hass.states.get(args["price_entity"])
    attrs = dict(state.attributes)
    if failure == "unit":
        attrs["unit_of_measurement"] = "EUR/kWh"
    elif failure == "nickname":
        attrs.pop("app_nickname")
    elif failure == "area":
        args["area"] = "SE4"
    elif failure == "account":
        MockConfigEntry(domain="tibber", data={}).add_to_hass(hass)
    hass.states.async_set(args["price_entity"], "unavailable" if failure == "unavailable" else "1.43", attrs)
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as call:
        with pytest.raises(ValueError):
            await async_estimate_markup(hass, **args)
        call.assert_not_called()


@pytest.mark.parametrize("accept", [False, True])
async def test_options_estimate_requires_review_and_allows_edit(hass, accept):
    nordpool = MockConfigEntry(domain="nordpool", data={"areas": ["SE3", "SE4"], "currency": "SEK"})
    nordpool.add_to_hass(hass)
    entry = MockConfigEntry(domain="electricity_pro", data={
        "source_profile": "tibber", "power_entity": "sensor.power",
        "price_entity": "sensor.price", "supplier_markup_per_kwh": 0.12,
    })
    entry.add_to_hass(hass)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"forecast_nordpool_config_entry": nordpool.entry_id})
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {
        "supplier_markup_per_kwh": 0.12, "price_vat_rate": 25, "estimate_supplier_markup": True,
    })
    assert flow["step_id"] == "tibber_markup_estimate"
    with patch("custom_components.electricity_pro.config_flow.async_estimate_markup", AsyncMock(return_value=MarkupEstimate(Decimal("0.18"), Decimal("0.001"), 12, "SEK"))):
        flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"forecast_price_area": "SE3", "confirm_matching_area": True})
    assert flow["step_id"] == "tibber_markup_review"
    assert entry.options == {}
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"supplier_markup_per_kwh": 0.19, "use_estimate": accept})
    if accept:
        assert flow["type"] == "create_entry"
        assert flow["data"]["supplier_markup_per_kwh"] == 0.19
        assert flow["data"]["forecast_price_area"] == "SE3"
        assert "estimate_supplier_markup" not in flow["data"]
    else:
        assert flow["step_id"] == "tibber_forecast_pricing"
        flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"supplier_markup_per_kwh": 0.12, "price_vat_rate": 25})
        assert flow["step_id"] == "forecast_area"
        flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"forecast_price_area": "SE3"})
        assert flow["data"]["supplier_markup_per_kwh"] == 0.12


@pytest.mark.parametrize("areas", [["SE3"], ["SE3", "SE4"]])
async def test_initial_setup_accepts_estimate_for_confirmed_area(hass, areas):
    tibber = MockConfigEntry(domain="tibber", data={})
    tibber.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=tibber.entry_id, identifiers={("tibber", "home")},
    )
    for key in ("power", "electricity_price"):
        er.async_get(hass).async_get_or_create(
            "sensor", "tibber", key, device_id=device.id,
            config_entry=tibber, translation_key=key,
        )
    nordpool = MockConfigEntry(domain="nordpool", data={"areas": areas, "currency": "SEK"})
    nordpool.add_to_hass(hass)
    flow = await hass.config_entries.flow.async_init("electricity_pro", context={"source": config_entries.SOURCE_USER})
    flow = await hass.config_entries.flow.async_configure(flow["flow_id"], {"setup_method": "tibber"})
    flow = await hass.config_entries.flow.async_configure(flow["flow_id"], {"forecast_nordpool_config_entry": nordpool.entry_id})
    flow = await hass.config_entries.flow.async_configure(flow["flow_id"], {"price_vat_rate": 25, "estimate_supplier_markup": True})
    assert flow["step_id"] == "tibber_markup_estimate"
    with patch("custom_components.electricity_pro.config_flow.async_estimate_markup", AsyncMock(return_value=MarkupEstimate(Decimal("0.18"), Decimal(0), 4, "SEK"))):
        flow = await hass.config_entries.flow.async_configure(flow["flow_id"], {"forecast_price_area": "SE3", "confirm_matching_area": True})
    assert flow["step_id"] == "tibber_markup_review"
    flow = await hass.config_entries.flow.async_configure(flow["flow_id"], {"supplier_markup_per_kwh": 0.18, "use_estimate": True})
    assert flow["type"] == "create_entry"
    assert flow["data"]["supplier_markup_per_kwh"] == 0.18
    assert flow["data"]["forecast_price_area"] == "SE3"


@pytest.mark.parametrize("error", [ValueError(), HomeAssistantError(), TimeoutError()])
async def test_failed_estimate_can_return_to_manual_without_saving(hass, error):
    nordpool = MockConfigEntry(domain="nordpool", data={"areas": ["SE3"], "currency": "SEK"})
    nordpool.add_to_hass(hass)
    entry = MockConfigEntry(domain="electricity_pro", data={"source_profile": "tibber", "power_entity": "sensor.power", "supplier_markup_per_kwh": 0.12})
    entry.add_to_hass(hass)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"forecast_nordpool_config_entry": nordpool.entry_id})
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"supplier_markup_per_kwh": 0.12, "price_vat_rate": 25, "estimate_supplier_markup": True})
    with patch("custom_components.electricity_pro.config_flow.async_estimate_markup", AsyncMock(side_effect=error)):
        flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"forecast_price_area": "SE3", "confirm_matching_area": True})
    assert flow["errors"] == {"base": "markup_estimate_unavailable"}
    assert entry.options == {}
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"confirm_matching_area": False})
    assert flow["step_id"] == "tibber_forecast_pricing"
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"supplier_markup_per_kwh": 0.12, "price_vat_rate": 25})
    assert flow["data"]["supplier_markup_per_kwh"] == 0.12


def test_estimation_control_not_in_standard_or_main_tibber_form():
    from custom_components.electricity_pro.config_flow import _entity_schema, _tibber_settings_schema
    for schema in (_entity_schema(), _tibber_settings_schema()):
        assert "estimate_supplier_markup" not in {key.schema for key in schema.schema}


async def test_duplicate_home_names_are_rejected(hass):
    args = await source(hass)
    second = er.async_get(hass).async_get_or_create("sensor", "tibber", "second-price", translation_key="electricity_price")
    hass.states.async_set(second.entity_id, "1.43", {"app_nickname": "Home"})
    with pytest.raises(ValueError, match="Ambiguous Tibber home names"):
        await async_estimate_markup(hass, **args)


@pytest.mark.parametrize("response", [None, {}, {"prices": {}}, {"prices": {"Home": None}}])
async def test_missing_action_prices_are_rejected(hass, response):
    args = await source(hass)
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock(return_value=response)):
        with pytest.raises(ValueError):
            await async_estimate_markup(hass, **args)
