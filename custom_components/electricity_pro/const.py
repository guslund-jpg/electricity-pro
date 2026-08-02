"""Constants for Electricity Pro."""

from homeassistant.const import Platform

DOMAIN = "electricity_pro"

CONF_POWER_ENTITY = "power_entity"
CONF_PRICE_ENTITY = "price_entity"
CONF_ENERGY_ENTITY = "energy_entity"
CONF_ACCUMULATED_COST_TODAY_ENTITY = "accumulated_cost_today_entity"
CONF_PEAK_POWER_TODAY_ENTITY = "peak_power_today_entity"
CONF_CURRENT_L1_ENTITY = "current_l1_entity"
CONF_CURRENT_L2_ENTITY = "current_l2_entity"
CONF_CURRENT_L3_ENTITY = "current_l3_entity"
CONF_VOLTAGE_L1_ENTITY = "voltage_l1_entity"
CONF_VOLTAGE_L2_ENTITY = "voltage_l2_entity"
CONF_VOLTAGE_L3_ENTITY = "voltage_l3_entity"
CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY = "monthly_peak_hour_consumption_entity"

PLATFORMS: list[Platform] = [Platform.SENSOR]
