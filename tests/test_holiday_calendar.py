"""Tests for Home Assistant holiday-calendar normalization."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from custom_components.electricity_pro.holiday_calendar import (
    async_get_excluded_dates,
)

STOCKHOLM = ZoneInfo("Europe/Stockholm")


async def test_calendar_events_become_local_excluded_dates(hass, monkeypatch) -> None:
    """All-day and timed events should produce the local dates they cover."""
    monkeypatch.setattr(
        type(hass.services),
        "async_call",
        AsyncMock(
            return_value={
                "calendar.swedish_holidays": {
                    "events": [
                        {
                            "start": "2026-12-24",
                            "end": "2026-12-26",
                            "summary": "Christmas",
                        },
                        {
                            "start": "2026-12-30T23:30:00+00:00",
                            "end": "2026-12-31T01:00:00+00:00",
                            "summary": "Local New Year closure",
                        },
                    ]
                }
            },
        ),
    )

    result = await async_get_excluded_dates(
        hass,
        entity_id="calendar.swedish_holidays",
        start=datetime(2026, 12, 1, tzinfo=UTC),
        end=datetime(2027, 1, 2, tzinfo=UTC),
        timezone=STOCKHOLM,
    )

    assert result == frozenset(
        {
            date(2026, 12, 24),
            date(2026, 12, 25),
            date(2026, 12, 31),
        }
    )


async def test_calendar_response_requires_selected_entity(hass, monkeypatch) -> None:
    """A missing calendar payload should fail instead of guessing dates."""
    monkeypatch.setattr(type(hass.services), "async_call", AsyncMock(return_value={}))

    with pytest.raises(ValueError, match="events list"):
        await async_get_excluded_dates(
            hass,
            entity_id="calendar.swedish_holidays",
            start=datetime(2026, 12, 1, tzinfo=UTC),
            end=datetime(2027, 1, 2, tzinfo=UTC),
            timezone=STOCKHOLM,
        )
