"""Home Assistant calendar adapter for grid-tariff excluded dates."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util


async def async_get_excluded_dates(
    hass: HomeAssistant,
    *,
    entity_id: str,
    start: datetime,
    end: datetime,
    timezone: ZoneInfo,
) -> frozenset[date]:
    """Return local dates covered by events from a Home Assistant calendar."""
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": entity_id,
            "start_date_time": start,
            "end_date_time": end,
        },
        blocking=True,
        return_response=True,
    )
    if not isinstance(response, dict):
        raise ValueError("Calendar action response must be a mapping")

    payload = response.get(entity_id)
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise ValueError("Calendar action response must include an events list")

    excluded: set[date] = set()
    for event in payload["events"]:
        if not isinstance(event, dict):
            raise ValueError("Calendar events must be mappings")
        excluded.update(_event_dates(event, timezone))
    return frozenset(excluded)


def _event_dates(event: dict[str, Any], timezone: ZoneInfo) -> set[date]:
    """Return local dates touched by one all-day or timed event."""
    start_raw = event.get("start")
    end_raw = event.get("end")
    if not isinstance(start_raw, str) or not isinstance(end_raw, str):
        raise ValueError("Calendar events require string start and end values")

    if "T" not in start_raw and "T" not in end_raw:
        start_date = date.fromisoformat(start_raw)
        end_date = date.fromisoformat(end_raw)
    else:
        start_value = dt_util.parse_datetime(start_raw)
        end_value = dt_util.parse_datetime(end_raw)
        if start_value is None or end_value is None:
            raise ValueError("Calendar events require valid ISO datetimes")
        start_date = start_value.astimezone(timezone).date()
        end_date = (end_value.astimezone(timezone) - timedelta(microseconds=1)).date()

    if end_date < start_date:
        raise ValueError("Calendar event end must not precede start")
    return {
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days)
    } if end_date > start_date else {start_date}
