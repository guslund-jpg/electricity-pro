"""Verify canonical provider inputs against the recorded pre-separation values."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime
from decimal import Decimal as D
from typing import get_type_hints
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.data import (
    CalculationContext,
    ElectricityProData,
    IntegrationResults,
    ProviderSnapshot,
    SourceReadings,
)
from custom_components.electricity_pro.pricing import (
    PriceComponent,
    PriceComponentScope,
    PriceCompleteness,
    PricingMetadata,
    PricingStrategy,
    VatTreatment,
)
from custom_components.electricity_pro.provider import ElectricityProEntityProvider

_METADATA = PricingMetadata(
    strategy=PricingStrategy.MARKET_PRICE_PLUS_TARIFF,
    scope=PriceComponentScope(
        frozenset({PriceComponent.MARKET_ENERGY}), VatTreatment.EXCLUDED
    ),
    completeness=PriceCompleteness.PARTIAL,
    vat_rate=D("25.00"),
)
_STATES = {
    "power": ("1.2500", "kW"),
    "price": ("-0.123400", "SEK/kWh"),
    "energy": ("123456.7890", "Wh"),
    "cost": ("12.3400", "SEK"),
    "l1": ("1250", "mA"),
    "l2": ("2.5000", "A"),
    "l3": ("0", "A"),
    "v1": ("230000", "mV"),
    "v2": ("231.500", "V"),
    "v3": ("0", "V"),
    "peak": ("2350.00", "Wh"),
    "peak_time": ("2026-11-08T09:30:00+01:00", None),
}
_BINDINGS = {
    "power_entity": "power",
    "price_entity": "price",
    "energy_entity": "energy",
    "accumulated_cost_today_entity": "cost",
    "current_l1_entity": "l1",
    "current_l2_entity": "l2",
    "current_l3_entity": "l3",
    "voltage_l1_entity": "v1",
    "voltage_l2_entity": "v2",
    "voltage_l3_entity": "v3",
    "monthly_peak_hour_consumption_entity": "peak",
    "monthly_peak_hour_time_entity": "peak_time",
}


def expected_flat_values():
    """Keep all 51 expected values independent of the future projection helper."""
    return {
        "current_power": D("1250.0000"),
        "current_power_bidirectional": False,
        "current_price": D("-0.123400"),
        "current_price_unit": "SEK/kWh",
        "pricing_metadata": _METADATA,
        "current_energy": D("123456.7890"),
        "current_energy_unit": "Wh",
        "energy_source_type": "lifetime",
        "energy_today_period_complete": False,
        "accumulated_cost_today": D("12.3400"),
        "accumulated_cost_today_unit": "SEK",
        "peak_power_today": None,
        "peak_power_time_today": None,
        "current_l1": D("1.25"),
        "current_l2": D("2.5000"),
        "current_l3": D(0),
        "voltage_l1": D(230),
        "voltage_l2": D("231.500"),
        "voltage_l3": D(0),
        "monthly_peak_hour_consumption": D("2350.00"),
        "monthly_peak_hour_consumption_unit": "Wh",
        "monthly_peak_hour_time": datetime.fromisoformat("2026-11-08T09:30:00+01:00"),
        "energy_this_month": None,
        "energy_this_month_unit": None,
        "cost_this_month": None,
        "cost_this_month_unit": None,
        "fixed_supplier_fee_this_month": D("49.00"),
        "fixed_supplier_fee_this_month_unit": None,
        "fixed_grid_fee_this_month": D("630.00"),
        "fixed_grid_fee_this_month_unit": None,
        "total_supplier_cost_this_month": None,
        "total_supplier_cost_this_month_unit": None,
        "grid_fee_per_kwh": D("0.1250"),
        "supplier_markup_per_kwh": D("0.0800"),
        "energy_tax_per_kwh": D("0.2500"),
        "good_price_threshold": D("1.5000"),
        "local_cost_estimate": False,
        "local_effective_cost_today": None,
        "local_priced_energy_today": None,
        "local_supplier_energy_today": None,
        "local_supplier_energy_month": None,
        "household_cost_today": None,
        "household_cost_this_month": None,
        "household_cost_unit": None,
        "household_variable_today": None,
        "household_variable_month": None,
        "household_fixed_today": None,
        "household_fixed_month": None,
        "household_fixed_supplier_month": None,
        "household_fixed_grid_month": None,
        "household_priced_energy_today": None,
        "household_priced_energy_month": None,
        "household_missing_fees": (),
    }


def make_provider(hass, changes=None, options=None, grid_fee_at=None):
    for key, reading in (_STATES | (changes or {})).items():
        if reading is not None:
            value, unit = reading
            hass.states.async_set(
                f"sensor.contract_{key}", value, {"unit_of_measurement": unit}
            )
    data = {key: f"sensor.contract_{source}" for key, source in _BINDINGS.items()}
    data.update(
        energy_source_type="lifetime",
        pricing_strategy="market_price_plus_tariff",
        price_included_components=["market_energy"],
        price_vat_treatment="excluded",
        price_completeness="partial",
        price_vat_rate="25.00",
        grid_fee_per_kwh="0.1250",
        supplier_markup_per_kwh="0.0800",
        energy_tax_per_kwh="0.2500",
        fixed_supplier_fee_monthly="49.00",
        fixed_grid_fee_monthly="630.00",
        good_price_threshold="1.5000",
    )
    entry = MockConfigEntry(domain=DOMAIN, data=data, options=options or {})
    return ElectricityProEntityProvider(hass, entry, grid_fee_at=grid_fee_at)


_CASES = [
    pytest.param({}, {}, {}, id="complete-lifetime-contract"),
    pytest.param(
        {"power": ("-0.5", "kW")},
        {},
        {"current_power": D("-500.0"), "current_power_bidirectional": True},
        id="signed-power",
    ),
    pytest.param(
        {
            "power": ("0", "W"),
            "price": ("0", "EUR/kWh"),
            "energy": ("0", "kWh"),
            "cost": ("0", "EUR"),
        },
        {"energy_source_type": "daily"},
        {
            "current_power": D(0),
            "current_price": D(0),
            "current_price_unit": "EUR/kWh",
            "current_energy": D(0),
            "current_energy_unit": "kWh",
            "accumulated_cost_today": D(0),
            "accumulated_cost_today_unit": "EUR",
            "energy_source_type": "daily",
            "energy_today_period_complete": True,
        },
        id="zero-and-daily",
    ),
    *[
        pytest.param(
            changes,
            {},
            {
                "current_power": None,
                "current_price": None,
                "current_price_unit": None,
                "current_energy": None,
                "current_energy_unit": None,
                "accumulated_cost_today": None,
                "accumulated_cost_today_unit": None,
            },
            id=label,
        )
        for label, changes in [
            (
                "missing-sources",
                {key: None for key in ("power", "price", "energy", "cost")},
            ),
            (
                "unavailable-sources",
                {
                    key: ("unavailable", unit)
                    for key, unit in (
                        ("power", "W"),
                        ("price", "SEK/kWh"),
                        ("energy", "kWh"),
                        ("cost", "SEK"),
                    )
                },
            ),
            (
                "nonfinite-sources",
                {
                    "power": ("NaN", "W"),
                    "price": ("Infinity", "SEK/kWh"),
                    "energy": ("NaN", "kWh"),
                    "cost": ("Infinity", "SEK"),
                },
            ),
            (
                "unsupported-units",
                {
                    "power": ("1", "V"),
                    "price": ("1", ""),
                    "energy": ("1", "MWh"),
                    "cost": ("1", 123),
                },
            ),
            (
                "malformed-units",
                {
                    "power": ("1", []),
                    "price": ("1", []),
                    "energy": ("1", {}),
                    "cost": ("1", []),
                },
            ),
        ]
    ],
    pytest.param(
        {"energy": ("-1", "kWh"), "cost": ("-1", "SEK")},
        {},
        {
            "current_energy": None,
            "current_energy_unit": None,
            "accumulated_cost_today": None,
            "accumulated_cost_today_unit": None,
        },
        id="negative-counters",
    ),
    pytest.param(
        {},
        {
            "price_entity": None,
            "energy_entity": None,
            "accumulated_cost_today_entity": None,
        },
        {
            "current_price": None,
            "current_price_unit": None,
            "current_energy": None,
            "current_energy_unit": None,
            "accumulated_cost_today": None,
            "accumulated_cost_today_unit": None,
        },
        id="explicit-source-clears",
    ),
    pytest.param(
        {},
        {"energy_source_type": "unsupported"},
        {"energy_source_type": "daily", "energy_today_period_complete": True},
        id="saved-semantics-fallback",
    ),
    pytest.param(
        {},
        {
            "grid_fee_per_kwh": 0,
            "supplier_markup_per_kwh": 0,
            "energy_tax_per_kwh": 0,
            "fixed_supplier_fee_monthly": 0,
            "fixed_grid_fee_monthly": 0,
            "good_price_threshold": 0,
            "price_vat_rate": 0,
        },
        {
            "grid_fee_per_kwh": D(0),
            "supplier_markup_per_kwh": D(0),
            "energy_tax_per_kwh": D(0),
            "fixed_supplier_fee_this_month": D(0),
            "fixed_grid_fee_this_month": D(0),
            "good_price_threshold": D(0),
            "pricing_metadata": replace(_METADATA, vat_rate=D(0)),
        },
        id="explicit-zero-settings",
    ),
    pytest.param(
        {},
        {
            "grid_fee_per_kwh": None,
            "supplier_markup_per_kwh": None,
            "energy_tax_per_kwh": None,
            "fixed_supplier_fee_monthly": None,
            "fixed_grid_fee_monthly": None,
            "good_price_threshold": None,
            "price_vat_rate": None,
        },
        {
            "grid_fee_per_kwh": None,
            "supplier_markup_per_kwh": None,
            "energy_tax_per_kwh": None,
            "fixed_supplier_fee_this_month": None,
            "fixed_grid_fee_this_month": None,
            "good_price_threshold": None,
            "pricing_metadata": replace(_METADATA, vat_rate=None),
        },
        id="explicit-setting-clears",
    ),
    pytest.param(
        {},
        {
            "grid_fee_per_kwh": "-1",
            "supplier_markup_per_kwh": True,
            "energy_tax_per_kwh": "Infinity",
            "fixed_supplier_fee_monthly": "NaN",
            "fixed_grid_fee_monthly": "invalid",
            "good_price_threshold": "-1",
        },
        {
            "grid_fee_per_kwh": None,
            "supplier_markup_per_kwh": None,
            "energy_tax_per_kwh": None,
            "fixed_supplier_fee_this_month": None,
            "fixed_grid_fee_this_month": None,
            "good_price_threshold": None,
        },
        id="invalid-adjustments",
    ),
    pytest.param(
        {},
        {"pricing_strategy": None},
        {"pricing_metadata": None},
        id="unknown-price-contract",
    ),
    pytest.param(
        {
            "l1": ("-1", "mA"),
            "l2": ("NaN", "A"),
            "l3": ("5", "V"),
            "v1": ("-230", "V"),
            "v2": ("230", 123),
            "v3": ("unknown", "V"),
            "peak": ("-1", "Wh"),
            "peak_time": ("invalid", None),
        },
        {},
        {
            "current_l1": None,
            "current_l2": None,
            "current_l3": None,
            "voltage_l1": None,
            "voltage_l2": None,
            "voltage_l3": None,
            "monthly_peak_hour_consumption": None,
            "monthly_peak_hour_consumption_unit": None,
            "monthly_peak_hour_time": None,
        },
        id="invalid-phase-and-peak-readings",
    ),
    pytest.param(
        {"price": ("-0.123400", "SEK/MWh")},
        {},
        {"current_price_unit": "SEK/MWh"},
        id="retain-nonempty-price-unit",
    ),
]


@pytest.fixture(params=[pytest.param(case.values, id=case.id) for case in _CASES])
def provider_case(hass, request):
    changes, options, expected = request.param
    return make_provider(hass, changes, options), expected_flat_values() | expected


_SOURCE_FIELDS = {
    "current_power": "current_power",
    "current_power_bidirectional": "current_power_bidirectional",
    "current_price": "current_price",
    "current_price_unit": "current_price_unit",
    "import_energy_value": "current_energy",
    "import_energy_unit": "current_energy_unit",
    "energy_source_type": "energy_source_type",
    "external_cost_today": "accumulated_cost_today",
    "external_cost_today_unit": "accumulated_cost_today_unit",
    "current_l1": "current_l1",
    "current_l2": "current_l2",
    "current_l3": "current_l3",
    "voltage_l1": "voltage_l1",
    "voltage_l2": "voltage_l2",
    "voltage_l3": "voltage_l3",
    "monthly_peak_hour_consumption": "monthly_peak_hour_consumption",
    "monthly_peak_hour_consumption_unit": "monthly_peak_hour_consumption_unit",
    "monthly_peak_hour_time": "monthly_peak_hour_time",
}
_CONTEXT_FIELDS = {
    "pricing_metadata",
    "fixed_supplier_fee_this_month",
    "fixed_grid_fee_this_month",
    "grid_fee_per_kwh",
    "supplier_markup_per_kwh",
    "energy_tax_per_kwh",
    "good_price_threshold",
}


def test_canonical_inputs_and_initial_results_match_recorded_values(provider_case):
    provider, expected = provider_case
    inputs = provider.read()
    for group, mapping in (
        (inputs.readings, _SOURCE_FIELDS),
        (inputs.context, {name: name for name in _CONTEXT_FIELDS}),
    ):
        assert {field.name for field in fields(group)} == mapping.keys()
        for name, old_name in mapping.items():
            value = getattr(group, name)
            assert value == expected[old_name]
            if isinstance(value, D):
                assert value.as_tuple() == expected[old_name].as_tuple()
    results = IntegrationResults.from_inputs(inputs)
    for field in fields(results):
        value = getattr(results, field.name)
        assert value == expected[field.name]
        if isinstance(value, D):
            assert value.as_tuple() == expected[field.name].as_tuple()


def test_canonical_model_inventory():
    assert len(fields(SourceReadings)) == 18
    assert len(fields(CalculationContext)) == 7
    assert len(fields(IntegrationResults)) == 32
    assert get_type_hints(ProviderSnapshot) == {
        "readings": SourceReadings,
        "context": CalculationContext,
    }
    assert get_type_hints(ElectricityProData) == {
        "readings": SourceReadings,
        "context": CalculationContext,
        "results": IntegrationResults,
    }


def test_input_groups_are_immutable_and_raw_values_survive_result_selection(hass):
    inputs = make_provider(hass).read()
    for group in (inputs, inputs.readings, inputs.context):
        assert not hasattr(group, "__dict__")
        name = fields(group)[0].name
        with pytest.raises(FrozenInstanceError):
            setattr(group, name, None)
    published = ElectricityProData(
        readings=inputs.readings,
        context=inputs.context,
        results=replace(
            IntegrationResults.from_inputs(inputs),
            current_energy=D("0.7500"),
            accumulated_cost_today=D("0.2500"),
        ),
    )
    assert published.results.current_energy == D("0.7500")
    assert published.results.accumulated_cost_today == D("0.2500")
    assert inputs.readings.import_energy_value.as_tuple() == D("123456.7890").as_tuple()
    assert inputs.readings.external_cost_today.as_tuple() == D("12.3400").as_tuple()


def test_provider_read_order_and_single_tariff_clock(hass):
    trace = []
    now = datetime(2026, 11, 8, 12, tzinfo=UTC)
    original_get = type(hass.states).get

    def read_state(machine, entity_id):
        trace.append(entity_id)
        return original_get(machine, entity_id)

    def clock():
        trace.append("clock")
        return now

    def tariff(at):
        trace.append(("tariff", at))
        return D("0.3750")

    provider = make_provider(hass, grid_fee_at=tariff)
    with (
        patch.object(type(hass.states), "get", autospec=True, side_effect=read_state),
        patch(
            "custom_components.electricity_pro.provider.dt_util.now", side_effect=clock
        ),
    ):
        result = provider.read()
    context = result.context
    assert context.grid_fee_per_kwh == D("0.3750")
    assert trace == [
        *[
            f"sensor.contract_{name}"
            for name in (
                "energy",
                "price",
                "cost",
                "l1",
                "l2",
                "l3",
                "v1",
                "v2",
                "v3",
                "peak",
                "peak_time",
                "power",
                "power",
            )
        ],
        "clock",
        ("tariff", now),
    ]


@pytest.mark.parametrize(
    "now,expected",
    [
        (datetime(2026, 11, 2, 4, 59, tzinfo=UTC), "0.1250"),
        (datetime(2026, 11, 2, 5, tzinfo=UTC), "0.2500"),
        (datetime(2026, 3, 30, 3, 59, tzinfo=UTC), "0.1250"),
        (datetime(2026, 3, 30, 4, tzinfo=UTC), "0.2500"),
        (datetime(2026, 10, 26, 4, 59, tzinfo=UTC), "0.1250"),
        (datetime(2026, 10, 26, 5, tzinfo=UTC), "0.2500"),
    ],
)
async def test_tariff_read_preserves_local_and_dst_boundaries(hass, now, expected):
    await hass.config.async_set_time_zone("Europe/Stockholm")
    provider = make_provider(
        hass,
        options={
            "grid_fee_high_per_kwh": "0.2500",
            "grid_fee_high_season_start": "01-01",
            "grid_fee_high_season_end": "12-31",
        },
    )
    with patch(
        "custom_components.electricity_pro.provider.dt_util.now", return_value=now
    ):
        result = provider.read()
    context = result.context
    assert context.grid_fee_per_kwh.as_tuple() == D(expected).as_tuple()


def test_provider_reads_are_fresh_and_keep_raw_counter_values(hass):
    provider = make_provider(hass)
    first = provider.read()
    hass.states.async_set(
        "sensor.contract_energy", "123457.0000", {"unit_of_measurement": "Wh"}
    )
    second = provider.read()
    assert first.readings.import_energy_value == D("123456.7890")
    assert second.readings.import_energy_value == D("123457.0000")
    assert first is not second
    assert first.context.pricing_metadata is second.context.pricing_metadata
    assert not hasattr(first, "results")
    assert not hasattr(first, "energy_this_month")
