"""Shared native Nord Pool selection, before supplier price declarations."""

from collections.abc import Mapping
from typing import Any

import probatio as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryBaseFlow,
    ConfigFlowResult,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .const import CONF_FORECAST_NORDPOOL_CONFIG_ENTRY, CONF_FORECAST_PRICE_AREA
from .vat_suggestions import country_hint

MARKET_KEYS = (CONF_FORECAST_NORDPOOL_CONFIG_ENTRY, CONF_FORECAST_PRICE_AREA)


def market_suggestions(hass: HomeAssistant) -> dict[str, Any]:
    """Suggest one enabled native entry during new setup only."""
    entries = [
        entry
        for entry in hass.config_entries.async_entries("nordpool")
        if entry.disabled_by is None
    ]
    return (
        {CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: entries[0].entry_id}
        if len(entries) == 1
        else {}
    )


def without_market_fields(schema: vol.Schema) -> vol.Schema:
    """Hide the inputs now owned by the market-price screen."""
    return vol.Schema(
        {
            key: value
            for key, value in schema.schema.items()
            if key.schema not in MARKET_KEYS
        }
    )


class MarketPriceFlow(ConfigEntryBaseFlow):
    """Collect source/area edits without persisting inferred VAT or currency."""

    _market_values: dict[str, Any] | None = None

    def _market_defaults(self) -> dict[str, Any]:
        raise NotImplementedError

    async def _async_market_prices_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        raise NotImplementedError

    def _market_entry(self, values: Mapping[str, Any]) -> ConfigEntry | None:
        entry_id = values.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY)
        if not isinstance(entry_id, str):
            return None
        entry = self.hass.config_entries.async_get_entry(entry_id)
        return entry if entry and entry.domain == "nordpool" else None

    @staticmethod
    def _market_areas(entry: ConfigEntry | None) -> list[str]:
        areas: object = entry.data.get("areas") if entry else None
        if (
            not isinstance(areas, list)
            or not areas
            or not all(isinstance(area, str) and area.strip() for area in areas)
        ):
            return []
        return list(dict.fromkeys(areas))

    def _market_description(self) -> dict[str, str]:
        values = self._market_values or {}
        entry = self._market_entry(values)
        areas = self._market_areas(entry)
        area = areas[0] if len(areas) == 1 else values.get(CONF_FORECAST_PRICE_AREA)
        currency = entry.data.get("currency") if entry else None
        return {
            "source": entry.title if entry else "—",
            "area": area if isinstance(area, str) and area in areas else "—",
            "currency": currency if isinstance(currency, str) and currency else "—",
            "country": country_hint(areas, area) or "—",
        }

    def _market_source_valid(self, entry: ConfigEntry | None) -> bool:
        currency = entry.data.get("currency") if entry else None
        return bool(
            self._market_areas(entry) and isinstance(currency, str) and currency.strip()
        )

    def _market_area_field(
        self, areas: list[str], *, required: bool
    ) -> dict[vol.Marker, selector.SelectSelector]:
        values = self._market_values or {}
        marker = vol.Required if required else vol.Optional
        return {
            marker(
                CONF_FORECAST_PRICE_AREA,
                description={
                    "suggested_value": values.get(CONF_FORECAST_PRICE_AREA)
                    if values.get(CONF_FORECAST_PRICE_AREA) in areas
                    else None
                },
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=areas, mode=selector.SelectSelectorMode.DROPDOWN
                )
            )
        }

    async def async_step_market_prices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select an optional native entry and edit its saved multi-area choice."""
        if self._market_values is None:
            defaults = self._market_defaults()
            self._market_values = {key: defaults.get(key) for key in MARKET_KEYS}
        values = self._market_values
        errors = {}
        if user_input is not None:
            source = user_input.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY) or None
            same_source = source == values.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY)
            area = (
                user_input.get(
                    CONF_FORECAST_PRICE_AREA, values.get(CONF_FORECAST_PRICE_AREA)
                )
                if same_source
                else None
            )
            self._market_values = values = {
                CONF_FORECAST_NORDPOOL_CONFIG_ENTRY: source,
                CONF_FORECAST_PRICE_AREA: area,
            }
            if source is None:
                values[CONF_FORECAST_PRICE_AREA] = None
                return await self._async_market_prices_complete(dict(values))
            entry = self._market_entry(values)
            areas = self._market_areas(entry)
            if not self._market_source_valid(entry):
                errors[CONF_FORECAST_NORDPOOL_CONFIG_ENTRY] = "invalid_market_source"
            elif len(areas) > 1 and area not in areas:
                return await self.async_step_market_area()
            else:
                if len(areas) == 1:
                    # Runtime inherits a single area. Override any older saved choice.
                    values[CONF_FORECAST_PRICE_AREA] = None
                return await self._async_market_prices_complete(dict(values))
        fields: dict[
            vol.Marker, selector.ConfigEntrySelector | selector.SelectSelector
        ] = {
            vol.Optional(
                CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
                description={
                    "suggested_value": values.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY)
                },
            ): selector.ConfigEntrySelector(
                selector.ConfigEntrySelectorConfig(integration="nordpool")
            )
        }
        areas = self._market_areas(self._market_entry(values))
        if len(areas) > 1:
            fields.update(self._market_area_field(areas, required=False))
        return self.async_show_form(
            step_id="market_prices",
            data_schema=vol.Schema(fields),
            errors=errors,
            description_placeholders=self._market_description(),
        )

    async def async_step_market_area(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Resolve a changed source before any downstream VAT assistance."""
        values = self._market_values or {}
        entry = self._market_entry(values)
        if not self._market_source_valid(entry):
            return await self.async_step_market_prices(dict(values))
        areas = self._market_areas(entry)
        errors = {}
        if user_input is not None:
            area = user_input.get(CONF_FORECAST_PRICE_AREA)
            if area not in areas:
                errors[CONF_FORECAST_PRICE_AREA] = "invalid_market_area"
            else:
                values[CONF_FORECAST_PRICE_AREA] = area if len(areas) > 1 else None
                return await self._async_market_prices_complete(dict(values))
        return self.async_show_form(
            step_id="market_area",
            data_schema=vol.Schema(self._market_area_field(areas, required=True)),
            errors=errors,
            description_placeholders=self._market_description(),
        )
