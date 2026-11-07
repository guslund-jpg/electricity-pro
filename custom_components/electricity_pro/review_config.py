"""Read-only configuration review using the existing pricing contracts."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigEntryBaseFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from .calculations import (
    calculate_declared_effective_price,
    effective_price_metadata,
    vat_inclusive_price,
)
from .const import (
    CONF_FORECAST_NORDPOOL_CONFIG_ENTRY,
    CONF_FORECAST_PRICE_AREA,
    CONF_PRICE_ENTITY,
    DEFAULT_ADAPTIVE_TARGET_PERCENTILE,
)
from .flow_compatibility import (
    CONF_ENABLED,
    CONF_GENERATION,
    CONF_STORAGE,
    PHASE_KEYS,
    PHASE_OPTIONS,
    PRESENCE_OPTIONS,
)
from .flow_sources import FLOW_KEYS
from .grid_config import SCHEDULE_DEFAULTS, TIME_OF_USE, grid_errors, grid_mode
from .insight_config import insight_errors
from .measurement_config import ADVANCED_MEASUREMENTS
from .pricing import (
    PriceComponent,
    PriceComponentScope,
    PriceCompleteness,
    PricingMetadata,
    PricingStrategy,
    VatTreatment,
)
from .pricing_config import pricing_metadata_from_mapping, vat_rate_from_mapping
from .vat_suggestions import country_hint

REVIEW_STATUS = ("not_configured", "unknown", "partial", "complete", "conflict")


def _amount(value: object, *, negative: bool = False) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() and (negative or result >= 0) else None
    except InvalidOperation, ValueError:
        return None


@dataclass(frozen=True, slots=True)
class PriceCoverage:
    """Configured variable-price coverage, not availability or cost history."""

    status: str
    missing: tuple[str, ...] = ()


def price_coverage(
    metadata: PricingMetadata | None, values: Mapping[str, Any]
) -> PriceCoverage:
    """Describe the same additions, VAT and complete-source guard as runtime."""
    if metadata is None:
        return PriceCoverage("unknown", ("price_declaration",))
    grid = _amount(values.get("grid_fee_per_kwh"))
    tax = _amount(values.get("energy_tax_per_kwh"))
    markup = _amount(values.get("supplier_markup_per_kwh"))
    additions = {
        PriceComponent.VARIABLE_GRID_FEE: grid,
        PriceComponent.ENERGY_TAX: tax,
        PriceComponent.SUPPLIER_MARKUP: markup,
    }
    effective = effective_price_metadata(metadata, grid, tax, markup)
    missing = (
        []
        if metadata.is_complete
        else sorted(
            component.value
            for component in PriceComponent
            if component not in effective.scope.included
        )
    )
    vat_known = vat_inclusive_price(Decimal(0), metadata) is not None
    if not vat_known:
        missing.append(
            "vat_rate"
            if metadata.scope.vat is VatTreatment.EXCLUDED
            else "vat_treatment"
        )
    if metadata.is_complete and any(
        value is not None and not metadata.scope.includes(component)
        for component, value in additions.items()
    ):
        return PriceCoverage("conflict", tuple([*missing, "price_additions"]))
    if (
        not vat_known
        or calculate_declared_effective_price(Decimal(0), metadata, grid, tax, markup)
        is None
    ):
        return PriceCoverage("unknown", tuple(missing))
    return PriceCoverage(
        "complete" if effective.is_complete else "partial", tuple(missing)
    )


class _Group:
    """Native selectors keep labels and enum choices in the frontend language."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.fields: dict[Any, Any] = {}

    def choice(
        self, key: str, value: object, options: tuple[str, ...], translation: str
    ) -> None:
        choices = options if "unknown" in options else (*options, "unknown")
        self.fields[
            vol.Optional(key, default=value if value in choices else "unknown")
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                read_only=True, options=list(choices), translation_key=translation
            )
        )

    def text(self, key: str, value: object) -> None:
        if value is None:
            self.choice(key, "unknown", REVIEW_STATUS, "review_status")
        else:
            self.fields[vol.Optional(key, default=str(value))] = selector.TextSelector(
                selector.TextSelectorConfig(read_only=True)
            )

    def source(self, key: str, value: object) -> None:
        if not isinstance(value, str) or not value.strip():
            self.choice(
                key,
                "not_configured" if value is None else "unknown",
                REVIEW_STATUS,
                "review_status",
            )
            return
        state = self.hass.states.get(value)
        self.text(
            key, f"{state.name} · {value}" if state and state.name != value else value
        )

    def number(self, key: str, value: object, *, negative: bool = False) -> None:
        amount = _amount(value, negative=negative)
        if amount is None or not isfinite(float(amount)):
            self.choice(key, "unknown", REVIEW_STATUS, "review_status")
        else:
            self.fields[vol.Optional(key, default=float(amount))] = (
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        read_only=True, step=0.001, mode=selector.NumberSelectorMode.BOX
                    )
                )
            )

    def boolean(self, key: str, value: bool) -> None:
        self.fields[vol.Optional(key, default=value)] = selector.BooleanSelector(
            selector.BooleanSelectorConfig(read_only=True)
        )

    def many(
        self,
        key: str,
        values: tuple[str, ...] | list[str],
        options: list[str],
        translation: str,
    ) -> None:
        if values:
            self.fields[vol.Optional(key, default=list(values))] = (
                selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        read_only=True,
                        multiple=True,
                        options=options,
                        translation_key=translation,
                    )
                )
            )


GAP_OPTIONS = [
    *(component.value for component in PriceComponent),
    "vat_rate",
    "vat_treatment",
    "price_declaration",
    "price_additions",
    "forecast_context",
    "fixed_supplier_fee",
    "fixed_grid_fee",
    "grid_schedule",
    "insight_settings",
]


def review_schema(hass: HomeAssistant, values: Mapping[str, Any]) -> vol.Schema:
    """Render a saved configuration or final setup draft without modifying it."""
    groups = {
        name: _Group(hass)
        for name in (
            "price_coverage",
            "measurements",
            "market_prices",
            "supplier",
            "grid",
            "energy_flows",
            "insights",
        )
    }
    coverage = groups["price_coverage"]
    metadata = pricing_metadata_from_mapping(values)
    live = (
        price_coverage(metadata, values)
        if values.get(CONF_PRICE_ENTITY)
        else PriceCoverage("not_configured")
    )
    coverage.choice("live_price_coverage", live.status, REVIEW_STATUS, "review_status")
    coverage.many("live_missing", live.missing, GAP_OPTIONS, "review_gaps")

    market = groups["market_prices"]
    entry_id = values.get(CONF_FORECAST_NORDPOOL_CONFIG_ENTRY)
    entry = (
        hass.config_entries.async_get_entry(entry_id)
        if isinstance(entry_id, str)
        else None
    )
    native = entry if entry and entry.domain == "nordpool" else None
    raw_areas = native.data.get("areas") if native else None
    areas = (
        list(dict.fromkeys(raw_areas))
        if isinstance(raw_areas, list)
        and raw_areas
        and all(isinstance(area, str) and area.strip() for area in raw_areas)
        else []
    )
    area = areas[0] if len(areas) == 1 else values.get(CONF_FORECAST_PRICE_AREA)
    area = area if isinstance(area, str) and area in areas else None
    currency = native.data.get("currency") if native else None
    currency = currency if isinstance(currency, str) and currency.strip() else None
    market.boolean("forecast_configured", bool(entry_id))
    if entry_id:
        market.text("forecast_source", native.title if native else entry_id)
        market.text("forecast_area", area)
        market.choice(
            "area_origin",
            "inherited" if len(areas) == 1 else "selected" if area else "unknown",
            ("inherited", "selected", "unknown"),
            "review_origin",
        )
        market.text("forecast_currency", currency)
        market.text("forecast_country", country_hint(areas, area) if area else None)
        forecast_metadata = PricingMetadata(
            PricingStrategy.MARKET_PRICE_PLUS_TARIFF,
            PriceComponentScope(
                frozenset((PriceComponent.MARKET_ENERGY,)), VatTreatment.EXCLUDED
            ),
            PriceCompleteness.PARTIAL,
            vat_rate_from_mapping(values),
        )
        forecast = price_coverage(forecast_metadata, values)
        if area is None or currency is None:
            forecast = PriceCoverage("unknown", (*forecast.missing, "forecast_context"))
    else:
        forecast = PriceCoverage("not_configured")
    coverage.choice(
        "forecast_price_coverage", forecast.status, REVIEW_STATUS, "review_status"
    )
    coverage.many("forecast_missing", forecast.missing, GAP_OPTIONS, "review_gaps")
    fixed_missing = tuple(
        name
        for name, key in (
            ("fixed_supplier_fee", "fixed_supplier_fee_monthly"),
            ("fixed_grid_fee", "fixed_grid_fee_monthly"),
        )
        if _amount(values.get(key)) is None
    )
    coverage.many("fixed_fees_missing", fixed_missing, GAP_OPTIONS, "review_gaps")

    measurements = groups["measurements"]
    for key in ("power_entity", "energy_entity"):
        measurements.source(key, values.get(key))
    if values.get("energy_entity"):
        measurements.choice(
            "energy_source_type",
            values.get("energy_source_type"),
            ("daily", "lifetime", "unknown"),
            "energy_source_type",
        )
    for key in ADVANCED_MEASUREMENTS:
        if values.get(key):
            measurements.source(key, values[key])

    supplier = groups["supplier"]
    supplier.source("price_entity", values.get("price_entity"))
    if values.get("price_entity"):
        supplier.choice(
            "pricing_strategy",
            metadata.strategy.value if metadata else None,
            tuple(strategy.value for strategy in PricingStrategy),
            "pricing_strategy",
        )
        supplier.choice(
            "price_vat_treatment",
            metadata.scope.vat.value if metadata else None,
            tuple(vat.value for vat in VatTreatment),
            "price_vat_treatment",
        )
        if metadata:
            supplier.many(
                "price_included_components",
                sorted(component.value for component in metadata.scope.included),
                [component.value for component in PriceComponent],
                "price_included_components",
            )
    supplier.number("price_vat_rate", vat_rate_from_mapping(values))
    supplier.number("supplier_markup_per_kwh", values.get("supplier_markup_per_kwh"))
    supplier.number(
        "fixed_supplier_fee_monthly", values.get("fixed_supplier_fee_monthly")
    )
    supplier.source(
        "accumulated_cost_today_entity", values.get("accumulated_cost_today_entity")
    )

    grid = groups["grid"]
    mode = grid_mode(dict(values))
    grid.choice(
        "grid_mode", mode, ("unconfigured", "constant", TIME_OF_USE), "grid_mode"
    )
    for key in ("grid_fee_per_kwh", "energy_tax_per_kwh", "fixed_grid_fee_monthly"):
        grid.number(key, values.get(key))
    if mode == TIME_OF_USE:
        schedule = {**SCHEDULE_DEFAULTS, **values}
        grid.number("grid_fee_high_per_kwh", values.get("grid_fee_high_per_kwh"))
        for key in SCHEDULE_DEFAULTS:
            grid.text(key, schedule.get(key))
        grid.choice(
            "schedule_origin",
            "default"
            if any(key not in values for key in SCHEDULE_DEFAULTS)
            else "selected",
            ("default", "selected", "unknown"),
            "review_origin",
        )
        grid.source("grid_fee_workday_entity", values.get("grid_fee_workday_entity"))
        if grid_errors(schedule, mode):
            coverage.many(
                "grid_warning", ("grid_schedule",), GAP_OPTIONS, "review_gaps"
            )

    production = groups["energy_flows"]
    production.boolean(
        "optional_sources_configured", any(values.get(key) for key in FLOW_KEYS)
    )
    for key in FLOW_KEYS:
        if values.get(key):
            production.source(key, values[key])
    for key in (CONF_GENERATION, CONF_STORAGE):
        production.choice(
            key, values.get(key) or "unknown", PRESENCE_OPTIONS, "flow_presence"
        )
    production.boolean(CONF_ENABLED, values.get(CONF_ENABLED) is True)
    for key in PHASE_KEYS:
        if values.get(key.replace("_phase_convention", "_entity")):
            production.choice(
                key, values.get(key) or "unknown", PHASE_OPTIONS, "flow_phase"
            )

    insights = groups["insights"]
    configured_mode = values.get("good_price_mode", "fixed")
    configured_mode = (
        configured_mode if configured_mode in ("fixed", "adaptive") else "fixed"
    )
    insights.choice(
        "good_price_mode", configured_mode, ("fixed", "adaptive"), "good_price_mode"
    )
    insights.number("good_price_threshold", values.get("good_price_threshold"))
    insight_values = {
        **values,
        "good_price_mode": configured_mode,
        "adaptive_target_percentile": values.get("adaptive_target_percentile")
        if values.get("adaptive_target_percentile") is not None
        else DEFAULT_ADAPTIVE_TARGET_PERCENTILE,
    }
    if configured_mode == "adaptive":
        insights.number(
            "adaptive_target_percentile", insight_values["adaptive_target_percentile"]
        )
        insights.number(
            "adaptive_price_ceiling",
            values.get("adaptive_price_ceiling"),
            negative=True,
        )
    if insight_errors(insight_values):
        coverage.many(
            "insight_warning", ("insight_settings",), GAP_OPTIONS, "review_gaps"
        )
    return vol.Schema(
        {
            vol.Optional(name): section(
                vol.Schema(group.fields), {"collapsed": name != "price_coverage"}
            )
            for name, group in groups.items()
        }
    )


class ReviewFlow(ConfigEntryBaseFlow):
    """Confirm the final setup draft or return from an options overview."""

    _review_step_id = "review"

    def _review_defaults(self) -> dict[str, Any] | None:
        raise NotImplementedError

    async def _async_review_complete(self, values: dict[str, Any]) -> ConfigFlowResult:
        raise NotImplementedError

    async def async_step_review(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        values = self._review_defaults()
        if values is None:
            return self.async_abort(reason="review_unavailable")
        if user_input is not None:
            # Display-only payloads never become configuration values.
            return await self._async_review_complete(values)
        return self.async_show_form(
            step_id=self._review_step_id, data_schema=review_schema(self.hass, values)
        )

    async def async_step_overview(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self.async_step_review(user_input)
