"""Constants for Electricity Pro."""

from homeassistant.const import Platform

DOMAIN = "electricity_pro"

CONF_POWER_ENTITY = "power_entity"
CONF_PRICE_ENTITY = "price_entity"
CONF_ENERGY_ENTITY = "energy_entity"
CONF_ACCUMULATED_COST_TODAY_ENTITY = "accumulated_cost_today_entity"
CONF_PEAK_POWER_TODAY_ENTITY = "peak_power_today_entity"

PLATFORMS: list[Platform] = [Platform.SENSOR]
