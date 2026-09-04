"""Binary sensor platform for Electricity Pro insights."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import ElectricityProConfigEntry
from .adaptive_price import (
    AdaptivePriceReason,
    AdaptivePriceScope,
    HistoricalPriceObservation,
    evaluate_adaptive_good_price,
)
from .calculations import calculate_declared_effective_price
from .const import (
    CONF_ADAPTIVE_PRICE_CEILING,
    CONF_ADAPTIVE_TARGET_PERCENTILE,
    CONF_GOOD_PRICE_MODE,
    CONF_GOOD_PRICE_THRESHOLD,
    DEFAULT_ADAPTIVE_TARGET_PERCENTILE,
    DOMAIN,
    GOOD_PRICE_MODE_ADAPTIVE,
    GOOD_PRICE_MODE_FIXED,
)
from .coordinator import ElectricityProCoordinator
from .provider import ElectricityProData


@dataclass(frozen=True, slots=True)
class GoodTimeEvaluation:
    """Explain one fixed or adaptive Good Time evaluation."""

    is_good: bool | None
    attributes: dict[str, Any]


def evaluate_good_time(
    data: ElectricityProData,
    *,
    mode: str = GOOD_PRICE_MODE_FIXED,
    observations: tuple[HistoricalPriceObservation, ...] = (),
    current_scope: AdaptivePriceScope | None = None,
    evaluation_time: datetime | None = None,
    target_percentile: Decimal = Decimal("0.25"),
    absolute_ceiling: Decimal | None = None,
) -> GoodTimeEvaluation:
    """Evaluate Good Time using the selected explicit method."""
    effective_price = calculate_declared_effective_price(
        data.current_price,
        data.pricing_metadata,
        data.grid_fee_per_kwh,
        data.energy_tax_per_kwh,
        data.supplier_markup_per_kwh,
    )
    common_attributes: dict[str, Any] = {
        "configured_mode": mode,
        "current_price": _decimal_attribute(effective_price),
        "fixed_threshold": _decimal_attribute(data.good_price_threshold),
    }
    if mode != GOOD_PRICE_MODE_ADAPTIVE:
        if effective_price is None:
            return GoodTimeEvaluation(
                is_good=None,
                attributes={
                    **common_attributes,
                    "evaluation_method": GOOD_PRICE_MODE_FIXED,
                    "reason": AdaptivePriceReason.INVALID_CURRENT_PRICE.value,
                },
            )
        if data.good_price_threshold is None:
            return GoodTimeEvaluation(
                is_good=None,
                attributes={
                    **common_attributes,
                    "evaluation_method": GOOD_PRICE_MODE_FIXED,
                    "reason": "fixed_threshold_not_configured",
                },
            )
        is_good = effective_price <= data.good_price_threshold
        return GoodTimeEvaluation(
            is_good=is_good,
            attributes={
                **common_attributes,
                "evaluation_method": GOOD_PRICE_MODE_FIXED,
                "reason": (
                    "within_fixed_threshold"
                    if is_good
                    else "above_fixed_threshold"
                ),
            },
        )

    adaptive = evaluate_adaptive_good_price(
        current_price=effective_price,
        current_scope=current_scope,
        observations=observations,
        evaluation_time=evaluation_time or dt_util.now(),
        target_percentile=target_percentile,
        fixed_fallback=data.good_price_threshold,
        absolute_ceiling=absolute_ceiling,
    )
    return GoodTimeEvaluation(
        is_good=adaptive.is_good,
        attributes={
            **common_attributes,
            "evaluation_method": (
                adaptive.method.value if adaptive.method is not None else None
            ),
            "reason": adaptive.reason.value,
            "adaptive_threshold": _decimal_attribute(adaptive.threshold),
            "absolute_ceiling": _decimal_attribute(absolute_ceiling),
            "target_percentile": _decimal_attribute(target_percentile),
            "current_percentile": _decimal_attribute(adaptive.current_percentile),
            "cohort_type": (
                adaptive.cohort_type.value
                if adaptive.cohort_type is not None
                else None
            ),
            "historical_days": adaptive.historical_days,
            "sample_count": adaptive.sample_count,
            "required_sample_count": adaptive.required_sample_count,
        },
    )


def good_time_to_use_electricity(data: ElectricityProData) -> bool | None:
    """Return legacy fixed-threshold behavior for compatibility."""
    return evaluate_good_time(data).is_good


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectricityProConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Electricity Pro insight binary sensors."""
    settings = {**entry.data, **entry.options}
    if (
        CONF_GOOD_PRICE_THRESHOLD not in entry.options
        and CONF_GOOD_PRICE_THRESHOLD not in entry.data
        and settings.get(CONF_GOOD_PRICE_MODE) != GOOD_PRICE_MODE_ADAPTIVE
    ):
        return

    async_add_entities([GoodTimeToUseElectricityBinarySensor(entry)])


class GoodTimeToUseElectricityBinarySensor(
    CoordinatorEntity[ElectricityProCoordinator],
    BinarySensorEntity,
):
    """Represent the Good time to use electricity insight."""

    _attr_has_entity_name = True
    _attr_name = "Good time to use electricity"
    _attr_icon = "mdi:check-circle-outline"

    def __init__(self, entry: ElectricityProConfigEntry) -> None:
        """Initialize the insight."""
        super().__init__(entry.runtime_data)
        self._attr_unique_id = f"{entry.entry_id}_good_time_to_use_electricity"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Electricity Pro",
            manufacturer="Electricity Pro",
            model="Electricity monitor",
        )
        settings = {**entry.data, **entry.options}
        configured_mode = settings.get(
            CONF_GOOD_PRICE_MODE,
            GOOD_PRICE_MODE_FIXED,
        )
        self._mode = (
            configured_mode
            if configured_mode in {GOOD_PRICE_MODE_FIXED, GOOD_PRICE_MODE_ADAPTIVE}
            else GOOD_PRICE_MODE_FIXED
        )
        self._target_percentile = _percentile_setting(
            settings.get(
                CONF_ADAPTIVE_TARGET_PERCENTILE,
                DEFAULT_ADAPTIVE_TARGET_PERCENTILE,
            )
        )
        self._absolute_ceiling = _optional_decimal(
            settings.get(CONF_ADAPTIVE_PRICE_CEILING)
        )

    @property
    def _evaluation(self) -> GoodTimeEvaluation:
        """Return the current explainable Good Time evaluation."""
        return evaluate_good_time(
            self.coordinator.data,
            mode=self._mode,
            observations=self.coordinator.adaptive_price_history.observations,
            current_scope=self.coordinator.adaptive_price_scope,
            evaluation_time=dt_util.now().astimezone(
                self.coordinator.adaptive_price_history.local_timezone
            ),
            target_percentile=self._target_percentile,
            absolute_ceiling=self._absolute_ceiling,
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether now is a good time to use electricity."""
        return self._evaluation.is_good

    @property
    def available(self) -> bool:
        """Return whether the insight has sufficient input data."""
        return (
            super().available
            and (
                self._mode == GOOD_PRICE_MODE_ADAPTIVE
                or self._evaluation.is_good is not None
            )
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the selected method and its compact explanation."""
        attributes = self._evaluation.attributes
        history = self.coordinator.adaptive_price_history
        if history.restarted_at is not None:
            attributes["history_restarted_at"] = history.restarted_at.isoformat()
        if history.restart_reason is not None:
            attributes["history_restart_reason"] = history.restart_reason
        return attributes


def _optional_decimal(value: Any) -> Decimal | None:
    """Normalize one optional finite numeric setting."""
    if value is None:
        return None
    try:
        normalized = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return normalized if normalized.is_finite() else None


def _percentile_setting(value: Any) -> Decimal:
    """Normalize a user-facing percentage to the calculation's 0-1 range."""
    percentage = _optional_decimal(value)
    if percentage is None or not Decimal(0) < percentage <= Decimal(100):
        percentage = Decimal(DEFAULT_ADAPTIVE_TARGET_PERCENTILE)
    return percentage / Decimal(100)


def _decimal_attribute(value: Decimal | None) -> str | None:
    """Serialize a Decimal for stable Home Assistant attributes."""
    return str(value) if value is not None else None
