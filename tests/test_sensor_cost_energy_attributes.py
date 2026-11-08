"""Characterize local cost and daily import-energy attribute contracts."""

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
from custom_components.electricity_pro.data import (
    ElectricityProData,
    IntegrationResults,
)
from custom_components.electricity_pro.provider import ElectricityProEntityProvider
from custom_components.electricity_pro.sensor import (
    SENSOR_DESCRIPTIONS,
    ElectricityProSensor,
)


@pytest.fixture
def make_sensor(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"power_entity": "sensor.power"})
    coordinator = ElectricityProCoordinator(hass, entry)
    inputs = ElectricityProEntityProvider(hass, entry).read()
    data = ElectricityProData(
        readings=inputs.readings,
        context=inputs.context,
        results=IntegrationResults.from_inputs(inputs),
    )
    data = replace(
        data,
        results=replace(
            data.results,
            current_energy=Decimal("12.3400"),
            current_energy_unit="kWh",
            energy_today_period_complete=True,
            accumulated_cost_today=Decimal("10.1200"),
            accumulated_cost_today_unit="SEK",
            cost_this_month=Decimal("100.001"),
            cost_this_month_unit="SEK",
            total_supplier_cost_this_month=Decimal("110.001"),
            total_supplier_cost_this_month_unit="SEK",
            local_cost_estimate=True,
            local_effective_cost_today=Decimal("8.6000"),
            local_supplier_energy_today=Decimal("2.1000"),
            local_supplier_energy_month=Decimal("3.2000"),
            local_priced_energy_today=Decimal("4.3000"),
        ),
        readings=replace(data.readings, energy_source_type="daily"),
    )

    def create(key, *, readings=None, context=None, results=None):
        coordinator.async_set_updated_data(
            replace(
                data,
                readings=replace(data.readings, **(readings or {})),
                context=replace(data.context, **(context or {})),
                results=replace(data.results, **(results or {})),
            )
        )
        description = next(item for item in SENSOR_DESCRIPTIONS if item.key == key)
        return ElectricityProSensor(coordinator, entry, description)

    return create


@pytest.fixture(
    params=[
        ("cost_today", "2.1000", "10.1200"),
        ("cost_this_month", "3.2000", "100.001"),
        ("total_supplier_cost_this_month", "3.2000", "110.001"),
        ("consumption_weighted_average_price_today", "4.3000", "2"),
    ],
    ids=lambda row: row[0],
)
def local_cost_sensor(request, make_sensor):
    key, energy, value = request.param
    return make_sensor(key), energy, Decimal(value)


def test_local_cost_payload_uses_the_correct_supplier_or_effective_energy(
    local_cost_sensor,
):
    """Distinct coverage amounts protect day/month and supplier/effective scope."""
    sensor, energy, value = local_cost_sensor
    assert sensor.native_value == value
    assert isinstance(sensor.native_value, Decimal)
    assert sensor.available is True
    assert sensor.extra_state_attributes == {
        "source": "local_estimate",
        "coverage": "partial",
        "method": "meter_delta_uniform_allocation_over_observed_prices",
        "priced_energy_kwh": energy,
    }


def test_external_cost_has_no_local_estimate_attributes(local_cost_sensor):
    sensor, _, _ = local_cost_sensor
    sensor.coordinator.data = replace(
        sensor.coordinator.data,
        results=replace(sensor.coordinator.data.results, local_cost_estimate=False),
    )
    assert sensor.extra_state_attributes is None


@pytest.mark.parametrize(
    "energy", [None, Decimal("0.000"), Decimal("1.234567890123456789")]
)
def test_local_coverage_preserves_missing_zero_and_decimal_precision(
    local_cost_sensor, energy
):
    sensor, _, _ = local_cost_sensor
    sensor.coordinator.data = replace(
        sensor.coordinator.data,
        results=replace(
            sensor.coordinator.data.results,
            local_supplier_energy_today=energy,
            local_supplier_energy_month=energy,
            local_priced_energy_today=energy,
        ),
    )
    assert sensor.extra_state_attributes["priced_energy_kwh"] == (
        None if energy is None else str(energy)
    )


@pytest.mark.parametrize(
    "reason", ["missing-value", "missing-unit", "coordinator-failure"]
)
def test_local_attributes_do_not_depend_on_availability(local_cost_sensor, reason):
    sensor, _, _ = local_cost_sensor
    expected = sensor.extra_state_attributes
    if reason == "missing-value":
        sensor.coordinator.data = replace(
            sensor.coordinator.data,
            results=replace(
                sensor.coordinator.data.results,
                accumulated_cost_today=None,
                cost_this_month=None,
                total_supplier_cost_this_month=None,
                local_effective_cost_today=None,
            ),
        )
    elif reason == "missing-unit":
        sensor.coordinator.data = replace(
            sensor.coordinator.data,
            results=replace(
                sensor.coordinator.data.results,
                accumulated_cost_today_unit=None,
                cost_this_month_unit=None,
                total_supplier_cost_this_month_unit=None,
            ),
        )
    else:
        sensor.coordinator.last_update_success = False
    assert sensor.available is False
    assert sensor.extra_state_attributes == expected


def test_local_attribute_mappings_are_fresh(local_cost_sensor):
    sensor, _, _ = local_cost_sensor
    expected = sensor.extra_state_attributes
    changed = sensor.extra_state_attributes
    changed["source"] = "changed"
    assert sensor.extra_state_attributes == expected


@pytest.mark.parametrize("source_type", ["daily", "lifetime"])
@pytest.mark.parametrize("complete", [False, True])
@pytest.mark.parametrize(
    "reason", ["available", "missing-value", "missing-unit", "coordinator-failure"]
)
def test_energy_today_preserves_source_and_completeness_when_unavailable(
    make_sensor, source_type, complete, reason
):
    sensor = make_sensor(
        "current_energy",
        readings={"energy_source_type": source_type},
        results={
            "energy_today_period_complete": complete,
            "current_energy": None if reason == "missing-value" else Decimal("12.3400"),
            "current_energy_unit": None if reason == "missing-unit" else "kWh",
        },
    )
    sensor.coordinator.last_update_success = reason != "coordinator-failure"
    assert sensor.available is (reason == "available")
    assert sensor.native_value == (
        None if reason == "missing-value" else Decimal("12.3400")
    )
    assert sensor.extra_state_attributes == {
        "source_type": source_type,
        "period_complete": complete,
    }


@pytest.mark.parametrize("unit", ["Wh", "kWh"])
def test_zero_energy_keeps_its_unit_and_fresh_attributes(make_sensor, unit):
    sensor = make_sensor(
        "current_energy",
        results={"current_energy": Decimal(0), "current_energy_unit": unit},
    )
    expected = {"source_type": "daily", "period_complete": True}
    assert sensor.available is True
    assert sensor.native_value == Decimal(0)
    assert sensor.native_unit_of_measurement == unit
    changed = sensor.extra_state_attributes
    changed["period_complete"] = False
    assert sensor.extra_state_attributes == expected


@pytest.mark.parametrize("external", [False, True])
async def test_cost_energy_publication_and_reload_preserve_scopes_and_identity(
    hass, setup_electricity_pro, freezer, external
):
    """Keep local/external ownership and the average's five-minute publication."""
    await hass.config.async_set_time_zone("UTC")
    now = datetime(2026, 11, 8, 12, tzinfo=UTC)
    freezer.move_to(now)
    entry = await setup_electricity_pro(
        energy_value="100",
        energy_source_type="lifetime",
        price_value="2",
        supplier_markup_per_kwh=0.18,
        grid_fee_per_kwh=0.1,
        energy_tax_per_kwh=0.2,
        fixed_supplier_fee_monthly=10,
        accumulated_cost_today_value="20" if external else None,
    )
    entities = {
        "cost_today": "sensor.electricity_pro_cost_today",
        "cost_this_month": "sensor.electricity_pro_cost_this_month",
        "total_supplier_cost_this_month": "sensor.electricity_pro_total_supplier_cost_this_month",
        "consumption_weighted_average_price_today": "sensor.electricity_pro_consumption_weighted_average_price_today",
        "current_energy": "sensor.electricity_pro_energy_today",
    }
    average_id = entities["consumption_weighted_average_price_today"]
    initial_average = hass.states.get(average_id)
    settings = (dict(entry.data), dict(entry.options))
    registry = er.async_get(hass)
    freezer.move_to(now + timedelta(seconds=10))
    hass.states.async_set("sensor.test_energy", "102", {"unit_of_measurement": "kWh"})
    await hass.async_block_till_done()
    assert hass.states.get(average_id) is initial_average
    for key, expected in (
        ("cost_today", "20" if external else "4.36"),
        ("cost_this_month", "20" if external else "4.36"),
        ("total_supplier_cost_this_month", "30" if external else "14.36"),
    ):
        assert Decimal(hass.states.get(entities[key]).state) == Decimal(expected)
    assert Decimal(hass.states.get(entities["current_energy"]).state) == 2

    freezer.move_to(now + timedelta(minutes=4))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(average_id) is initial_average

    freezer.move_to(now + timedelta(minutes=5))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    values = {
        "cost_today": "20" if external else "4.36",
        "cost_this_month": "20" if external else "4.36",
        "total_supplier_cost_this_month": "30" if external else "14.36",
        "consumption_weighted_average_price_today": None if external else "2.48",
        "current_energy": "2",
    }
    expected_attributes = {}
    local_attributes = {
        "source": "local_estimate",
        "coverage": "partial",
        "method": "meter_delta_uniform_allocation_over_observed_prices",
        "priced_energy_kwh": "2",
    }
    for key, entity_id in entities.items():
        state = hass.states.get(entity_id)
        if values[key] is None:
            assert state.state == "unavailable"
        else:
            assert Decimal(state.state) == Decimal(values[key])
        assert registry.async_get(entity_id).unique_id == f"{entry.entry_id}_{key}"
        if key == "current_energy":
            assert state.attributes["source_type"] == "lifetime"
            assert state.attributes["period_complete"] is False
        elif external:
            assert not local_attributes.keys() & state.attributes.keys()
        else:
            assert {
                name: state.attributes[name] for name in local_attributes
            } == local_attributes
        expected_attributes[key] = dict(state.attributes)

    monthly = hass.states.get("sensor.electricity_pro_energy_this_month")
    monthly_attributes = dict(monthly.attributes)
    monthly_value = monthly.state
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    for key, entity_id in entities.items():
        state = hass.states.get(entity_id)
        if values[key] is None:
            assert state.state == "unavailable"
        else:
            assert Decimal(state.state) == Decimal(values[key])
        assert dict(state.attributes) == expected_attributes[key]
        assert registry.async_get(entity_id).unique_id == f"{entry.entry_id}_{key}"
    monthly = hass.states.get("sensor.electricity_pro_energy_this_month")
    assert monthly.state == monthly_value
    assert dict(monthly.attributes) == monthly_attributes
    assert (dict(entry.data), dict(entry.options)) == settings
