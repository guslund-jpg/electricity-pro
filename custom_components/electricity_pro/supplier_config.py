"""Shared supplier declarations and billing inputs for setup and options."""

from decimal import Decimal, InvalidOperation
from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
    CONF_FIXED_SUPPLIER_FEE_MONTHLY,
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_ENTITY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_RATE,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICING_STRATEGY,
    CONF_SOURCE_PROFILE,
    CONF_SUPPLIER_MARKUP_PER_KWH,
    DOMAIN,
)
from .markup_estimate import CONF_ESTIMATE_MARKUP
from .pricing import PriceComponent, PricingStrategy, VatTreatment
from .pricing_config import prepare_pricing_metadata, pricing_metadata_from_mapping
from .vat_suggestions import CONF_SUGGEST_VAT, VatSuggestionFlow

PRICE_METADATA_KEYS = (
    CONF_PRICING_STRATEGY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICE_COMPLETENESS,
)
SUPPLIER_KEYS = (
    CONF_PRICE_ENTITY,
    *PRICE_METADATA_KEYS,
    CONF_PRICE_VAT_RATE,
    CONF_SUPPLIER_MARKUP_PER_KWH,
    CONF_FIXED_SUPPLIER_FEE_MONTHLY,
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
)


def without_supplier_fields(schema: vol.Schema) -> vol.Schema:
    """Leave grid charges and other settings on their remaining screens."""
    return vol.Schema(
        {
            key: value
            for key, value in schema.schema.items()
            if key.schema
            not in (*SUPPLIER_KEYS, CONF_SUGGEST_VAT, CONF_ESTIMATE_MARKUP)
        }
    )


class SupplierFlow(VatSuggestionFlow):
    """Collect supplier edits without changing another section or saved state."""

    _supplier_values: dict[str, Any] | None = None
    _supplier_reference: dict[str, Any]
    _pending_forecast_settings: dict[str, Any] | None

    def _supplier_defaults(self) -> dict[str, Any]:
        raise NotImplementedError

    def _supplier_form_schema(
        self, values: dict[str, Any], known_tibber: bool
    ) -> vol.Schema:
        raise NotImplementedError

    async def _async_supplier_market(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult | None:
        """Resolve a legacy area before rendering price/VAT declarations."""
        return None

    async def _async_supplier_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        raise NotImplementedError

    async def _async_supplier_estimate(self) -> ConfigFlowResult:
        raise NotImplementedError

    def _supplier_is_tibber(self) -> bool:
        values = {**self._supplier_reference, **(self._supplier_values or {})}
        # Incomplete older declarations remain editable through the standard form.
        metadata = pricing_metadata_from_mapping(values)
        price_entity = values.get(CONF_PRICE_ENTITY)
        registered = (
            er.async_get(self.hass).async_get(price_entity)
            if isinstance(price_entity, str)
            else None
        )
        return (
            values.get(CONF_SOURCE_PROFILE) == "tibber"
            and bool(price_entity)
            and (registered is None or registered.platform == "tibber")
            and metadata is not None
            and metadata.strategy is PricingStrategy.SUPPLIER_CONTRACTED_PRICE
            and metadata.scope.vat is VatTreatment.INCLUDED
            and metadata.scope.included
            == frozenset((PriceComponent.MARKET_ENERGY, PriceComponent.SUPPLIER_MARKUP))
        )

    def _supplier_errors(self, values: dict[str, Any]) -> dict[str, str]:
        own = {
            entity.entity_id
            for entity in er.async_get(self.hass).entities.values()
            if entity.platform == DOMAIN
        }
        errors = {
            key: "electricity_pro_source"
            for key in (CONF_PRICE_ENTITY, CONF_ACCUMULATED_COST_TODAY_ENTITY)
            if values.get(key) in own
        }
        if errors:
            return errors
        if not prepare_pricing_metadata(values):
            errors["base"] = "pricing_metadata_required"
        elif not values.get(CONF_PRICE_ENTITY):
            # Explicit clears must override the original setup declarations too.
            values.update(dict.fromkeys(PRICE_METADATA_KEYS))
        for key, maximum in (
            (CONF_PRICE_VAT_RATE, 100),
            (CONF_SUPPLIER_MARKUP_PER_KWH, None),
            (CONF_FIXED_SUPPLIER_FEE_MONTHLY, None),
        ):
            value = values.get(key)
            if value is None:
                continue
            try:
                amount = Decimal(str(value))
                if (
                    not amount.is_finite()
                    or amount < 0
                    or (maximum is not None and amount > maximum)
                ):
                    raise ValueError
            except InvalidOperation, ValueError:
                errors[key] = "invalid_supplier_amount"
        return errors

    async def async_step_supplier(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Review live supplier pricing, fixed fees and optional cost sources."""
        if self._supplier_values is None:
            defaults = self._supplier_defaults()
            market_result = await self._async_supplier_market(defaults)
            if market_result is not None:
                return market_result
            self._supplier_reference = defaults
            self._supplier_values = {
                key: defaults[key] for key in SUPPLIER_KEYS if key in defaults
            }
        context = {**self._supplier_reference, **self._supplier_values}
        known_tibber = self._supplier_is_tibber()
        schema = self._supplier_form_schema(
            self._vat_form_values(context), known_tibber
        )
        errors = {}
        if user_input is not None:
            values = dict(self._supplier_values)
            for marker in schema.schema:
                key = marker.schema
                if key in SUPPLIER_KEYS:
                    values[key] = user_input.get(key)
            self._supplier_values = values
            errors = self._supplier_errors(values)
            if not errors:
                assisted = {
                    **values,
                    CONF_SUGGEST_VAT: user_input.get(CONF_SUGGEST_VAT, False),
                }
                result = await self._async_maybe_suggest_vat(
                    assisted, "supplier", self._supplier_reference
                )
                if result is not None:
                    return result
                if (
                    user_input.get(CONF_ESTIMATE_MARKUP)
                    and known_tibber
                    and context.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY)
                ):
                    self._pending_forecast_settings = {
                        **self._supplier_reference,
                        **values,
                    }
                    return await self._async_supplier_estimate()
                return await self._async_supplier_complete(dict(values))
        values = {**self._supplier_reference, **self._supplier_values}
        return self.async_show_form(
            step_id="supplier_tibber" if known_tibber else "supplier",
            data_schema=self.add_suggested_values_to_schema(
                self._supplier_form_schema(self._vat_form_values(values), known_tibber),
                self._vat_form_values(values),
            ),
            errors=errors,
            description_placeholders={
                "price_source": str(values.get(CONF_PRICE_ENTITY) or "—"),
                "cost_source": str(
                    values.get(CONF_ACCUMULATED_COST_TODAY_ENTITY) or "—"
                ),
            },
        )

    async def async_step_supplier_tibber(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Use the same supplier flow with Tibber's known declarations hidden."""
        return await self.async_step_supplier(user_input)
