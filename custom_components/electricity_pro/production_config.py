"""Shared optional production/export/household configuration and review."""

from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigEntryBaseFlow, ConfigFlowResult
from homeassistant.helpers import entity_registry as er, selector

from .const import DOMAIN
from .flow_sources import CONF_CONFIGURE_FLOWS, FLOW_KEYS
from .flow_compatibility import (
    COMPATIBILITY_KEYS,
    CONF_ENABLED,
    CONF_GENERATION,
    CONF_STORAGE,
    PHASE_KEYS,
    PHASE_OPTIONS,
    PRESENCE_OPTIONS,
)

PRODUCTION_KEYS = (*FLOW_KEYS, *COMPATIBILITY_KEYS)
CONF_CONFIRM_SEMANTICS = "confirm_flow_semantics"


class ProductionFlow(ConfigEntryBaseFlow):
    """Keep bindings and installation answers in one draft until completion."""

    _production_values: dict[str, Any] | None = None
    _production_reference: dict[str, Any]
    _production_enabled = False
    _production_review_pending = False

    def _production_defaults(self) -> dict[str, Any]:
        raise NotImplementedError

    def _production_binding_errors(self, values: dict[str, Any]) -> dict[str, str]:
        raise NotImplementedError

    async def _async_production_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        raise NotImplementedError

    def _production_schema(self) -> vol.Schema:
        fields: dict[Any, Any] = {
            vol.Required(
                CONF_CONFIGURE_FLOWS, default=self._production_enabled
            ): selector.BooleanSelector()
        }
        if self._production_enabled:
            own = [
                entity.entity_id
                for entity in er.async_get(self.hass).entities.values()
                if entity.platform == DOMAIN
            ]
            for key in FLOW_KEYS:
                fields[vol.Optional(key)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        filter={
                            "domain": "sensor",
                            "device_class": "power" if "_power_" in key else "energy",
                        },
                        exclude_entities=own,
                    )
                )
            fields[vol.Optional(CONF_CONFIRM_SEMANTICS, default=False)] = (
                selector.BooleanSelector()
            )
        return vol.Schema(fields)

    async def _async_clear_production(self) -> ConfigFlowResult:
        assert self._production_values is not None
        values = {
            **self._production_values,
            **dict.fromkeys(FLOW_KEYS),
            CONF_ENABLED: False,
        }
        # Removing a binding removes its convention, not the physical installation.
        for key in PHASE_KEYS:
            if self._production_reference.get(
                key.replace("_phase_convention", "_entity")
            ):
                values[key] = "unknown"
        self._production_values = values
        return await self._async_production_complete(values)

    async def async_step_energy_flows(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer only explicitly selected whole-site AC and lifetime sources."""
        if self._production_values is None:
            defaults = self._production_defaults()
            self._production_reference = defaults
            self._production_values = {
                **{key: defaults.get(key) for key in FLOW_KEYS},
                CONF_ENABLED: defaults.get(CONF_ENABLED) is True,
                **{
                    key: defaults.get(key) or "unknown"
                    for key in (CONF_GENERATION, CONF_STORAGE, *PHASE_KEYS)
                },
            }
            self._production_enabled = any(
                self._production_values.get(key) for key in FLOW_KEYS
            )
        errors = {}
        confirmed = False
        if user_input is not None:
            was_enabled = self._production_enabled
            self._production_enabled = user_input[CONF_CONFIGURE_FLOWS]
            if not self._production_enabled:
                return await self._async_clear_production()
            if was_enabled:
                selected = {key: user_input.get(key) or None for key in FLOW_KEYS}
                self._production_values.update(selected)
                errors = self._production_binding_errors(selected)
                sources = [value for value in selected.values() if value]
                for key, entity_id in selected.items():
                    state = self.hass.states.get(entity_id) if entity_id else None
                    power = "_power_" in key
                    if entity_id and (
                        state is None
                        or state.attributes.get("device_class")
                        != ("power" if power else "energy")
                        or state.attributes.get("unit_of_measurement")
                        not in (("W", "kW") if power else ("Wh", "kWh"))
                    ):
                        errors[key] = "invalid_flow_source"
                confirmed = user_input.get(CONF_CONFIRM_SEMANTICS) is True
                if sources and not confirmed:
                    errors["base"] = "confirm_flow_semantics"
                if not errors:
                    if not sources:
                        return await self._async_clear_production()
                    for key in PHASE_KEYS:
                        source_key = key.replace("_phase_convention", "_entity")
                        if selected[source_key] != self._production_reference.get(
                            source_key
                        ):
                            self._production_values[key] = "unknown"
                    self._production_review_pending = True
                    return await self.async_step_flow_compatibility()
        return self.async_show_form(
            step_id="energy_flows",
            data_schema=self.add_suggested_values_to_schema(
                self._production_schema(),
                {**self._production_values, CONF_CONFIRM_SEMANTICS: confirmed},
            ),
            errors=errors,
        )

    async def async_step_flow_compatibility(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Review installation facts; unknown answers do not block readings."""
        if not self._production_review_pending:
            return await self.async_step_energy_flows()
        assert self._production_values is not None
        phases = tuple(
            key
            for key in PHASE_KEYS
            if self._production_values.get(key.replace("_phase_convention", "_entity"))
        )
        errors = {}
        if user_input is not None:
            self._production_values.update(
                {
                    key: user_input[key]
                    for key in (CONF_ENABLED, CONF_GENERATION, CONF_STORAGE, *phases)
                    if key in user_input
                }
            )
            if self._production_values.get(CONF_GENERATION) == "absent" and any(
                self._production_values.get(f"production_{q}_entity")
                for q in ("power", "energy")
            ):
                errors[CONF_GENERATION] = "contradictory_topology"
            else:
                return await self._async_production_complete(
                    dict(self._production_values)
                )
        fields: dict[Any, Any] = {}
        for key in (CONF_GENERATION, CONF_STORAGE, *phases):
            options = (
                PRESENCE_OPTIONS
                if key in (CONF_GENERATION, CONF_STORAGE)
                else PHASE_OPTIONS
            )
            value = self._production_values.get(key)
            fields[
                vol.Required(key, default=value if value in options else "unknown")
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(options),
                    translation_key="flow_presence"
                    if key in (CONF_GENERATION, CONF_STORAGE)
                    else "flow_phase",
                )
            )
        fields[
            vol.Required(
                CONF_ENABLED, default=self._production_values.get(CONF_ENABLED) is True
            )
        ] = selector.BooleanSelector()
        return self.async_show_form(
            step_id="flow_compatibility", data_schema=vol.Schema(fields), errors=errors
        )
