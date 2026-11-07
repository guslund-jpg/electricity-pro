"""Shared measurement selection for setup and options."""

from collections.abc import Mapping
from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigEntryBaseFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import section
from homeassistant.helpers import device_registry as dr, entity_registry as er, selector

from .const import (
    CONF_ENERGY_ENTITY,
    CONF_ENERGY_SOURCE_TYPE,
    CONF_POWER_ENTITY,
    DOMAIN,
    ENERGY_SOURCE_DAILY,
    ENERGY_SOURCE_LIFETIME,
)
from .flow_sources import FLOW_KEYS
from .source_adapters import discover_tibber_sources

ADVANCED_MEASUREMENTS = {
    **{f"current_l{phase}_entity": ("current", ("A",)) for phase in (1, 2, 3)},
    **{f"voltage_l{phase}_entity": ("voltage", ("V",)) for phase in (1, 2, 3)},
    "monthly_peak_hour_consumption_entity": ("energy", ("Wh", "kWh")),
    "monthly_peak_hour_time_entity": ("timestamp", ()),
}
MEASUREMENT_KEYS = (
    CONF_POWER_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_ENERGY_SOURCE_TYPE,
    *ADVANCED_MEASUREMENTS,
)


def measurement_suggestions(hass: HomeAssistant) -> dict[str, Any]:
    """Suggest a single known meter independently of its price capabilities."""
    sources = [
        source
        for source in discover_tibber_sources(er.async_get(hass).entities.values())
        if CONF_POWER_ENTITY in source.data
    ]
    if len(sources) != 1:
        return {}
    return {
        key: value for key, value in sources[0].data.items() if key in MEASUREMENT_KEYS
    }


def remaining_settings_schema(schema: vol.Schema) -> vol.Schema:
    """Remove the measurement fields owned by the shared screen."""
    return vol.Schema(
        {
            key: value
            for key, value in schema.schema.items()
            if key.schema not in MEASUREMENT_KEYS
        }
    )


class MeasurementFlow(ConfigEntryBaseFlow):
    """Collect measurement edits without writing until the flow completes."""

    _measurement_values: dict[str, Any] | None = None
    _measurement_reference: dict[str, Any]

    def _measurement_defaults(self) -> dict[str, Any]:
        raise NotImplementedError

    async def _async_measurements_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        raise NotImplementedError

    def _measurement_summary(self) -> str:
        """Show current readings and source ownership alongside the selectors."""
        values = self._measurement_values or {}
        registry = er.async_get(self.hass)
        lines = []
        for key in (CONF_POWER_ENTITY, CONF_ENERGY_ENTITY):
            entity_id = values.get(key)
            if not entity_id:
                continue
            state = self.hass.states.get(entity_id)
            registered = registry.async_get(entity_id)
            owner = f" · {registered.platform}" if registered else ""
            if registered and registered.device_id:
                device = dr.async_get(self.hass).async_get(registered.device_id)
                if device and (device_name := device.name_by_user or device.name):
                    owner = f" · {device_name}{owner}"
            reading = (
                f" · {state.state} {state.attributes.get('unit_of_measurement', '')}"
                if state
                else ""
            )
            lines.append(f"- {entity_id}{owner}{reading}")
        return "\n".join(lines)

    def _measurement_errors(self, values: Mapping[str, Any]) -> dict[str, str]:
        """Validate source ownership and available metadata, retaining offline sources."""
        registry = er.async_get(self.hass)
        own = {
            entity.entity_id
            for entity in registry.entities.values()
            if entity.platform == DOMAIN
        }
        flows = {self._measurement_reference.get(key) for key in FLOW_KEYS}
        errors = {}
        quantities = {
            CONF_POWER_ENTITY: ("power", ("W", "kW")),
            CONF_ENERGY_ENTITY: ("energy", ("Wh", "kWh")),
            **ADVANCED_MEASUREMENTS,
        }
        for key, (device_class, units) in quantities.items():
            entity_id = values.get(key)
            if not entity_id:
                continue
            if entity_id in own:
                errors[
                    key if key in (CONF_POWER_ENTITY, CONF_ENERGY_ENTITY) else "base"
                ] = "electricity_pro_source"
            elif entity_id in flows:
                errors[
                    key if key in (CONF_POWER_ENTITY, CONF_ENERGY_ENTITY) else "base"
                ] = "invalid_flow_source"
            elif (state := self.hass.states.get(entity_id)) is not None:
                if state.attributes.get("device_class") not in (None, device_class) or (
                    units and state.attributes.get("unit_of_measurement") not in units
                ):
                    errors[
                        key
                        if key in (CONF_POWER_ENTITY, CONF_ENERGY_ENTITY)
                        else "base"
                    ] = "invalid_measurement_source"
        return errors

    async def async_step_measurements(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the two basic sources and optional advanced readings."""
        if self._measurement_values is None:
            self._measurement_reference = self._measurement_defaults()
            self._measurement_values = {
                key: value
                for key, value in self._measurement_reference.items()
                if key in MEASUREMENT_KEYS
            }
        errors = {}
        if user_input is not None:
            advanced = user_input.get("advanced_measurements", self._measurement_values)
            values = {
                CONF_POWER_ENTITY: user_input[CONF_POWER_ENTITY],
                CONF_ENERGY_ENTITY: user_input.get(CONF_ENERGY_ENTITY) or None,
                **{key: advanced.get(key) or None for key in ADVANCED_MEASUREMENTS},
            }
            errors = self._measurement_errors(values)
            previous = self._measurement_values
            self._measurement_values = values
            if not errors:
                energy = values[CONF_ENERGY_ENTITY]
                if energy == self._measurement_reference.get(CONF_ENERGY_ENTITY):
                    values[CONF_ENERGY_SOURCE_TYPE] = advanced.get(
                        CONF_ENERGY_SOURCE_TYPE,
                        self._measurement_reference.get(CONF_ENERGY_SOURCE_TYPE)
                        or ENERGY_SOURCE_DAILY,
                    )
                elif energy:
                    registered = er.async_get(self.hass).async_get(energy)
                    if (
                        registered
                        and registered.platform == "tibber"
                        and (registered.translation_key == "accumulated_consumption")
                    ):
                        values[CONF_ENERGY_SOURCE_TYPE] = ENERGY_SOURCE_DAILY
                    else:
                        values[CONF_ENERGY_SOURCE_TYPE] = previous.get(
                            CONF_ENERGY_SOURCE_TYPE
                        )
                        return await self.async_step_measurement_energy()
                else:
                    values[CONF_ENERGY_SOURCE_TYPE] = previous.get(
                        CONF_ENERGY_SOURCE_TYPE, ENERGY_SOURCE_DAILY
                    )
                return await self._async_measurements_complete(dict(values))
        own = [
            entity.entity_id
            for entity in er.async_get(self.hass).entities.values()
            if entity.platform == DOMAIN
        ]
        values = self._measurement_values
        fields: dict[
            vol.Marker, selector.EntitySelector | selector.SelectSelector | section
        ] = {}
        for key, device_class in (
            (CONF_POWER_ENTITY, "power"),
            (CONF_ENERGY_ENTITY, "energy"),
        ):
            marker_type = vol.Required if key == CONF_POWER_ENTITY else vol.Optional
            fields[
                marker_type(key, description={"suggested_value": values.get(key)})
            ] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor", device_class=device_class, exclude_entities=own
                )
            )
        advanced_fields: dict[
            vol.Marker, selector.EntitySelector | selector.SelectSelector
        ] = {
            vol.Optional(
                key, description={"suggested_value": values.get(key)}
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor", device_class=kind, exclude_entities=own
                )
            )
            for key, (kind, _) in ADVANCED_MEASUREMENTS.items()
        }
        advanced_fields[
            vol.Optional(
                CONF_ENERGY_SOURCE_TYPE,
                description={"suggested_value": values.get(CONF_ENERGY_SOURCE_TYPE)},
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[ENERGY_SOURCE_DAILY, ENERGY_SOURCE_LIFETIME],
                translation_key="energy_source_type",
            )
        )
        fields[vol.Optional("advanced_measurements")] = section(
            vol.Schema(advanced_fields), {"collapsed": True}
        )
        return self.async_show_form(
            step_id="measurements",
            data_schema=vol.Schema(fields),
            errors=errors,
            description_placeholders={"sources": self._measurement_summary()},
        )

    async def async_step_measurement_energy(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the accumulation period only when the source is unresolved."""
        assert self._measurement_values is not None
        if user_input is not None:
            self._measurement_values[CONF_ENERGY_SOURCE_TYPE] = user_input[
                CONF_ENERGY_SOURCE_TYPE
            ]
            return await self._async_measurements_complete(
                dict(self._measurement_values)
            )
        return self.async_show_form(
            step_id="measurement_energy",
            description_placeholders={"sources": self._measurement_summary()},
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ENERGY_SOURCE_TYPE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[ENERGY_SOURCE_DAILY, ENERGY_SOURCE_LIFETIME],
                            translation_key="energy_source_type",
                        )
                    )
                }
            ),
        )
