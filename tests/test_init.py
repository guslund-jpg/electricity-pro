"""Basic integration setup test."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import (
    CONF_POWER_ENTITY,
    DOMAIN,
)


async def test_setup_entry(hass):
    """Verify the integration loads."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Electricity Pro",
        data={
            CONF_POWER_ENTITY: "sensor.test_power",
        },
    )

    hass.states.async_set(
        "sensor.test_power",
        "1000",
        {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
    )

    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
