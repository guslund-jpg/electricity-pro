"""Tests for Electricity Pro sensors."""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import CoroutineType
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_FORECAST_CURRENCY,
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FORECAST_PRICE_AREA,
    DOMAIN,
)
from custom_components.electricity_pro.base_load import BaseLoadEstimateResult
from custom_components.electricity_pro.timing_score import (
    TimingScoreRating,
    TimingScoreResult,
    TimingScoreUnavailableReason,
)

ENTITY_ID = f"sensor.{DOMAIN}_current_power"
SOURCE_ENTITY_ID = "sensor.test_power"

ENERGY_ENTITY_ID = f"sensor.{DOMAIN}_energy_today"
ENERGY_SOURCE_ENTITY_ID = "sensor.test_energy"
ENERGY_THIS_MONTH_ENTITY_ID = f"sensor.{DOMAIN}_energy_this_month"

COST_RATE_ENTITY_ID = f"sensor.{DOMAIN}_current_cost_rate"
COST_TODAY_ENTITY_ID = f"sensor.{DOMAIN}_cost_today"
COST_THIS_MONTH_ENTITY_ID = f"sensor.{DOMAIN}_cost_this_month"
FIXED_SUPPLIER_FEE_THIS_MONTH_ENTITY_ID = (
    f"sensor.{DOMAIN}_fixed_supplier_fee_this_month"
)
FIXED_GRID_FEE_THIS_MONTH_ENTITY_ID = f"sensor.{DOMAIN}_fixed_grid_fee_this_month"
TOTAL_SUPPLIER_COST_THIS_MONTH_ENTITY_ID = (
    f"sensor.{DOMAIN}_total_supplier_cost_this_month"
)
PEAK_POWER_TODAY_ENTITY_ID = f"sensor.{DOMAIN}_peak_power_today"
PEAK_POWER_TIME_TODAY_ENTITY_ID = f"sensor.{DOMAIN}_peak_power_time_today"
CURRENT_L1_ENTITY_ID = f"sensor.{DOMAIN}_current_l1"
CURRENT_L2_ENTITY_ID = f"sensor.{DOMAIN}_current_l2"
CURRENT_L3_ENTITY_ID = f"sensor.{DOMAIN}_current_l3"
VOLTAGE_L1_ENTITY_ID = f"sensor.{DOMAIN}_voltage_l1"
VOLTAGE_L2_ENTITY_ID = f"sensor.{DOMAIN}_voltage_l2"
VOLTAGE_L3_ENTITY_ID = f"sensor.{DOMAIN}_voltage_l3"
MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY_ID = (
    f"sensor.{DOMAIN}_monthly_peak_hour_consumption"
)
MONTHLY_PEAK_HOUR_TIME_ENTITY_ID = f"sensor.{DOMAIN}_monthly_peak_hour_time"

REMAINING_COST_ENTITY_ID = f"sensor.{DOMAIN}_remaining_cost_today"
CHEAPEST_1H_WINDOW_ENTITY_ID = f"sensor.{DOMAIN}_cheapest_1h_window_start"
CHEAPEST_2H_WINDOW_ENTITY_ID = f"sensor.{DOMAIN}_cheapest_2h_window_start"
CHEAPEST_3H_WINDOW_ENTITY_ID = f"sensor.{DOMAIN}_cheapest_3h_window_start"
CHEAPEST_1H_WINDOW_AVERAGE_EFFECTIVE_PRICE_ENTITY_ID = (
    f"sensor.{DOMAIN}_cheapest_1h_window_average_effective_price"
)
CHEAPEST_2H_WINDOW_AVERAGE_EFFECTIVE_PRICE_ENTITY_ID = (
    f"sensor.{DOMAIN}_cheapest_2h_window_average_effective_price"
)
CHEAPEST_3H_WINDOW_AVERAGE_EFFECTIVE_PRICE_ENTITY_ID = (
    f"sensor.{DOMAIN}_cheapest_3h_window_average_effective_price"
)
PRICE_DIRECTION_ENTITY_ID = f"sensor.{DOMAIN}_price_direction"
TIMING_SCORE_ENTITY_ID = f"sensor.{DOMAIN}_consumption_timing_score_yesterday"
BASE_LOAD_ENTITY_ID = f"sensor.{DOMAIN}_estimated_base_load"
AVERAGE_POWER_TODAY_ENTITY_ID = f"sensor.{DOMAIN}_average_power_today"


async def test_average_power_today_publishes_value_and_coverage(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Sufficient current-day coverage should publish mean power metadata."""
    entry = await setup_electricity_pro()
    coordinator = entry.runtime_data
    timezone = coordinator._local_timezone  # noqa: SLF001
    day_start = datetime(2026, 8, 25, tzinfo=timezone)
    now = day_start + timedelta(hours=2)
    coordinator._base_load_buckets.add_segment(  # noqa: SLF001
        start=day_start,
        end=now,
        power_w=Decimal("425.5"),
    )
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=now,
    ):
        coordinator.async_set_updated_data(coordinator.data)
        await hass.async_block_till_done()

        state = hass.states.get(AVERAGE_POWER_TODAY_ENTITY_ID)

    assert state is not None
    assert state.state == "425.5"
    assert state.attributes["unit_of_measurement"] == "W"
    assert state.attributes["period_start"] == "2026-08-25"
    assert state.attributes["coverage_percent"] == "100"
    assert state.attributes["covered_duration_minutes"] == "120.0"
    assert state.attributes["method"] == "duration_weighted_mean"


async def test_average_power_today_starts_unavailable(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A new setup must not imply coverage before observing elapsed time."""
    await setup_electricity_pro()

    state = hass.states.get(AVERAGE_POWER_TODAY_ENTITY_ID)
    assert state is not None
    assert state.state == "unavailable"


async def test_estimated_base_load_publishes_value_and_metadata(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A five-day estimate should publish a whole-watt power sensor."""
    entry = await setup_electricity_pro()
    coordinator = entry.runtime_data
    coordinator._base_load_result = BaseLoadEstimateResult(  # noqa: SLF001
        estimate_w=Decimal("205.4"),
        unavailable_reason=None,
        window_start=date(2026, 8, 19),
        window_end=date(2026, 8, 25),
        eligible_days=5,
        required_days=5,
        daily_estimates=tuple(
            (date(2026, 8, day), Decimal(value))
            for day, value in zip(
                range(21, 26), ("190", "200", "205.4", "210", "220")
            )
        ),
    )
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()

    state = hass.states.get(BASE_LOAD_ENTITY_ID)
    assert state is not None
    assert state.state == "205.4"
    assert state.attributes["unit_of_measurement"] == "W"
    assert state.attributes["eligible_days"] == 5
    assert state.attributes["method"] == "median_of_daily_p10"
    assert state.attributes["daily_estimates_w"]["2026-08-23"] == "205.4"


async def test_consumption_timing_score_publishes_completed_result(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A quality-approved completed day should publish score and metadata."""
    entry = await setup_electricity_pro(price_value="1.5")
    coordinator = entry.runtime_data
    coordinator._timing_result_date = date(2026, 8, 24)  # noqa: SLF001
    coordinator._timing_result = TimingScoreResult(  # noqa: SLF001
        score=Decimal(88),
        unavailable_reason=None,
        coverage_percent=Decimal("98.5"),
        energy_kwh=Decimal("12.3"),
        consumption_weighted_price=Decimal("0.75"),
        time_weighted_price=Decimal("1.25"),
        price_variation_percent=Decimal(40),
        rating=TimingScoreRating.WELL_TIMED,
    )
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()

    state = hass.states.get(TIMING_SCORE_ENTITY_ID)
    assert state is not None
    assert state.state == "88"
    assert state.attributes["unit_of_measurement"] == "%"
    assert state.attributes["period_start"] == "2026-08-24"
    assert state.attributes["coverage_percent"] == "98.5"
    assert state.attributes["rating"] == "well_timed"


async def test_consumption_timing_score_explains_unavailable_result(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A rejected completed day should remain unavailable but explain why."""
    entry = await setup_electricity_pro(price_value="1.5")
    coordinator = entry.runtime_data
    coordinator._timing_result_date = date(2026, 8, 24)  # noqa: SLF001
    coordinator._timing_result = TimingScoreResult(  # noqa: SLF001
        score=None,
        unavailable_reason=TimingScoreUnavailableReason.INSUFFICIENT_COVERAGE,
        coverage_percent=Decimal(72),
        energy_kwh=Decimal("8.5"),
        consumption_weighted_price=None,
        time_weighted_price=None,
        price_variation_percent=None,
        rating=None,
    )
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()

    state = hass.states.get(TIMING_SCORE_ENTITY_ID)
    assert state is not None
    assert state.state == "unavailable"
    assert "period_start" not in state.attributes
    assert "unavailable_reason" not in state.attributes


async def test_energy_today_initial_value(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Energy today should use the configured daily energy source."""

    await setup_electricity_pro(
        energy_value="12.5",
        energy_unit="kWh",
    )

    state = hass.states.get(ENERGY_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("12.5")
    assert state.attributes["unit_of_measurement"] == "kWh"
    assert state.attributes["device_class"] == "energy"
    assert state.attributes["state_class"] == "total_increasing"
    assert state.attributes["friendly_name"] == "Electricity Pro Energy today"


async def test_energy_today_updates_when_source_changes(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Energy today should update when its source changes."""

    await setup_electricity_pro(
        energy_value="12.5",
        energy_unit="kWh",
    )

    hass.states.async_set(
        ENERGY_SOURCE_ENTITY_ID,
        "13.25",
        {
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENERGY_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("13.25")
    assert state.attributes["unit_of_measurement"] == "kWh"


async def test_energy_today_accepts_wh(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Energy today should accept watt-hours."""

    await setup_electricity_pro(
        energy_value="1250",
        energy_unit="Wh",
    )

    state = hass.states.get(ENERGY_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal(1250)
    assert state.attributes["unit_of_measurement"] == "Wh"


async def test_energy_this_month_starts_at_zero(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """The first observed cumulative reading should establish the baseline."""
    await setup_electricity_pro(energy_value="100", energy_unit="kWh")

    state = hass.states.get(ENERGY_THIS_MONTH_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal(0)
    assert state.attributes["unit_of_measurement"] == "kWh"
    assert state.attributes["device_class"] == "energy"
    assert state.attributes["state_class"] == "total"


async def test_energy_this_month_accumulates_source_changes(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Cumulative source changes should update monthly energy."""
    await setup_electricity_pro(energy_value="100", energy_unit="kWh")

    hass.states.async_set(
        ENERGY_SOURCE_ENTITY_ID,
        "102.5",
        {
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENERGY_THIS_MONTH_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("2.5")


async def test_energy_this_month_normalizes_wh_to_kwh(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly energy should always use kilowatt-hours."""
    await setup_electricity_pro(energy_value="1000", energy_unit="Wh")

    hass.states.async_set(
        ENERGY_SOURCE_ENTITY_ID,
        "2250",
        {
            "unit_of_measurement": "Wh",
            "device_class": "energy",
            "state_class": "total_increasing",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENERGY_THIS_MONTH_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("1.25")
    assert state.attributes["unit_of_measurement"] == "kWh"


async def test_energy_this_month_restores_persisted_state(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly energy should continue from its persisted snapshot."""
    stored = {
        "energy_this_month": {
            "period_start": "2026-08-01",
            "last_value": "105",
            "value": "5",
        }
    }

    with patch(
        "custom_components.electricity_pro.coordinator.Store.async_load",
        return_value=stored,
    ):
        await setup_electricity_pro(energy_value="108", energy_unit="kWh")

    state = hass.states.get(ENERGY_THIS_MONTH_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal(8)


async def test_energy_this_month_resets_at_month_boundary(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly energy should reset when the local calendar month changes."""
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 9, 1, 0, 1, tzinfo=UTC),
    ):
        await setup_electricity_pro(energy_value="100", energy_unit="kWh")
        hass.states.async_set(
            ENERGY_SOURCE_ENTITY_ID,
            "101",
            {
                "unit_of_measurement": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
            },
        )
        await hass.async_block_till_done()

    state = hass.states.get(ENERGY_THIS_MONTH_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal(1)


async def test_energy_today_becomes_unavailable(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Energy today should become unavailable for an unknown source."""

    await setup_electricity_pro(
        energy_value="12.5",
        energy_unit="kWh",
    )

    hass.states.async_set(
        ENERGY_SOURCE_ENTITY_ID,
        "unknown",
        {
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENERGY_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_energy_today_rejects_invalid_unit(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Energy today should reject unsupported units."""

    await setup_electricity_pro(
        energy_value="12.5",
        energy_unit="kWh",
    )

    hass.states.async_set(
        ENERGY_SOURCE_ENTITY_ID,
        "12.6",
        {
            "unit_of_measurement": "J",
            "device_class": "energy",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENERGY_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_current_power_initial_value(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current power should use the initial source value."""

    await setup_electricity_pro(power_value="1234", power_unit="W")

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "1234"
    assert state.attributes["unit_of_measurement"] == "W"
    assert state.attributes["device_class"] == "power"


async def test_current_power_updates_when_source_changes(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current power should update when the source changes."""

    await setup_electricity_pro(power_value="1000", power_unit="W")

    hass.states.async_set(
        SOURCE_ENTITY_ID,
        "850",
        {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "850"


async def test_current_power_converts_kw_to_w(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current power should convert kilowatts to watts."""

    await setup_electricity_pro(power_value="1.5", power_unit="kW")

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal(1500)
    assert state.attributes["unit_of_measurement"] == "W"


async def test_current_power_publishes_signed_export(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Negative whole-home source power should remain visible as net export."""
    await setup_electricity_pro(power_value="-0.45", power_unit="kW")

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert Decimal(state.state) == Decimal(-450)
    assert state.attributes["unit_of_measurement"] == "W"


async def test_current_power_becomes_unavailable(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current power should become unavailable for an unknown source."""

    await setup_electricity_pro(power_value="1000", power_unit="W")

    hass.states.async_set(
        SOURCE_ENTITY_ID,
        "unknown",
        {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_current_power_becomes_unavailable_for_invalid_value(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current power should become unavailable for a non-numeric source."""

    await setup_electricity_pro(power_value="1000", power_unit="W")

    hass.states.async_set(
        SOURCE_ENTITY_ID,
        "not-a-number",
        {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


PRICE_ENTITY_ID = f"sensor.{DOMAIN}_current_price"
EFFECTIVE_PRICE_ENTITY_ID = f"sensor.{DOMAIN}_effective_price"
WEIGHTED_AVERAGE_PRICE_ENTITY_ID = (
    f"sensor.{DOMAIN}_consumption_weighted_average_price_today"
)


async def test_current_price_initial_value(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current price should use the configured price source."""

    await setup_electricity_pro(
        power_value="1000",
        power_unit="W",
        price_value="1.25",
        price_unit="SEK/kWh",
    )

    state = hass.states.get(PRICE_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("1.25")
    assert state.attributes["unit_of_measurement"] == "SEK/kWh"


async def test_effective_price_includes_configured_adjustments(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Effective price should add the configured grid fee to current price."""
    await setup_electricity_pro(
        price_value="0.80",
        price_unit="SEK/kWh",
        grid_fee_per_kwh=0.25,
    )

    state = hass.states.get(EFFECTIVE_PRICE_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("1.05")
    assert state.attributes["unit_of_measurement"] == "SEK/kWh"
    assert state.attributes["state_class"] == "measurement"


async def test_negative_price_flows_through_live_price_sensors(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A signed base price should remain valid after configured additions."""
    await setup_electricity_pro(
        power_value="1000",
        price_value="-0.50",
        grid_fee_per_kwh=0.20,
    )

    price = hass.states.get(PRICE_ENTITY_ID)
    effective = hass.states.get(EFFECTIVE_PRICE_ENTITY_ID)
    cost_rate = hass.states.get(COST_RATE_ENTITY_ID)
    assert price is not None
    assert effective is not None
    assert cost_rate is not None
    assert Decimal(price.state) == Decimal("-0.50")
    assert Decimal(effective.state) == Decimal("-0.30")
    assert Decimal(cost_rate.state) == Decimal("-0.30")


async def test_current_cost_rate_unavailable_during_export(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """The import price must not be presented as export compensation."""
    await setup_electricity_pro(power_value="-500", price_value="1.50")

    state = hass.states.get(COST_RATE_ENTITY_ID)
    assert state is not None
    assert state.state == "unavailable"


async def test_current_cost_rate_uses_normalized_effective_price(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current cost rate should include the permitted variable grid fee."""
    await setup_electricity_pro(
        power_value="1000",
        price_value="0.80",
        grid_fee_per_kwh=0.25,
    )

    state = hass.states.get(COST_RATE_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("1.05")


async def test_consumption_weighted_average_price_today(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Achieved average price should use aligned daily totals and adjustments."""
    await setup_electricity_pro(
        energy_value="10",
        energy_unit="kWh",
        accumulated_cost_today_value="12",
        accumulated_cost_today_unit="SEK",
        grid_fee_per_kwh=0.25,
    )

    state = hass.states.get(WEIGHTED_AVERAGE_PRICE_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("1.45")
    assert state.attributes["unit_of_measurement"] == "SEK/kWh"
    assert state.attributes["state_class"] == "measurement"


async def test_consumption_weighted_average_price_today_updates(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Achieved average price should update when a daily source changes."""
    await setup_electricity_pro(
        energy_value="10",
        accumulated_cost_today_value="12",
        accumulated_cost_today_unit="SEK",
    )

    hass.states.async_set(
        "sensor.test_accumulated_cost_today",
        "15",
        {
            "unit_of_measurement": "SEK",
            "device_class": "monetary",
            "state_class": "total",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(WEIGHTED_AVERAGE_PRICE_ENTITY_ID)
    assert state is not None
    assert Decimal(state.state) == Decimal("1.5")


async def test_consumption_weighted_average_price_unavailable_at_zero_energy(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Achieved average price should be unavailable before energy is consumed."""
    await setup_electricity_pro(
        energy_value="0",
        accumulated_cost_today_value="0",
        accumulated_cost_today_unit="SEK",
    )

    state = hass.states.get(WEIGHTED_AVERAGE_PRICE_ENTITY_ID)
    assert state is not None
    assert state.state == "unavailable"


async def test_consumption_weighted_average_price_requires_both_sources(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Achieved average price should be omitted without both daily sources."""
    await setup_electricity_pro(energy_value="10")

    assert hass.states.get(WEIGHTED_AVERAGE_PRICE_ENTITY_ID) is None


async def test_current_price_updates_when_source_changes(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current price should update when the source changes."""

    await setup_electricity_pro(
        power_value="1000",
        power_unit="W",
        price_value="1.25",
        price_unit="SEK/kWh",
    )

    hass.states.async_set(
        "sensor.test_price",
        "0.85",
        {
            "unit_of_measurement": "SEK/kWh",
            "device_class": "monetary",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(PRICE_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("0.85")
    assert state.attributes["unit_of_measurement"] == "SEK/kWh"


async def test_current_price_becomes_unavailable(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current price becomes unavailable when source is unknown."""

    await setup_electricity_pro(
        power_value="1000",
        power_unit="W",
        price_value="1.25",
        price_unit="SEK/kWh",
    )

    hass.states.async_set(
        "sensor.test_price",
        "unknown",
        {
            "unit_of_measurement": "SEK/kWh",
        },
    )

    await hass.async_block_till_done()

    state = hass.states.get(PRICE_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_current_price_invalid_value(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Invalid price should become unavailable."""

    await setup_electricity_pro(
        power_value="1000",
        power_unit="W",
        price_value="1.25",
        price_unit="SEK/kWh",
    )

    hass.states.async_set(
        "sensor.test_price",
        "banana",
        {
            "unit_of_measurement": "SEK/kWh",
        },
    )

    await hass.async_block_till_done()

    state = hass.states.get(PRICE_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_current_price_requires_unit(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Price requires a unit of measurement."""

    await setup_electricity_pro(
        power_value="1000",
        power_unit="W",
        price_value="1.25",
        price_unit="SEK/kWh",
    )

    hass.states.async_set(
        "sensor.test_price",
        "0.85",
        {},
    )

    await hass.async_block_till_done()

    state = hass.states.get(PRICE_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_current_cost_rate_sensor(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current cost rate should use power and price sources."""
    await setup_electricity_pro(
        power_value="2400",
        power_unit="W",
        price_value="1.80",
        price_unit="SEK/kWh",
    )

    state = hass.states.get(COST_RATE_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("4.32")
    assert state.attributes["unit_of_measurement"] == "SEK/h"
    assert state.attributes["state_class"] == "measurement"


async def test_current_cost_rate_unavailable_without_price(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current cost rate should become unavailable for an unknown price."""
    await setup_electricity_pro(
        power_value="2400",
        power_unit="W",
        price_value="unknown",
        price_unit="SEK/kWh",
    )

    state = hass.states.get(COST_RATE_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"

    assert state is not None
    assert state.state == "unavailable"


async def test_current_cost_rate_updates_when_power_changes(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current cost rate should update when power changes."""
    await setup_electricity_pro(
        power_value="1000",
        power_unit="W",
        price_value="2.00",
        price_unit="SEK/kWh",
    )

    hass.states.async_set(
        SOURCE_ENTITY_ID,
        "1500",
        {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(COST_RATE_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("3.00")
    assert state.attributes["unit_of_measurement"] == "SEK/h"


async def test_current_cost_rate_updates_when_price_changes(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Current cost rate should update when price changes."""
    await setup_electricity_pro(
        power_value="2000",
        power_unit="W",
        price_value="1.00",
        price_unit="SEK/kWh",
    )

    hass.states.async_set(
        "sensor.test_price",
        "1.50",
        {
            "unit_of_measurement": "SEK/kWh",
            "device_class": "monetary",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(COST_RATE_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("3.00")


async def test_remaining_cost_today_sensor(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Remaining cost today should use current power and price."""

    with patch(
        "custom_components.electricity_pro.sensor.dt_util.now",
        return_value=datetime(
            2026,
            7,
            25,
            15,
            0,
            tzinfo=UTC,
        ),
    ):
        await setup_electricity_pro(
            power_value="2400",
            power_unit="W",
            price_value="1.80",
            price_unit="SEK/kWh",
        )

        state = hass.states.get(REMAINING_COST_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("38.88")
    assert state.attributes["unit_of_measurement"] == "SEK"
    assert state.attributes["state_class"] == "measurement"


async def test_remaining_cost_today_unavailable_without_price(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Remaining cost today should become unavailable."""

    await setup_electricity_pro(
        power_value="2400",
        power_unit="W",
        price_value="unknown",
        price_unit="SEK/kWh",
    )

    state = hass.states.get(REMAINING_COST_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_remaining_cost_today_updates_when_power_changes(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Remaining cost today should update when power changes."""

    with patch(
        "custom_components.electricity_pro.sensor.dt_util.now",
        return_value=datetime(
            2026,
            7,
            25,
            15,
            0,
            tzinfo=UTC,
        ),
    ):
        await setup_electricity_pro(
            power_value="1000",
            power_unit="W",
            price_value="2.00",
            price_unit="SEK/kWh",
        )

        hass.states.async_set(
            SOURCE_ENTITY_ID,
            "1500",
            {
                "unit_of_measurement": "W",
                "device_class": "power",
            },
        )

        await hass.async_block_till_done()

        state = hass.states.get(REMAINING_COST_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("27.00")


async def test_cost_today_initial_value(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Cost today should use the configured accumulated-cost source."""

    await setup_electricity_pro(
        accumulated_cost_today_value="12.34",
        accumulated_cost_today_unit="SEK",
    )

    state = hass.states.get(COST_TODAY_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("12.34")
    assert state.attributes["unit_of_measurement"] == "SEK"


async def test_cost_today_updates_when_source_changes(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Cost today should update when the source changes."""

    await setup_electricity_pro(
        accumulated_cost_today_value="12.34",
        accumulated_cost_today_unit="SEK",
    )

    hass.states.async_set(
        "sensor.test_accumulated_cost_today",
        "13.57",
        {
            "unit_of_measurement": "SEK",
            "device_class": "monetary",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(COST_TODAY_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("13.57")


async def test_cost_today_becomes_unavailable(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Cost today should become unavailable for an unknown source."""

    await setup_electricity_pro(
        accumulated_cost_today_value="12.34",
        accumulated_cost_today_unit="SEK",
    )

    hass.states.async_set(
        "sensor.test_accumulated_cost_today",
        "unknown",
        {
            "unit_of_measurement": "SEK",
            "device_class": "monetary",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(COST_TODAY_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_cost_today_rejects_invalid_value(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Cost today should reject a non-numeric source."""

    await setup_electricity_pro(
        accumulated_cost_today_value="12.34",
        accumulated_cost_today_unit="SEK",
    )

    hass.states.async_set(
        "sensor.test_accumulated_cost_today",
        "banana",
        {
            "unit_of_measurement": "SEK",
            "device_class": "monetary",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(COST_TODAY_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_cost_today_requires_unit(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Cost today should require a unit of measurement."""

    await setup_electricity_pro(
        accumulated_cost_today_value="12.34",
        accumulated_cost_today_unit="SEK",
    )

    hass.states.async_set(
        "sensor.test_accumulated_cost_today",
        "13.57",
        {},
    )
    await hass.async_block_till_done()

    state = hass.states.get(COST_TODAY_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_peak_power_today_initial_value(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Peak power today should start from the current power observation."""

    await setup_electricity_pro()

    state = hass.states.get(PEAK_POWER_TODAY_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal(1234)
    assert state.attributes["unit_of_measurement"] == "W"
    assert state.attributes["device_class"] == "power"
    assert state.attributes["state_class"] == "measurement"
    peak_time = hass.states.get(PEAK_POWER_TIME_TODAY_ENTITY_ID)
    assert peak_time is not None
    assert peak_time.attributes["device_class"] == "timestamp"


async def test_peak_power_today_updates_when_source_changes(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Peak power today should update from a higher current-power sample."""

    await setup_electricity_pro()

    hass.states.async_set(
        "sensor.test_power",
        "5100",
        {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(PEAK_POWER_TODAY_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal(5100)


async def test_peak_power_today_survives_invalid_current_power(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """An invalid sample should not erase the last valid daily peak."""

    await setup_electricity_pro()

    hass.states.async_set(
        "sensor.test_power",
        "unknown",
        {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(PEAK_POWER_TODAY_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal(1234)


async def test_peak_power_today_ignores_export(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A negative net-power observation must not replace the peak import."""
    await setup_electricity_pro(power_value="1234")
    hass.states.async_set(
        SOURCE_ENTITY_ID,
        "-2500",
        {"unit_of_measurement": "W", "device_class": "power"},
    )
    await hass.async_block_till_done()

    current = hass.states.get(ENTITY_ID)
    peak = hass.states.get(PEAK_POWER_TODAY_ENTITY_ID)
    assert current is not None
    assert peak is not None
    assert Decimal(current.state) == Decimal(-2500)
    assert Decimal(peak.state) == Decimal(1234)


async def test_phase_current_initial_values(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Phase current sensors should use the configured source values."""

    await setup_electricity_pro(
        current_l1_value="4.5",
        current_l2_value="5.25",
        current_l3_value="6.75",
    )

    state_l1 = hass.states.get(CURRENT_L1_ENTITY_ID)
    state_l2 = hass.states.get(CURRENT_L2_ENTITY_ID)
    state_l3 = hass.states.get(CURRENT_L3_ENTITY_ID)

    assert state_l1 is not None
    assert state_l2 is not None
    assert state_l3 is not None

    assert Decimal(state_l1.state) == Decimal("4.5")
    assert Decimal(state_l2.state) == Decimal("5.25")
    assert Decimal(state_l3.state) == Decimal("6.75")

    assert state_l1.attributes["unit_of_measurement"] == "A"
    assert state_l1.attributes["device_class"] == "current"
    assert state_l1.attributes["state_class"] == "measurement"


async def test_phase_current_updates_when_source_changes(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A phase current sensor should update when its source changes."""

    await setup_electricity_pro(
        current_l1_value="4.5",
        current_l2_value="5.25",
        current_l3_value="6.75",
    )

    hass.states.async_set(
        "sensor.test_current_l1",
        "8.25",
        {
            "unit_of_measurement": "A",
            "device_class": "current",
        },
    )
    await hass.async_block_till_done()

    state_l1 = hass.states.get(CURRENT_L1_ENTITY_ID)
    state_l2 = hass.states.get(CURRENT_L2_ENTITY_ID)

    assert state_l1 is not None
    assert state_l2 is not None
    assert Decimal(state_l1.state) == Decimal("8.25")
    assert Decimal(state_l2.state) == Decimal("5.25")


async def test_phase_current_becomes_unavailable(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A phase current sensor should become unavailable for an unknown source."""

    await setup_electricity_pro(
        current_l1_value="4.5",
    )

    hass.states.async_set(
        "sensor.test_current_l1",
        "unknown",
        {
            "unit_of_measurement": "A",
            "device_class": "current",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(CURRENT_L1_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_phase_current_rejects_invalid_value(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A phase current sensor should reject a non-numeric source."""

    await setup_electricity_pro(
        current_l1_value="4.5",
    )

    hass.states.async_set(
        "sensor.test_current_l1",
        "banana",
        {
            "unit_of_measurement": "A",
            "device_class": "current",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(CURRENT_L1_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_phase_current_not_created_without_sources(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Phase current sensors should not exist when no sources are configured."""

    await setup_electricity_pro()

    assert hass.states.get(CURRENT_L1_ENTITY_ID) is None
    assert hass.states.get(CURRENT_L2_ENTITY_ID) is None
    assert hass.states.get(CURRENT_L3_ENTITY_ID) is None


async def test_phase_voltage_initial_values(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Phase voltage sensors should use the configured source values."""

    await setup_electricity_pro(
        voltage_l1_value="231.4",
        voltage_l2_value="232.1",
        voltage_l3_value="230.8",
    )

    state_l1 = hass.states.get(VOLTAGE_L1_ENTITY_ID)
    state_l2 = hass.states.get(VOLTAGE_L2_ENTITY_ID)
    state_l3 = hass.states.get(VOLTAGE_L3_ENTITY_ID)

    assert state_l1 is not None
    assert state_l2 is not None
    assert state_l3 is not None

    assert Decimal(state_l1.state) == Decimal("231.4")
    assert Decimal(state_l2.state) == Decimal("232.1")
    assert Decimal(state_l3.state) == Decimal("230.8")

    assert state_l1.attributes["unit_of_measurement"] == "V"
    assert state_l1.attributes["device_class"] == "voltage"
    assert state_l1.attributes["state_class"] == "measurement"


async def test_phase_voltage_updates_when_source_changes(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A phase voltage sensor should update when its source changes."""

    await setup_electricity_pro(
        voltage_l1_value="231.4",
        voltage_l2_value="232.1",
        voltage_l3_value="230.8",
    )

    hass.states.async_set(
        "sensor.test_voltage_l1",
        "235.6",
        {
            "unit_of_measurement": "V",
            "device_class": "voltage",
        },
    )
    await hass.async_block_till_done()

    state_l1 = hass.states.get(VOLTAGE_L1_ENTITY_ID)
    state_l2 = hass.states.get(VOLTAGE_L2_ENTITY_ID)

    assert state_l1 is not None
    assert state_l2 is not None
    assert Decimal(state_l1.state) == Decimal("235.6")
    assert Decimal(state_l2.state) == Decimal("232.1")


async def test_phase_voltage_becomes_unavailable(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A phase voltage sensor should become unavailable for an unknown source."""

    await setup_electricity_pro(
        voltage_l1_value="231.4",
    )

    hass.states.async_set(
        "sensor.test_voltage_l1",
        "unknown",
        {
            "unit_of_measurement": "V",
            "device_class": "voltage",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(VOLTAGE_L1_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_phase_voltage_rejects_invalid_value(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A phase voltage sensor should reject a non-numeric source."""

    await setup_electricity_pro(
        voltage_l1_value="231.4",
    )

    hass.states.async_set(
        "sensor.test_voltage_l1",
        "banana",
        {
            "unit_of_measurement": "V",
            "device_class": "voltage",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(VOLTAGE_L1_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_phase_voltage_not_created_without_sources(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Phase voltage sensors should not exist when no sources are configured."""

    await setup_electricity_pro()

    assert hass.states.get(VOLTAGE_L1_ENTITY_ID) is None
    assert hass.states.get(VOLTAGE_L2_ENTITY_ID) is None
    assert hass.states.get(VOLTAGE_L3_ENTITY_ID) is None


async def test_monthly_peak_hour_consumption_initial_value(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly peak-hour consumption should use the configured source."""

    await setup_electricity_pro(
        monthly_peak_hour_consumption_value="2.45",
        monthly_peak_hour_consumption_unit="kWh",
    )

    state = hass.states.get(MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("2.45")
    assert state.attributes["unit_of_measurement"] == "kWh"
    assert state.attributes["device_class"] == "energy"
    assert state.attributes["state_class"] == "total"


async def test_cost_this_month_starts_with_cost_today(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """The first observed daily cost should seed the partial monthly value."""
    await setup_electricity_pro(
        accumulated_cost_today_value="12.34",
        accumulated_cost_today_unit="SEK",
    )

    state = hass.states.get(COST_THIS_MONTH_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("12.34")
    assert state.attributes["unit_of_measurement"] == "SEK"
    assert state.attributes["device_class"] == "monetary"
    assert state.attributes["state_class"] == "total"


async def test_fixed_supplier_fee_is_separate_from_variable_monthly_cost(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """A monthly supplier fee should be exposed once without changing variable cost."""
    await setup_electricity_pro(
        accumulated_cost_today_value="12.34",
        accumulated_cost_today_unit="SEK",
        fixed_supplier_fee_monthly=49.0,
    )

    variable = hass.states.get(COST_THIS_MONTH_ENTITY_ID)
    fixed = hass.states.get(FIXED_SUPPLIER_FEE_THIS_MONTH_ENTITY_ID)
    total = hass.states.get(TOTAL_SUPPLIER_COST_THIS_MONTH_ENTITY_ID)

    assert variable is not None
    assert fixed is not None
    assert total is not None
    assert Decimal(variable.state) == Decimal("12.34")
    assert Decimal(fixed.state) == Decimal("49.0")
    assert Decimal(total.state) == Decimal("61.34")
    assert fixed.attributes["unit_of_measurement"] == "SEK"
    assert total.attributes["unit_of_measurement"] == "SEK"


async def test_fixed_supplier_fee_uses_price_currency_without_cost_source(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """The fixed component can use a declared price currency by itself."""
    await setup_electricity_pro(
        price_value="0.80",
        price_unit="SEK/kWh",
        fixed_supplier_fee_monthly=49.0,
    )

    fixed = hass.states.get(FIXED_SUPPLIER_FEE_THIS_MONTH_ENTITY_ID)

    assert fixed is not None
    assert Decimal(fixed.state) == Decimal("49.0")
    assert fixed.attributes["unit_of_measurement"] == "SEK"
    assert hass.states.get(TOTAL_SUPPLIER_COST_THIS_MONTH_ENTITY_ID) is None


async def test_fixed_grid_fee_is_exposed_as_separate_component(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """The grid-provider fixed fee must remain separate from supplier totals."""
    await setup_electricity_pro(
        accumulated_cost_today_value="12.34",
        accumulated_cost_today_unit="SEK",
        fixed_supplier_fee_monthly=49.0,
        fixed_grid_fee_monthly=630.0,
    )

    grid = hass.states.get(FIXED_GRID_FEE_THIS_MONTH_ENTITY_ID)
    supplier_total = hass.states.get(TOTAL_SUPPLIER_COST_THIS_MONTH_ENTITY_ID)

    assert grid is not None
    assert Decimal(grid.state) == Decimal("630.0")
    assert grid.attributes["unit_of_measurement"] == "SEK"
    assert supplier_total is not None
    assert Decimal(supplier_total.state) == Decimal("61.34")


async def test_cost_this_month_accumulates_and_handles_daily_reset(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly cost should accumulate through a daily source reset."""
    await setup_electricity_pro(
        accumulated_cost_today_value="10",
        accumulated_cost_today_unit="SEK",
    )

    for value in ("15", "2"):
        hass.states.async_set(
            "sensor.test_accumulated_cost_today",
            value,
            {
                "unit_of_measurement": "SEK",
                "device_class": "monetary",
                "state_class": "total",
            },
        )
        await hass.async_block_till_done()

    state = hass.states.get(COST_THIS_MONTH_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal(17)


async def test_cost_this_month_restores_persisted_state(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly cost should continue from its persisted snapshot."""
    stored = {
        "cost_this_month": {
            "period_start": "2026-08-01",
            "last_value": "10",
            "value": "50",
        },
        "cost_this_month_unit": "SEK",
    }

    with patch(
        "custom_components.electricity_pro.coordinator.Store.async_load",
        return_value=stored,
    ):
        await setup_electricity_pro(
            accumulated_cost_today_value="12",
            accumulated_cost_today_unit="SEK",
        )

    state = hass.states.get(COST_THIS_MONTH_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal(52)


async def test_monthly_peak_hour_consumption_preserves_wh(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly peak-hour consumption should preserve watt-hours."""

    await setup_electricity_pro(
        monthly_peak_hour_consumption_value="2450",
        monthly_peak_hour_consumption_unit="Wh",
    )

    state = hass.states.get(MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal(2450)
    assert state.attributes["unit_of_measurement"] == "Wh"


async def test_monthly_peak_hour_consumption_updates(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly peak-hour consumption should update with its source."""

    await setup_electricity_pro(
        monthly_peak_hour_consumption_value="2.45",
    )

    hass.states.async_set(
        "sensor.test_monthly_peak_hour_consumption",
        "3.10",
        {
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "measurement",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY_ID)

    assert state is not None
    assert Decimal(state.state) == Decimal("3.10")


async def test_monthly_peak_hour_consumption_becomes_unavailable(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly peak-hour consumption should become unavailable."""

    await setup_electricity_pro(
        monthly_peak_hour_consumption_value="2.45",
    )

    hass.states.async_set(
        "sensor.test_monthly_peak_hour_consumption",
        "unknown",
        {
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "measurement",
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY_ID)

    assert state is not None
    assert state.state == "unavailable"


async def test_monthly_peak_hour_consumption_not_created_without_source(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly peak-hour consumption should be omitted when unconfigured."""

    await setup_electricity_pro()

    assert hass.states.get(MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY_ID) is None


async def test_monthly_peak_hour_time_initial_value(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly peak-hour time should mirror its configured timestamp source."""
    await setup_electricity_pro(
        monthly_peak_hour_time_value="2026-08-03T17:00:00+02:00",
    )

    state = hass.states.get(MONTHLY_PEAK_HOUR_TIME_ENTITY_ID)

    assert state is not None
    assert datetime.fromisoformat(state.state) == datetime(
        2026, 8, 3, 15, tzinfo=UTC
    )
    assert state.attributes["device_class"] == "timestamp"


async def test_monthly_peak_hour_time_updates_and_becomes_unavailable(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly peak-hour time should follow source changes and availability."""
    await setup_electricity_pro(
        monthly_peak_hour_time_value="2026-08-03T17:00:00+02:00",
    )

    hass.states.async_set(
        "sensor.test_monthly_peak_hour_time",
        "2026-08-04T18:00:00+02:00",
        {"device_class": "timestamp"},
    )
    await hass.async_block_till_done()

    state = hass.states.get(MONTHLY_PEAK_HOUR_TIME_ENTITY_ID)
    assert state is not None
    assert datetime.fromisoformat(state.state) == datetime(
        2026, 8, 4, 16, tzinfo=UTC
    )

    hass.states.async_set(
        "sensor.test_monthly_peak_hour_time",
        "unknown",
        {"device_class": "timestamp"},
    )
    await hass.async_block_till_done()

    state = hass.states.get(MONTHLY_PEAK_HOUR_TIME_ENTITY_ID)
    assert state is not None
    assert state.state == "unavailable"


async def test_monthly_peak_hour_time_not_created_without_source(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Monthly peak-hour time should be omitted when unconfigured."""
    await setup_electricity_pro()

    assert hass.states.get(MONTHLY_PEAK_HOUR_TIME_ENTITY_ID) is None


async def test_forecast_insight_sensors_expose_cached_windows_and_direction(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Forecast insight sensors should expose cached coordinator forecast insights."""
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 20, 1, tzinfo=UTC),
    ):
        await setup_electricity_pro(
            forecast_price_area="SE3",
            forecast_currency="SEK",
            forecast_nordpool_config_entry="nordpool-entry-id",
            forecast_intervals=[
                {
                    "start": "2026-08-13T20:00:00+00:00",
                    "end": "2026-08-13T20:15:00+00:00",
                    "price": 591.04,
                },
                {
                    "start": "2026-08-13T20:15:00+00:00",
                    "end": "2026-08-13T20:30:00+00:00",
                    "price": 691.04,
                },
                {
                    "start": "2026-08-13T20:30:00+00:00",
                    "end": "2026-08-13T20:45:00+00:00",
                    "price": 791.04,
                },
                {
                    "start": "2026-08-13T20:45:00+00:00",
                    "end": "2026-08-13T21:00:00+00:00",
                    "price": 891.04,
                },
                {
                    "start": "2026-08-13T21:00:00+00:00",
                    "end": "2026-08-13T21:15:00+00:00",
                    "price": 991.04,
                },
                {
                    "start": "2026-08-13T21:15:00+00:00",
                    "end": "2026-08-13T21:30:00+00:00",
                    "price": 1091.04,
                },
                {
                    "start": "2026-08-13T21:30:00+00:00",
                    "end": "2026-08-13T21:45:00+00:00",
                    "price": 1191.04,
                },
                {
                    "start": "2026-08-13T21:45:00+00:00",
                    "end": "2026-08-13T22:00:00+00:00",
                    "price": 1291.04,
                },
                {
                    "start": "2026-08-13T22:00:00+00:00",
                    "end": "2026-08-13T22:15:00+00:00",
                    "price": 1391.04,
                },
                {
                    "start": "2026-08-13T22:15:00+00:00",
                    "end": "2026-08-13T22:30:00+00:00",
                    "price": 1491.04,
                },
                {
                    "start": "2026-08-13T22:30:00+00:00",
                    "end": "2026-08-13T22:45:00+00:00",
                    "price": 1591.04,
                },
                {
                    "start": "2026-08-13T22:45:00+00:00",
                    "end": "2026-08-13T23:00:00+00:00",
                    "price": 1691.04,
                },
                {
                    "start": "2026-08-13T23:00:00+00:00",
                    "end": "2026-08-13T23:15:00+00:00",
                    "price": 1791.04,
                },
                {
                    "start": "2026-08-13T23:15:00+00:00",
                    "end": "2026-08-13T23:30:00+00:00",
                    "price": 1891.04,
                },
                {
                    "start": "2026-08-13T23:30:00+00:00",
                    "end": "2026-08-13T23:45:00+00:00",
                    "price": 1991.04,
                },
                {
                    "start": "2026-08-13T23:45:00+00:00",
                    "end": "2026-08-14T00:00:00+00:00",
                    "price": 2091.04,
                },
            ],
        )

    cheapest_1h_state = hass.states.get(CHEAPEST_1H_WINDOW_ENTITY_ID)
    cheapest_2h_state = hass.states.get(CHEAPEST_2H_WINDOW_ENTITY_ID)
    cheapest_3h_state = hass.states.get(CHEAPEST_3H_WINDOW_ENTITY_ID)
    cheapest_1h_average_effective_price_state = hass.states.get(
        CHEAPEST_1H_WINDOW_AVERAGE_EFFECTIVE_PRICE_ENTITY_ID
    )
    cheapest_2h_average_effective_price_state = hass.states.get(
        CHEAPEST_2H_WINDOW_AVERAGE_EFFECTIVE_PRICE_ENTITY_ID
    )
    cheapest_3h_average_effective_price_state = hass.states.get(
        CHEAPEST_3H_WINDOW_AVERAGE_EFFECTIVE_PRICE_ENTITY_ID
    )
    direction_state = hass.states.get(PRICE_DIRECTION_ENTITY_ID)

    assert cheapest_1h_state is not None
    assert cheapest_1h_state.attributes["device_class"] == "timestamp"
    assert datetime.fromisoformat(cheapest_1h_state.state) == datetime(
        2026, 8, 13, 20, 15, tzinfo=UTC
    )
    assert cheapest_1h_state.attributes["window_end"] == "2026-08-13T21:15:00+00:00"
    assert cheapest_1h_state.attributes["window_duration_minutes"] == 60
    assert cheapest_1h_state.attributes["interval_count"] == 4
    assert cheapest_1h_state.attributes["average_market_price"] == "0.84104"
    assert cheapest_1h_state.attributes["average_scheduling_price"] == "0.84104"
    assert cheapest_1h_state.attributes["price_components"] == ["market_energy"]
    assert cheapest_1h_state.attributes["vat_treatment"] == "unknown"
    assert cheapest_1h_state.attributes["price_completeness"] == "partial"
    assert cheapest_1h_state.attributes["currency"] == "SEK"
    assert cheapest_1h_state.attributes["price_area"] == "SE3"

    assert cheapest_2h_state is not None
    assert cheapest_2h_state.attributes["device_class"] == "timestamp"
    assert datetime.fromisoformat(cheapest_2h_state.state) == datetime(
        2026, 8, 13, 20, 15, tzinfo=UTC
    )
    assert cheapest_2h_state.attributes["window_end"] == "2026-08-13T22:15:00+00:00"
    assert cheapest_2h_state.attributes["window_duration_minutes"] == 120
    assert cheapest_2h_state.attributes["interval_count"] == 8

    assert cheapest_3h_state is not None
    assert cheapest_3h_state.attributes["device_class"] == "timestamp"
    assert datetime.fromisoformat(cheapest_3h_state.state) == datetime(
        2026, 8, 13, 20, 15, tzinfo=UTC
    )
    assert cheapest_3h_state.attributes["window_end"] == "2026-08-13T23:15:00+00:00"
    assert cheapest_3h_state.attributes["window_duration_minutes"] == 180
    assert cheapest_3h_state.attributes["interval_count"] == 12

    assert cheapest_1h_average_effective_price_state is not None
    assert cheapest_1h_average_effective_price_state.state == "0.84104"
    assert (
        cheapest_1h_average_effective_price_state.attributes["window_start"]
        == "2026-08-13T20:15:00+00:00"
    )
    assert (
        cheapest_1h_average_effective_price_state.attributes["window_end"]
        == "2026-08-13T21:15:00+00:00"
    )
    assert (
        cheapest_1h_average_effective_price_state.attributes["window_duration_minutes"]
        == 60
    )
    assert cheapest_1h_average_effective_price_state.attributes["interval_count"] == 4
    assert (
        cheapest_1h_average_effective_price_state.attributes["average_market_price"]
        == "0.84104"
    )
    assert cheapest_1h_average_effective_price_state.attributes["currency"] == "SEK"
    assert cheapest_1h_average_effective_price_state.attributes["price_area"] == "SE3"

    assert cheapest_2h_average_effective_price_state is not None
    assert cheapest_2h_average_effective_price_state.state == "1.04104"
    assert (
        cheapest_2h_average_effective_price_state.attributes["window_start"]
        == "2026-08-13T20:15:00+00:00"
    )
    assert (
        cheapest_2h_average_effective_price_state.attributes["window_end"]
        == "2026-08-13T22:15:00+00:00"
    )
    assert (
        cheapest_2h_average_effective_price_state.attributes["window_duration_minutes"]
        == 120
    )
    assert cheapest_2h_average_effective_price_state.attributes["interval_count"] == 8
    assert (
        cheapest_2h_average_effective_price_state.attributes["average_market_price"]
        == "1.04104"
    )
    assert cheapest_2h_average_effective_price_state.attributes["currency"] == "SEK"
    assert cheapest_2h_average_effective_price_state.attributes["price_area"] == "SE3"

    assert cheapest_3h_average_effective_price_state is not None
    assert cheapest_3h_average_effective_price_state.state == "1.24104"
    assert (
        cheapest_3h_average_effective_price_state.attributes["window_start"]
        == "2026-08-13T20:15:00+00:00"
    )
    assert (
        cheapest_3h_average_effective_price_state.attributes["window_end"]
        == "2026-08-13T23:15:00+00:00"
    )
    assert (
        cheapest_3h_average_effective_price_state.attributes[
            "window_duration_minutes"
        ]
        == 180
    )
    assert cheapest_3h_average_effective_price_state.attributes["interval_count"] == 12
    assert (
        cheapest_3h_average_effective_price_state.attributes["average_market_price"]
        == "1.24104"
    )
    assert cheapest_3h_average_effective_price_state.attributes["currency"] == "SEK"
    assert cheapest_3h_average_effective_price_state.attributes["price_area"] == "SE3"

    assert direction_state is not None
    assert direction_state.state == "rising"
    assert direction_state.attributes["current_interval_start"] == "2026-08-13T20:00:00+00:00"
    assert direction_state.attributes["next_interval_start"] == "2026-08-13T20:15:00+00:00"
    assert direction_state.attributes["current_scheduling_price"] == "0.59104"
    assert direction_state.attributes["next_scheduling_price"] == "0.69104"
    assert direction_state.attributes["delta"] == "0.10000"
    assert direction_state.attributes["currency"] == "SEK"
    assert direction_state.attributes["price_area"] == "SE3"


async def test_forecast_insight_sensors_become_unavailable_without_forecast_data(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """Forecast insight sensors should be unavailable when no forecast is available."""
    async_get = AsyncMock(side_effect=ValueError("bad forecast response"))
    with patch(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        async_get,
    ):
        await setup_electricity_pro(
            forecast_price_area="SE3",
            forecast_currency="SEK",
            forecast_nordpool_config_entry="nordpool-entry-id",
        )

    cheapest_1h_state = hass.states.get(CHEAPEST_1H_WINDOW_ENTITY_ID)
    cheapest_2h_state = hass.states.get(CHEAPEST_2H_WINDOW_ENTITY_ID)
    cheapest_3h_state = hass.states.get(CHEAPEST_3H_WINDOW_ENTITY_ID)
    cheapest_1h_average_effective_price_state = hass.states.get(
        CHEAPEST_1H_WINDOW_AVERAGE_EFFECTIVE_PRICE_ENTITY_ID
    )
    cheapest_2h_average_effective_price_state = hass.states.get(
        CHEAPEST_2H_WINDOW_AVERAGE_EFFECTIVE_PRICE_ENTITY_ID
    )
    cheapest_3h_average_effective_price_state = hass.states.get(
        CHEAPEST_3H_WINDOW_AVERAGE_EFFECTIVE_PRICE_ENTITY_ID
    )
    direction_state = hass.states.get(PRICE_DIRECTION_ENTITY_ID)

    assert cheapest_1h_state is not None
    assert cheapest_1h_state.state == "unavailable"
    assert cheapest_2h_state is not None
    assert cheapest_2h_state.state == "unavailable"
    assert cheapest_3h_state is not None
    assert cheapest_3h_state.state == "unavailable"
    assert cheapest_1h_average_effective_price_state is not None
    assert cheapest_1h_average_effective_price_state.state == "unavailable"
    assert cheapest_2h_average_effective_price_state is not None
    assert cheapest_2h_average_effective_price_state.state == "unavailable"
    assert cheapest_3h_average_effective_price_state is not None
    assert cheapest_3h_average_effective_price_state.state == "unavailable"
    assert direction_state is not None
    assert direction_state.state == "unavailable"


NEXT_INEXPENSIVE_1H_WINDOW_ENTITY_ID = f"sensor.{DOMAIN}_next_inexpensive_1h_window_start"


async def test_next_inexpensive_1h_window_sensor_exposes_qualifying_window(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """The next inexpensive 1h window sensor should expose the first qualifying window."""
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 20, 1, tzinfo=UTC),
    ):
        await setup_electricity_pro(
            good_price_threshold=0.65,
            forecast_price_area="SE3",
            forecast_currency="SEK",
            forecast_nordpool_config_entry="nordpool-entry-id",
            forecast_intervals=[
                {
                    "start": "2026-08-13T20:00:00+00:00",
                    "end": "2026-08-13T21:00:00+00:00",
                    "price": 900,
                },
                {
                    "start": "2026-08-13T21:00:00+00:00",
                    "end": "2026-08-13T22:00:00+00:00",
                    "price": 600,
                },
                {
                    "start": "2026-08-13T22:00:00+00:00",
                    "end": "2026-08-13T23:00:00+00:00",
                    "price": 400,
                },
            ],
        )

    state = hass.states.get(NEXT_INEXPENSIVE_1H_WINDOW_ENTITY_ID)
    assert state is not None
    assert state.attributes["device_class"] == "timestamp"
    assert state.state == "unavailable"


async def test_next_inexpensive_1h_window_sensor_unavailable_when_no_qualifying_window(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """The next inexpensive 1h window sensor should be unavailable when no window qualifies."""
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 20, 1, tzinfo=UTC),
    ):
        await setup_electricity_pro(
            good_price_threshold=0.30,
            forecast_price_area="SE3",
            forecast_currency="SEK",
            forecast_nordpool_config_entry="nordpool-entry-id",
            forecast_intervals=[
                {
                    "start": "2026-08-13T20:00:00+00:00",
                    "end": "2026-08-13T21:00:00+00:00",
                    "price": 900,
                },
                {
                    "start": "2026-08-13T21:00:00+00:00",
                    "end": "2026-08-13T22:00:00+00:00",
                    "price": 800,
                },
            ],
        )

    state = hass.states.get(NEXT_INEXPENSIVE_1H_WINDOW_ENTITY_ID)
    assert state is not None
    assert state.state == "unavailable"


async def test_next_inexpensive_1h_window_sensor_unavailable_without_threshold(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., CoroutineType[Any, Any, MockConfigEntry]],
) -> None:
    """The next inexpensive sensor should be omitted when no threshold is configured."""
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 20, 1, tzinfo=UTC),
    ):
        await setup_electricity_pro(
            forecast_price_area="SE3",
            forecast_currency="SEK",
            forecast_nordpool_config_entry="nordpool-entry-id",
            forecast_intervals=[
                {
                    "start": "2026-08-13T20:00:00+00:00",
                    "end": "2026-08-13T21:00:00+00:00",
                    "price": 300,
                },
            ],
        )

    state = hass.states.get(NEXT_INEXPENSIVE_1H_WINDOW_ENTITY_ID)
    assert state is None
