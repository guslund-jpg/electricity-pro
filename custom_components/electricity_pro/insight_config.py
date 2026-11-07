"""Shared Good Time configuration without changing the evaluation model."""

from decimal import Decimal, InvalidOperation
from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigEntryBaseFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ADAPTIVE_PRICE_CEILING,
    CONF_ADAPTIVE_TARGET_PERCENTILE,
    CONF_GOOD_PRICE_MODE,
    CONF_GOOD_PRICE_THRESHOLD,
    DEFAULT_ADAPTIVE_TARGET_PERCENTILE,
    GOOD_PRICE_MODE_ADAPTIVE,
    GOOD_PRICE_MODE_FIXED,
)

INSIGHT_KEYS = (
    CONF_GOOD_PRICE_MODE,
    CONF_GOOD_PRICE_THRESHOLD,
    CONF_ADAPTIVE_TARGET_PERCENTILE,
    CONF_ADAPTIVE_PRICE_CEILING,
)


def insight_schema(values: dict[str, Any]) -> vol.Schema:
    """Show only applicable controls; optional amounts remain clearable."""
    mode = values[CONF_GOOD_PRICE_MODE]
    fields: dict[Any, Any] = {
        vol.Required(CONF_GOOD_PRICE_MODE, default=mode): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[GOOD_PRICE_MODE_FIXED, GOOD_PRICE_MODE_ADAPTIVE],
                translation_key="good_price_mode",
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional(CONF_GOOD_PRICE_THRESHOLD): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, step=0.001, mode=selector.NumberSelectorMode.BOX
            )
        ),
    }
    if mode == GOOD_PRICE_MODE_ADAPTIVE:
        fields[
            vol.Required(
                CONF_ADAPTIVE_TARGET_PERCENTILE,
                default=values[CONF_ADAPTIVE_TARGET_PERCENTILE],
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=100,
                step=1,
                unit_of_measurement="%",
                mode=selector.NumberSelectorMode.BOX,
            )
        )
        fields[vol.Optional(CONF_ADAPTIVE_PRICE_CEILING)] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                step=0.001, mode=selector.NumberSelectorMode.BOX
            )
        )
    return vol.Schema(fields)


def insight_errors(values: dict[str, Any]) -> dict[str, str]:
    """Reject invalid displayed inputs before saving or hiding a draft."""
    checks: list[tuple[str, str, Decimal | None, Decimal | None]] = [
        (CONF_GOOD_PRICE_THRESHOLD, "invalid_insight_threshold", Decimal(0), None)
    ]
    if values[CONF_GOOD_PRICE_MODE] == GOOD_PRICE_MODE_ADAPTIVE:
        checks.extend(
            [
                (
                    CONF_ADAPTIVE_TARGET_PERCENTILE,
                    "invalid_insight_percentile",
                    Decimal(1),
                    Decimal(100),
                ),
                (CONF_ADAPTIVE_PRICE_CEILING, "invalid_insight_ceiling", None, None),
            ]
        )
    errors = {}
    for key, error, minimum, maximum in checks:
        value = values.get(key)
        if value is None and key != CONF_ADAPTIVE_TARGET_PERCENTILE:
            continue
        try:
            amount = Decimal(str(value))
            if (
                not amount.is_finite()
                or (minimum is not None and amount < minimum)
                or (maximum is not None and amount > maximum)
            ):
                raise ValueError
        except InvalidOperation, ValueError:
            errors[key] = error
    return errors


class InsightFlow(ConfigEntryBaseFlow):
    """Draft method changes and preserve inactive settings until completion."""

    _insight_values: dict[str, Any] | None = None
    _insight_had_threshold = False

    def _insight_defaults(self) -> dict[str, Any]:
        raise NotImplementedError

    async def _async_insights_complete(
        self, values: dict[str, Any]
    ) -> ConfigFlowResult:
        raise NotImplementedError

    async def async_step_insights(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Review fixed or adaptive Good Time settings with the same flow."""
        if self._insight_values is None:
            defaults = self._insight_defaults()
            self._insight_had_threshold = CONF_GOOD_PRICE_THRESHOLD in defaults
            self._insight_values = {
                key: defaults[key] for key in INSIGHT_KEYS if key in defaults
            }
            if self._insight_values.get(CONF_GOOD_PRICE_MODE) not in (
                GOOD_PRICE_MODE_FIXED,
                GOOD_PRICE_MODE_ADAPTIVE,
            ):
                self._insight_values[CONF_GOOD_PRICE_MODE] = GOOD_PRICE_MODE_FIXED
            if self._insight_values.get(CONF_ADAPTIVE_TARGET_PERCENTILE) is None:
                self._insight_values[CONF_ADAPTIVE_TARGET_PERCENTILE] = (
                    DEFAULT_ADAPTIVE_TARGET_PERCENTILE
                )
        errors = {}
        if user_input is not None:
            previous_mode = self._insight_values[CONF_GOOD_PRICE_MODE]
            next_mode = user_input[CONF_GOOD_PRICE_MODE]
            for marker in insight_schema(self._insight_values).schema:
                if marker.schema != CONF_GOOD_PRICE_MODE:
                    self._insight_values[marker.schema] = user_input.get(marker.schema)
            errors = insight_errors(self._insight_values)
            if next_mode not in (GOOD_PRICE_MODE_FIXED, GOOD_PRICE_MODE_ADAPTIVE):
                errors["base"] = "invalid_good_price_settings"
            if not errors:
                self._insight_values[CONF_GOOD_PRICE_MODE] = next_mode
                if next_mode == previous_mode:
                    values = dict(self._insight_values)
                    if (
                        not self._insight_had_threshold
                        and values.get(CONF_GOOD_PRICE_THRESHOLD) is None
                    ):
                        # Key presence controls entity creation. An untouched blank
                        # must not turn an unconfigured fixed rule into an entity.
                        values.pop(CONF_GOOD_PRICE_THRESHOLD, None)
                    return await self._async_insights_complete(values)
        return self.async_show_form(
            step_id="insights_adaptive"
            if self._insight_values[CONF_GOOD_PRICE_MODE] == GOOD_PRICE_MODE_ADAPTIVE
            else "insights",
            data_schema=self.add_suggested_values_to_schema(
                insight_schema(self._insight_values), self._insight_values
            ),
            errors=errors,
        )

    async def async_step_insights_adaptive(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Use the same draft with adaptive-specific labels and controls."""
        return await self.async_step_insights(user_input)
