"""Integration coverage for dongles without supplier cost sensors."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.sensor import consumption_weighted_average_price

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)


async def test_local_cost_entities_and_matching_effective_average(hass, setup_electricity_pro):
    with patch("custom_components.electricity_pro.coordinator.dt_util.now", return_value=NOW):
        entry = await setup_electricity_pro(
            energy_value="100", energy_source_type="lifetime", price_value="2",
            supplier_markup_per_kwh=0.18, grid_fee_per_kwh=0.1,
            energy_tax_per_kwh=0.2, fixed_supplier_fee_monthly=10,
        )
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=NOW + timedelta(minutes=5),
    ):
        hass.states.async_set("sensor.test_energy", "102", {"unit_of_measurement": "kWh"})
        await hass.async_block_till_done()
    data = entry.runtime_data.data
    assert data.accumulated_cost_today == Decimal("4.36")
    assert data.cost_this_month == Decimal("4.36")
    assert data.total_supplier_cost_this_month == Decimal("14.36")
    assert consumption_weighted_average_price(data) == Decimal("2.48")
    assert data.local_priced_energy_today == Decimal(2)
    assert data.local_cost_estimate
    for name in ("cost_today", "cost_this_month"):
        state = hass.states.get("sensor.electricity_pro_" + name)
        assert state is not None
        assert state.attributes["source"] == "local_estimate"
        assert state.attributes["coverage"] == "partial"


async def test_configured_external_cost_remains_authoritative(hass, setup_electricity_pro):
    entry = await setup_electricity_pro(
        energy_value="100", price_value="2", supplier_markup_per_kwh=0,
        accumulated_cost_today_value="20",
    )
    assert entry.runtime_data.data.accumulated_cost_today == Decimal(20)
    assert not entry.runtime_data.data.local_cost_estimate
    hass.states.async_set("sensor.test_accumulated_cost_today", "unavailable")
    await hass.async_block_till_done()
    assert entry.runtime_data.data.accumulated_cost_today is None
    assert not entry.runtime_data.data.local_cost_estimate


async def test_changed_pricing_does_not_restore_old_estimates(hass, setup_electricity_pro):
    entry = await setup_electricity_pro(
        energy_value="100", price_value="2", supplier_markup_per_kwh=0,
    )
    stored = entry.runtime_data._statistics_data()
    stored["local_costs"]["monthly_supplier"] = "999"
    changed = MockConfigEntry(domain=entry.domain, data={
        **entry.data, "supplier_markup_per_kwh": 0.18,
    })
    coordinator = ElectricityProCoordinator(hass, changed)
    with patch.object(coordinator._store, "async_load", return_value=stored):
        await coordinator._async_restore_statistics()
    assert coordinator._local_costs.monthly_supplier == 0
