"""Constants for Electricity Pro."""

from homeassistant.const import Platform

DOMAIN = "electricity_pro"

CONF_POWER_ENTITY = "power_entity"
CONF_PRICE_ENTITY = "price_entity"

PLATFORMS: list[Platform] = [Platform.SENSOR]
