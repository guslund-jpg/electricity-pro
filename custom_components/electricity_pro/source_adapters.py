"""Discovery adapters for supported Home Assistant source integrations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from .const import (
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
    CONF_CURRENT_L1_ENTITY,
    CONF_CURRENT_L2_ENTITY,
    CONF_CURRENT_L3_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
    CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
    CONF_PEAK_POWER_TODAY_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_ENTITY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICING_STRATEGY,
    CONF_SOURCE_PROFILE,
    CONF_VOLTAGE_L1_ENTITY,
    CONF_VOLTAGE_L2_ENTITY,
    CONF_VOLTAGE_L3_ENTITY,
)
from .pricing import (
    PriceComponent,
    PriceCompleteness,
    PricingStrategy,
    VatTreatment,
)


class RegistryEntity(Protocol):
    """Entity-registry fields used by source discovery."""

    entity_id: str
    platform: str
    device_id: str | None
    translation_key: str | None
    disabled_by: object | None


@dataclass(frozen=True)
class DiscoveredSource:
    """A reviewable set of entities discovered for one physical home."""

    device_id: str
    data: dict[str, object]

    @property
    def is_complete_tibber_fast_track(self) -> bool:
        """Return whether the required Tibber fast-track sources exist."""
        return CONF_POWER_ENTITY in self.data and CONF_PRICE_ENTITY in self.data


_TIBBER_ENTITY_MAP = {
    "electricity_price": CONF_PRICE_ENTITY,
    "power": CONF_POWER_ENTITY,
    "accumulated_consumption": CONF_ENERGY_ENTITY,
    "accumulated_cost": CONF_ACCUMULATED_COST_TODAY_ENTITY,
    "max_power": CONF_PEAK_POWER_TODAY_ENTITY,
    "current_l1": CONF_CURRENT_L1_ENTITY,
    "current_l2": CONF_CURRENT_L2_ENTITY,
    "current_l3": CONF_CURRENT_L3_ENTITY,
    "voltage_phase1": CONF_VOLTAGE_L1_ENTITY,
    "voltage_phase2": CONF_VOLTAGE_L2_ENTITY,
    "voltage_phase3": CONF_VOLTAGE_L3_ENTITY,
    "peak_hour": CONF_MONTHLY_PEAK_HOUR_CONSUMPTION_ENTITY,
    "peak_hour_time": CONF_MONTHLY_PEAK_HOUR_TIME_ENTITY,
}

_TIBBER_PRICE_METADATA: dict[str, object] = {
    CONF_SOURCE_PROFILE: "tibber",
    CONF_PRICING_STRATEGY: PricingStrategy.SUPPLIER_CONTRACTED_PRICE.value,
    CONF_PRICE_INCLUDED_COMPONENTS: [
        PriceComponent.ENERGY_TAX.value,
        PriceComponent.MARKET_ENERGY.value,
        PriceComponent.SUPPLIER_MARKUP.value,
    ],
    CONF_PRICE_VAT_TREATMENT: VatTreatment.INCLUDED.value,
    CONF_PRICE_COMPLETENESS: PriceCompleteness.PARTIAL.value,
}


def discover_tibber_sources(
    entities: Iterable[RegistryEntity],
) -> list[DiscoveredSource]:
    """Discover enabled Tibber entities, grouped by Home Assistant device."""
    by_device: dict[str, dict[str, object]] = {}

    for entity in entities:
        if (
            entity.platform != "tibber"
            or entity.device_id is None
            or entity.disabled_by is not None
            or entity.translation_key not in _TIBBER_ENTITY_MAP
        ):
            continue

        config_key = _TIBBER_ENTITY_MAP[entity.translation_key]
        by_device.setdefault(entity.device_id, {})[config_key] = entity.entity_id

    discovered: list[DiscoveredSource] = []
    for device_id, data in sorted(by_device.items()):
        if CONF_PRICE_ENTITY in data:
            data.update(_TIBBER_PRICE_METADATA)
        discovered.append(DiscoveredSource(device_id=device_id, data=data))

    return discovered
