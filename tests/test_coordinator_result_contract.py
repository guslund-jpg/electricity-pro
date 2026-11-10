"""Publication/order oracles recorded from 54e0c05 before ADR-0014 stage 2."""

from contextlib import ExitStack
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
import json
from pathlib import Path
from typing import get_type_hints
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import (
    ElectricityProCoordinator,
    _DataUpdates,
)
from custom_components.electricity_pro.cost_ledger import VariableCostSummary
from custom_components.electricity_pro.data import (
    CalculationContext,
    ElectricityProData,
    SourceReadings,
    IntegrationResults,
    ProviderSnapshot,
)
from custom_components.electricity_pro.household_cost import BilledDemandCharge

_START = datetime(2026, 11, 2, 22, 50, tzinfo=UTC)
_FIXTURES = Path(__file__).parent / "fixtures" / "coordinator_results"


def _encode(value):
    """Retain Decimal scale, timestamp offsets and every snapshot field."""
    if isinstance(value, ElectricityProData):
        return {
            "current_power": _encode(value.readings.current_power),
            "current_power_bidirectional": _encode(
                value.readings.current_power_bidirectional
            ),
            "current_price": _encode(value.readings.current_price),
            "current_price_unit": _encode(value.readings.current_price_unit),
            "pricing_metadata": _encode(value.context.pricing_metadata),
            "current_energy": _encode(value.results.current_energy),
            "current_energy_unit": _encode(value.results.current_energy_unit),
            "energy_source_type": _encode(value.readings.energy_source_type),
            "energy_today_period_complete": _encode(
                value.results.energy_today_period_complete
            ),
            "accumulated_cost_today": _encode(value.results.accumulated_cost_today),
            "accumulated_cost_today_unit": _encode(
                value.results.accumulated_cost_today_unit
            ),
            "peak_power_today": _encode(value.results.peak_power_today),
            "peak_power_time_today": _encode(value.results.peak_power_time_today),
            "current_l1": _encode(value.readings.current_l1),
            "current_l2": _encode(value.readings.current_l2),
            "current_l3": _encode(value.readings.current_l3),
            "voltage_l1": _encode(value.readings.voltage_l1),
            "voltage_l2": _encode(value.readings.voltage_l2),
            "voltage_l3": _encode(value.readings.voltage_l3),
            "monthly_peak_hour_consumption": _encode(
                value.readings.monthly_peak_hour_consumption
            ),
            "monthly_peak_hour_consumption_unit": _encode(
                value.readings.monthly_peak_hour_consumption_unit
            ),
            "monthly_peak_hour_time": _encode(value.readings.monthly_peak_hour_time),
            "energy_this_month": _encode(value.results.energy_this_month),
            "energy_this_month_unit": _encode(value.results.energy_this_month_unit),
            "cost_this_month": _encode(value.results.cost_this_month),
            "cost_this_month_unit": _encode(value.results.cost_this_month_unit),
            "fixed_supplier_fee_this_month": _encode(
                value.context.fixed_supplier_fee_this_month
            ),
            "fixed_supplier_fee_this_month_unit": _encode(
                value.results.fixed_supplier_fee_this_month_unit
            ),
            "fixed_grid_fee_this_month": _encode(
                value.context.fixed_grid_fee_this_month
            ),
            "fixed_grid_fee_this_month_unit": _encode(
                value.results.fixed_grid_fee_this_month_unit
            ),
            "total_supplier_cost_this_month": _encode(
                value.results.total_supplier_cost_this_month
            ),
            "total_supplier_cost_this_month_unit": _encode(
                value.results.total_supplier_cost_this_month_unit
            ),
            "grid_fee_per_kwh": _encode(value.context.grid_fee_per_kwh),
            "supplier_markup_per_kwh": _encode(value.context.supplier_markup_per_kwh),
            "energy_tax_per_kwh": _encode(value.context.energy_tax_per_kwh),
            "good_price_threshold": _encode(value.context.good_price_threshold),
            "local_cost_estimate": _encode(value.results.local_cost_estimate),
            "local_effective_cost_today": _encode(
                value.results.local_effective_cost_today
            ),
            "local_priced_energy_today": _encode(
                value.results.local_priced_energy_today
            ),
            "local_supplier_energy_today": _encode(
                value.results.local_supplier_energy_today
            ),
            "local_supplier_energy_month": _encode(
                value.results.local_supplier_energy_month
            ),
            "household_cost_today": _encode(value.results.household_cost_today),
            "household_cost_this_month": _encode(
                value.results.household_cost_this_month
            ),
            "household_cost_unit": _encode(value.results.household_cost_unit),
            "household_variable_today": _encode(value.results.household_variable_today),
            "household_variable_month": _encode(value.results.household_variable_month),
            "household_fixed_today": _encode(value.results.household_fixed_today),
            "household_fixed_month": _encode(value.results.household_fixed_month),
            "household_priced_energy_today": _encode(
                value.results.household_priced_energy_today
            ),
            "household_priced_energy_month": _encode(
                value.results.household_priced_energy_month
            ),
            "household_missing_fees": _encode(value.results.household_missing_fees),
        }
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    if isinstance(value, datetime):
        return {"datetime": value.isoformat()}
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            field.name: _encode(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(_encode(item) for item in value)
    if isinstance(value, (tuple, list)):
        return [_encode(item) for item in value]
    return value


def _coordinator(hass, mode="lifetime", external=False):
    data = {
        "power_entity": "sensor.result_power",
        "price_entity": "sensor.result_price",
        "energy_entity": "sensor.result_energy",
        "energy_source_type": mode,
        "pricing_strategy": "market_price_plus_tariff",
        "price_included_components": ["market_energy"],
        "price_vat_treatment": "excluded",
        "price_completeness": "partial",
        "price_vat_rate": "25.00",
        "grid_fee_per_kwh": "0.1250",
        "supplier_markup_per_kwh": "0.0800",
        "energy_tax_per_kwh": "0.2500",
        "fixed_supplier_fee_monthly": "49.00",
        "fixed_grid_fee_monthly": "630.00",
        "good_price_threshold": "1.5000",
    }
    if external:
        data["accumulated_cost_today_entity"] = "sensor.result_cost"
    for name, value, unit in (
        ("power", "1.2500", "kW"),
        ("price", "-0.123400", "SEK/kWh"),
        ("energy", "100000.0000", "Wh"),
        ("cost", "12.3400", "SEK"),
    ):
        _set(hass, name, value, unit)
    return ElectricityProCoordinator(hass, MockConfigEntry(domain=DOMAIN, data=data))


def _set(hass, name, value, unit):
    hass.states.async_set(f"sensor.result_{name}", value, {"unit_of_measurement": unit})


@pytest.mark.parametrize("mode", ["daily", "lifetime"])
@pytest.mark.parametrize("external", [False, True], ids=["local", "external"])
async def test_publication_matches_pre_extraction_snapshots(hass, mode, external):
    await hass.config.async_set_time_zone("Europe/Stockholm")
    coordinator = _coordinator(hass, mode, external)
    snapshots = {}

    def read(label, minutes):
        with patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=_START + timedelta(minutes=minutes),
        ):
            data = coordinator._read(power_observed=True)
            coordinator.async_set_updated_data(data)
        snapshots[label] = _encode(data)

    with (
        patch.object(coordinator._store, "async_delay_save"),
        patch.object(coordinator._store, "async_save"),
    ):
        read("initial", 0)
        _set(hass, "energy", "101250.0000", "Wh")
        _set(hass, "cost", "13.4500", "SEK")
        read("delta", 5)
        for name, unit in (
            ("energy", "Wh"),
            ("cost", "SEK"),
            ("price", "SEK/kWh"),
            ("power", "kW"),
        ):
            _set(hass, name, "unavailable", unit)
        read("outage", 6)
        _set(hass, "energy", "101750.0000", "Wh")
        _set(hass, "cost", "13.5000", "SEK")
        _set(hass, "price", "0.0000", "SEK/kWh")
        _set(hass, "power", "-0.5000", "kW")
        read("recovery", 7)
        midnight = _START + timedelta(minutes=10)
        with patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=midnight,
        ):
            coordinator._async_daily_rollover(midnight)
        snapshots["rollover"] = _encode(coordinator.data)
        _set(hass, "energy", "101800.0000" if mode == "lifetime" else "50.0000", "Wh")
        read("new_day", 11)
        with patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=midnight + timedelta(minutes=2),
        ):
            await coordinator.async_reset_monthly_energy()
        snapshots["monthly_reset"] = _encode(coordinator.data)
        if mode == "lifetime":
            _set(hass, "energy", "100.0000", "Wh")
            with patch(
                "custom_components.electricity_pro.coordinator.dt_util.now",
                return_value=midnight + timedelta(minutes=3),
            ):
                await coordinator.async_confirm_meter_reset()
            snapshots["meter_reset"] = _encode(coordinator.data)

    # One full baseline followed by recorded field changes keeps the oracle small.
    path = _FIXTURES / f"{mode}_{'external' if external else 'local'}.json"
    expected = {}
    for label, changes in json.loads(path.read_text()).items():
        expected.update(changes)
        assert len(expected) == 51
        assert snapshots[label] == expected, label


@pytest.mark.parametrize("power_observed", [False, True])
async def test_read_keeps_separate_clocks_and_feature_order(hass, power_observed):
    await hass.config.async_set_time_zone("UTC")
    coordinator = _coordinator(hass)
    trace = []
    moments = iter([_START, _START + timedelta(seconds=1)])

    def clock():
        moment = next(moments)
        trace.append(("clock", moment))
        return moment

    def tariff(at):
        trace.append(("tariff", at))
        return Decimal("0.1250")

    def observe(owner, name, label):
        original = getattr(owner, name)

        def call(*args, **kwargs):
            trace.append((label, kwargs) if label in {"timing", "base_load"} else label)
            return original(*args, **kwargs)

        return patch.object(owner, name, side_effect=call)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "custom_components.electricity_pro.coordinator.dt_util.now",
                side_effect=clock,
            )
        )
        stack.enter_context(
            patch.object(coordinator._provider, "grid_fee_at", side_effect=tariff)
        )
        stack.enter_context(patch.object(coordinator._store, "async_delay_save"))
        for owner, name, label in (
            (coordinator._provider, "read", "inputs"),
            (coordinator, "_read_flows", "flows"),
            (coordinator._energy_today_from_total, "update", "daily_energy"),
            (coordinator, "_update_timing_history", "timing"),
            (coordinator, "_update_base_load_history", "base_load"),
            (coordinator, "_update_adaptive_price_history", "adaptive"),
            (coordinator._peak_power_today, "update", "peak"),
            (coordinator._energy_this_month, "update", "monthly_energy"),
            (coordinator._local_costs, "update", "ledger"),
            (coordinator, "_schedule_statistics_save", "save"),
        ):
            stack.enter_context(observe(owner, name, label))
        coordinator._read(power_observed=power_observed)
    assert trace == [
        "inputs",
        ("clock", _START),
        ("tariff", _START),
        ("clock", _START + timedelta(seconds=1)),
        "flows",
        "daily_energy",
        ("timing", {"power_observed": power_observed}),
        ("base_load", {"power_observed": power_observed}),
        "adaptive",
        "peak",
        "monthly_energy",
        "ledger",
        "save",
    ]


@pytest.mark.parametrize("path", ["read", "rollover", "forecast", "meter_reset"])
async def test_provider_read_sites_keep_their_existing_clock_cadence(hass, path):
    await hass.config.async_set_time_zone("UTC")
    coordinator = _coordinator(hass)
    trace = []
    original = coordinator._provider.read

    def inputs():
        trace.append("inputs")
        return original()

    def clock():
        trace.append("clock")
        return _START

    def tariff(at):
        trace.append("tariff")
        assert at == _START
        return Decimal("0.1250")

    with (
        patch.object(coordinator._provider, "read", side_effect=inputs),
        patch.object(coordinator._provider, "grid_fee_at", side_effect=tariff),
        patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            side_effect=clock,
        ),
        patch.object(coordinator._store, "async_delay_save"),
        patch.object(coordinator._store, "async_save"),
    ):
        if path == "read":
            coordinator._read()
        elif path == "rollover":
            coordinator._async_daily_rollover(_START)
        elif path == "forecast":
            coordinator._recalculate_forecast_insights()
        else:
            await coordinator.async_confirm_meter_reset()
    assert (
        trace
        == {
            "read": ["inputs", "clock", "tariff", "clock"],
            "rollover": ["inputs", "clock", "tariff"],
            "forecast": ["clock", "inputs", "clock", "tariff"],
            "meter_reset": [
                "inputs",
                "clock",
                "tariff",
                "clock",
                "inputs",
                "clock",
                "tariff",
                "clock",
            ],
        }[path]
    )


def test_result_schema_retains_snapshot_types():
    """Keep the reviewed types independent of the new container hierarchy."""
    updates = get_type_hints(_DataUpdates)
    results = get_type_hints(IntegrationResults)
    expected = {
        "current_energy": Decimal | None,
        "current_energy_unit": str | None,
        "energy_today_period_complete": bool,
        "accumulated_cost_today": Decimal | None,
        "accumulated_cost_today_unit": str | None,
        "peak_power_today": Decimal | None,
        "peak_power_time_today": datetime | None,
        "energy_this_month": Decimal | None,
        "energy_this_month_unit": str | None,
        "cost_this_month": Decimal | None,
        "cost_this_month_unit": str | None,
        "fixed_supplier_fee_this_month_unit": str | None,
        "fixed_grid_fee_this_month_unit": str | None,
        "total_supplier_cost_this_month": Decimal | None,
        "total_supplier_cost_this_month_unit": str | None,
        "local_cost_estimate": bool,
        "local_effective_cost_today": Decimal | None,
        "local_priced_energy_today": Decimal | None,
        "local_supplier_energy_today": Decimal | None,
        "local_supplier_energy_month": Decimal | None,
        "household_cost_today": Decimal | None,
        "household_cost_this_month": Decimal | None,
        "household_cost_unit": str | None,
        "household_variable_today": Decimal | None,
        "household_variable_month": Decimal | None,
        "household_variable_breakdown_month": VariableCostSummary | None,
        "household_fixed_today": Decimal | None,
        "household_fixed_month": Decimal | None,
        "household_fixed_supplier_month": Decimal | None,
        "household_fixed_grid_month": Decimal | None,
        "billed_demand_charge": BilledDemandCharge | None,
        "billed_demand_charge_in_estimate": bool,
        "household_priced_energy_today": Decimal | None,
        "household_priced_energy_month": Decimal | None,
        "household_missing_fees": tuple[str, ...],
    }
    assert len(updates) == len(results) == 35
    assert results == expected
    assert updates.keys() == expected.keys()
    assert sum(updates[name] != results[name] for name in updates) == 10


def test_grouped_publication_keeps_input_identity_and_is_immutable(hass):
    inputs = _coordinator(hass)._provider.read()
    results = replace(
        IntegrationResults.from_inputs(inputs),
        current_energy=Decimal("1.2500"),
        current_energy_unit="kWh",
        accumulated_cost_today=Decimal("12.5000"),
    )
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        side_effect=AssertionError("clock"),
    ):
        published = ElectricityProData(
            readings=inputs.readings, context=inputs.context, results=results
        )
    assert published.readings is inputs.readings
    assert published.context is inputs.context
    assert published.results is results
    assert published.readings.import_energy_value == Decimal("100000.0000")
    assert published.readings.import_energy_unit == "Wh"
    assert published.readings.external_cost_today is None
    assert published.results.current_energy == Decimal("1.2500")
    assert published.results.current_energy_unit == "kWh"
    assert published.results.accumulated_cost_today == Decimal("12.5000")
    assert get_type_hints(ElectricityProData) == {
        "readings": SourceReadings,
        "context": CalculationContext,
        "results": IntegrationResults,
    }
    assert not hasattr(published, "current_energy")
    assert not hasattr(_coordinator(hass)._provider, "read_inputs")
    for group in (published, published.readings, published.context, published.results):
        assert not hasattr(group, "__dict__")
        with pytest.raises(FrozenInstanceError):
            setattr(group, fields(group)[0].name, None)


async def test_each_read_composes_fresh_results_without_mutating_raw_sources(hass):
    await hass.config.async_set_time_zone("UTC")
    coordinator = _coordinator(hass)
    captured = []
    original = coordinator._provider.read

    def read_provider():
        inputs = original()
        captured.append(inputs)
        return inputs

    with (
        patch.object(coordinator._provider, "read", side_effect=read_provider),
        patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=_START,
        ),
        patch.object(coordinator._store, "async_delay_save"),
    ):
        first = coordinator._read()
        _set(hass, "energy", "101250.0000", "Wh")
        with patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=_START + timedelta(minutes=5),
        ):
            second = coordinator._read()
    old_inputs, new_inputs = captured
    assert isinstance(old_inputs, ProviderSnapshot)
    assert old_inputs is not new_inputs
    assert first.readings is old_inputs.readings
    assert second.readings is new_inputs.readings
    assert first.context is old_inputs.context
    assert second.context is new_inputs.context
    assert first.results is not second.results
    assert old_inputs.readings.import_energy_value == Decimal("100000.0000")
    assert new_inputs.readings.import_energy_value == Decimal("101250.0000")
    assert old_inputs.readings.external_cost_today is None
    assert new_inputs.readings.external_cost_today is None
    assert first.results.current_energy == Decimal(0)
    assert second.results.current_energy == Decimal("1.2500000")
    assert second.results.accumulated_cost_today == Decimal("-0.092812500000000")
    assert not any(
        isinstance(value, IntegrationResults) for value in vars(coordinator).values()
    )


@pytest.mark.parametrize("mode", ["daily", "lifetime"])
@pytest.mark.parametrize("action", ["monthly_reset", "rollover"])
async def test_action_overlays_replace_only_results(hass, mode, action):
    """Fresh provider reads must not replace the overlay's original input groups."""
    await hass.config.async_set_time_zone("UTC")
    coordinator = _coordinator(hass, mode)
    with (
        patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=_START,
        ),
        patch.object(coordinator._store, "async_delay_save"),
        patch.object(coordinator._store, "async_save"),
    ):
        coordinator.async_set_updated_data(coordinator._read(power_observed=True))
        _set(hass, "energy", "101250.0000", "Wh")
        with patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=_START + timedelta(minutes=5),
        ):
            coordinator.async_set_updated_data(coordinator._read())
        _set(hass, "energy", "101750.0000", "Wh")
        if action == "rollover":
            before = coordinator.data
            midnight = datetime(2026, 11, 3, tzinfo=UTC)
            with patch(
                "custom_components.electricity_pro.coordinator.dt_util.now",
                return_value=midnight,
            ):
                coordinator._async_daily_rollover(midnight)
            allowed = {"peak_power_today", "peak_power_time_today"}
            if mode == "lifetime":
                allowed |= {
                    "current_energy",
                    "current_energy_unit",
                    "energy_today_period_complete",
                }
                assert coordinator.data.results.current_energy == 0
            assert coordinator.data.results.peak_power_today is None
            assert coordinator.data.readings.import_energy_value == Decimal(
                "101250.0000"
            )
        else:
            captured = []
            original = coordinator._read

            def read():
                snapshot = original()
                captured.append(snapshot)
                return snapshot

            with (
                patch.object(coordinator, "_read", side_effect=read),
                patch(
                    "custom_components.electricity_pro.coordinator.dt_util.now",
                    return_value=_START + timedelta(minutes=6),
                ),
            ):
                await coordinator.async_reset_monthly_energy()
            before = captured[0]
            allowed = {"energy_this_month", "energy_this_month_unit"}
            assert coordinator.data.results.energy_this_month == 0
            assert coordinator.data.readings.import_energy_value == Decimal(
                "101750.0000"
            )
    after = coordinator.data
    assert after.readings is before.readings
    assert after.context is before.context
    assert after.results is not before.results
    for field in fields(before.results):
        if field.name not in allowed:
            assert getattr(after.results, field.name) is getattr(
                before.results, field.name
            )
