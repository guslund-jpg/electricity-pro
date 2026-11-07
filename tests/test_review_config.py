"""Read-only review of real setup drafts, saved settings and price coverage."""

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import config_validation as cv, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from probatio import to_field_list

from custom_components.electricity_pro.pricing import (
    PriceComponent,
    PriceComponentScope,
    PriceCompleteness,
    PricingMetadata,
    PricingStrategy,
    VatTreatment,
)
from custom_components.electricity_pro.review_config import (
    PriceCoverage,
    price_coverage,
    review_schema,
)
from tests.flow_helpers import form_values
from tests.test_insight_config import open_setup

DOMAIN = "electricity_pro"
ZERO_ADDITIONS = {
    "grid_fee_per_kwh": 0,
    "energy_tax_per_kwh": 0,
    "supplier_markup_per_kwh": 0,
}


def declaration(*, components=None, vat="included", rate=None, complete=False):
    return PricingMetadata(
        PricingStrategy.MARKET_PRICE_PLUS_TARIFF,
        PriceComponentScope(
            frozenset(components or [PriceComponent.MARKET_ENERGY]), VatTreatment(vat)
        ),
        PriceCompleteness.COMPLETE if complete else PriceCompleteness.PARTIAL,
        rate,
    )


def values_by_section(schema):
    return {
        marker.schema: {key.schema: key.default() for key in group.schema.schema}
        for marker, group in schema.schema.items()
    }


async def open_overview(hass, entry):
    manager = hass.config_entries.options
    result = await manager.async_init(entry.entry_id)
    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "overview"}
    )
    assert result["step_id"] == "overview"
    return manager, result


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_setup_waits_for_review_and_ignores_display_payload(
    hass, profile, cancel
):
    manager, result = await open_setup(hass, profile)
    original = form_values(result)
    result = await manager.async_configure(result["flow_id"], original)
    assert result["step_id"] == "review"
    assert not hass.config_entries.async_entries(DOMAIN)
    shown = values_by_section(result["data_schema"])
    power = shown["measurements"]["power_entity"]
    assert shown["supplier"]["supplier_markup_per_kwh"] == (
        0 if profile == "custom" else "unknown"
    )
    if cancel:
        manager.async_abort(result["flow_id"])
        assert not hass.config_entries.async_entries(DOMAIN)
        return
    result = await manager.async_configure(
        result["flow_id"],
        {
            "measurements": {"power_entity": "sensor.changed_display"},
            "grid": {"grid_fee_per_kwh": 999},
        },
    )
    assert result["type"] == "create_entry"
    assert result["data"]["power_entity"] in power
    assert result["data"]["grid_fee_per_kwh"] == 0
    assert result["data"].get("supplier_markup_per_kwh") == (
        0 if profile == "custom" else None
    )
    assert "good_price_threshold" not in result["data"]
    assert not set(shown).intersection(result["data"])


@pytest.mark.parametrize("profile", ["custom", "tibber"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_overview_never_saves_or_reloads_and_resolves_explicit_clears(
    hass, profile, cancel
):
    data = {
        "source_profile": profile,
        "power_entity": "sensor.power",
        "energy_entity": "sensor.energy",
        "price_vat_rate": 25,
        "supplier_markup_per_kwh": 0.2,
        "grid_fee_per_kwh": 0.3,
    }
    options = {"energy_entity": None, "price_vat_rate": None, "grid_fee_per_kwh": 0}
    entry = MockConfigEntry(domain=DOMAIN, data=data, options=options)
    entry.add_to_hass(hass)
    listener = AsyncMock()
    entry.add_update_listener(listener)
    before = deepcopy((dict(entry.data), dict(entry.options)))
    with patch.object(
        hass.config_entries, "async_reload", new_callable=AsyncMock
    ) as reload:
        manager, result = await open_overview(hass, entry)
        shown = values_by_section(result["data_schema"])
        assert shown["measurements"]["energy_entity"] == "not_configured"
        assert shown["supplier"]["price_vat_rate"] == "unknown"
        assert shown["grid"]["grid_fee_per_kwh"] == 0
        if cancel:
            manager.async_abort(result["flow_id"])
        else:
            result = await manager.async_configure(
                result["flow_id"], {"grid": {"grid_fee_per_kwh": 999}}
            )
            assert result["type"] == "menu"
        await hass.async_block_till_done()
        reload.assert_not_called()
    listener.assert_not_called()
    assert (dict(entry.data), dict(entry.options)) == before


async def test_overview_uses_latest_settings_when_reopened(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"supplier_markup_per_kwh": 1})
    entry.add_to_hass(hass)
    manager, result = await open_overview(hass, entry)
    result = await manager.async_configure(result["flow_id"], {})
    hass.config_entries.async_update_entry(
        entry, options={"supplier_markup_per_kwh": 0}
    )
    result = await manager.async_configure(
        result["flow_id"], {"next_step_id": "overview"}
    )
    assert (
        values_by_section(result["data_schema"])["supplier"]["supplier_markup_per_kwh"]
        == 0
    )


@pytest.mark.parametrize(
    ("metadata", "amounts", "expected"),
    [
        (None, {}, PriceCoverage("unknown", ("price_declaration",))),
        (
            declaration(),
            {},
            PriceCoverage(
                "partial", ("energy_tax", "supplier_markup", "variable_grid_fee")
            ),
        ),
        (declaration(), ZERO_ADDITIONS, PriceCoverage("complete")),
        (
            declaration(vat="excluded"),
            ZERO_ADDITIONS,
            PriceCoverage("unknown", ("vat_rate",)),
        ),
        (
            declaration(vat="excluded", rate=Decimal(0)),
            ZERO_ADDITIONS,
            PriceCoverage("complete"),
        ),
        (
            declaration(vat="unknown"),
            ZERO_ADDITIONS,
            PriceCoverage("unknown", ("vat_treatment",)),
        ),
        (declaration(components=list(PriceComponent)), {}, PriceCoverage("complete")),
        (
            declaration(components=list(PriceComponent)),
            ZERO_ADDITIONS,
            PriceCoverage("complete"),
        ),
        (declaration(complete=True), {}, PriceCoverage("complete")),
        (
            declaration(complete=True),
            {"supplier_markup_per_kwh": 0},
            PriceCoverage("conflict", ("price_additions",)),
        ),
        (
            declaration(),
            {**ZERO_ADDITIONS, "energy_tax_per_kwh": None},
            PriceCoverage("partial", ("energy_tax",)),
        ),
        (
            declaration(),
            {**ZERO_ADDITIONS, "energy_tax_per_kwh": "NaN"},
            PriceCoverage("partial", ("energy_tax",)),
        ),
    ],
)
def test_price_coverage_matches_runtime_declarations(metadata, amounts, expected):
    assert price_coverage(metadata, amounts) == expected


@pytest.mark.parametrize("vat_rate", [None, 0, 25])
async def test_live_included_components_are_independent_of_raw_forecast(hass, vat_rate):
    native = MockConfigEntry(
        domain="nordpool", title="SE3", data={"areas": ["SE3"], "currency": "SEK"}
    )
    native.add_to_hass(hass)
    values = {
        "price_entity": "sensor.supplier",
        "pricing_strategy": "supplier_contracted_price",
        "price_included_components": [component.value for component in PriceComponent],
        "price_vat_treatment": "included",
        "price_completeness": "complete",
        "forecast_nordpool_config_entry": native.entry_id,
        "price_vat_rate": vat_rate,
        "fixed_supplier_fee_monthly": 0,
    }
    original = deepcopy(values)
    shown = values_by_section(review_schema(hass, values))
    assert shown["price_coverage"]["live_price_coverage"] == "complete"
    assert "live_missing" not in shown["price_coverage"]
    assert shown["price_coverage"]["forecast_price_coverage"] == (
        "unknown" if vat_rate is None else "partial"
    )
    assert set(shown["price_coverage"]["forecast_missing"]) == {
        "supplier_markup",
        "energy_tax",
        "variable_grid_fee",
        *(["vat_rate"] if vat_rate is None else []),
    }
    assert shown["price_coverage"]["fixed_fees_missing"] == ["fixed_grid_fee"]
    assert shown["energy_flows"]["flow_storage_presence"] == "unknown"
    assert values == original


@pytest.mark.parametrize(
    ("areas", "area", "currency", "expected_area", "origin", "country", "valid"),
    [
        (["SE3"], "SE4", "SEK", "SE3", "inherited", "SE", True),
        (["SE3", "FI"], "FI", "EUR", "FI", "selected", "FI", True),
        (["SE3", "SE4"], None, "SEK", "unknown", "unknown", "unknown", False),
        (["SE3"], None, None, "SE3", "inherited", "SE", False),
        (["UNKNOWN"], None, "SEK", "UNKNOWN", "inherited", "unknown", True),
        ([], None, "SEK", "unknown", "unknown", "unknown", False),
    ],
)
async def test_forecast_provenance_uses_native_context_without_currency_country_guess(
    hass, areas, area, currency, expected_area, origin, country, valid
):
    native = MockConfigEntry(
        domain="nordpool", title="Native", data={"areas": areas, "currency": currency}
    )
    native.add_to_hass(hass)
    shown = values_by_section(
        review_schema(
            hass,
            {
                "forecast_nordpool_config_entry": native.entry_id,
                "forecast_price_area": area,
                "price_vat_rate": 25,
                **ZERO_ADDITIONS,
            },
        )
    )
    assert shown["market_prices"]["forecast_area"] == expected_area
    assert shown["market_prices"]["area_origin"] == origin
    assert shown["market_prices"]["forecast_country"] == country
    assert shown["price_coverage"]["forecast_price_coverage"] == (
        "complete" if valid else "unknown"
    )


@pytest.mark.parametrize("source", ["missing", "wrong_domain"])
async def test_missing_or_wrong_native_source_is_unknown(hass, source):
    if source == "wrong_domain":
        native = MockConfigEntry(
            domain="tibber", data={"areas": ["SE3"], "currency": "SEK"}
        )
        native.add_to_hass(hass)
        source = native.entry_id
    shown = values_by_section(
        review_schema(
            hass,
            {
                "forecast_nordpool_config_entry": source,
                **ZERO_ADDITIONS,
                "price_vat_rate": 25,
            },
        )
    )
    assert shown["price_coverage"]["forecast_price_coverage"] == "unknown"
    assert shown["market_prices"]["forecast_area"] == "unknown"


async def test_unknowns_zero_runtime_defaults_and_invalid_settings_are_not_repaired(
    hass,
):
    values = {
        "grid_fee_per_kwh": 0,
        "grid_fee_high_per_kwh": 0.2,
        "fixed_grid_fee_monthly": 0,
        "good_price_mode": "adaptive",
        "adaptive_price_ceiling": -0.5,
        "adaptive_target_percentile": 0,
    }
    original = deepcopy(values)
    shown = values_by_section(review_schema(hass, values))
    assert shown["price_coverage"]["live_price_coverage"] == "not_configured"
    assert shown["price_coverage"]["forecast_price_coverage"] == "not_configured"
    assert shown["grid"]["grid_fee_high_start"] == "06:00"
    assert shown["grid"]["schedule_origin"] == "default"
    assert shown["grid"]["energy_tax_per_kwh"] == "unknown"
    assert shown["insights"]["adaptive_price_ceiling"] == -0.5
    assert shown["price_coverage"]["insight_warning"] == ["insight_settings"]
    invalid = values_by_section(
        review_schema(hass, {**values, "grid_fee_high_start": None})
    )
    assert invalid["grid"]["grid_fee_high_start"] == "unknown"
    assert invalid["price_coverage"]["grid_warning"] == ["grid_schedule"]
    assert values == original


async def test_native_serialized_controls_are_read_only_and_localized(hass):
    native = MockConfigEntry(
        domain="nordpool", data={"areas": ["SE3", "SE4"], "currency": "SEK"}
    )
    native.add_to_hass(hass)
    schema = review_schema(
        hass,
        {
            "power_entity": "sensor.missing_power",
            "energy_entity": "sensor.missing_energy",
            "energy_source_type": "lifetime",
            "price_entity": "sensor.price",
            "pricing_strategy": "market_price_plus_tariff",
            "price_included_components": ["market_energy"],
            "price_vat_treatment": "excluded",
            "price_completeness": "partial",
            "forecast_nordpool_config_entry": native.entry_id,
            "forecast_price_area": "SE4",
            "grid_fee_per_kwh": 0,
            "grid_fee_high_per_kwh": 0.2,
            "production_power_entity": "sensor.production",
            "production_power_phase_convention": "unknown",
            "good_price_mode": "adaptive",
            "adaptive_target_percentile": 25,
        },
    )
    serialized = to_field_list(schema, custom_serializer=cv.custom_serializer)
    translations = [
        json.loads((Path("custom_components/electricity_pro") / path).read_text())
        for path in ("strings.json", "translations/en.json", "translations/sv.json")
    ]
    for group in serialized:
        for field in group["schema"]:
            kind, config = next(iter(field["selector"].items()))
            assert config["read_only"] is True
            for translation in translations:
                sections = translation["options"]["step"]["overview"]["sections"]
                assert field["name"] in sections[group["name"]]["data"]
                assert translation["config"]["step"]["review"]["sections"] == sections
                if kind == "select":
                    labels = translation["selector"][config["translation_key"]][
                        "options"
                    ]
                    assert all(option in labels for option in config["options"])


async def test_loaded_entry_overview_preserves_runtime_totals_history_and_identity(
    hass, freezer, setup_electricity_pro
):
    now = datetime(2026, 11, 7, 12, 30, tzinfo=UTC)
    freezer.move_to(now)
    entry = await setup_electricity_pro(
        energy_value="3.5",
        price_value="1.2",
        accumulated_cost_today_value="4.2",
        good_price_threshold=2,
        grid_fee_per_kwh=0,
        energy_tax_per_kwh=0,
        supplier_markup_per_kwh=0,
        price_completeness=PriceCompleteness.COMPLETE,
    )
    coordinator = entry.runtime_data
    coordinator.adaptive_price_history.add_segment(
        start=now.replace(hour=11, minute=0),
        end=now.replace(minute=0),
        effective_price=Decimal("1.1"),
    )
    history = deepcopy(coordinator.adaptive_price_history.as_dict())
    ids = [
        "sensor.electricity_pro_current_power",
        "sensor.electricity_pro_energy_today",
        "sensor.electricity_pro_cost_today",
        "binary_sensor.electricity_pro_good_time_to_use_electricity",
    ]
    before = {key: hass.states.get(key).state for key in ids}
    identities = {key: er.async_get(hass).async_get(key).id for key in ids}
    manager, result = await open_overview(hass, entry)
    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] == "menu"
    await hass.async_block_till_done()
    assert entry.runtime_data is coordinator
    assert coordinator.adaptive_price_history.as_dict() == history
    assert {key: hass.states.get(key).state for key in ids} == before
    assert {key: er.async_get(hass).async_get(key).id for key in ids} == identities
