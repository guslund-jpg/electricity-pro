"""Tests for source discovery adapters."""

from __future__ import annotations

from dataclasses import dataclass

from custom_components.electricity_pro.const import (
    CONF_ACCUMULATED_COST_TODAY_ENTITY,
    CONF_CURRENT_L1_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_ENERGY_SOURCE_TYPE,
    CONF_POWER_ENTITY,
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_ENTITY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICING_STRATEGY,
    CONF_SOURCE_PROFILE,
    ENERGY_SOURCE_DAILY,
)
from custom_components.electricity_pro.pricing import (
    PriceComponent,
    PriceCompleteness,
    PricingStrategy,
    VatTreatment,
)
from custom_components.electricity_pro.source_adapters import discover_tibber_sources


@dataclass
class FakeRegistryEntity:
    """Minimal entity-registry entry for discovery tests."""

    entity_id: str
    translation_key: str | None
    device_id: str | None = "home-1"
    platform: str = "tibber"
    disabled_by: object | None = None


def test_discovers_tibber_capabilities_without_entity_name_assumptions() -> None:
    """Discovery should use stable registry metadata, not editable entity IDs."""
    sources = discover_tibber_sources(
        [
            FakeRegistryEntity("sensor.my_renamed_live_load", "power"),
            FakeRegistryEntity("sensor.my_renamed_contract_rate", "electricity_price"),
            FakeRegistryEntity("sensor.energy_so_far", "accumulated_consumption"),
            FakeRegistryEntity("sensor.cost_so_far", "accumulated_cost"),
            FakeRegistryEntity("sensor.phase_one", "current_l1"),
        ]
    )

    assert len(sources) == 1
    source = sources[0]
    assert source.is_complete_tibber_fast_track
    assert source.data[CONF_POWER_ENTITY] == "sensor.my_renamed_live_load"
    assert source.data[CONF_PRICE_ENTITY] == "sensor.my_renamed_contract_rate"
    assert source.data[CONF_ENERGY_ENTITY] == "sensor.energy_so_far"
    assert source.data[CONF_ENERGY_SOURCE_TYPE] == ENERGY_SOURCE_DAILY
    assert source.data[CONF_ACCUMULATED_COST_TODAY_ENTITY] == "sensor.cost_so_far"
    assert source.data[CONF_CURRENT_L1_ENTITY] == "sensor.phase_one"
    assert source.data[CONF_PRICING_STRATEGY] == (
        PricingStrategy.SUPPLIER_CONTRACTED_PRICE.value
    )
    assert source.data[CONF_PRICE_INCLUDED_COMPONENTS] == [
        PriceComponent.MARKET_ENERGY.value,
        PriceComponent.SUPPLIER_MARKUP.value,
    ]
    assert source.data[CONF_PRICE_VAT_TREATMENT] == VatTreatment.INCLUDED.value
    assert source.data[CONF_PRICE_COMPLETENESS] == PriceCompleteness.PARTIAL.value
    assert source.data[CONF_SOURCE_PROFILE] == "tibber"


def test_groups_homes_and_ignores_disabled_or_unrelated_entities() -> None:
    """Each Tibber home should be reviewable as a separate source."""
    sources = discover_tibber_sources(
        [
            FakeRegistryEntity("sensor.home_1_power", "power"),
            FakeRegistryEntity(
                "sensor.home_1_disabled_price",
                "electricity_price",
                disabled_by="integration",
            ),
            FakeRegistryEntity(
                "sensor.home_2_power", "power", device_id="home-2"
            ),
            FakeRegistryEntity(
                "sensor.home_2_price", "electricity_price", device_id="home-2"
            ),
            FakeRegistryEntity(
                "sensor.other_power", "power", platform="other_integration"
            ),
        ]
    )

    assert [source.device_id for source in sources] == ["home-1", "home-2"]
    assert not sources[0].is_complete_tibber_fast_track
    assert sources[1].is_complete_tibber_fast_track
