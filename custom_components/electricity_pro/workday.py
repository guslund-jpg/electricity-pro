"""Home Assistant Workday adapter for grid-tariff excluded dates."""

from __future__ import annotations

from datetime import date, timedelta

from homeassistant.core import HomeAssistant


async def async_get_non_working_dates(
    hass: HomeAssistant,
    *,
    entity_id: str,
    start: date,
    end: date,
) -> frozenset[date]:
    """Return dates that the selected Workday entity marks as non-working."""
    if end < start:
        raise ValueError("Workday date range end must not precede start")

    excluded: set[date] = set()
    current = start
    while current <= end:
        response = await hass.services.async_call(
            "workday",
            "check_date",
            {"check_date": current.isoformat()},
            target={"entity_id": entity_id},
            blocking=True,
            return_response=True,
        )
        if not isinstance(response, dict):
            raise ValueError("Workday action response must be a mapping")
        payload = response.get(entity_id)
        if not isinstance(payload, dict) or not isinstance(
            payload.get("workday"), bool
        ):
            raise ValueError("Workday action response must include a workday flag")
        if not payload["workday"]:
            excluded.add(current)
        current += timedelta(days=1)

    return frozenset(excluded)
