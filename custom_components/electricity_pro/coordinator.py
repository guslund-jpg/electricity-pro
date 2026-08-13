"""Data coordinator for Electricity Pro."""

from __future__ import annotations

import logging

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FORECAST_CURRENCY,
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FORECAST_PRICE_AREA,
    DOMAIN,
)
from .forecast import ForecastInterval
from .forecast_insights import (
    ForecastDirectionInsight,
    ForecastWindowInsight,
    find_cheapest_continuous_window,
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
    StatisticsSnapshot,
)

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1
_ENERGY_THIS_MONTH = "energy_this_month"
_COST_THIS_MONTH = "cost_this_month"
_COST_THIS_MONTH_UNIT = "cost_this_month_unit"
_KWH_PER_WH = Decimal("0.001")


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
        self._provider = ElectricityProEntityProvider(
            hass=hass,
            entry=entry,
        )
        self._energy_this_month = CumulativeStatistic(CalendarPeriod.MONTH)
        self._cost_this_month = CumulativeStatistic(CalendarPeriod.MONTH)
        self._cost_this_month_unit: str | None = None
        self._forecast_intervals: list[ForecastInterval] = []
        self._cheapest_1h_window: ForecastWindowInsight | None = None
        self._cheapest_2h_window: ForecastWindowInsight | None = None
        self._cheapest_3h_window: ForecastWindowInsight | None = None
        self._price_direction: ForecastDirectionInsight | None = None
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry.entry_id}.statistics",
        )

    async def async_start(self) -> None:
        """Start listening for provider source changes."""
        await self._async_restore_statistics()
        await self._async_refresh_forecast_intervals(date.today())

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
    def price_direction(self) -> ForecastDirectionInsight | None:
        """Return the currently calculated near-term price direction."""
        return self._price_direction

    async def _async_refresh_forecast_intervals(self, target_date: date) -> None:
        """Retrieve forecast intervals for one date and store them."""
        try:
            nordpool_config_entry_id = self._entry.options.get(
                CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
                self._entry.data.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY),
            )
            if not isinstance(nordpool_config_entry_id, str) or not nordpool_config_entry_id:
                raise ValueError("Forecast Nord Pool config entry is required")

            self._forecast_intervals = await async_get_nordpool_forecast_intervals_for_date(
                self.hass,
                config_entry_id=nordpool_config_entry_id,
                target_date=target_date,
                area=self._entry.options.get(
                    CONF_FORECAST_PRICE_AREA,
                    self._entry.data.get(CONF_FORECAST_PRICE_AREA),
                ),
                currency=self._entry.options.get(
                    CONF_FORECAST_CURRENCY,
                    self._entry.data.get(CONF_FORECAST_CURRENCY),
                ),
                published_at=dt_util.now(),
            )
        except ValueError:
            _LOGGER.warning("Unable to refresh Nord Pool forecast intervals")
            self._forecast_intervals = []

        self._recalculate_forecast_insights()

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
            tax_per_kwh=provider_data.tax_per_kwh,
        )
        self._cheapest_2h_window = find_cheapest_continuous_window(
            self._forecast_intervals,
            now=now,
            duration_minutes=120,
            grid_fee_per_kwh=provider_data.grid_fee_per_kwh,
            tax_per_kwh=provider_data.tax_per_kwh,
        )
        self._cheapest_3h_window = find_cheapest_continuous_window(
            self._forecast_intervals,
            now=now,
            duration_minutes=180,
            grid_fee_per_kwh=provider_data.grid_fee_per_kwh,
            tax_per_kwh=provider_data.tax_per_kwh,
        )
        self._price_direction = find_price_direction(
            self._forecast_intervals,
            now=now,
            grid_fee_per_kwh=provider_data.grid_fee_per_kwh,
            tax_per_kwh=provider_data.tax_per_kwh,
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
