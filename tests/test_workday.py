"""Tests for Home Assistant Workday date normalization."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from custom_components.electricity_pro.workday import (
    async_get_non_working_dates,
)


async def test_non_working_dates_are_excluded(hass, monkeypatch) -> None:
    """The adapter should return dates that Workday reports as non-working."""
    responses = [
        {"binary_sensor.workday": {"workday": True}},
        {"binary_sensor.workday": {"workday": False}},
        {"binary_sensor.workday": {"workday": False}},
    ]
    async_call = AsyncMock(side_effect=responses)
    monkeypatch.setattr(type(hass.services), "async_call", async_call)

    result = await async_get_non_working_dates(
        hass,
        entity_id="binary_sensor.workday",
        start=date(2026, 12, 24),
        end=date(2026, 12, 26),
    )

    assert result == frozenset({date(2026, 12, 25), date(2026, 12, 26)})
    assert async_call.await_args_list[0].kwargs["target"] == {
        "entity_id": "binary_sensor.workday"
    }


async def test_workday_response_requires_selected_entity(hass, monkeypatch) -> None:
    """A missing Workday payload should fail instead of guessing dates."""
    monkeypatch.setattr(type(hass.services), "async_call", AsyncMock(return_value={}))

    with pytest.raises(ValueError, match="workday flag"):
        await async_get_non_working_dates(
            hass,
            entity_id="binary_sensor.workday",
            start=date(2026, 12, 25),
            end=date(2026, 12, 25),
        )


async def test_workday_range_must_be_ordered(hass) -> None:
    """An invalid date range should be rejected before calling Home Assistant."""
    with pytest.raises(ValueError, match="must not precede"):
        await async_get_non_working_dates(
            hass,
            entity_id="binary_sensor.workday",
            start=date(2026, 12, 26),
            end=date(2026, 12, 25),
        )
