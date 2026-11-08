"""Publication/order oracles recorded from 54e0c05 before ADR-0014 stage 2."""

from contextlib import ExitStack
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
import json
from pathlib import Path
from typing import get_args, get_type_hints
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import DOMAIN
from custom_components.electricity_pro.coordinator import (
    ElectricityProCoordinator,
    _DataUpdates,
)
from custom_components.electricity_pro.data import (
    ElectricityProData,
    IntegrationResults,
    ProviderSnapshot,
    legacy_provider_view,
    legacy_published_view,
)

_START = datetime(2026, 11, 2, 22, 50, tzinfo=UTC)
_FIXTURES = Path(__file__).parent / "fixtures" / "coordinator_results"


def _encode(value):
    """Retain Decimal scale, timestamp offsets and every snapshot field."""
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
            (coordinator._provider, "read_inputs", "inputs"),
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
    original = coordinator._provider.read_inputs

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
        patch.object(coordinator._provider, "read_inputs", side_effect=inputs),
        patch.object(
            coordinator._provider, "read", side_effect=AssertionError("legacy read")
        ),
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


def test_result_schema_retains_all_thirty_snapshot_types():
    updates = get_type_hints(_DataUpdates)
    snapshot = get_type_hints(ElectricityProData)
    results = get_type_hints(IntegrationResults)
    assert len(updates) == len(results) == 30
    assert results == {name: snapshot[name] for name in updates}
    # The update dictionary deliberately has ten narrower Decimal annotations.
    assert sum(updates[name] != results[name] for name in updates) == 10


def test_publication_projection_selects_every_result_and_keeps_input_identity(hass):
    inputs = _coordinator(hass)._provider.read_inputs()
    before = _encode(inputs)
    values = {}
    for index, (name, annotation) in enumerate(
        get_type_hints(IntegrationResults).items()
    ):
        choices = get_args(annotation) or (annotation,)
        if Decimal in choices:
            value = Decimal(f"{index + 10}.0000")
        elif annotation == tuple[str, ...]:
            value = ("result:missing_fee",)
        elif str in choices:
            value = f"result:{name}"
        elif datetime in choices:
            value = _START
        elif annotation is bool:
            value = True
        else:
            value = ("result:missing_fee",)
        values[name] = value
    results = IntegrationResults(**values)
    raw = legacy_provider_view(inputs)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        side_effect=AssertionError("clock"),
    ):
        published = legacy_published_view(inputs, results)
    for field in fields(published):
        owner = results if field.name in values else raw
        assert getattr(published, field.name) is getattr(owner, field.name)
    assert _encode(inputs) == before
    assert not hasattr(results, "__dict__")
    with pytest.raises(FrozenInstanceError):
        results.current_energy = None


async def test_each_read_composes_fresh_results_without_mutating_raw_sources(hass):
    await hass.config.async_set_time_zone("UTC")
    coordinator = _coordinator(hass)
    composed = []

    def publish(inputs, results):
        assert isinstance(inputs, ProviderSnapshot)
        assert isinstance(results, IntegrationResults)
        composed.append((inputs, results))
        return legacy_published_view(inputs, results)

    with (
        patch(
            "custom_components.electricity_pro.coordinator.legacy_published_view",
            side_effect=publish,
        ),
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
    old_inputs, old_results = composed[0]
    new_inputs, new_results = composed[1]
    assert old_inputs is not new_inputs
    assert old_results is not new_results
    assert old_inputs.readings.import_energy_value == Decimal("100000.0000")
    assert new_inputs.readings.import_energy_value == Decimal("101250.0000")
    assert old_inputs.readings.external_cost_today is None
    assert new_inputs.readings.external_cost_today is None
    assert first.current_energy == old_results.current_energy == Decimal(0)
    assert second.current_energy == new_results.current_energy == Decimal("1.2500000")
    assert second.accumulated_cost_today == Decimal("-0.092812500000000")
    assert not any(
        isinstance(value, IntegrationResults) for value in vars(coordinator).values()
    )
