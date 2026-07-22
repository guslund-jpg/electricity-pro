"""Constants for Electricity Pro."""

from homeassistant.const import Platform

DOMAIN = "electricity_pro"

CONF_POWER_ENTITY = "power_entity"

PLATFORMS: list[Platform] = [Platform.SENSOR]
