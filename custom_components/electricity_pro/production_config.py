"""Shared optional production/export/household configuration and review."""

from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigEntryBaseFlow, ConfigFlowResult
from homeassistant.helpers import entity_registry as er, selector

from .const import DOMAIN
from .export_price_config import (
    EXPORT_COMPONENTS,
    EXPORT_ENERGY_SOURCE,
    EXPORT_PRICE_PERIODS,
    EXPORT_VAT_OPTIONS,
    ExportPriceTerms,
    parse_export_price_terms,
)
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
    _offer_fixed_export_price = False
    _export_price_edited = False
    _export_price_terms: ExportPriceTerms | None = None

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
        can_edit_export_price = self._offer_fixed_export_price and bool(
            self._production_values.get(EXPORT_ENERGY_SOURCE)
        )
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
            elif can_edit_export_price and user_input.get("edit_fixed_export_price"):
                return await self.async_step_fixed_export_price()
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
        if can_edit_export_price:
            fields[vol.Optional("edit_fixed_export_price", default=False)] = (
                selector.BooleanSelector()
            )
        return self.async_show_form(
            step_id="flow_compatibility", data_schema=vol.Schema(fields), errors=errors
        )

    async def async_step_fixed_export_price(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the terms for the export register already confirmed in this flow."""
        values = self._production_values
        meter = values.get(EXPORT_ENERGY_SOURCE) if values is not None else None
        if (
            not self._offer_fixed_export_price
            or not self._production_review_pending
            or not isinstance(meter, str)
            or not meter
        ):
            return await self.async_step_energy_flows()
        assert values is not None
        errors: dict[str, str] = {}
        periods = self._production_defaults().get(EXPORT_PRICE_PERIODS, [])
        last = next(
            (period for period in reversed(periods) if period["meter"] == meter), None
        )
        defaults = {
            "fixed_export_price_enabled": bool(last and last["valid_until"] is None),
            "export_price_amount": last["amount_per_kwh"] if last else None,
            "export_price_currency": last["currency"] if last else None,
            "export_price_vat_treatment": last["vat_treatment"] if last else None,
            "export_price_components": last["components"] if last else None,
        }
        if user_input is not None:
            if user_input["fixed_export_price_enabled"]:
                self._export_price_terms, errors = parse_export_price_terms(
                    meter,
                    user_input.get("export_price_amount", ""),
                    user_input.get("export_price_currency", ""),
                    user_input.get("export_price_vat_treatment", ""),
                    user_input.get("export_price_components", []),
                )
            else:
                self._export_price_terms = None
            if not errors:
                self._export_price_edited = True
                return await self._async_production_complete(dict(values))
            defaults.update(user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    "fixed_export_price_enabled", default=False
                ): selector.BooleanSelector(),
                vol.Optional("export_price_amount"): selector.TextSelector(),
                vol.Optional("export_price_currency"): selector.TextSelector(),
                vol.Optional("export_price_vat_treatment"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(EXPORT_VAT_OPTIONS),
                        translation_key="export_price_vat",
                    )
                ),
                vol.Optional("export_price_components"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(EXPORT_COMPONENTS),
                        translation_key="export_price_components",
                        multiple=True,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="fixed_export_price",
            data_schema=self.add_suggested_values_to_schema(schema, defaults),
            description_placeholders={"export_meter": meter},
            errors=errors,
        )
