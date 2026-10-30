"""Characterize runtime option precedence before sharing settings resolution."""

import hashlib
from decimal import Decimal

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN, ENERGY_SOURCE_LIFETIME
from custom_components.electricity_pro.coordinator import (
    ElectricityProCoordinator,
    _adaptive_tariff_signature,
)
from custom_components.electricity_pro.provider import ElectricityProEntityProvider


@pytest.mark.parametrize("value", [None, 0, ""])
def test_provider_options_do_not_fall_back_to_setup_values(hass, value):
    """Cleared and zero options retain the provider's existing normalization."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "power_entity": "sensor.old_power",
            "energy_entity": "sensor.old_energy",
            "grid_fee_per_kwh": 1,
            "good_price_threshold": 2,
            "fixed_supplier_fee_monthly": 49,
            "fixed_grid_fee_monthly": 600,
        },
        options={
            "power_entity": "sensor.new_power",
            "energy_entity": None,
            "grid_fee_per_kwh": value,
            "good_price_threshold": value,
            "fixed_supplier_fee_monthly": value,
            "fixed_grid_fee_monthly": value,
        },
    )
    hass.states.async_set("sensor.new_power", "1000", {"unit_of_measurement": "W"})
    provider = ElectricityProEntityProvider(hass, entry)
    data = provider.read()
    expected = Decimal(0) if value == 0 else None
    assert provider.power_entity_id == "sensor.new_power"
    assert provider.energy_entity_id is None
    assert data.current_power == Decimal(1000)
    assert data.grid_fee_per_kwh == expected
    assert data.good_price_threshold == expected
    assert data.fixed_supplier_fee_this_month == expected
    assert data.fixed_grid_fee_this_month == expected


@pytest.mark.parametrize("value", [None, "", False])
def test_coordinator_explicit_clearing_and_fresh_settings(hass, value):
    """Coordinator lookups preserve clearing and do not cache merged options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "power_entity": "sensor.power",
            "forecast_nordpool_config_entry": "old-source",
            "grid_fee_workday_entity": "binary_sensor.old_workday",
        },
        options={
            "forecast_nordpool_config_entry": value,
            "grid_fee_workday_entity": value,
        },
    )
    entry.add_to_hass(hass)
    coordinator = ElectricityProCoordinator(hass, entry)
    assert coordinator.forecast_configured is False
    assert coordinator._workday_entity_id is None
    hass.config_entries.async_update_entry(entry, options={
        "forecast_nordpool_config_entry": "new-source",
        "grid_fee_workday_entity": "binary_sensor.new_workday",
    })
    assert coordinator.forecast_configured is True
    assert coordinator._workday_entity_id == "binary_sensor.new_workday"
    hass.config_entries.async_update_entry(entry, options={})
    assert coordinator.forecast_configured is True
    assert coordinator._workday_entity_id == "binary_sensor.old_workday"


def test_stored_scope_and_tariff_signature_keep_explicit_zero_and_none(hass):
    """The same resolved values must retain stored cost/history identities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "power_entity": "sensor.power",
            "energy_entity": "sensor.old_energy",
            "grid_fee_per_kwh": 1,
            "supplier_markup_per_kwh": 2,
        },
        options={
            "energy_entity": None,
            "grid_fee_per_kwh": 0,
            "supplier_markup_per_kwh": None,
        },
    )
    coordinator = ElectricityProCoordinator(hass, entry)
    assert coordinator._local_cost_scope["settings"] == {
        "energy_entity": None,
        "grid_fee_per_kwh": 0,
        "supplier_markup_per_kwh": None,
    }
    expected = hashlib.sha256(
        b'{"grid_fee_per_kwh":0,"supplier_markup_per_kwh":null}'
    ).hexdigest()
    assert _adaptive_tariff_signature(entry) == expected


async def test_cleared_keys_still_create_existing_unavailable_entities(hass):
    """Presence-based entity creation is not replaced with truthiness checks."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "power_entity": "sensor.power",
            "price_entity": "sensor.old_price",
            "good_price_threshold": 1,
        },
        options={"price_entity": None, "good_price_threshold": None},
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.power", "1000", {"unit_of_measurement": "W"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    for entity_id in (
        "sensor.electricity_pro_current_price",
        "binary_sensor.electricity_pro_good_time_to_use_electricity",
    ):
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "unavailable"


def test_provider_still_requires_power_in_setup_data(hass):
    """An options-only power source does not relax the existing setup contract."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, options={"power_entity": "sensor.power"},
    )
    with pytest.raises(KeyError, match="power_entity"):
        ElectricityProEntityProvider(hass, entry)


@pytest.mark.parametrize("value", [None, "", "invalid"])
def test_invalid_energy_source_option_keeps_daily_fallback(hass, value):
    """Value validation stays with the provider, after option precedence."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"power_entity": "sensor.power", "energy_source_type": ENERGY_SOURCE_LIFETIME},
        options={"energy_source_type": value},
    )
    assert ElectricityProEntityProvider(hass, entry).energy_source_is_lifetime_total is False
