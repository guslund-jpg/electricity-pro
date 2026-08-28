"""Tests for coordinator forecast runtime behavior."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_FORECAST_CURRENCY,
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FORECAST_PRICE_AREA,
    CONF_GRID_FEE_HIGH_END,
    CONF_GRID_FEE_HIGH_PER_KWH,
    CONF_GRID_FEE_HIGH_SEASON_END,
    CONF_GRID_FEE_HIGH_SEASON_START,
    CONF_GRID_FEE_HIGH_START,
    CONF_GRID_FEE_WORKDAY_ENTITY,
    CONF_GRID_FEE_PER_KWH,
    CONF_POWER_ENTITY,
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_ENTITY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICING_STRATEGY,
    DOMAIN,
)
from custom_components.electricity_pro.base_load import BaseLoadUnavailableReason
from custom_components.electricity_pro.coordinator import ElectricityProCoordinator
from custom_components.electricity_pro.forecast import ForecastInterval
from custom_components.electricity_pro.forecast_insights import (
    ForecastDirectionInsight,
    ForecastWindowInsight,
)
from custom_components.electricity_pro.pricing import (
    PriceCompleteness,
    PriceComponent,
    PricingStrategy,
    VatTreatment,
)
from custom_components.electricity_pro.timing_score import (
    TimingBucketAccumulator,
    TimingScoreUnavailableReason,
)


def _daily_peak_entry() -> MockConfigEntry:
    """Create a minimal entry for daily peak tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={CONF_POWER_ENTITY: "sensor.test_power"},
        entry_id="daily-peak-entry",
    )


def _timing_entry() -> MockConfigEntry:
    """Create a complete entry for consumption-timing runtime tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_PRICE_ENTITY: "sensor.test_price",
            CONF_PRICING_STRATEGY: PricingStrategy.SUPPLIER_CONTRACTED_PRICE,
            CONF_PRICE_INCLUDED_COMPONENTS: [
                PriceComponent.MARKET_ENERGY,
                PriceComponent.SUPPLIER_MARKUP,
            ],
            CONF_PRICE_VAT_TREATMENT: VatTreatment.INCLUDED,
            CONF_PRICE_COMPLETENESS: PriceCompleteness.PARTIAL,
        },
        entry_id="timing-entry",
    )


def test_timing_runtime_expires_stale_power_after_ten_minutes(hass) -> None:
    """A quiet source must not turn stale power into fabricated coverage."""
    hass.config.time_zone = "Europe/Stockholm"
    hass.states.async_set("sensor.test_power", "1000", {"unit_of_measurement": "W"})
    hass.states.async_set(
        "sensor.test_price",
        "1.5",
        {"unit_of_measurement": "SEK/kWh"},
    )
    coordinator = ElectricityProCoordinator(hass, _timing_entry())
    start = datetime(2026, 8, 25, 0, 0, tzinfo=UTC)

    with patch.object(coordinator._store, "async_delay_save"):  # noqa: SLF001
        with patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=start,
        ):
            coordinator._read(power_observed=True)  # noqa: SLF001
        with patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=start + timedelta(minutes=5),
        ):
            coordinator._read()  # noqa: SLF001
        with patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=start + timedelta(minutes=20),
        ):
            coordinator._read()  # noqa: SLF001

    intervals = coordinator._timing_buckets.intervals_for_date(  # noqa: SLF001
        start.astimezone(coordinator._local_timezone).date()  # noqa: SLF001
    )
    assert sum(
        (interval.covered_duration for interval in intervals),
        timedelta(0),
    ) == timedelta(minutes=10)
    assert sum(
        (interval.energy_kwh for interval in intervals),
        Decimal(0),
    ) == Decimal(1) / Decimal(6)


def test_base_load_runtime_tracks_power_without_price(hass) -> None:
    """Base-load coverage must not depend on a configured price source."""
    hass.config.time_zone = "Europe/Stockholm"
    hass.states.async_set("sensor.test_power", "600", {"unit_of_measurement": "W"})
    coordinator = ElectricityProCoordinator(hass, _daily_peak_entry())
    start = datetime(2026, 8, 25, 0, 0, tzinfo=UTC)

    with patch.object(coordinator._store, "async_delay_save"):  # noqa: SLF001
        with patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=start,
        ):
            coordinator._read(power_observed=True)  # noqa: SLF001
        with patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=start + timedelta(minutes=5),
        ):
            coordinator._read()  # noqa: SLF001

    intervals = coordinator._base_load_buckets.intervals_for_date(  # noqa: SLF001
        start.astimezone(coordinator._local_timezone).date()  # noqa: SLF001
    )
    assert len(intervals) == 1
    assert intervals[0].mean_power_w == Decimal(600)
    assert intervals[0].covered_duration == timedelta(minutes=5)


def test_base_load_runtime_marks_negative_source_power(hass) -> None:
    """A negative source value should reject the day without being published."""
    hass.config.time_zone = "Europe/Stockholm"
    hass.states.async_set("sensor.test_power", "-100", {"unit_of_measurement": "W"})
    coordinator = ElectricityProCoordinator(hass, _daily_peak_entry())
    start = datetime(2026, 8, 25, 0, 0, tzinfo=UTC)

    with patch.object(coordinator._store, "async_delay_save"):  # noqa: SLF001
        with patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=start,
        ):
            data = coordinator._read(power_observed=True)  # noqa: SLF001
        with patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=start + timedelta(minutes=5),
        ):
            coordinator._read()  # noqa: SLF001

    local_date = start.astimezone(coordinator._local_timezone).date()  # noqa: SLF001
    assert data.current_power == Decimal(-100)
    assert coordinator._base_load_buckets.bidirectional_observed(local_date)  # noqa: SLF001


def test_base_load_runtime_publishes_after_five_eligible_days(hass) -> None:
    """Five complete recent days should produce the rolling median estimate."""
    hass.config.time_zone = "Europe/Stockholm"
    coordinator = ElectricityProCoordinator(hass, _daily_peak_entry())
    timezone = coordinator._local_timezone  # noqa: SLF001
    for day, power in zip(range(20, 25), (180, 190, 200, 210, 220)):
        period_start = date(2026, 8, day)
        day_start = datetime(2026, 8, day, tzinfo=timezone)
        coordinator._base_load_buckets.add_segment(  # noqa: SLF001
            start=day_start,
            end=day_start + timedelta(days=1),
            power_w=Decimal(power),
        )
        coordinator._finalize_base_load_day(period_start)  # noqa: SLF001

    result = coordinator.estimated_base_load
    assert result is not None
    assert result.estimate_w == Decimal(200)
    assert result.unavailable_reason is None


def test_average_power_today_uses_elapsed_local_day(hass) -> None:
    """The coordinator should calculate against elapsed time since midnight."""
    hass.config.time_zone = "Europe/Stockholm"
    coordinator = ElectricityProCoordinator(hass, _daily_peak_entry())
    timezone = coordinator._local_timezone  # noqa: SLF001
    day_start = datetime(2026, 8, 25, tzinfo=timezone)
    now = day_start + timedelta(hours=4)
    coordinator._base_load_buckets.add_segment(  # noqa: SLF001
        start=day_start,
        end=day_start + timedelta(hours=1),
        power_w=Decimal(100),
    )
    coordinator._base_load_buckets.add_segment(  # noqa: SLF001
        start=day_start + timedelta(hours=1),
        end=now,
        power_w=Decimal(300),
    )

    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=now,
    ):
        stored = coordinator.average_power_today

    assert stored is not None
    period_start, result = stored
    assert period_start == date(2026, 8, 25)
    assert result.average_power_w == Decimal(250)
    assert result.coverage_percent == Decimal(100)


@pytest.mark.parametrize(
    ("day", "elapsed_hours"),
    [
        (date(2026, 3, 29), 3),
        (date(2026, 10, 25), 5),
    ],
)
def test_average_power_today_uses_actual_dst_elapsed_time(
    hass,
    day: date,
    elapsed_hours: int,
) -> None:
    """Spring and autumn clock changes must use elapsed real time."""
    hass.config.time_zone = "Europe/Stockholm"
    coordinator = ElectricityProCoordinator(hass, _daily_peak_entry())
    timezone = coordinator._local_timezone  # noqa: SLF001
    day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone)
    now = datetime.combine(day, datetime.min.time(), tzinfo=timezone).replace(hour=4)
    coordinator._base_load_buckets.add_segment(  # noqa: SLF001
        start=day_start,
        end=now,
        power_w=Decimal(400),
    )

    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=now,
    ):
        stored = coordinator.average_power_today

    assert stored is not None
    assert stored[1].covered_duration == timedelta(hours=elapsed_hours)
    assert stored[1].coverage_percent == Decimal(100)


def test_average_power_today_is_empty_at_local_midnight(hass) -> None:
    """The new local day should begin unavailable before any interval."""
    hass.config.time_zone = "Europe/Stockholm"
    coordinator = ElectricityProCoordinator(hass, _daily_peak_entry())
    midnight = datetime(2026, 8, 25, tzinfo=coordinator._local_timezone)  # noqa: SLF001

    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=midnight,
    ):
        assert coordinator.average_power_today is None


async def test_base_load_runtime_restores_bounded_history(hass) -> None:
    """Restart restoration should preserve buckets and daily summaries."""
    hass.config.time_zone = "Europe/Stockholm"
    original = ElectricityProCoordinator(hass, _daily_peak_entry())
    period_start = date(2026, 8, 24)
    day_start = datetime(2026, 8, 24, tzinfo=original._local_timezone)  # noqa: SLF001
    original._base_load_buckets.add_segment(  # noqa: SLF001
        start=day_start,
        end=day_start + timedelta(days=1),
        power_w=Decimal(250),
    )
    original._finalize_base_load_day(period_start)  # noqa: SLF001
    stored = original._statistics_data()  # noqa: SLF001
    restored = ElectricityProCoordinator(hass, _daily_peak_entry())

    with patch.object(
        restored._store,  # noqa: SLF001
        "async_load",
        AsyncMock(return_value=stored),
    ):
        await restored._async_restore_statistics()  # noqa: SLF001

    assert restored._base_load_buckets.as_dict() == (  # noqa: SLF001
        original._base_load_buckets.as_dict()  # noqa: SLF001
    )
    restored._recalculate_base_load(period_start)  # noqa: SLF001
    assert restored.estimated_base_load is not None
    assert (
        restored.estimated_base_load.unavailable_reason
        is BaseLoadUnavailableReason.INSUFFICIENT_HISTORY
    )


def test_timing_runtime_finalizes_a_complete_local_day(hass) -> None:
    """A completed day should produce the agreed retrospective score."""
    hass.config.time_zone = "Europe/Stockholm"
    coordinator = ElectricityProCoordinator(hass, _timing_entry())
    period_start = date(2026, 8, 24)
    day_start = datetime(2026, 8, 24, tzinfo=coordinator._local_timezone)  # noqa: SLF001
    for index, price in enumerate(("1", "2", "3", "4")):
        coordinator._timing_buckets.add_segment(  # noqa: SLF001
            start=day_start + timedelta(hours=6 * index),
            end=day_start + timedelta(hours=6 * (index + 1)),
            power_w=Decimal("4000") if index == 0 else Decimal(0),
            effective_price=Decimal(price),
        )

    coordinator._finalize_timing_day(period_start)  # noqa: SLF001

    assert coordinator.timing_score_yesterday is not None
    result_date, result = coordinator.timing_score_yesterday
    assert result_date == period_start
    assert result.score == Decimal(88)


def test_timing_runtime_rejects_a_day_containing_export(hass) -> None:
    """A complete priced day is still unsupported when net export occurred."""
    hass.config.time_zone = "Europe/Stockholm"
    coordinator = ElectricityProCoordinator(hass, _timing_entry())
    period_start = date(2026, 8, 24)
    day_start = datetime(2026, 8, 24, tzinfo=coordinator._local_timezone)  # noqa: SLF001
    coordinator._timing_buckets.add_segment(  # noqa: SLF001
        start=day_start,
        end=day_start + timedelta(days=1),
        power_w=Decimal(1000),
        effective_price=Decimal(1),
    )
    coordinator._base_load_buckets.add_segment(  # noqa: SLF001
        start=day_start,
        end=day_start + timedelta(minutes=5),
        power_w=Decimal(-100),
    )

    coordinator._finalize_timing_day(period_start)  # noqa: SLF001

    assert coordinator.timing_score_yesterday is not None
    result = coordinator.timing_score_yesterday[1]
    assert result.score is None
    assert (
        result.unavailable_reason
        is TimingScoreUnavailableReason.UNSUPPORTED_BIDIRECTIONAL_POWER
    )


async def test_timing_runtime_restores_buckets_and_completed_result(hass) -> None:
    """Restart restoration should preserve aggregate history and the last result."""
    hass.config.time_zone = "Europe/Stockholm"
    original = ElectricityProCoordinator(hass, _timing_entry())
    period_start = date(2026, 8, 24)
    day_start = datetime(2026, 8, 24, tzinfo=original._local_timezone)  # noqa: SLF001
    original._timing_buckets.add_segment(  # noqa: SLF001
        start=day_start,
        end=day_start + timedelta(minutes=15),
        power_w=Decimal("1000"),
        effective_price=Decimal("1.5"),
    )
    original._finalize_timing_day(period_start)  # noqa: SLF001
    stored = original._statistics_data()  # noqa: SLF001
    restored = ElectricityProCoordinator(hass, _timing_entry())

    with patch.object(
        restored._store,  # noqa: SLF001
        "async_load",
        AsyncMock(return_value=stored),
    ):
        await restored._async_restore_statistics()  # noqa: SLF001

    assert restored._timing_buckets.as_dict() == original._timing_buckets.as_dict()  # noqa: SLF001
    assert restored.timing_score_yesterday == original.timing_score_yesterday


def test_daily_peak_is_calculated_from_current_power(hass) -> None:
    """Coordinator should retain only the highest observed power and its time."""
    hass.config.time_zone = "Europe/Stockholm"
    hass.states.async_set("sensor.test_power", "1000", {"unit_of_measurement": "W"})
    coordinator = ElectricityProCoordinator(hass, _daily_peak_entry())
    first = datetime(2026, 8, 24, 8, 0, tzinfo=UTC)

    with (
        patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=first,
        ),
        patch.object(coordinator._store, "async_delay_save"),  # noqa: SLF001
    ):
        data = coordinator._read()  # noqa: SLF001
    assert data.peak_power_today == Decimal("1000")
    assert data.peak_power_time_today == first.astimezone(coordinator._local_timezone)  # noqa: SLF001

    hass.states.async_set("sensor.test_power", "900", {"unit_of_measurement": "W"})
    with (
        patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=first.replace(hour=9),
        ),
        patch.object(coordinator._store, "async_delay_save"),  # noqa: SLF001
    ):
        data = coordinator._read()  # noqa: SLF001
    assert data.peak_power_today == Decimal("1000")


async def test_daily_peak_restores_current_day_snapshot(hass) -> None:
    """A restart should preserve a valid peak from the current local day."""
    hass.config.time_zone = "Europe/Stockholm"
    hass.states.async_set("sensor.test_power", "900", {"unit_of_measurement": "W"})
    coordinator = ElectricityProCoordinator(hass, _daily_peak_entry())
    now = datetime(2026, 8, 24, 10, 0, tzinfo=UTC)
    peak_time = datetime(2026, 8, 24, 9, 0, tzinfo=UTC)
    stored = {
        "peak_power_today": {
            "period_start": "2026-08-24",
            "peak_power_w": "1200",
            "peak_time": peak_time.astimezone(coordinator._local_timezone).isoformat(),  # noqa: SLF001
        }
    }

    with (
        patch.object(coordinator._store, "async_load", AsyncMock(return_value=stored)),  # noqa: SLF001
        patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=now,
        ),
    ):
        await coordinator._async_restore_statistics()  # noqa: SLF001
        with patch.object(coordinator._store, "async_delay_save"):  # noqa: SLF001
            data = coordinator._read()  # noqa: SLF001

    assert data.peak_power_today == Decimal("1200")
    assert data.peak_power_time_today == peak_time.astimezone(
        coordinator._local_timezone  # noqa: SLF001
    )


def test_daily_peak_midnight_rollover_publishes_unavailable(hass) -> None:
    """Local midnight should clear both daily peak entities until a new sample."""
    hass.config.time_zone = "Europe/Stockholm"
    hass.states.async_set("sensor.test_power", "1000", {"unit_of_measurement": "W"})
    coordinator = ElectricityProCoordinator(hass, _daily_peak_entry())
    with (
        patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=datetime(2026, 8, 24, 21, 0, tzinfo=UTC),
        ),
        patch.object(coordinator._store, "async_delay_save"),  # noqa: SLF001
    ):
        coordinator.async_set_updated_data(coordinator._read())  # noqa: SLF001
        coordinator._async_daily_rollover(  # noqa: SLF001
            datetime(2026, 8, 25, 0, 0, tzinfo=coordinator._local_timezone)  # noqa: SLF001
        )

    assert coordinator.data is not None
    assert coordinator.data.peak_power_today is None
    assert coordinator.data.peak_power_time_today is None
    assert "peak_power_today" not in coordinator._statistics_data()  # noqa: SLF001


async def test_unavailable_workday_source_uses_ordinary_weekday_schedule(
    hass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Workday failure should conservatively retain the ordinary high fee."""
    hass.config.time_zone = "Europe/Stockholm"
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_GRID_FEE_PER_KWH: 0.125,
            CONF_GRID_FEE_HIGH_PER_KWH: 0.25,
            CONF_GRID_FEE_HIGH_START: "06:00",
            CONF_GRID_FEE_HIGH_END: "22:00",
            CONF_GRID_FEE_HIGH_SEASON_START: "11-01",
            CONF_GRID_FEE_HIGH_SEASON_END: "03-31",
            CONF_GRID_FEE_WORKDAY_ENTITY: "binary_sensor.workday",
        },
    )
    async_get = AsyncMock(side_effect=HomeAssistantError("workday unavailable"))
    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_non_working_dates",
        async_get,
    )
    coordinator = ElectricityProCoordinator(hass, entry)

    refreshed = await coordinator._async_refresh_non_working_dates(  # noqa: SLF001
        datetime(2026, 12, 25, 10, 0, tzinfo=UTC)
    )

    assert not refreshed
    assert coordinator._provider.grid_fee_at(  # noqa: SLF001
        datetime(2026, 12, 25, 10, 0, tzinfo=UTC)
    ) == Decimal("0.25")


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """Create a minimal config entry for coordinator tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_FORECAST_PRICE_AREA: "SE3",
            CONF_FORECAST_CURRENCY: "SEK",
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: "nordpool-entry-id",
        },
        entry_id="test-entry-id",
    )


async def test_async_start_stores_forecast_intervals(
    hass,
    mock_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coordinator startup should retrieve and store today's forecast intervals."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    mock_entry.add_to_hass(hass)

    forecast_intervals = [
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 20, 15, tzinfo=UTC),
            market_price=Decimal("0.59104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 15, tzinfo=UTC),
            end=datetime(2026, 8, 13, 20, 30, tzinfo=UTC),
            market_price=Decimal("0.69104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 30, tzinfo=UTC),
            end=datetime(2026, 8, 13, 20, 45, tzinfo=UTC),
            market_price=Decimal("0.79104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 45, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            market_price=Decimal("0.89104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 15, tzinfo=UTC),
            market_price=Decimal("0.99104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 21, 15, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 30, tzinfo=UTC),
            market_price=Decimal("1.09104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 21, 30, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 45, tzinfo=UTC),
            market_price=Decimal("1.19104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 21, 45, tzinfo=UTC),
            end=datetime(2026, 8, 13, 22, 0, tzinfo=UTC),
            market_price=Decimal("1.29104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 22, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 22, 15, tzinfo=UTC),
            market_price=Decimal("1.39104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 22, 15, tzinfo=UTC),
            end=datetime(2026, 8, 13, 22, 30, tzinfo=UTC),
            market_price=Decimal("1.49104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 22, 30, tzinfo=UTC),
            end=datetime(2026, 8, 13, 22, 45, tzinfo=UTC),
            market_price=Decimal("1.59104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 22, 45, tzinfo=UTC),
            end=datetime(2026, 8, 13, 23, 0, tzinfo=UTC),
            market_price=Decimal("1.69104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 23, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 23, 15, tzinfo=UTC),
            market_price=Decimal("1.79104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 23, 15, tzinfo=UTC),
            end=datetime(2026, 8, 13, 23, 30, tzinfo=UTC),
            market_price=Decimal("1.89104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 23, 30, tzinfo=UTC),
            end=datetime(2026, 8, 13, 23, 45, tzinfo=UTC),
            market_price=Decimal("1.99104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 23, 45, tzinfo=UTC),
            end=datetime(2026, 8, 14, 0, 0, tzinfo=UTC),
            market_price=Decimal("2.09104"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
    ]

    async_get = AsyncMock(return_value=forecast_intervals)
    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        async_get,
    )

    coordinator = ElectricityProCoordinator(hass, mock_entry)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 20, 1, tzinfo=UTC),
    ):
        await coordinator.async_start()

    assert coordinator.forecast_intervals == forecast_intervals
    assert async_get.await_count == 2
    assert [call.kwargs["target_date"] for call in async_get.await_args_list] == [
        date(2026, 8, 13),
        date(2026, 8, 14),
    ]
    assert all(
        call.kwargs["config_entry_id"] == "nordpool-entry-id"
        and call.kwargs["area"] == "SE3"
        for call in async_get.await_args_list
    )
    assert isinstance(coordinator.cheapest_1h_window, ForecastWindowInsight)
    assert coordinator.cheapest_1h_window.start == datetime(2026, 8, 13, 20, 15, tzinfo=UTC)
    assert coordinator.cheapest_1h_window.end == datetime(2026, 8, 13, 21, 15, tzinfo=UTC)
    assert isinstance(coordinator.cheapest_2h_window, ForecastWindowInsight)
    assert coordinator.cheapest_2h_window.start == datetime(2026, 8, 13, 20, 15, tzinfo=UTC)
    assert coordinator.cheapest_2h_window.end == datetime(2026, 8, 13, 22, 15, tzinfo=UTC)
    assert isinstance(coordinator.cheapest_3h_window, ForecastWindowInsight)
    assert coordinator.cheapest_3h_window.start == datetime(2026, 8, 13, 20, 15, tzinfo=UTC)
    assert coordinator.cheapest_3h_window.end == datetime(2026, 8, 13, 23, 15, tzinfo=UTC)
    assert isinstance(coordinator.price_direction, ForecastDirectionInsight)
    assert coordinator.price_direction.direction == "rising"


async def test_async_start_keeps_empty_forecast_intervals_on_retrieval_failure(
    hass,
    mock_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coordinator startup should keep an empty forecast state on retrieval failure."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    mock_entry.add_to_hass(hass)

    async_get = AsyncMock(side_effect=ValueError("bad forecast response"))
    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        async_get,
    )

    coordinator = ElectricityProCoordinator(hass, mock_entry)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
    ):
        await coordinator.async_start()

    assert coordinator.forecast_intervals == []
    assert coordinator.cheapest_1h_window is None
    assert coordinator.cheapest_2h_window is None
    assert coordinator.cheapest_3h_window is None
    assert coordinator.price_direction is None
    async_get.assert_awaited_once()


async def test_empty_forecast_response_remains_retryable(
    hass,
    mock_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty publication response should not be cached as a complete date."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    mock_entry.add_to_hass(hass)

    async_get = AsyncMock(return_value=[])
    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        async_get,
    )

    coordinator = ElectricityProCoordinator(hass, mock_entry)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
    ):
        await coordinator.async_start()
    await coordinator._async_forecast_tick(  # noqa: SLF001
        datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    )

    assert coordinator.forecast_intervals == []
    assert async_get.await_count == 2


async def test_async_start_degrades_gracefully_on_native_action_failure(
    hass,
    mock_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native Nord Pool action failures must not prevent integration startup."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    mock_entry.add_to_hass(hass)
    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        AsyncMock(side_effect=HomeAssistantError("Nord Pool unavailable")),
    )

    coordinator = ElectricityProCoordinator(hass, mock_entry)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
    ):
        await coordinator.async_start()

    assert coordinator.data is not None
    assert coordinator.forecast_intervals == []


async def test_forecast_tick_retries_tomorrow_and_expires_insights(
    hass,
    mock_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lifecycle should retry tomorrow publication and expire old windows."""
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    mock_entry.add_to_hass(hass)
    today_intervals = [
        ForecastInterval(
            start=datetime(2026, 8, 13, 12, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 13, 0, tzinfo=UTC),
            market_price=Decimal("0.40"),
            currency="SEK",
            area="SE3",
        )
    ]
    tomorrow_intervals = [
        ForecastInterval(
            start=datetime(2026, 8, 14, 0, 0, tzinfo=UTC),
            end=datetime(2026, 8, 14, 1, 0, tzinfo=UTC),
            market_price=Decimal("0.20"),
            currency="SEK",
            area="SE3",
        )
    ]
    async_get = AsyncMock(return_value=today_intervals)
    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        async_get,
    )

    coordinator = ElectricityProCoordinator(hass, mock_entry)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 12, 0, tzinfo=UTC),
    ):
        await coordinator.async_start()
    assert coordinator.cheapest_1h_window is not None

    async_get.side_effect = HomeAssistantError("not published yet")
    with (
        patch(
            "custom_components.electricity_pro.coordinator.dt_util.as_local",
            side_effect=lambda value: value,
        ),
        patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=datetime(2026, 8, 13, 13, 0, tzinfo=UTC),
        ),
    ):
        await coordinator._async_forecast_tick(
            datetime(2026, 8, 13, 13, 0, tzinfo=UTC)
        )
    assert coordinator.cheapest_1h_window is None

    async_get.side_effect = None
    async_get.return_value = tomorrow_intervals
    with (
        patch(
            "custom_components.electricity_pro.coordinator.dt_util.as_local",
            side_effect=lambda value: value,
        ),
        patch(
            "custom_components.electricity_pro.coordinator.dt_util.now",
            return_value=datetime(2026, 8, 13, 13, 15, tzinfo=UTC),
        ),
    ):
        await coordinator._async_forecast_tick(
            datetime(2026, 8, 13, 13, 15, tzinfo=UTC)
        )

    assert tomorrow_intervals[0] in coordinator.forecast_intervals
    assert coordinator.cheapest_1h_window is not None
    assert coordinator.cheapest_1h_window.start == tomorrow_intervals[0].start


async def test_async_start_caches_next_inexpensive_1h_window_when_threshold_configured(
    hass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coordinator should cache the next inexpensive 1h window when a good price threshold is set."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
            CONF_FORECAST_PRICE_AREA: "SE3",
            CONF_FORECAST_CURRENCY: "SEK",
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: "nordpool-entry-id",
            "good_price_threshold": 0.70,
        },
        entry_id="test-entry-id-threshold",
    )
    hass.states.async_set("sensor.test_power", "1000", {"unit_of_measurement": "W"})
    entry.add_to_hass(hass)

    forecast_intervals = [
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            market_price=Decimal("0.90"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 22, 0, tzinfo=UTC),
            market_price=Decimal("0.60"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 22, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 23, 0, tzinfo=UTC),
            market_price=Decimal("0.50"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
    ]

    async_get = AsyncMock(return_value=forecast_intervals)
    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        async_get,
    )

    coordinator = ElectricityProCoordinator(hass, entry)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 20, 1, tzinfo=UTC),
    ):
        await coordinator.async_start()

    assert coordinator.next_inexpensive_1h_window is None


async def test_async_start_next_inexpensive_1h_window_none_without_threshold(
    hass,
    mock_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coordinator should leave next_inexpensive_1h_window as None when no threshold is configured."""
    hass.states.async_set("sensor.test_power", "1000", {"unit_of_measurement": "W"})
    mock_entry.add_to_hass(hass)

    forecast_intervals = [
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            market_price=Decimal("0.30"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
    ]

    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        AsyncMock(return_value=forecast_intervals),
    )

    coordinator = ElectricityProCoordinator(hass, mock_entry)
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 13, 19, 0, tzinfo=UTC),
    ):
        await coordinator.async_start()

    assert coordinator.next_inexpensive_1h_window is None


async def test_recalculate_forecast_insights_returns_none_when_now_is_past_all_intervals(
    hass,
    mock_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Insights should all be None when 'now' has advanced past every stored interval.

    This is the expected stale-data behavior: as time moves forward the coordinator
    does not have a refresh mechanism that automatically fetches new intervals, so
    if 'now' lands beyond the last stored interval end, every insight returns None
    rather than exposing an expired window.
    """
    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {"unit_of_measurement": "W"},
    )
    mock_entry.add_to_hass(hass)

    forecast_intervals = [
        ForecastInterval(
            start=datetime(2026, 8, 13, 20, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            market_price=Decimal("0.30"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
        ForecastInterval(
            start=datetime(2026, 8, 13, 21, 0, tzinfo=UTC),
            end=datetime(2026, 8, 13, 22, 0, tzinfo=UTC),
            market_price=Decimal("0.40"),
            currency="SEK",
            area="SE3",
            published_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        ),
    ]

    monkeypatch.setattr(
        "custom_components.electricity_pro.coordinator.async_get_nordpool_forecast_intervals_for_date",
        AsyncMock(return_value=forecast_intervals),
    )

    coordinator = ElectricityProCoordinator(hass, mock_entry)

    # Start with 'now' well after the last interval end (22:00 UTC).
    with patch(
        "custom_components.electricity_pro.coordinator.dt_util.now",
        return_value=datetime(2026, 8, 14, 6, 0, tzinfo=UTC),
    ):
        await coordinator.async_start()

    # Intervals are stored but all are in the past relative to 'now'.
    assert coordinator.forecast_intervals == forecast_intervals
    assert coordinator.cheapest_1h_window is None
    assert coordinator.cheapest_2h_window is None
    assert coordinator.cheapest_3h_window is None
    assert coordinator.next_inexpensive_1h_window is None
    assert coordinator.price_direction is None
