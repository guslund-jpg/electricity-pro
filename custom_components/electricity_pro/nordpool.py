"""Nord Pool forecast normalization helpers."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .forecast import ForecastInterval

_MWH_TO_KWH = Decimal("0.001")
_NORDPOOL_GET_PRICES_FOR_DATE = "get_prices_for_date"


def normalize_nordpool_forecast_intervals(
    area: str,
    intervals: list[dict[str, str | int | float]],
    currency: str,
    published_at: datetime | None = None,
) -> list[ForecastInterval]:
    """Normalize Nord Pool action response intervals into forecast intervals."""
    if not area:
        raise ValueError("Nord Pool area is required")

    if not currency:
        raise ValueError("Nord Pool currency is required")

    normalized: list[ForecastInterval] = []

    for interval in intervals:
        start_raw = interval.get("start")
        end_raw = interval.get("end")
        price_raw = interval.get("price")

        if not isinstance(start_raw, str) or not isinstance(end_raw, str):
            raise ValueError("Nord Pool intervals must include string start and end")

        if not isinstance(price_raw, int | float):
            raise ValueError("Nord Pool intervals must include numeric price")

        start = dt_util.parse_datetime(start_raw)
        end = dt_util.parse_datetime(end_raw)

        if start is None or end is None:
            raise ValueError("Nord Pool intervals must include valid ISO datetimes")

        normalized.append(
            ForecastInterval(
                start=start,
                end=end,
                market_price=Decimal(str(price_raw)) * _MWH_TO_KWH,
                currency=currency,
                area=area,
                published_at=published_at,
            )
        )

    return sorted(normalized, key=lambda interval: interval.start)

async def async_get_nordpool_forecast_intervals_for_date(
    hass: HomeAssistant,
    *,
    config_entry_id: str,
    target_date: date,
    area: str | None = None,
    currency: str | None = None,
    published_at: datetime | None = None,
) -> list[ForecastInterval]:
    """Retrieve and normalize Nord Pool forecast intervals for one date."""
    nordpool_entry = None
    config_entries = getattr(hass, "config_entries", None)
    if config_entries is not None:
        nordpool_entry = config_entries.async_get_entry(config_entry_id)

    if nordpool_entry is not None:
        configured_areas = nordpool_entry.data.get("areas", [])
        configured_currency = nordpool_entry.data.get("currency")
        if not isinstance(configured_areas, list) or not all(
            isinstance(configured_area, str) for configured_area in configured_areas
        ):
            raise ValueError("Nord Pool config entry has invalid areas")
        if not isinstance(configured_currency, str) or not configured_currency:
            raise ValueError("Nord Pool config entry has invalid currency")

        if len(configured_areas) == 1:
            area = configured_areas[0]
        elif area not in configured_areas:
            raise ValueError(
                "A configured Nord Pool area is required for multi-area entries"
            )
        currency = configured_currency

    service_data: dict[str, Any] = {
        "config_entry": config_entry_id,
        "date": target_date.isoformat(),
    }
    if area is not None:
        service_data["areas"] = [area]

    response = await hass.services.async_call(
        "nordpool",
        _NORDPOOL_GET_PRICES_FOR_DATE,
        service_data,
        blocking=True,
        return_response=True,
    )

    if not isinstance(response, dict):
        raise ValueError("Nord Pool action response must be a mapping")

    if area is None:
        if len(response) != 1:
            raise ValueError(
                "Nord Pool action response must contain exactly one area when no area is requested"
            )
        area, area_intervals = next(iter(response.items()))
    else:
        area_intervals = response.get(area)
        if not isinstance(area_intervals, list):
            raise ValueError(
                "Nord Pool action response must include a list for the requested area"
            )

    if not all(isinstance(interval, dict) for interval in area_intervals):
        raise ValueError("Nord Pool action area payload must contain interval mappings")

    if currency is None:
        raise ValueError(
            "Nord Pool action retrieval requires an explicit currency for normalization"
        )

    return normalize_nordpool_forecast_intervals(
        area=area,
        intervals=area_intervals,
        currency=currency,
        published_at=published_at,
    )
