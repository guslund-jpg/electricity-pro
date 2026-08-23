"""Data coordinator for Electricity Pro."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FORECAST_PRICE_AREA,
    CONF_GRID_FEE_WORKDAY_ENTITY,
    DOMAIN,
)
from .forecast import ForecastInterval
from .forecast_insights import (
    ForecastDirectionInsight,
    ForecastWindowInsight,
    NextInexpensive1hWindowInsight,
    find_cheapest_continuous_window,
    find_next_inexpensive_1h_window,
    find_price_direction,
)
from .workday import async_get_non_working_dates
from .nordpool import async_get_nordpool_forecast_intervals_for_date
from .provider import (
    ElectricityProData,
    ElectricityProEntityProvider,
)
from .statistics_engine import (
    CalendarPeriod,
    CumulativeStatistic,
    StatisticsSnapshot,
)

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1
_ENERGY_THIS_MONTH = "energy_this_month"
_COST_THIS_MONTH = "cost_this_month"
_COST_THIS_MONTH_UNIT = "cost_this_month_unit"
_KWH_PER_WH = Decimal("0.001")
_FORECAST_REFRESH_INTERVAL = timedelta(minutes=15)
_WORKDAY_REFRESH_INTERVAL = timedelta(hours=6)
_HOLIDAY_LOOKAHEAD_DAYS = 32
_TOMORROW_PUBLICATION_HOUR = 13


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
        self._cost_this_month = CumulativeStatistic(CalendarPeriod.MONTH)
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

        self.async_set_updated_data(self._read())

    @callback
    def _async_source_changed(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle a configured source entity change."""
        self.async_set_updated_data(self._read())

    @property
    def forecast_intervals(self) -> list[ForecastInterval]:
        """Return the currently stored forecast intervals."""
        return self._forecast_intervals

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
        unique_intervals = {
            (
                interval.start,
                interval.end,
                interval.currency,
                interval.area,
            ): interval
            for intervals in self._forecast_intervals_by_date.values()
            for interval in intervals
        }
        self._forecast_intervals = sorted(
            unique_intervals.values(),
            key=lambda interval: interval.start,
        )

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

    @callback
    def _read(self) -> ElectricityProData:
        """Read provider data and update derived statistics."""
        data = self._provider.read()
        energy_kwh = _energy_in_kwh(
            data.current_energy,
            data.current_energy_unit,
        )

        now = dt_util.now()
        updates: dict[str, Decimal | str | None] = {}
        should_save = False

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
        )
        self._cheapest_2h_window = find_cheapest_continuous_window(
            self._forecast_intervals,
            now=now,
            duration_minutes=120,
            grid_fee_per_kwh=provider_data.grid_fee_per_kwh,
            grid_fee_at=self._provider.grid_fee_at,
            energy_tax_per_kwh=provider_data.energy_tax_per_kwh,
        )
        self._cheapest_3h_window = find_cheapest_continuous_window(
            self._forecast_intervals,
            now=now,
            duration_minutes=180,
            grid_fee_per_kwh=provider_data.grid_fee_per_kwh,
            grid_fee_at=self._provider.grid_fee_at,
            energy_tax_per_kwh=provider_data.energy_tax_per_kwh,
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
        )

    @callback
    def _statistics_data(self) -> dict[str, Any]:
        """Return serializable statistics state."""
        data: dict[str, Any] = {}
        if (snapshot := self._energy_this_month.snapshot) is not None:
            data[_ENERGY_THIS_MONTH] = snapshot.as_dict()
        if (
            (snapshot := self._cost_this_month.snapshot) is not None
            and self._cost_this_month_unit is not None
        ):
            data[_COST_THIS_MONTH] = snapshot.as_dict()
            data[_COST_THIS_MONTH_UNIT] = self._cost_this_month_unit
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
