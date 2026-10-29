"""Startup must reuse Home Assistant's already-loaded timezone."""

from unittest.mock import patch

import pytest
from homeassistant.util import dt as dt_util


@pytest.mark.parametrize("zone", ["UTC", "Europe/Stockholm", "Europe/Helsinki", "Europe/Oslo"])
async def test_setup_and_reload_reuse_loaded_timezone(hass, setup_electricity_pro, zone):
    """Do not construct ZoneInfo on the event loop, even on first startup."""
    await hass.config.async_set_time_zone(zone)
    expected = dt_util.get_default_time_zone()
    assert str(expected) == zone

    # Catch the former module-level imports even if ZoneInfo has a warm cache.
    # No filesystem timing or platform-specific tzdata behaviour is required.
    with (
        patch("custom_components.electricity_pro.coordinator.ZoneInfo",
              create=True, side_effect=AssertionError("Blocking timezone construction")),
        patch("custom_components.electricity_pro.provider.ZoneInfo",
              create=True, side_effect=AssertionError("Blocking timezone construction")),
    ):
        entry = await setup_electricity_pro()
        coordinator = entry.runtime_data
        assert coordinator._local_timezone is expected
        assert coordinator._provider._local_timezone is expected

        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.runtime_data is not coordinator
        assert entry.runtime_data._local_timezone is expected
        assert entry.runtime_data._provider._local_timezone is expected
