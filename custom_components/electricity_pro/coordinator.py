"""Data coordinator for Electricity Pro."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, UnitOfEnergy
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .adaptive_price import (
    AdaptivePriceHistory,
    AdaptivePriceScope,
)
from .base_load import (
    AveragePowerResult,
    BaseLoadBucketAccumulator,
    BaseLoadEstimateResult,
    DailyBaseLoadSummary,
    calculate_average_power,
    calculate_base_load_estimate,
    calculate_daily_base_load,
)
from .calculations import (
    calculate_declared_effective_price,
    effective_price_metadata,
)
from .const import (
    CONF_ENERGY_TAX_PER_KWH,
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FORECAST_PRICE_AREA,
    CONF_GRID_FEE_HIGH_END,
    CONF_GRID_FEE_HIGH_PER_KWH,
    CONF_GRID_FEE_HIGH_SEASON_END,
    CONF_GRID_FEE_HIGH_SEASON_START,
    CONF_GRID_FEE_HIGH_START,
    CONF_GRID_FEE_PER_KWH,
    CONF_GRID_FEE_WORKDAY_ENTITY,
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_ENTITY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICING_STRATEGY,
    CONF_SUPPLIER_MARKUP_PER_KWH,
    DOMAIN,
)
from .forecast import (
    DailyAverageMarketPriceResult,
    ForecastInterval,
    current_market_price_interval,
    daily_average_market_price,
    serialize_market_price_forecast,
    validate_forecast_series,
)
from .forecast_insights import (
    ForecastDirectionInsight,
    ForecastWindowInsight,
    NextInexpensive1hWindowInsight,
    find_cheapest_continuous_window,
    find_next_inexpensive_1h_window,
    find_price_direction,
)
from .nordpool import async_get_nordpool_forecast_intervals_for_date
from .provider import (
    ElectricityProData,
    ElectricityProEntityProvider,
)
from .statistics_engine import (
    CalendarPeriod,
    CumulativeStatistic,
    DailyConsumptionFromTotal,
    DailyPeakSnapshot,
    DailyPeakStatistic,
    StatisticsSnapshot,
)
from .timing_score import (
    TimingBucketAccumulator,
    TimingScoreResult,
    calculate_timing_score,
)
from .workday import async_get_non_working_dates

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1
_ENERGY_THIS_MONTH = "energy_this_month"
_ENERGY_TODAY_FROM_TOTAL = "energy_today_from_total"
_ENERGY_TODAY_SOURCE_ENTITY = "energy_today_source_entity"
_ENERGY_TODAY_PERIOD_COMPLETE = "energy_today_period_complete"
_COST_THIS_MONTH = "cost_this_month"
_COST_THIS_MONTH_UNIT = "cost_this_month_unit"
_PEAK_POWER_TODAY = "peak_power_today"
_TIMING_BUCKETS = "consumption_timing_buckets"
_TIMING_RESULT = "consumption_timing_score_yesterday"
_BASE_LOAD_BUCKETS = "base_load_buckets"
_BASE_LOAD_DAILY_SUMMARIES = "base_load_daily_summaries"
_ADAPTIVE_PRICE_HISTORY = "adaptive_price_history"
_KWH_PER_WH = Decimal("0.001")
_FORECAST_REFRESH_INTERVAL = timedelta(minutes=15)
_WORKDAY_REFRESH_INTERVAL = timedelta(hours=6)
_HOLIDAY_LOOKAHEAD_DAYS = 32
_TOMORROW_PUBLICATION_HOUR = 13
_TIMING_TICK_INTERVAL = timedelta(minutes=5)
_TIMING_POWER_MAX_HOLD = timedelta(minutes=10)
_ADAPTIVE_SCOPE_CONFIG_KEYS = (
    CONF_PRICE_ENTITY,
    CONF_PRICING_STRATEGY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICE_COMPLETENESS,
    CONF_SUPPLIER_MARKUP_PER_KWH,
    CONF_ENERGY_TAX_PER_KWH,
    CONF_GRID_FEE_PER_KWH,
    CONF_GRID_FEE_HIGH_PER_KWH,
    CONF_GRID_FEE_HIGH_START,
    CONF_GRID_FEE_HIGH_END,
    CONF_GRID_FEE_HIGH_SEASON_START,
    CONF_GRID_FEE_HIGH_SEASON_END,
    CONF_GRID_FEE_WORKDAY_ENTITY,
)


class ElectricityProCoordinator(
    DataUpdateCoordinator[ElectricityProData]
):
    """Coordinate Electricity Pro provider updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )

        self._entry = entry
        self._local_timezone = ZoneInfo(hass.config.time_zone)
        self._provider = ElectricityProEntityProvider(
            hass=hass,
            entry=entry,
        )
        self._energy_this_month = CumulativeStatistic(CalendarPeriod.MONTH)
        self._energy_today_from_total = DailyConsumptionFromTotal()
        self._energy_today_period_complete = False
        self._cost_this_month = CumulativeStatistic(CalendarPeriod.MONTH)
        self._peak_power_today = DailyPeakStatistic()
        self._timing_buckets = TimingBucketAccumulator(self._local_timezone)
        self._timing_result_date: date | None = None
        self._timing_result: TimingScoreResult | None = None
        self._timing_last_time: datetime | None = None
        self._timing_power: Decimal | None = None
        self._timing_power_observed_at: datetime | None = None
        self._timing_effective_price: Decimal | None = None
        self._base_load_buckets = BaseLoadBucketAccumulator(self._local_timezone)
        self._base_load_daily_summaries: dict[date, DailyBaseLoadSummary] = {}
        self._base_load_result: BaseLoadEstimateResult | None = None
        self._base_load_last_time: datetime | None = None
        self._base_load_power: Decimal | None = None
        self._base_load_power_observed_at: datetime | None = None
        self._adaptive_price_history = AdaptivePriceHistory(self._local_timezone)
        self._adaptive_price_last_time: datetime | None = None
        self._adaptive_price: Decimal | None = None
        self._adaptive_price_scope: AdaptivePriceScope | None = None
        self._adaptive_tariff_signature = _adaptive_tariff_signature(entry)
        self._cost_this_month_unit: str | None = None
        self._forecast_intervals_by_date: dict[date, list[ForecastInterval]] = {}
        self._forecast_intervals: list[ForecastInterval] = []
        self._cheapest_1h_window: ForecastWindowInsight | None = None
        self._cheapest_2h_window: ForecastWindowInsight | None = None
        self._cheapest_3h_window: ForecastWindowInsight | None = None
        self._next_inexpensive_1h_window: NextInexpensive1hWindowInsight | None = None
        self._price_direction: ForecastDirectionInsight | None = None
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry.entry_id}.statistics",
        )

    async def async_start(self) -> None:
        """Start listening for provider source changes."""
        await self._async_restore_statistics()
        self._entry.async_on_unload(self._save_statistics)
        local_today = dt_util.now().astimezone(self._local_timezone).date()
        self._finalize_restored_timing_days(local_today)
        self._finalize_restored_base_load_days(local_today)
        cancel_daily_rollover = async_track_time_change(
            self.hass,
            self._async_daily_rollover,
            hour=0,
            minute=0,
            second=0,
        )
        self._entry.async_on_unload(cancel_daily_rollover)
        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP,
            lambda event: cancel_daily_rollover(),
        )
        self._entry.async_on_unload(
            async_track_time_interval(
                self.hass,
                self._async_timing_tick,
                _TIMING_TICK_INTERVAL,
                cancel_on_shutdown=True,
            )
        )
        if self._workday_entity_id is not None:
            await self._async_refresh_non_working_dates(dt_util.now())
            self._entry.async_on_unload(
                async_track_time_interval(
                    self.hass,
                    self._async_workday_tick,
                    _WORKDAY_REFRESH_INTERVAL,
                    cancel_on_shutdown=True,
                )
            )
        if self._forecast_configured:
            now = dt_util.now()
            await self._async_refresh_forecast_intervals(now.date())
            if now.hour >= _TOMORROW_PUBLICATION_HOUR:
                await self._async_refresh_forecast_intervals(
                    now.date() + timedelta(days=1)
                )

            self._entry.async_on_unload(
                async_track_time_interval(
                    self.hass,
                    self._async_forecast_tick,
                    _FORECAST_REFRESH_INTERVAL,
                    cancel_on_shutdown=True,
                )
            )

        self._entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                self._provider.source_entity_ids,
                self._async_source_changed,
            )
        )

        self.async_set_updated_data(self._read(power_observed=True))

    @property
    def timing_score_yesterday(self) -> tuple[date, TimingScoreResult] | None:
        """Return the most recently finalized timing score."""
        if self._timing_result_date is None or self._timing_result is None:
            return None
        return self._timing_result_date, self._timing_result

    @property
    def estimated_base_load(self) -> BaseLoadEstimateResult | None:
        """Return the latest rolling base-load calculation."""
        return self._base_load_result

    @property
    def average_power_today(self) -> tuple[date, AveragePowerResult] | None:
        """Return the duration-weighted mean for the elapsed local day."""
        now = dt_util.now().astimezone(self._local_timezone)
        period_start = now.date()
        day_start = datetime.combine(
            period_start,
            datetime.min.time(),
            tzinfo=self._local_timezone,
        )
        elapsed_duration = now.astimezone(UTC) - day_start.astimezone(UTC)
        if elapsed_duration <= timedelta(0):
            return None
        return period_start, calculate_average_power(
            self._base_load_buckets.intervals_for_date(period_start),
            elapsed_duration=elapsed_duration,
            longest_uncovered_gap=self._base_load_buckets.longest_uncovered_gap(
                period_start,
                day_start=day_start,
                day_end=now,
            ),
            bidirectional_power_observed=(
                self._base_load_buckets.bidirectional_observed(period_start)
            ),
        )

    @property
    def adaptive_price_history(self) -> AdaptivePriceHistory:
        """Return the bounded persisted Effective Price history."""
        return self._adaptive_price_history

    @property
    def adaptive_price_scope(self) -> AdaptivePriceScope | None:
        """Return the compatibility scope of the current Effective Price."""
        return self._adaptive_price_scope

    @callback
    def _save_statistics(self) -> None:
        """Schedule an immediate final save when the config entry unloads."""
        self._store.async_delay_save(self._statistics_data, delay=0)

    async def _async_timing_tick(self, now: datetime) -> None:
        """Close timing-history segments while source states remain quiet."""
        self.async_set_updated_data(self._read())

    @callback
    def _async_daily_rollover(self, now: datetime) -> None:
        """Finalize timing history and clear daily state at local midnight."""
        local_now = now.astimezone(self._local_timezone)
        data = self._provider.read()
        energy_kwh = _energy_in_kwh(
            data.current_energy,
            data.current_energy_unit,
        )
        if self._provider.energy_source_is_lifetime_total:
            self._energy_today_from_total.reset(energy_kwh, local_now)
            self._energy_today_period_complete = energy_kwh is not None
        self._update_timing_history(data, local_now, power_observed=False)
        self._update_base_load_history(data, local_now, power_observed=False)
        self._update_adaptive_price_history(data, local_now)
        self._finalize_timing_day(local_now.date() - timedelta(days=1))
        self._finalize_base_load_day(local_now.date() - timedelta(days=1))
        self._timing_buckets.retain_dates({local_now.date()})
        self._base_load_buckets.retain_dates({local_now.date()})
        self._adaptive_price_history.retain_for_date(local_now.date())
        peak_cleared = self._peak_power_today.clear()
        self._store.async_delay_save(self._statistics_data, delay=1)
        if self.data is not None:
            rollover_updates: dict[str, Decimal | datetime | str | None] = {}
            if self._provider.energy_source_is_lifetime_total:
                rollover_updates["current_energy"] = (
                    Decimal(0) if energy_kwh is not None else None
                )
                rollover_updates["current_energy_unit"] = (
                    UnitOfEnergy.KILO_WATT_HOUR
                    if energy_kwh is not None
                    else None
                )
                rollover_updates["energy_today_period_complete"] = (
                    self._energy_today_period_complete
                )
            if peak_cleared:
                rollover_updates["peak_power_today"] = None
                rollover_updates["peak_power_time_today"] = None
            self.async_set_updated_data(
                replace(
                    self.data,
                    **rollover_updates,
                )
            )

    @callback
    def _async_source_changed(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle a configured source entity change."""
        self.async_set_updated_data(
            self._read(
                power_observed=(
                    event.data["entity_id"] == self._provider.power_entity_id
                )
            )
        )

    @property
    def forecast_intervals(self) -> list[ForecastInterval]:
        """Return the currently stored forecast intervals."""
        return self._forecast_intervals

    @property
    def current_market_price_interval(self) -> ForecastInterval | None:
        """Return the normalized market-price interval covering now."""
        return current_market_price_interval(
            self._forecast_intervals,
            now=dt_util.now(),
        )

    @property
    def average_market_price_today(self) -> DailyAverageMarketPriceResult | None:
        """Return the complete local day's duration-weighted market average."""
        local_now = dt_util.now().astimezone(self._local_timezone)
        period_start = datetime.combine(
            local_now.date(),
            datetime.min.time(),
            tzinfo=self._local_timezone,
        )
        period_end = datetime.combine(
            local_now.date() + timedelta(days=1),
            datetime.min.time(),
            tzinfo=self._local_timezone,
        )
        return daily_average_market_price(
            self._forecast_intervals,
            period_start=period_start,
            period_end=period_end,
        )

    @property
    def market_price_forecast_response(self) -> dict[str, Any]:
        """Return the serialized bounded market-price forecast series."""
        return serialize_market_price_forecast(self._forecast_intervals)

    @property
    def cheapest_1h_window(self) -> ForecastWindowInsight | None:
        """Return the cheapest upcoming one-hour forecast window."""
        return self._cheapest_1h_window

    @property
    def cheapest_2h_window(self) -> ForecastWindowInsight | None:
        """Return the cheapest upcoming two-hour forecast window."""
        return self._cheapest_2h_window

    @property
    def cheapest_3h_window(self) -> ForecastWindowInsight | None:
        """Return the cheapest upcoming three-hour forecast window."""
        return self._cheapest_3h_window

    @property
    def next_inexpensive_1h_window(self) -> NextInexpensive1hWindowInsight | None:
        """Return the next upcoming 1-hour window at or below the good price threshold."""
        return self._next_inexpensive_1h_window

    @property
    def price_direction(self) -> ForecastDirectionInsight | None:
        """Return the currently calculated near-term price direction."""
        return self._price_direction

    @property
    def _forecast_configured(self) -> bool:
        """Return whether native Nord Pool forecast retrieval is configured."""
        config_entry_id = self._entry.options.get(
            CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
            self._entry.data.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY),
        )
        return isinstance(config_entry_id, str) and bool(config_entry_id)

    @property
    def _workday_entity_id(self) -> str | None:
        """Return the configured Home Assistant Workday entity ID."""
        entity_id = self._entry.options.get(
            CONF_GRID_FEE_WORKDAY_ENTITY,
            self._entry.data.get(CONF_GRID_FEE_WORKDAY_ENTITY),
        )
        return entity_id if isinstance(entity_id, str) and entity_id else None

    async def _async_workday_tick(self, now: datetime) -> None:
        """Refresh non-working dates and dependent live/forecast values."""
        await self._async_refresh_non_working_dates(now)
        self._recalculate_forecast_insights()
        self.async_set_updated_data(self._read())

    async def _async_refresh_non_working_dates(self, now: datetime) -> bool:
        """Refresh the cached local dates excluded from high grid tariffs."""
        entity_id = self._workday_entity_id
        if entity_id is None:
            self._provider.set_grid_tariff_excluded_dates(frozenset())
            return True

        local_today = now.astimezone(self._local_timezone).date()
        start = local_today - timedelta(days=1)
        end = local_today + timedelta(days=_HOLIDAY_LOOKAHEAD_DAYS)
        try:
            excluded_dates = await async_get_non_working_dates(
                self.hass,
                entity_id=entity_id,
                start=start,
                end=end,
            )
        except (HomeAssistantError, TimeoutError, ValueError) as err:
            _LOGGER.warning(
                "Unable to refresh grid-tariff Workday source %s; "
                "using the ordinary weekday schedule: %s",
                entity_id,
                err,
            )
            self._provider.set_grid_tariff_excluded_dates(frozenset())
            return False

        self._provider.set_grid_tariff_excluded_dates(excluded_dates)
        return True

    async def _async_forecast_tick(self, now: datetime) -> None:
        """Refresh published dates and expire cached insights as time advances."""
        local_now = dt_util.as_local(now)
        today = local_now.date()

        stale_dates = [
            stored_date
            for stored_date in self._forecast_intervals_by_date
            if stored_date < today
        ]
        for stale_date in stale_dates:
            del self._forecast_intervals_by_date[stale_date]

        if today not in self._forecast_intervals_by_date:
            await self._async_refresh_forecast_intervals(today)

        tomorrow = today + timedelta(days=1)
        if (
            local_now.hour >= _TOMORROW_PUBLICATION_HOUR
            and tomorrow not in self._forecast_intervals_by_date
        ):
            await self._async_refresh_forecast_intervals(tomorrow)

        self._rebuild_forecast_intervals()
        self._recalculate_forecast_insights()
        if self.data is not None:
            self.async_set_updated_data(self.data)

    async def _async_refresh_forecast_intervals(self, target_date: date) -> bool:
        """Retrieve forecast intervals for one date and store them."""
        try:
            nordpool_config_entry_id = self._entry.options.get(
                CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
                self._entry.data.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY),
            )
            if not isinstance(nordpool_config_entry_id, str) or not nordpool_config_entry_id:
                raise ValueError("Forecast Nord Pool config entry is required")

            intervals = await async_get_nordpool_forecast_intervals_for_date(
                self.hass,
                config_entry_id=nordpool_config_entry_id,
                target_date=target_date,
                area=self._entry.options.get(
                    CONF_FORECAST_PRICE_AREA,
                    self._entry.data.get(CONF_FORECAST_PRICE_AREA),
                ),
            )
            if not intervals:
                raise ValueError("Nord Pool returned no forecast intervals")
        except (HomeAssistantError, TimeoutError, ValueError) as err:
            _LOGGER.warning(
                "Unable to refresh Nord Pool forecast intervals for %s: %s",
                target_date,
                err,
            )
            self._forecast_intervals_by_date.pop(target_date, None)
            self._rebuild_forecast_intervals()
            self._recalculate_forecast_insights()
            return False

        self._forecast_intervals_by_date[target_date] = intervals
        self._rebuild_forecast_intervals()
        self._recalculate_forecast_insights()
        return True

    def _rebuild_forecast_intervals(self) -> None:
        """Build one ordered forecast sequence from the cached delivery dates."""
        try:
            self._forecast_intervals = validate_forecast_series(
                interval
                for intervals in self._forecast_intervals_by_date.values()
                for interval in intervals
            )
        except ValueError as err:
            _LOGGER.warning("Unable to publish market-price forecast series: %s", err)
            self._forecast_intervals = []

    async def _async_restore_statistics(self) -> None:
        """Restore persisted statistics state when available."""
        stored = await self._store.async_load()
        if stored is None:
            return

        if _ENERGY_THIS_MONTH in stored:
            try:
                snapshot = StatisticsSnapshot.from_dict(stored[_ENERGY_THIS_MONTH])
            except ValueError:
                _LOGGER.warning("Ignoring invalid persisted energy statistics state")
            else:
                self._energy_this_month = CumulativeStatistic(
                    CalendarPeriod.MONTH,
                    snapshot,
                )

        if (
            self._provider.energy_source_is_lifetime_total
            and stored.get(_ENERGY_TODAY_SOURCE_ENTITY)
            == self._provider.energy_entity_id
            and _ENERGY_TODAY_FROM_TOTAL in stored
        ):
            try:
                snapshot = StatisticsSnapshot.from_dict(
                    stored[_ENERGY_TODAY_FROM_TOTAL]
                )
            except ValueError:
                _LOGGER.warning(
                    "Ignoring invalid persisted lifetime energy baseline"
                )
            else:
                self._energy_today_from_total = DailyConsumptionFromTotal(snapshot)
                self._energy_today_period_complete = stored.get(
                    _ENERGY_TODAY_PERIOD_COMPLETE
                ) is True

        cost_unit = stored.get(_COST_THIS_MONTH_UNIT)
        if _COST_THIS_MONTH in stored and isinstance(cost_unit, str) and cost_unit:
            try:
                snapshot = StatisticsSnapshot.from_dict(stored[_COST_THIS_MONTH])
            except ValueError:
                _LOGGER.warning("Ignoring invalid persisted cost statistics state")
            else:
                self._cost_this_month = CumulativeStatistic(
                    CalendarPeriod.MONTH,
                    snapshot,
                )
                self._cost_this_month_unit = cost_unit

        if _PEAK_POWER_TODAY in stored:
            try:
                snapshot = DailyPeakSnapshot.from_dict(stored[_PEAK_POWER_TODAY])
            except ValueError:
                _LOGGER.warning("Ignoring invalid persisted daily peak state")
            else:
                local_today = dt_util.now().astimezone(self._local_timezone).date()
                if snapshot.period_start == local_today:
                    self._peak_power_today = DailyPeakStatistic(snapshot)

        if _TIMING_BUCKETS in stored:
            try:
                self._timing_buckets = TimingBucketAccumulator.from_dict(
                    self._local_timezone,
                    stored[_TIMING_BUCKETS],
                )
            except ValueError:
                _LOGGER.warning("Ignoring invalid persisted timing bucket history")

        timing_result = stored.get(_TIMING_RESULT)
        if isinstance(timing_result, dict):
            try:
                self._timing_result_date = date.fromisoformat(
                    timing_result["period_start"]
                )
                self._timing_result = TimingScoreResult.from_dict(
                    timing_result["result"]
                )
            except (KeyError, TypeError, ValueError):
                self._timing_result_date = None
                self._timing_result = None
                _LOGGER.warning("Ignoring invalid persisted timing score result")

        if _BASE_LOAD_BUCKETS in stored:
            try:
                self._base_load_buckets = BaseLoadBucketAccumulator.from_dict(
                    self._local_timezone,
                    stored[_BASE_LOAD_BUCKETS],
                )
            except ValueError:
                _LOGGER.warning("Ignoring invalid persisted base-load bucket history")

        summaries = stored.get(_BASE_LOAD_DAILY_SUMMARIES)
        if isinstance(summaries, list):
            try:
                restored_summaries = tuple(
                    DailyBaseLoadSummary.from_dict(item) for item in summaries
                )
                if len({item.period_start for item in restored_summaries}) != len(
                    restored_summaries
                ):
                    raise ValueError
            except (TypeError, ValueError):
                _LOGGER.warning("Ignoring invalid persisted base-load summaries")
            else:
                self._base_load_daily_summaries = {
                    item.period_start: item for item in restored_summaries
                }

        if _ADAPTIVE_PRICE_HISTORY in stored:
            try:
                self._adaptive_price_history = AdaptivePriceHistory.from_dict(
                    self._local_timezone,
                    stored[_ADAPTIVE_PRICE_HISTORY],
                )
            except ValueError:
                _LOGGER.warning("Ignoring invalid persisted adaptive price history")

    @callback
    def _read(self, *, power_observed: bool = False) -> ElectricityProData:
        """Read provider data and update derived statistics."""
        data = self._provider.read()
        source_energy_kwh = _energy_in_kwh(
            data.current_energy,
            data.current_energy_unit,
        )

        now = dt_util.now().astimezone(self._local_timezone)
        updates: dict[str, Decimal | datetime | str | None] = {}
        should_save = False

        if self._provider.energy_source_is_lifetime_total:
            if source_energy_kwh is None:
                energy_kwh = None
                updates["current_energy"] = None
                updates["current_energy_unit"] = None
            else:
                previous_snapshot = self._energy_today_from_total.snapshot
                if (
                    previous_snapshot is None
                    or previous_snapshot.period_start != now.date()
                ):
                    self._energy_today_period_complete = False
                energy_kwh = self._energy_today_from_total.update(
                    source_energy_kwh,
                    now,
                )
                if self._energy_today_from_total.source_reset_detected:
                    self._energy_today_period_complete = False
                updates["current_energy"] = energy_kwh
                updates["current_energy_unit"] = UnitOfEnergy.KILO_WATT_HOUR
                should_save = True
            updates["energy_today_period_complete"] = (
                self._energy_today_period_complete
            )
        else:
            energy_kwh = source_energy_kwh

        should_save |= self._update_timing_history(
            data,
            now,
            power_observed=power_observed,
        )
        should_save |= self._update_base_load_history(
            data,
            now,
            power_observed=power_observed,
        )
        should_save |= self._update_adaptive_price_history(data, now)

        if data.current_power is not None and data.current_power >= 0:
            should_save |= self._peak_power_today.update(data.current_power, now)
        peak_snapshot = self._peak_power_today.snapshot
        updates["peak_power_today"] = (
            peak_snapshot.peak_power_w if peak_snapshot is not None else None
        )
        updates["peak_power_time_today"] = (
            peak_snapshot.peak_time if peak_snapshot is not None else None
        )

        if energy_kwh is None:
            updates["energy_this_month"] = None
            updates["energy_this_month_unit"] = None
        else:
            updates["energy_this_month"] = self._energy_this_month.update(
                energy_kwh,
                now,
            )
            updates["energy_this_month_unit"] = UnitOfEnergy.KILO_WATT_HOUR
            should_save = True

        cost = data.accumulated_cost_today
        cost_unit = data.accumulated_cost_today_unit
        if cost is None or cost_unit is None:
            updates["cost_this_month"] = None
            updates["cost_this_month_unit"] = None
        else:
            if (
                self._cost_this_month_unit is not None
                and self._cost_this_month_unit != cost_unit
            ):
                self._cost_this_month = CumulativeStatistic(CalendarPeriod.MONTH)
            self._cost_this_month_unit = cost_unit
            if self._cost_this_month.snapshot is None:
                self._cost_this_month = CumulativeStatistic(
                    CalendarPeriod.MONTH,
                    StatisticsSnapshot(
                        period_start=CalendarPeriod.MONTH.start(now),
                        last_value=cost,
                        value=cost,
                    ),
                )
            updates["cost_this_month"] = self._cost_this_month.update(cost, now)
            updates["cost_this_month_unit"] = cost_unit
            should_save = True

        monthly_cost = updates.get("cost_this_month")
        monthly_cost_unit = updates.get("cost_this_month_unit")
        fixed_fee = data.fixed_supplier_fee_this_month
        fixed_fee_unit = (
            monthly_cost_unit
            if isinstance(monthly_cost_unit, str)
            else _currency_from_price_unit(data.current_price_unit)
        )
        updates["fixed_supplier_fee_this_month_unit"] = (
            fixed_fee_unit if fixed_fee is not None else None
        )
        updates["fixed_grid_fee_this_month_unit"] = (
            fixed_fee_unit if data.fixed_grid_fee_this_month is not None else None
        )
        if (
            isinstance(monthly_cost, Decimal)
            and fixed_fee is not None
            and fixed_fee_unit is not None
        ):
            updates["total_supplier_cost_this_month"] = monthly_cost + fixed_fee
            updates["total_supplier_cost_this_month_unit"] = fixed_fee_unit
        else:
            updates["total_supplier_cost_this_month"] = None
            updates["total_supplier_cost_this_month_unit"] = None

        if should_save:
            self._store.async_delay_save(self._statistics_data, delay=1)

        return replace(data, **updates)

    def _update_timing_history(
        self,
        data: ElectricityProData,
        now: datetime,
        *,
        power_observed: bool,
    ) -> bool:
        """Integrate the previous valid observation up to the current time."""
        bucket_closed = False
        if (
            self._timing_last_time is not None
            and self._timing_power is not None
            and self._timing_power_observed_at is not None
            and self._timing_effective_price is not None
        ):
            valid_end = min(
                now,
                self._timing_power_observed_at + _TIMING_POWER_MAX_HOLD,
            )
            if valid_end > self._timing_last_time:
                bucket_closed = (
                    int(self._timing_last_time.timestamp()) // (15 * 60)
                    != int(valid_end.timestamp()) // (15 * 60)
                )
                self._timing_buckets.add_segment(
                    start=self._timing_last_time,
                    end=valid_end,
                    power_w=self._timing_power,
                    effective_price=self._timing_effective_price,
                )

        self._timing_last_time = now
        if power_observed:
            self._timing_power = (
                data.current_power
                if data.current_power is not None and data.current_power >= 0
                else None
            )
            self._timing_power_observed_at = (
                now if self._timing_power is not None else None
            )
        self._timing_effective_price = calculate_declared_effective_price(
            data.current_price,
            data.pricing_metadata,
            data.grid_fee_per_kwh,
            data.energy_tax_per_kwh,
            data.supplier_markup_per_kwh,
        )
        return bucket_closed

    def _update_base_load_history(
        self,
        data: ElectricityProData,
        now: datetime,
        *,
        power_observed: bool,
    ) -> bool:
        """Integrate power-only history independently of price availability."""
        bucket_closed = False
        if (
            self._base_load_last_time is not None
            and self._base_load_power is not None
            and self._base_load_power_observed_at is not None
        ):
            valid_end = min(
                now,
                self._base_load_power_observed_at + _TIMING_POWER_MAX_HOLD,
            )
            if valid_end > self._base_load_last_time:
                bucket_closed = (
                    int(self._base_load_last_time.timestamp()) // (15 * 60)
                    != int(valid_end.timestamp()) // (15 * 60)
                )
                self._base_load_buckets.add_segment(
                    start=self._base_load_last_time,
                    end=valid_end,
                    power_w=self._base_load_power,
                )

        self._base_load_last_time = now
        if power_observed:
            self._base_load_power = (
                Decimal(-1)
                if data.current_power_bidirectional
                else data.current_power
            )
            self._base_load_power_observed_at = (
                now
                if data.current_power is not None
                or data.current_power_bidirectional
                else None
            )
        return bucket_closed

    def _update_adaptive_price_history(
        self,
        data: ElectricityProData,
        now: datetime,
    ) -> bool:
        """Integrate compatible Effective Price into bounded hourly history."""
        hour_closed = False
        if (
            self._adaptive_price_last_time is not None
            and self._adaptive_price is not None
            and self._adaptive_price_scope is not None
            and now.astimezone(UTC)
            > self._adaptive_price_last_time.astimezone(UTC)
        ):
            self._adaptive_price_history.ensure_scope(
                self._adaptive_price_scope,
                changed_at=self._adaptive_price_last_time,
            )
            hour_closed = self._adaptive_price_history.add_segment(
                start=self._adaptive_price_last_time,
                end=now,
                effective_price=self._adaptive_price,
            )

        self._adaptive_price_last_time = now
        effective_price = calculate_declared_effective_price(
            data.current_price,
            data.pricing_metadata,
            data.grid_fee_per_kwh,
            data.energy_tax_per_kwh,
            data.supplier_markup_per_kwh,
        )
        scope = self._adaptive_scope(data)
        scope_changed = False
        if effective_price is not None and scope is not None:
            scope_changed = self._adaptive_price_history.ensure_scope(
                scope,
                changed_at=now,
            )
            self._adaptive_price = effective_price
            self._adaptive_price_scope = scope
        else:
            self._adaptive_price = None
            self._adaptive_price_scope = None
        return hour_closed or scope_changed

    def _adaptive_scope(
        self,
        data: ElectricityProData,
    ) -> AdaptivePriceScope | None:
        """Return a complete compatibility scope for the current price."""
        currency = _currency_from_price_unit(data.current_price_unit)
        if currency is None or data.pricing_metadata is None:
            return None
        effective_metadata = effective_price_metadata(
            data.pricing_metadata,
            data.grid_fee_per_kwh,
            data.energy_tax_per_kwh,
            data.supplier_markup_per_kwh,
        )
        scope = AdaptivePriceScope.from_metadata(
            currency=currency,
            unit=f"{currency}/kWh",
            metadata=effective_metadata,
            tariff_signature=self._adaptive_tariff_signature,
        )
        return scope if scope.is_comparable else None

    def _finalize_restored_timing_days(self, local_today: date) -> None:
        """Finalize a retained previous day after a restart across midnight."""
        previous_day = local_today - timedelta(days=1)
        if self._timing_buckets.intervals_for_date(previous_day):
            self._finalize_timing_day(previous_day)
        self._timing_buckets.retain_dates({local_today})

    def _finalize_timing_day(self, period_start: date) -> None:
        """Calculate and retain one completed local-day timing result."""
        day_start = datetime.combine(
            period_start,
            datetime.min.time(),
            tzinfo=self._local_timezone,
        )
        day_end = datetime.combine(
            period_start + timedelta(days=1),
            datetime.min.time(),
            tzinfo=self._local_timezone,
        )
        period_duration = day_end.astimezone(UTC) - day_start.astimezone(UTC)
        self._timing_result = calculate_timing_score(
            self._timing_buckets.intervals_for_date(period_start),
            period_duration=period_duration,
            longest_uncovered_gap=self._timing_buckets.longest_uncovered_gap(
                period_start,
                day_start=day_start,
                day_end=day_end,
            ),
            bidirectional_power_observed=(
                self._base_load_buckets.bidirectional_observed(period_start)
            ),
        )
        self._timing_result_date = period_start

    def _finalize_restored_base_load_days(self, local_today: date) -> None:
        """Finalize retained power history after a restart across midnight."""
        previous_day = local_today - timedelta(days=1)
        if (
            self._base_load_buckets.intervals_for_date(previous_day)
            or self._base_load_buckets.bidirectional_observed(previous_day)
        ):
            self._finalize_base_load_day(previous_day)
        self._base_load_buckets.retain_dates({local_today})
        self._recalculate_base_load(previous_day)

    def _finalize_base_load_day(self, period_start: date) -> None:
        """Calculate and retain one completed local-day base-load summary."""
        day_start = datetime.combine(
            period_start,
            datetime.min.time(),
            tzinfo=self._local_timezone,
        )
        day_end = datetime.combine(
            period_start + timedelta(days=1),
            datetime.min.time(),
            tzinfo=self._local_timezone,
        )
        summary = calculate_daily_base_load(
            period_start,
            self._base_load_buckets.intervals_for_date(period_start),
            period_duration=day_end.astimezone(UTC) - day_start.astimezone(UTC),
            longest_uncovered_gap=self._base_load_buckets.longest_uncovered_gap(
                period_start,
                day_start=day_start,
                day_end=day_end,
            ),
            bidirectional_power_observed=(
                self._base_load_buckets.bidirectional_observed(period_start)
            ),
        )
        self._base_load_daily_summaries[period_start] = summary
        self._recalculate_base_load(period_start)

    def _recalculate_base_load(self, window_end: date) -> None:
        """Refresh the rolling estimate and enforce seven-day retention."""
        window_start = window_end - timedelta(days=6)
        self._base_load_daily_summaries = {
            stored_date: summary
            for stored_date, summary in self._base_load_daily_summaries.items()
            if window_start <= stored_date <= window_end
        }
        self._base_load_result = calculate_base_load_estimate(
            tuple(self._base_load_daily_summaries.values()),
            window_end=window_end,
        )

    def _recalculate_forecast_insights(self) -> None:
        """Recalculate cached forecast insight results from current intervals."""
        now = dt_util.now()
        provider_data = self._provider.read()
        self._cheapest_1h_window = find_cheapest_continuous_window(
            self._forecast_intervals,
            now=now,
            duration_minutes=60,
            grid_fee_per_kwh=provider_data.grid_fee_per_kwh,
            grid_fee_at=self._provider.grid_fee_at,
            energy_tax_per_kwh=provider_data.energy_tax_per_kwh,
            supplier_markup_per_kwh=provider_data.supplier_markup_per_kwh,
        )
        self._cheapest_2h_window = find_cheapest_continuous_window(
            self._forecast_intervals,
            now=now,
            duration_minutes=120,
            grid_fee_per_kwh=provider_data.grid_fee_per_kwh,
            grid_fee_at=self._provider.grid_fee_at,
            energy_tax_per_kwh=provider_data.energy_tax_per_kwh,
            supplier_markup_per_kwh=provider_data.supplier_markup_per_kwh,
        )
        self._cheapest_3h_window = find_cheapest_continuous_window(
            self._forecast_intervals,
            now=now,
            duration_minutes=180,
            grid_fee_per_kwh=provider_data.grid_fee_per_kwh,
            grid_fee_at=self._provider.grid_fee_at,
            energy_tax_per_kwh=provider_data.energy_tax_per_kwh,
            supplier_markup_per_kwh=provider_data.supplier_markup_per_kwh,
        )
        threshold = provider_data.good_price_threshold
        forecast_metadata = (
            self._forecast_intervals[0].pricing_metadata
            if self._forecast_intervals
            else None
        )
        prices_are_comparable = bool(
            forecast_metadata is not None
            and forecast_metadata.is_complete
            and provider_data.pricing_metadata is not None
            and provider_data.pricing_metadata.is_complete
            and forecast_metadata.scope == provider_data.pricing_metadata.scope
        )
        self._next_inexpensive_1h_window = (
            find_next_inexpensive_1h_window(
                self._forecast_intervals,
                now=now,
                threshold=threshold,
                grid_fee_per_kwh=provider_data.grid_fee_per_kwh,
                grid_fee_at=self._provider.grid_fee_at,
                energy_tax_per_kwh=provider_data.energy_tax_per_kwh,
                supplier_markup_per_kwh=provider_data.supplier_markup_per_kwh,
                price_is_comparable=prices_are_comparable,
            )
            if threshold is not None
            else None
        )
        self._price_direction = find_price_direction(
            self._forecast_intervals,
            now=now,
            grid_fee_per_kwh=provider_data.grid_fee_per_kwh,
            grid_fee_at=self._provider.grid_fee_at,
            energy_tax_per_kwh=provider_data.energy_tax_per_kwh,
            supplier_markup_per_kwh=provider_data.supplier_markup_per_kwh,
        )

    @callback
    def _statistics_data(self) -> dict[str, Any]:
        """Return serializable statistics state."""
        data: dict[str, Any] = {}
        if (snapshot := self._energy_this_month.snapshot) is not None:
            data[_ENERGY_THIS_MONTH] = snapshot.as_dict()
        if (
            self._provider.energy_source_is_lifetime_total
            and (snapshot := self._energy_today_from_total.snapshot) is not None
            and self._provider.energy_entity_id is not None
        ):
            data[_ENERGY_TODAY_FROM_TOTAL] = snapshot.as_dict()
            data[_ENERGY_TODAY_SOURCE_ENTITY] = self._provider.energy_entity_id
            data[_ENERGY_TODAY_PERIOD_COMPLETE] = (
                self._energy_today_period_complete
            )
        if (
            (snapshot := self._cost_this_month.snapshot) is not None
            and self._cost_this_month_unit is not None
        ):
            data[_COST_THIS_MONTH] = snapshot.as_dict()
            data[_COST_THIS_MONTH_UNIT] = self._cost_this_month_unit
        if (snapshot := self._peak_power_today.snapshot) is not None:
            data[_PEAK_POWER_TODAY] = snapshot.as_dict()
        data[_TIMING_BUCKETS] = self._timing_buckets.as_dict()
        if self._timing_result_date is not None and self._timing_result is not None:
            data[_TIMING_RESULT] = {
                "period_start": self._timing_result_date.isoformat(),
                "result": self._timing_result.as_dict(),
            }
        data[_BASE_LOAD_BUCKETS] = self._base_load_buckets.as_dict()
        data[_BASE_LOAD_DAILY_SUMMARIES] = [
            summary.as_dict()
            for _, summary in sorted(self._base_load_daily_summaries.items())
        ]
        data[_ADAPTIVE_PRICE_HISTORY] = self._adaptive_price_history.as_dict()
        return data


def _energy_in_kwh(
    value: Decimal | None,
    unit: str | None,
) -> Decimal | None:
    """Normalize a cumulative energy measurement to kilowatt-hours."""
    if value is None:
        return None
    if unit == UnitOfEnergy.KILO_WATT_HOUR:
        return value
    if unit == UnitOfEnergy.WATT_HOUR:
        return value * _KWH_PER_WH
    return None


def _currency_from_price_unit(unit: str | None) -> str | None:
    """Return a currency from a currency-per-kWh unit."""
    if unit is None:
        return None
    for suffix in ("/kWh", "/kwh"):
        if unit.endswith(suffix):
            currency = unit[: -len(suffix)].strip()
            return currency or None
    return None


def _adaptive_tariff_signature(entry: ConfigEntry) -> str:
    """Return a stable fingerprint for price-affecting configuration."""
    settings = {**entry.data, **entry.options}
    relevant_settings = {
        key: settings[key]
        for key in _ADAPTIVE_SCOPE_CONFIG_KEYS
        if key in settings
    }
    serialized = json.dumps(
        relevant_settings,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
