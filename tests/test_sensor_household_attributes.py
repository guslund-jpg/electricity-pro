"""Characterize household total attributes independently of their dispatch."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.cost_ledger import VariableCostSummary
from custom_components.electricity_pro.pricing import (
    PriceCompleteness,
    VariableCostComponent,
)
from custom_components.electricity_pro.data import (
    ElectricityProData,
    IntegrationResults,
)
from custom_components.electricity_pro.provider import ElectricityProEntityProvider
from custom_components.electricity_pro.sensor import (
    SENSOR_DESCRIPTIONS,
    ElectricityProSensor,
)


@pytest.fixture(params=["total_cost_today", "total_cost_this_month"])
def household_sensor(hass, request):
    """Use distinct day/month amounts so a period mix-up cannot pass unnoticed."""
    entry = MockConfigEntry(domain=DOMAIN, data={"power_entity": "sensor.power"})
    coordinator = ElectricityProCoordinator(hass, entry)
    inputs = ElectricityProEntityProvider(hass, entry).read()
    data = ElectricityProData(
        readings=inputs.readings,
        context=inputs.context,
        results=IntegrationResults.from_inputs(inputs),
    )
    coordinator.async_set_updated_data(
        replace(
            data,
            results=replace(
                data.results,
                household_cost_today=Decimal("12.3400"),
                household_cost_this_month=Decimal("123.456700"),
                household_cost_unit="SEK",
                household_variable_today=Decimal("10.1200"),
                household_variable_month=Decimal("100.001"),
                household_fixed_today=Decimal("2.2200"),
                household_fixed_month=Decimal("23.455700"),
                household_fixed_supplier_month=Decimal("23.455700"),
                household_priced_energy_today=Decimal("8.0100"),
                household_priced_energy_month=Decimal("80.001"),
                household_missing_fees=("fixed_grid_fee",),
            ),
        )
    )
    description = next(
        item for item in SENSOR_DESCRIPTIONS if item.key == request.param
    )
    return ElectricityProSensor(coordinator, entry, description)


def test_household_attributes_preserve_period_and_decimal_strings(household_sensor):
    sensor = household_sensor
    if sensor.entity_description.key == "total_cost_today":
        expected_value = Decimal("12.3400")
        expected_attributes = {
            "source": "local_household_estimate",
            "coverage": "partial",
            "variable_cost": "10.1200",
            "accrued_fixed_fees": "2.2200",
            "priced_energy_kwh": "8.0100",
            "missing_components": ["fixed_grid_fee"],
            "excluded_charges": ["demand_charges", "other_unconfigured_charges"],
            "fixed_fee_method": "calendar_day_share_accrued_to_now",
            "fixed_fee_coverage": "local_midnight_to_now",
        }
    else:
        expected_value = Decimal("123.456700")
        expected_attributes = {
            "source": "local_household_estimate",
            "coverage": "partial",
            "variable_cost": "100.001",
            "accrued_fixed_fees": "23.455700",
            "accrued_fixed_fee_breakdown": {"supplier": "23.455700", "grid": None},
            "variable_cost_breakdown": None,
            "monthly_cost_display": {
                "total": "123.46",
                "lines": {"variable": "100.00", "supplier": "23.46"},
            },
            "priced_energy_kwh": "80.001",
            "missing_components": ["fixed_grid_fee"],
            "excluded_charges": ["demand_charges", "other_unconfigured_charges"],
            "fixed_fee_method": "calendar_day_share_accrued_to_now",
            "fixed_fee_coverage": "calendar_month_to_now",
        }
    assert isinstance(sensor.native_value, Decimal)
    assert sensor.native_value == expected_value
    assert sensor.native_unit_of_measurement == "SEK"
    assert sensor.available is True
    assert sensor.extra_state_attributes == expected_attributes


@pytest.mark.parametrize("household_sensor", ["total_cost_this_month"], indirect=True)
def test_monthly_estimate_rounds_known_fees_for_display(household_sensor):
    sensor = household_sensor
    data = sensor.coordinator.data
    sensor.coordinator.data = replace(
        data,
        results=replace(
            data.results,
            household_cost_this_month=Decimal("835.172"),
            household_variable_month=Decimal("633.087"),
            household_fixed_month=Decimal("202.085"),
            household_fixed_supplier_month=Decimal("15.257"),
            household_fixed_grid_month=Decimal("186.828"),
            household_missing_fees=(),
        ),
    )
    assert sensor.native_value == Decimal("835.172")
    assert sensor.extra_state_attributes["monthly_cost_display"] == {
        "total": "835.17",
        "lines": {
            "variable": "633.09",
            "supplier": "15.26",
            "grid": "186.83",
            "rounding_adjustment": "-0.01",
        },
    }


@pytest.mark.parametrize("amount", [None, Decimal("0.000"), Decimal("-1.2300")])
def test_household_attributes_preserve_missing_zero_and_signed_amounts(
    household_sensor, amount
):
    sensor = household_sensor
    sensor.coordinator.data = replace(
        sensor.coordinator.data,
        results=replace(
            sensor.coordinator.data.results,
            household_cost_today=amount,
            household_cost_this_month=amount,
            household_variable_today=amount,
            household_variable_month=amount,
            household_fixed_today=amount,
            household_fixed_month=amount,
            household_priced_energy_today=amount,
            household_priced_energy_month=amount,
            household_missing_fees=(),
        ),
    )
    assert sensor.native_value == amount
    assert sensor.available is (amount is not None)
    attributes = sensor.extra_state_attributes
    expected = None if amount is None else str(amount)
    assert attributes["variable_cost"] == expected
    assert attributes["accrued_fixed_fees"] == expected
    assert attributes["priced_energy_kwh"] == expected
    assert attributes["missing_components"] == []
    assert attributes["coverage"] == "partial"


@pytest.mark.parametrize("unavailable", ["missing-unit", "coordinator-failure"])
def test_household_attributes_remain_visible_when_unavailable(
    household_sensor, unavailable
):
    sensor = household_sensor
    expected = sensor.extra_state_attributes
    if unavailable == "missing-unit":
        sensor.coordinator.data = replace(
            sensor.coordinator.data,
            results=replace(sensor.coordinator.data.results, household_cost_unit=None),
        )
    else:
        sensor.coordinator.last_update_success = False
    assert sensor.available is False
    assert sensor.extra_state_attributes == expected


def test_household_attribute_containers_are_fresh(household_sensor):
    sensor = household_sensor
    expected = sensor.extra_state_attributes
    changed = sensor.extra_state_attributes
    changed["source"] = "changed"
    changed["missing_components"].append("unexpected")
    changed["excluded_charges"].clear()
    assert sensor.extra_state_attributes == expected
    assert sensor.coordinator.data.results.household_missing_fees == ("fixed_grid_fee",)


@pytest.mark.parametrize("household_sensor", ["total_cost_this_month"], indirect=True)
@pytest.mark.parametrize(
    ("older_cost", "total", "rounding"),
    [
        (None, "79.01", "+0.01"),
        ("0.000", "79.01", "+0.01"),
        ("20.004", "99.02", "+0.02"),
    ],
    ids=["full-breakdown", "zero-unsplit-cost", "positive-unsplit-cost"],
)
def test_monthly_variable_breakdown_rounds_for_display_only(
    household_sensor, older_cost, total, rounding
):
    sensor = household_sensor
    now = datetime(2026, 11, 8, 12, tzinfo=UTC)
    summary = VariableCostSummary(
        now,
        Decimal(60),
        Decimal("79.012"),
        (
            (VariableCostComponent.SUPPLIER_PRICE, Decimal("52.004")),
            (VariableCostComponent.ENERGY_TAX, Decimal("18.004")),
            (VariableCostComponent.VARIABLE_GRID_FEE, Decimal("9.004")),
        ),
    )
    raw_total = summary.covered_cost + Decimal(older_cost or 0)
    sensor.coordinator.data = replace(
        sensor.coordinator.data,
        results=replace(
            sensor.coordinator.data.results,
            household_variable_month=raw_total,
            household_priced_energy_month=Decimal(60 if older_cost is None else 80),
            household_variable_breakdown_month=summary,
        ),
    )

    attributes = sensor.extra_state_attributes
    breakdown = attributes["variable_cost_breakdown"]
    assert attributes["variable_cost"] == str(raw_total)
    assert breakdown["started_at"] == now.isoformat()
    assert breakdown["priced_energy_kwh"] == "60"
    assert breakdown["covered_cost"] == "79.012"
    assert breakdown["unallocated_cost"] == older_cost
    assert breakdown["components"] == {
        "supplier_price": "52.004",
        "energy_tax": "18.004",
        "variable_grid_fee": "9.004",
    }
    lines = {
        "supplier_price": "52.00",
        "energy_tax": "18.00",
        "variable_grid_fee": "9.00",
        "rounding_adjustment": rounding,
    }
    if older_cost is not None:
        lines["unallocated_cost"] = f"{Decimal(older_cost):.2f}"
    assert breakdown["display"] == {"total": total, "lines": lines}
    assert sum(map(Decimal, lines.values())) == Decimal(total)
    breakdown["display"]["lines"].clear()
    assert (
        sensor.extra_state_attributes["variable_cost_breakdown"]["display"]["lines"]
        == lines
    )


async def test_household_publication_schedule_and_reload_preserve_identity_and_totals(
    hass, setup_electricity_pro, freezer
):
    """Keep one-minute publication and restore the same persisted ledger totals."""
    await hass.config.async_set_time_zone("UTC")
    now = datetime(2026, 11, 8, 12, tzinfo=UTC)
    freezer.move_to(now)
    entry = await setup_electricity_pro(
        energy_value="100",
        energy_source_type="lifetime",
        price_value="2",
        price_completeness=PriceCompleteness.COMPLETE,
        fixed_supplier_fee_monthly=0,
        fixed_grid_fee_monthly=0,
    )
    entities = {
        "total_cost_today": "sensor.electricity_pro_total_cost_estimate_today",
        "total_cost_this_month": "sensor.electricity_pro_total_cost_estimate_this_month",
    }
    registry = er.async_get(hass)
    saved_settings = (dict(entry.data), dict(entry.options))
    initial_states = {
        key: hass.states.get(entity_id) for key, entity_id in entities.items()
    }
    for state in initial_states.values():
        assert Decimal(state.state) == 0

    freezer.move_to(now + timedelta(seconds=10))
    hass.states.async_set("sensor.test_energy", "101", {"unit_of_measurement": "kWh"})
    await hass.async_block_till_done()
    assert entry.runtime_data.data.results.household_variable_today == Decimal(2)
    for key, entity_id in entities.items():
        assert hass.states.get(entity_id) is initial_states[key]

    freezer.move_to(now + timedelta(minutes=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    expected_attributes = {}
    for key, entity_id in entities.items():
        state = hass.states.get(entity_id)
        assert Decimal(state.state) == 2
        assert state.attributes["variable_cost"] == "2"
        assert state.attributes["priced_energy_kwh"] == "1"
        assert state.attributes["missing_components"] == []
        assert state.attributes["unit_of_measurement"] == "SEK"
        assert state.attributes["device_class"] == "monetary"
        assert state.attributes["state_class"] == "total"
        if key == "total_cost_this_month":
            breakdown = state.attributes["accrued_fixed_fee_breakdown"]
            assert Decimal(breakdown["supplier"]) == Decimal(breakdown["grid"]) == 0
            assert state.attributes["variable_cost_breakdown"] == {
                "components": {"bundled_price": "2"},
                "unallocated_cost": None,
                "covered_cost": "2",
                "priced_energy_kwh": "1",
                "started_at": now.isoformat(),
                "display": {"total": "2.00", "lines": {"bundled_price": "2.00"}},
            }
        else:
            assert "variable_cost_breakdown" not in state.attributes
        assert registry.async_get(entity_id).unique_id == f"{entry.entry_id}_{key}"
        expected_attributes[key] = dict(state.attributes)

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    for key, entity_id in entities.items():
        state = hass.states.get(entity_id)
        assert Decimal(state.state) == 2
        assert dict(state.attributes) == expected_attributes[key]
        assert registry.async_get(entity_id).unique_id == f"{entry.entry_id}_{key}"
    assert (dict(entry.data), dict(entry.options)) == saved_settings
