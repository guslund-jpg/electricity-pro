"""Exercise the shared market screen through Home Assistant's flow manager."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from tests.flow_helpers import confirm_measurements, start_settings

DOMAIN = "electricity_pro"
SOURCE = "forecast_nordpool_config_entry"
AREA = "forecast_price_area"


def add_market(hass, areas=None, currency="SEK", **kwargs):
    entry = MockConfigEntry(
        domain="nordpool",
        title="Nord Pool home",
        data={"areas": areas if areas is not None else ["SE3"], "currency": currency},
        **kwargs,
    )
    entry.add_to_hass(hass)
    return entry


def shown_values(result):
    return {
        key.schema: (key.description or {}).get("suggested_value")
        for key in result["data_schema"].schema
    }


async def start_setup(hass, profile):
    if profile == "tibber":
        tibber = MockConfigEntry(domain="tibber")
        tibber.add_to_hass(hass)
        device = dr.async_get(hass).async_get_or_create(
            config_entry_id=tibber.entry_id, identifiers={("tibber", "home")}
        )
        for key in ("power", "electricity_price"):
            er.async_get(hass).async_get_or_create(
                "sensor", "tibber", key, device_id=device.id, translation_key=key
            )
    manager = hass.config_entries.flow
    result = await manager.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await manager.async_configure(result["flow_id"], {"setup_method": profile})
    return manager, await confirm_measurements(manager, result)


async def open_market(hass, profile="custom", data=None, options=None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "source_profile": profile,
            "power_entity": "sensor.power",
            **(data or {}),
        },
        options=options or {},
    )
    entry.add_to_hass(hass)
    manager = hass.config_entries.options
    menu = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        menu["flow_id"], {"next_step_id": "market_prices"}
    )
    return entry, manager, result


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_setup_resolves_market_before_vat_and_inherits_currency(
    hass, freezer, profile
):
    freezer.move_to("2026-11-07T12:00:00Z")
    market = add_market(hass, currency="EUR")
    manager, result = await start_setup(hass, profile)
    assert result["step_id"] == "market_prices"
    assert shown_values(result)[SOURCE] == market.entry_id
    assert result["description_placeholders"] == {
        "source": "Nord Pool home",
        "area": "SE3",
        "country": "SE",
        "currency": "EUR",
    }
    assert AREA not in shown_values(result)
    result = await manager.async_configure(result["flow_id"], {SOURCE: market.entry_id})
    assert result["step_id"] == ("manual" if profile == "custom" else "tibber_settings")
    assert SOURCE not in shown_values(result)
    if profile == "tibber":
        result = await manager.async_configure(result["flow_id"], {})
        assert result["step_id"] == "tibber_forecast_pricing"
    values = result["data_schema"]({})
    assert values["price_vat_rate"] == 25
    # Accepting the displayed default saves it without a separate country/review step.
    result = await manager.async_configure(result["flow_id"], values)
    assert result["type"] == "create_entry"
    assert result["data"][SOURCE] == market.entry_id
    assert not result["data"].get(AREA)
    assert result["data"]["price_vat_rate"] == 25
    if profile == "tibber":
        assert result["data"]["price_vat_treatment"] == "included"


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_multi_country_area_determines_subsequent_editable_vat(
    hass, freezer, profile
):
    freezer.move_to("2026-11-07T12:00:00Z")
    market = add_market(hass, ["SE3", "FI"], currency="NOK")
    manager, result = await start_setup(hass, profile)
    assert AREA in shown_values(result)
    result = await manager.async_configure(result["flow_id"], {SOURCE: market.entry_id})
    assert result["step_id"] == "market_area"
    result = await manager.async_configure(result["flow_id"], {AREA: "FI"})
    if profile == "tibber":
        result = await manager.async_configure(result["flow_id"], {})
    assert result["data_schema"]({})["price_vat_rate"] == 25.5
    values = {**result["data_schema"]({}), "price_vat_rate": 12.3}
    result = await manager.async_configure(result["flow_id"], values)
    assert result["type"] == "create_entry"
    assert result["data"][AREA] == "FI"
    assert result["data"]["price_vat_rate"] == 12.3


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_norwegian_setup_still_requires_household_context(hass, freezer, profile):
    freezer.move_to("2026-11-07T12:00:00Z")
    market = add_market(hass, ["NO4"], currency="NOK")
    manager, result = await start_setup(hass, profile)
    result = await manager.async_configure(result["flow_id"], {SOURCE: market.entry_id})
    if profile == "tibber":
        result = await manager.async_configure(result["flow_id"], {})
    assert "price_vat_rate" not in result["data_schema"]({})
    result = await manager.async_configure(result["flow_id"], {})
    assert result["step_id"] == "vat_context"
    result = await manager.async_configure(
        result["flow_id"], {"vat_context": "north_household"}
    )
    assert result["step_id"] == "vat_review"
    assert result["data_schema"]({})["price_vat_rate"] == 0


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_pricing_resolves_missing_saved_area_before_vat_without_early_save(
    hass, freezer, profile
):
    freezer.move_to("2026-11-07T12:00:00Z")
    market = add_market(hass, ["SE3", "FI"], currency="EUR")
    entry, manager, result = await open_market(
        hass,
        profile,
        data={SOURCE: market.entry_id},
        options={"fixed_grid_fee_monthly": 0},
    )
    original = dict(entry.options)
    manager.async_abort(result["flow_id"])
    result = await start_settings(manager, entry.entry_id)
    assert result["step_id"] == "market_area"
    result = await manager.async_configure(result["flow_id"], {AREA: "FI"})
    assert result["step_id"] == "init"
    assert dict(entry.options) == original
    if profile == "tibber":
        result = await manager.async_configure(result["flow_id"], {})
        assert result["step_id"] == "tibber_forecast_pricing"
    assert result["data_schema"]({})["price_vat_rate"] == 25.5
    manager.async_abort(result["flow_id"])
    assert dict(entry.options) == original
    result = await start_settings(manager, entry.entry_id)
    assert result["step_id"] == "market_area"
    result = await manager.async_configure(result["flow_id"], {AREA: "FI"})
    result = await manager.async_configure(result["flow_id"], {})
    if profile == "tibber":
        result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    assert entry.options[AREA] == "FI"
    assert entry.options["price_vat_rate"] == 25.5
    assert entry.options["fixed_grid_fee_monthly"] == 0


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_saved_area_is_editable_without_repeating_vat(hass, profile):
    market = add_market(hass, ["SE3", "SE4"])
    options = {AREA: "SE4", "price_vat_rate": 0, "fixed_grid_fee_monthly": 0}
    entry, manager, result = await open_market(
        hass, profile, data={SOURCE: market.entry_id, AREA: "SE3"}, options=options
    )
    assert shown_values(result)[AREA] == "SE4"
    result = await manager.async_configure(
        result["flow_id"], {SOURCE: market.entry_id, AREA: "SE3"}
    )
    assert result["type"] == "create_entry"
    assert dict(entry.options) == {**options, SOURCE: market.entry_id, AREA: "SE3"}
    assert entry.data[AREA] == "SE3"


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_changed_source_requires_its_own_area_and_cancel_is_atomic(hass, profile):
    old = add_market(hass, ["SE3", "SE4"])
    new = add_market(hass, ["SE4", "FI"], currency="EUR")
    data = {SOURCE: old.entry_id, AREA: "SE4", "supplier_markup_per_kwh": 0.119}
    options = {"price_vat_rate": 17.2, "grid_fee_per_kwh": 0.4}
    entry, manager, result = await open_market(hass, profile, data, options)
    result = await manager.async_configure(
        result["flow_id"], {SOURCE: new.entry_id, AREA: "SE4"}
    )
    assert result["step_id"] == "market_area"
    assert result["description_placeholders"]["currency"] == "EUR"
    assert shown_values(result)[AREA] is None
    assert dict(entry.options) == options
    manager.async_abort(result["flow_id"])
    menu = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        menu["flow_id"], {"next_step_id": "market_prices"}
    )
    assert shown_values(result)[SOURCE] == old.entry_id
    assert shown_values(result)[AREA] == "SE4"
    result = await manager.async_configure(result["flow_id"], {SOURCE: new.entry_id})
    result = await manager.async_configure(result["flow_id"], {AREA: "FI"})
    assert dict(entry.options) == {**options, SOURCE: new.entry_id, AREA: "FI"}
    assert dict(entry.data) == {
        "source_profile": profile,
        "power_entity": "sensor.power",
        **data,
    }


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_clear_and_reopen_does_not_auto_enable_the_only_market(hass, profile):
    market = add_market(hass)
    entry, manager, result = await open_market(
        hass, profile, data={SOURCE: market.entry_id, AREA: "SE4", "price_vat_rate": 0}
    )
    result = await manager.async_configure(result["flow_id"], {})
    assert dict(entry.options) == {SOURCE: None, AREA: None}
    menu = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        menu["flow_id"], {"next_step_id": "market_prices"}
    )
    assert shown_values(result)[SOURCE] is None
    manager.async_abort(result["flow_id"])
    result = await start_settings(manager, entry.entry_id)
    assert SOURCE not in shown_values(result)
    result = await manager.async_configure(result["flow_id"], {})
    assert entry.options[SOURCE] is None
    assert entry.data["price_vat_rate"] == 0


@pytest.mark.parametrize("profile", ["custom", "tibber"])
async def test_switch_to_single_area_clears_old_override_but_keeps_vat(hass, profile):
    old = add_market(hass, ["SE3", "SE4"])
    new = add_market(hass, ["FI"], currency="EUR")
    entry, manager, result = await open_market(
        hass, profile, {SOURCE: old.entry_id, AREA: "SE4", "price_vat_rate": 0}
    )
    result = await manager.async_configure(result["flow_id"], {SOURCE: new.entry_id})
    assert result["type"] == "create_entry"
    assert dict(entry.options) == {SOURCE: new.entry_id, AREA: None}
    # Inherited fields and a country-based tax suggestion are not written on this screen.
    assert entry.data["price_vat_rate"] == 0
    assert "currency" not in entry.options


@pytest.mark.parametrize(
    "metadata",
    [
        {"areas": None},
        {"areas": "SE3"},
        {"areas": []},
        {"areas": ["SE3", True]},
        {"areas": [" "]},
        {"currency": None},
        {"currency": ""},
    ],
)
async def test_malformed_native_metadata_cannot_be_saved(hass, metadata):
    market = MockConfigEntry(
        domain="nordpool", data={"areas": ["SE3"], "currency": "SEK", **metadata}
    )
    market.add_to_hass(hass)
    entry, manager, result = await open_market(hass)
    result = await manager.async_configure(result["flow_id"], {SOURCE: market.entry_id})
    assert result["errors"] == {SOURCE: "invalid_market_source"}
    assert not entry.options


async def test_unrelated_entry_and_invalid_area_are_rejected(hass):
    unrelated = MockConfigEntry(
        domain="other", data={"areas": ["SE3"], "currency": "SEK"}
    )
    unrelated.add_to_hass(hass)
    entry, manager, result = await open_market(hass)
    result = await manager.async_configure(
        result["flow_id"], {SOURCE: unrelated.entry_id}
    )
    assert result["errors"] == {SOURCE: "invalid_market_source"}
    market = add_market(hass, ["SE3", "SE4"])
    result = await manager.async_configure(result["flow_id"], {SOURCE: market.entry_id})
    # The old form permits SE4, but the source metadata may change while it is open.
    hass.config_entries.async_update_entry(
        market, data={"areas": ["SE3", "FI"], "currency": "SEK"}
    )
    result = await manager.async_configure(result["flow_id"], {AREA: "SE4"})
    assert result["errors"] == {AREA: "invalid_market_area"}
    assert not entry.options


async def test_setup_does_not_guess_between_entries(hass):
    add_market(hass)
    add_market(hass, ["SE4"])
    manager, result = await start_setup(hass, "custom")
    assert shown_values(result)[SOURCE] is None
    manager.async_abort(result["flow_id"])


async def test_setup_does_not_enable_disabled_only_source(hass):
    add_market(hass, disabled_by=config_entries.ConfigEntryDisabler.USER)
    _, result = await start_setup(hass, "custom")
    assert shown_values(result)[SOURCE] is None


@pytest.mark.parametrize("keep_forecast", [False, True])
async def test_market_save_preserves_loaded_readings_totals_and_registry(
    hass, setup_electricity_pro, keep_forecast
):
    market = add_market(hass)
    entry = await setup_electricity_pro(
        energy_value="3.5",
        price_value="1.2",
        accumulated_cost_today_value="4.2",
        forecast_nordpool_config_entry=market.entry_id,
        forecast_intervals=[],
    )
    ids = [
        "sensor.electricity_pro_current_power",
        "sensor.electricity_pro_energy_today",
        "sensor.electricity_pro_cost_today",
    ]
    before = {entity_id: hass.states.get(entity_id).state for entity_id in ids}
    registry = er.async_get(hass)
    identities = {entity_id: registry.async_get(entity_id).id for entity_id in ids}
    manager = hass.config_entries.options
    menu = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        menu["flow_id"], {"next_step_id": "market_prices"}
    )
    # Keeping or clearing an existing forecast must preserve meter/cost state.
    with patch(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        AsyncMock(return_value=[]),
    ):
        result = await manager.async_configure(
            result["flow_id"], {SOURCE: market.entry_id} if keep_forecast else {}
        )
        assert result["type"] == "create_entry"
        await hass.async_block_till_done()
    assert {entity_id: hass.states.get(entity_id).state for entity_id in ids} == before
    assert {
        entity_id: registry.async_get(entity_id).id for entity_id in ids
    } == identities
    assert entry.options[SOURCE] == (market.entry_id if keep_forecast else None)
