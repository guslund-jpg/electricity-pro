"""Shared grid-charge forms; persist existing amounts, never a UI tariff mode."""

from datetime import time
from decimal import Decimal, InvalidOperation
from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigEntryBaseFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ENERGY_TAX_PER_KWH,
    CONF_FIXED_GRID_FEE_MONTHLY,
    CONF_GRID_FEE_HIGH_END,
    CONF_GRID_FEE_HIGH_PER_KWH,
    CONF_GRID_FEE_HIGH_SEASON_END,
    CONF_GRID_FEE_HIGH_SEASON_START,
    CONF_GRID_FEE_HIGH_START,
    CONF_GRID_FEE_PER_KWH,
    CONF_GRID_FEE_WORKDAY_ENTITY,
)
from .grid_tariff import HighLowGridTariff

CONF_GRID_MODE = "grid_mode"
UNCONFIGURED = "unconfigured"
CONSTANT = "constant"
TIME_OF_USE = "time_of_use"
AMOUNT_KEYS = (
    CONF_GRID_FEE_PER_KWH,
    CONF_ENERGY_TAX_PER_KWH,
    CONF_FIXED_GRID_FEE_MONTHLY,
)
SCHEDULE_DEFAULTS = {
    CONF_GRID_FEE_HIGH_START: "06:00",
    CONF_GRID_FEE_HIGH_END: "22:00",
    CONF_GRID_FEE_HIGH_SEASON_START: "11-01",
    CONF_GRID_FEE_HIGH_SEASON_END: "03-31",
}
TARIFF_KEYS = (
    CONF_GRID_FEE_HIGH_PER_KWH,
    *SCHEDULE_DEFAULTS,
    CONF_GRID_FEE_WORKDAY_ENTITY,
)
GRID_KEYS = (*AMOUNT_KEYS, *TARIFF_KEYS)


def without_grid_fields(schema: vol.Schema) -> vol.Schema:
    """Keep owned charges off other sections."""
    return vol.Schema(
        {
            key: value
            for key, value in schema.schema.items()
            if key.schema not in GRID_KEYS
        }
    )


def grid_mode(values: dict[str, Any]) -> str:
    """Infer the tariff from amounts; zero is known, dormant schedules are not fees."""
    if values.get(CONF_GRID_FEE_HIGH_PER_KWH) is not None:
        return TIME_OF_USE
    if any(values.get(key) is not None for key in AMOUNT_KEYS):
        return CONSTANT
    return UNCONFIGURED


def grid_schema(mode: str) -> vol.Schema:
    """Offer applicable fields as clearable suggestions, not implicit defaults."""
    fields: dict[Any, Any] = {
        vol.Required(CONF_GRID_MODE, default=mode): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[UNCONFIGURED, CONSTANT, TIME_OF_USE],
                translation_key="grid_mode",
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
    }
    if mode == UNCONFIGURED:
        return vol.Schema(fields)
    amount_selector = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, step=0.001, mode=selector.NumberSelectorMode.BOX
        )
    )
    fields[vol.Optional(CONF_GRID_FEE_PER_KWH)] = amount_selector
    if mode == TIME_OF_USE:
        fields[vol.Optional(CONF_GRID_FEE_HIGH_PER_KWH)] = amount_selector
        fields.update(
            {vol.Optional(key): selector.TextSelector() for key in SCHEDULE_DEFAULTS}
        )
        fields[vol.Optional(CONF_GRID_FEE_WORKDAY_ENTITY)] = selector.EntitySelector(
            selector.EntitySelectorConfig(
                filter={"domain": "binary_sensor", "integration": "workday"}
            )
        )
    for key in (CONF_ENERGY_TAX_PER_KWH, CONF_FIXED_GRID_FEE_MONTHLY):
        fields[vol.Optional(key)] = amount_selector
    return vol.Schema(fields)


def grid_errors(values: dict[str, Any], mode: str) -> dict[str, str]:
    """Validate only the selected tariff, with no invented zero amounts."""
    errors = {}
    for key in (
        *AMOUNT_KEYS,
        *((CONF_GRID_FEE_HIGH_PER_KWH,) if mode == TIME_OF_USE else ()),
    ):
        if values.get(key) is None:
            continue
        try:
            amount = Decimal(str(values[key]))
            if not amount.is_finite() or amount < 0:
                raise ValueError
        except InvalidOperation, ValueError:
            errors[key] = "invalid_grid_amount"
    if errors:
        return errors
    if mode == CONSTANT and not any(values.get(key) is not None for key in AMOUNT_KEYS):
        return {"base": "grid_amount_required"}
    if mode == TIME_OF_USE:
        for key in (CONF_GRID_FEE_PER_KWH, CONF_GRID_FEE_HIGH_PER_KWH):
            if values.get(key) is None:
                errors[key] = "grid_rate_required"
        if errors:
            return errors
        try:
            HighLowGridTariff(
                low_fee_per_kwh=Decimal(str(values[CONF_GRID_FEE_PER_KWH])),
                high_fee_per_kwh=Decimal(str(values[CONF_GRID_FEE_HIGH_PER_KWH])),
                high_start_time=time.fromisoformat(
                    str(values.get(CONF_GRID_FEE_HIGH_START))
                ),
                high_end_time=time.fromisoformat(
                    str(values.get(CONF_GRID_FEE_HIGH_END))
                ),
                high_season_start=_month_day(
                    values.get(CONF_GRID_FEE_HIGH_SEASON_START)
                ),
                high_season_end=_month_day(values.get(CONF_GRID_FEE_HIGH_SEASON_END)),
            )
        except TypeError, ValueError:
            return {"base": "invalid_grid_tariff"}
    return {}


def _month_day(value: object) -> tuple[int, int]:
    month, day = str(value).split("-", maxsplit=1)
    return int(month), int(day)


class GridFlow(ConfigEntryBaseFlow):
    """Draft grid-only changes until successful completion or cancellation."""

    _grid_values: dict[str, Any] | None = None
    _grid_mode: str = UNCONFIGURED

    def _grid_defaults(self) -> dict[str, Any]:
        raise NotImplementedError

    async def _async_grid_complete(self, values: dict[str, Any]) -> ConfigFlowResult:
        raise NotImplementedError

    async def async_step_grid(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select applicable charges without changing saved state on mode changes."""
        if self._grid_values is None:
            defaults = self._grid_defaults()
            self._grid_values = {key: defaults.get(key) for key in GRID_KEYS}
            self._grid_mode = grid_mode(defaults)
            if self._grid_mode == TIME_OF_USE:
                # Match the runtime defaults for older entries with absent keys.
                for key, value in SCHEDULE_DEFAULTS.items():
                    if key not in defaults:
                        self._grid_values[key] = value
        errors = {}
        if user_input is not None:
            previous_mode = self._grid_mode
            mode = user_input[CONF_GRID_MODE]
            for marker in grid_schema(previous_mode).schema:
                if marker.schema in GRID_KEYS:
                    self._grid_values[marker.schema] = user_input.get(marker.schema)
            self._grid_mode = mode
            if mode == UNCONFIGURED:
                return await self._async_grid_complete(dict.fromkeys(GRID_KEYS))
            if mode != previous_mode:
                if mode == TIME_OF_USE:
                    for key, value in SCHEDULE_DEFAULTS.items():
                        if self._grid_values.get(key) is None:
                            self._grid_values[key] = value
            else:
                errors = grid_errors(self._grid_values, mode)
                if not errors:
                    values = dict(self._grid_values)
                    if mode == CONSTANT:
                        values.update(dict.fromkeys(TARIFF_KEYS))
                    return await self._async_grid_complete(values)
        return self.async_show_form(
            step_id="grid",
            data_schema=self.add_suggested_values_to_schema(
                grid_schema(self._grid_mode), self._grid_values
            ),
            errors=errors,
        )
