"""Shared fixtures for Electricity Pro tests."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
    CONF_CURRENT_L1_ENTITY,
    CONF_CURRENT_L2_ENTITY,
    CONF_CURRENT_L3_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_FORECAST_CURRENCY,
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FORECAST_PRICE_AREA,
    CONF_FIXED_SUPPLIER_FEE_MONTHLY,
    CONF_FIXED_GRID_FEE_MONTHLY,
    CONF_GRID_FEE_PER_KWH,
    CONF_GOOD_PRICE_THRESHOLD,
    CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
    CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
    CONF_PEAK_POWER_TODAY_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICING_STRATEGY,
    CONF_VOLTAGE_L1_ENTITY,
    CONF_VOLTAGE_L2_ENTITY,
    CONF_VOLTAGE_L3_ENTITY,
    DOMAIN,
)
from custom_components.electricity_pro.forecast import ForecastInterval
from custom_components.electricity_pro.pricing import (
    PriceComponent,
    PriceCompleteness,
    PricingStrategy,
    VatTreatment,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable custom integrations for every test."""


@pytest.fixture
def setup_electricity_pro(hass):
    """Set up Electricity Pro with configurable source sensors."""

    async def _setup(
        power_value: str = "1234",
        power_unit: str = "W",
        price_value: str | None = None,
        price_unit: str = "SEK/kWh",
        include_pricing_metadata: bool = True,
        energy_value: str | None = None,
        energy_unit: str = "kWh",
        accumulated_cost_today_value: str | None = None,
        accumulated_cost_today_unit: str = "SEK",
        peak_power_today_value: str | None = None,
        peak_power_today_unit: str = "W",
        current_l1_value: str | None = None,
        current_l2_value: str | None = None,
        current_l3_value: str | None = None,
        voltage_l1_value: str | None = None,
        voltage_l2_value: str | None = None,
        voltage_l3_value: str | None = None,
        monthly_peak_hour_consumption_value: str | None = None,
        monthly_peak_hour_consumption_unit: str = "kWh",
        monthly_peak_hour_time_value: str | None = None,
        grid_fee_per_kwh: float | None = None,
        fixed_supplier_fee_monthly: float | None = None,
        fixed_grid_fee_monthly: float | None = None,
        good_price_threshold: float | None = None,
        forecast_price_area: str | None = None,
        forecast_currency: str | None = None,
        forecast_nordpool_config_entry: str | None = None,
        forecast_intervals: list[dict[str, object]] | None = None,
    ) -> MockConfigEntry:
        """Create and set up an Electricity Pro config entry."""

        hass.states.async_set(
            "sensor.test_power",
            power_value,
            {
                "unit_of_measurement": power_unit,
                "device_class": "power",
            },
        )

        entry_data = {
            CONF_POWER_ENTITY: "sensor.test_power",
        }

        if grid_fee_per_kwh is not None:
            entry_data[CONF_GRID_FEE_PER_KWH] = grid_fee_per_kwh

        if fixed_supplier_fee_monthly is not None:
            entry_data[CONF_FIXED_SUPPLIER_FEE_MONTHLY] = (
                fixed_supplier_fee_monthly
            )

        if fixed_grid_fee_monthly is not None:
            entry_data[CONF_FIXED_GRID_FEE_MONTHLY] = fixed_grid_fee_monthly

        if good_price_threshold is not None:
            entry_data[CONF_GOOD_PRICE_THRESHOLD] = good_price_threshold

        if forecast_price_area is not None:
            entry_data[CONF_FORECAST_PRICE_AREA] = forecast_price_area

        if forecast_currency is not None:
            entry_data[CONF_FORECAST_CURRENCY] = forecast_currency

        if forecast_nordpool_config_entry is not None:
            entry_data[CONF_FORECAST_NORDPOOL_CONFIG_ENTRY] = (
                forecast_nordpool_config_entry
            )

        if price_value is not None:
            hass.states.async_set(
                "sensor.test_price",
                price_value,
                {
                    "unit_of_measurement": price_unit,
                    "device_class": "monetary",
                },
            )
            entry_data[CONF_PRICE_ENTITY] = "sensor.test_price"
            if include_pricing_metadata:
                entry_data[CONF_PRICING_STRATEGY] = (
                    PricingStrategy.SUPPLIER_CONTRACTED_PRICE.value
                )
                entry_data[CONF_PRICE_INCLUDED_COMPONENTS] = [
                    PriceComponent.MARKET_ENERGY.value,
                ]
                entry_data[CONF_PRICE_VAT_TREATMENT] = VatTreatment.INCLUDED.value
                entry_data[CONF_PRICE_COMPLETENESS] = (
                    PriceCompleteness.PARTIAL.value
                )

        if energy_value is not None:
            hass.states.async_set(
                "sensor.test_energy",
                energy_value,
                {
                    "unit_of_measurement": energy_unit,
                    "device_class": "energy",
                    "state_class": "total_increasing",
                },
            )
            entry_data[CONF_ENERGY_ENTITY] = "sensor.test_energy"

        if accumulated_cost_today_value is not None:
            hass.states.async_set(
                "sensor.test_accumulated_cost_today",
                accumulated_cost_today_value,
                {
                    "unit_of_measurement": accumulated_cost_today_unit,
                    "device_class": "monetary",
                    "state_class": "total",
                },
            )
            entry_data[CONF_ACCUMULATED_COST_TODAY_ENTITY] = (
                "sensor.test_accumulated_cost_today"
            )

        if peak_power_today_value is not None:
            hass.states.async_set(
                "sensor.test_peak_power_today",
                peak_power_today_value,
                {
                    "unit_of_measurement": peak_power_today_unit,
                    "device_class": "power",
                },
            )
            entry_data[CONF_PEAK_POWER_TODAY_ENTITY] = "sensor.test_peak_power_today"

        if current_l1_value is not None:
            hass.states.async_set(
                "sensor.test_current_l1",
                current_l1_value,
                {
                    "unit_of_measurement": "A",
                    "device_class": "current",
                },
            )
            entry_data[CONF_CURRENT_L1_ENTITY] = "sensor.test_current_l1"

        if current_l2_value is not None:
            hass.states.async_set(
                "sensor.test_current_l2",
                current_l2_value,
                {
                    "unit_of_measurement": "A",
                    "device_class": "current",
                },
            )
            entry_data[CONF_CURRENT_L2_ENTITY] = "sensor.test_current_l2"

        if current_l3_value is not None:
            hass.states.async_set(
                "sensor.test_current_l3",
                current_l3_value,
                {
                    "unit_of_measurement": "A",
                    "device_class": "current",
                },
            )
            entry_data[CONF_CURRENT_L3_ENTITY] = "sensor.test_current_l3"
        if voltage_l1_value is not None:
            hass.states.async_set(
                "sensor.test_voltage_l1",
                voltage_l1_value,
                {
                    "unit_of_measurement": "V",
                    "device_class": "voltage",
                },
            )
            entry_data[CONF_VOLTAGE_L1_ENTITY] = "sensor.test_voltage_l1"

        if voltage_l2_value is not None:
            hass.states.async_set(
                "sensor.test_voltage_l2",
                voltage_l2_value,
                {
                    "unit_of_measurement": "V",
                    "device_class": "voltage",
                },
            )
            entry_data[CONF_VOLTAGE_L2_ENTITY] = "sensor.test_voltage_l2"

        if voltage_l3_value is not None:
            hass.states.async_set(
                "sensor.test_voltage_l3",
                voltage_l3_value,
                {
                    "unit_of_measurement": "V",
                    "device_class": "voltage",
                },
            )
            entry_data[CONF_VOLTAGE_L3_ENTITY] = "sensor.test_voltage_l3"

        if monthly_peak_hour_consumption_value is not None:
            hass.states.async_set(
                "sensor.test_monthly_peak_hour_consumption",
                monthly_peak_hour_consumption_value,
                {
                    "unit_of_measurement": monthly_peak_hour_consumption_unit,
                    "device_class": "energy",
                    "state_class": "measurement",
                },
            )
            entry_data[CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY] = (
                "sensor.test_monthly_peak_hour_consumption"
            )
        if monthly_peak_hour_time_value is not None:
            hass.states.async_set(
                "sensor.test_monthly_peak_hour_time",
                monthly_peak_hour_time_value,
                {"device_class": "timestamp"},
            )
            entry_data[CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY] = (
                "sensor.test_monthly_peak_hour_time"
            )
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Electricity Pro",
            data=entry_data,
        )

        entry.add_to_hass(hass)

        if forecast_intervals is None:
            assert await hass.config_entries.async_setup(entry.entry_id)
        else:
            normalized_forecast_intervals = [
                ForecastInterval(
                    start=datetime.fromisoformat(str(interval["start"])),
                    end=datetime.fromisoformat(str(interval["end"])),
                    market_price=Decimal(str(interval["price"])) / Decimal("1000"),
                    currency=str(forecast_currency),
                    area=str(forecast_price_area),
                )
                for interval in forecast_intervals
            ]
            with pytest.MonkeyPatch.context() as monkeypatch:
                monkeypatch.setattr(
                    "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
                    AsyncMock(return_value=normalized_forecast_intervals),
                )
                assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        return entry

    return _setup
