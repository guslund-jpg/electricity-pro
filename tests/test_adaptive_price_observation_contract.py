"""Characterize live adaptive-price observations before moving ownership."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_POWER_ENTITY,
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_ENTITY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICING_STRATEGY,
    DOMAIN,
)
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.pricing import (
    PriceCompleteness,
    PriceComponent,
    PricingStrategy,
    VatTreatment,
)

_UNCHANGED = object()


async def _coordinator(hass):
    """Use a declared complete price and the existing local-hour timezone."""
    await hass.config.async_set_time_zone("Europe/Stockholm")
    hass.states.async_set("sensor.test_price", "1", {"unit_of_measurement": "SEK/kWh"})
    return ElectricityProCoordinator(
        hass,
        MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_POWER_ENTITY: "sensor.test_power",
                CONF_PRICE_ENTITY: "sensor.test_price",
                CONF_PRICING_STRATEGY: PricingStrategy.EXTERNAL_COMPLETE_PRICE,
                CONF_PRICE_INCLUDED_COMPONENTS: list(PriceComponent),
                CONF_PRICE_VAT_TREATMENT: VatTreatment.INCLUDED,
                CONF_PRICE_COMPLETENESS: PriceCompleteness.COMPLETE,
            },
            entry_id="adaptive-price-observation-contract",
        ),
    )


def _update(coordinator, now, price="1", *, unit="SEK/kWh", metadata=_UNCHANGED):
    """Retain real price/scope calculation over explicit normalized inputs."""
    inputs = coordinator._provider.read()
    return coordinator._update_adaptive_price_history(
        replace(
            inputs,
            readings=replace(
                inputs.readings,
                current_price=Decimal(price) if price is not None else None,
                current_price_unit=unit,
            ),
            context=inputs.context
            if metadata is _UNCHANGED
            else replace(inputs.context, pricing_metadata=metadata),
        ),
        now,
    )


def _start(coordinator):
    return datetime(2026, 8, 24, tzinfo=coordinator._local_timezone)


async def test_adaptive_observation_weights_previous_price_and_signals_closed_hour(
    hass,
):
    """Price replacement preserves the old interval and exact Decimal weighting."""
    coordinator = await _coordinator(hass)
    start = _start(coordinator)
    assert _update(coordinator, start, "-0.1000")
    scope = coordinator.adaptive_price_scope
    assert scope == coordinator.adaptive_price_history.scope
    assert coordinator.adaptive_price_history.restart_reason is None
    assert not _update(coordinator, start + timedelta(minutes=15), "0.2500")
    assert _update(coordinator, start + timedelta(hours=1), "2")

    (observation,) = coordinator.adaptive_price_history.observations
    assert observation.effective_price == Decimal("0.1625")
    assert observation.covered_duration == timedelta(hours=1)
    assert observation.scope == scope == coordinator.adaptive_price_scope
    assert observation.as_dict()["effective_price"] == "0.1625"


async def test_adaptive_observation_quiet_valid_price_continues_without_power_hold(
    hass,
):
    """Adaptive price intervals retain their existing policy through quiet hours."""
    coordinator = await _coordinator(hass)
    start = _start(coordinator)
    _update(coordinator, start, "0")
    assert _update(coordinator, start + timedelta(hours=3), "2")

    observations = coordinator.adaptive_price_history.observations
    assert len(observations) == 3
    assert all(
        o.effective_price == 0 and o.covered_duration == timedelta(hours=1)
        for o in observations
    )


@pytest.mark.parametrize("missing", ["price", "metadata", "partial", "vat", "unit"])
async def test_adaptive_observation_invalid_input_clears_live_scope_without_erasing_history(
    hass, missing
):
    """A temporary invalid price/scope leaves a gap and keeps compatible history."""
    coordinator = await _coordinator(hass)
    start = _start(coordinator)
    _update(coordinator, start)
    old_scope = coordinator.adaptive_price_scope
    metadata = coordinator._provider.read().context.pricing_metadata
    arguments = {}
    if missing == "price":
        arguments["price"] = None
    elif missing == "metadata":
        arguments["metadata"] = None
    elif missing == "partial":
        arguments["metadata"] = replace(
            metadata,
            completeness=PriceCompleteness.PARTIAL,
            scope=replace(
                metadata.scope,
                included=metadata.scope.included - {PriceComponent.ENERGY_TAX},
            ),
        )
    elif missing == "vat":
        arguments["metadata"] = replace(
            metadata, scope=replace(metadata.scope, vat=VatTreatment.UNKNOWN)
        )
    else:
        arguments["unit"] = None

    assert _update(coordinator, start + timedelta(hours=1), **arguments)
    assert coordinator.adaptive_price_scope is None
    assert coordinator.adaptive_price_history.scope == old_scope
    assert len(coordinator.adaptive_price_history.observations) == 1
    assert not _update(coordinator, start + timedelta(hours=2), "2")
    assert _update(coordinator, start + timedelta(hours=3), "3")

    observations = coordinator.adaptive_price_history.observations
    assert [(o.start, o.effective_price) for o in observations] == [
        (start, Decimal(1)),
        (start + timedelta(hours=2), Decimal(2)),
    ]
    assert coordinator.adaptive_price_scope == old_scope
    assert coordinator.adaptive_price_history.restart_reason is None


@pytest.mark.parametrize("changed", ["currency", "components", "tariff"])
async def test_adaptive_observation_changed_comparable_scope_restarts_history_at_change(
    hass, changed
):
    """A genuinely different comparison partition clears prior hours and metadata."""
    coordinator = await _coordinator(hass)
    start = _start(coordinator)
    _update(coordinator, start)
    _update(coordinator, start + timedelta(hours=1))
    old_scope = coordinator.adaptive_price_scope
    assert len(coordinator.adaptive_price_history.observations) == 1
    arguments = {}
    if changed == "currency":
        arguments["unit"] = "EUR/kWh"
    elif changed == "components":
        metadata = coordinator._provider.read().context.pricing_metadata
        arguments["metadata"] = replace(
            metadata,
            scope=replace(
                metadata.scope,
                included=metadata.scope.included - {PriceComponent.VARIABLE_GRID_FEE},
            ),
        )
    else:
        coordinator._adaptive_tariff_signature = "replacement-tariff-signature"

    now = start + timedelta(hours=1, minutes=30)
    assert _update(coordinator, now, "2", **arguments)

    history = coordinator.adaptive_price_history
    assert coordinator.adaptive_price_scope != old_scope
    assert history.scope == coordinator.adaptive_price_scope
    assert history.observations == ()
    assert history.as_dict()["open_hours"] == []
    assert history.restarted_at == now
    assert history.restart_reason == "price_configuration_changed"


async def test_adaptive_observation_normalized_vat_keeps_comparable_history(hass):
    """A confirmed VAT conversion updates price without changing its final scope."""
    coordinator = await _coordinator(hass)
    start = _start(coordinator)
    _update(coordinator, start)
    old_scope = coordinator.adaptive_price_scope
    metadata = coordinator._provider.read().context.pricing_metadata
    excluding_vat = replace(
        metadata,
        vat_rate=Decimal(25),
        scope=replace(metadata.scope, vat=VatTreatment.EXCLUDED),
    )
    assert not _update(
        coordinator, start + timedelta(minutes=30), metadata=excluding_vat
    )
    assert _update(coordinator, start + timedelta(hours=1))

    (observation,) = coordinator.adaptive_price_history.observations
    assert observation.effective_price == Decimal("1.125")
    assert coordinator.adaptive_price_scope == old_scope
    assert coordinator.adaptive_price_history.restart_reason is None


@pytest.mark.parametrize("offset", [0, -1])
async def test_adaptive_observation_nonincreasing_time_retains_existing_cursor_policy(
    hass, offset
):
    """No interval is added for equal/backward time; later updates use that cursor."""
    coordinator = await _coordinator(hass)
    start = _start(coordinator)
    _update(coordinator, start)
    repeated = start + timedelta(hours=offset)
    assert not _update(coordinator, repeated, "2")
    assert not coordinator.adaptive_price_history.observations
    assert not coordinator.adaptive_price_history.as_dict()["open_hours"]
    assert _update(coordinator, repeated + timedelta(hours=1), "3")

    (observation,) = coordinator.adaptive_price_history.observations
    assert observation.start == repeated
    assert observation.effective_price == Decimal(2)
    assert observation.covered_duration == timedelta(hours=1)


@pytest.mark.parametrize(
    "start", [datetime(2026, 3, 29, tzinfo=UTC), datetime(2026, 10, 25, tzinfo=UTC)]
)
async def test_adaptive_observation_dst_uses_absolute_order_for_local_hours(
    hass, start
):
    """Spring's skipped hour and autumn's repeated hour remain distinct in UTC."""
    coordinator = await _coordinator(hass)
    timezone = coordinator._local_timezone
    for hour in range(3):
        assert _update(
            coordinator,
            (start + timedelta(hours=hour)).astimezone(timezone),
            str(hour + 1),
        )

    observations = coordinator.adaptive_price_history.observations
    assert [o.start.astimezone(UTC) for o in observations] == [
        start,
        start + timedelta(hours=1),
    ]
    assert [o.effective_price for o in observations] == [Decimal(1), Decimal(2)]
    assert all(o.covered_duration == timedelta(hours=1) for o in observations)


async def test_adaptive_observation_midnight_closes_previous_day_before_retention(hass):
    """Real daily rollover retains the previous completed hour and its scope."""
    coordinator = await _coordinator(hass)
    start = _start(coordinator).replace(hour=23)
    _update(coordinator, start)
    scope = coordinator.adaptive_price_scope
    midnight = start + timedelta(hours=1)
    with patch.object(coordinator, "_schedule_statistics_save") as save:
        coordinator._async_daily_rollover(midnight)
    save.assert_called_once_with(immediate=True)

    (observation,) = coordinator.adaptive_price_history.observations
    assert observation.start == start
    assert observation.effective_price == Decimal(1)
    assert observation.covered_duration == timedelta(hours=1)
    assert coordinator.adaptive_price_scope == scope
    assert not _update(coordinator, midnight + timedelta(minutes=15))
    assert (
        Decimal(
            coordinator.adaptive_price_history.as_dict()["open_hours"][0][
                "covered_seconds"
            ]
        )
        == 900
    )


async def test_adaptive_observation_json_restart_keeps_history_without_replaying_live_price(
    hass,
):
    """Saved open hours restore, but the unobserved restart gap is not invented."""
    original = await _coordinator(hass)
    start = _start(original)
    _update(original, start)
    _update(original, start + timedelta(hours=1), "2")
    _update(original, start + timedelta(hours=1, minutes=30), "3")
    stored = json.loads(json.dumps(original._statistics_data()))
    restored = await _coordinator(hass)
    with patch.object(restored._store, "async_load", AsyncMock(return_value=stored)):
        await restored._async_restore_statistics()

    assert restored.adaptive_price_scope is None
    assert (
        restored.adaptive_price_history.scope == original.adaptive_price_history.scope
    )
    assert not _update(restored, start + timedelta(hours=2), "4")
    assert (
        restored._statistics_data()["adaptive_price_history"]
        == stored["adaptive_price_history"]
    )
    assert set(restored._statistics_data()) == set(stored)
    assert _update(restored, start + timedelta(hours=3), "5")

    observations = restored.adaptive_price_history.observations
    assert [(o.start, o.effective_price) for o in observations] == [
        (start, Decimal(1)),
        (start + timedelta(hours=2), Decimal(4)),
    ]


@pytest.mark.parametrize("stage", ["price", "scope"])
async def test_adaptive_observation_calculation_failure_keeps_existing_update_order(
    hass, stage
):
    """Prior hours/cursor advance before calculation; failure retains old price/scope."""
    coordinator = await _coordinator(hass)
    start = _start(coordinator)
    _update(coordinator, start)
    old_scope = coordinator.adaptive_price_scope
    failure = RuntimeError("calculation failed")
    calculation = (
        patch(
            "custom_components.electricity_pro.coordinator.calculate_declared_effective_price",
            side_effect=failure,
        )
        if stage == "price"
        else patch.object(coordinator, "_adaptive_scope", side_effect=failure)
    )
    with calculation, pytest.raises(RuntimeError, match="calculation failed"):
        _update(coordinator, start + timedelta(hours=1), "2")
    assert coordinator.adaptive_price_scope == old_scope
    assert _update(coordinator, start + timedelta(hours=2), "3")

    observations = coordinator.adaptive_price_history.observations
    assert [o.effective_price for o in observations] == [Decimal(1), Decimal(1)]
    assert all(o.covered_duration == timedelta(hours=1) for o in observations)
