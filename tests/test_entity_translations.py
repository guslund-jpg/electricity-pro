"""Exercise translated entity names through Home Assistant's entity registry."""

from collections.abc import Awaitable, Callable
import json
from pathlib import Path

import pytest
from freezegun.api import FrozenDateTimeFactory

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import CONF_POWER_ENTITY, DOMAIN
from custom_components.electricity_pro.device import device_info_for_entry
from custom_components.electricity_pro.pricing import (
    PriceComponent,
    PriceComponentScope,
    PriceCompleteness,
    PricingMetadata,
    PricingStrategy,
    VatTreatment,
)

_INTEGRATION_ROOT = (
    Path(__file__).resolve().parents[1] / "custom_components/electricity_pro"
)
_FIXED_FORECAST_IDS = {
    f"cheapest_{hours}h_window_average_effective_price" for hours in (1, 2, 3)
}


def _entity_names(filename: str) -> dict[tuple[str, str], str]:
    translations = json.loads(
        (_INTEGRATION_ROOT / filename).read_text(encoding="utf-8")
    )
    return {
        (platform, key): description["name"]
        for platform, descriptions in translations["entity"].items()
        for key, description in descriptions.items()
    }


def test_english_entity_names_match_source_strings() -> None:
    """The custom integration's English resource follows its source strings."""
    assert _entity_names("strings.json") == _entity_names("translations/en.json")


@pytest.mark.parametrize("language", ["en", "sv", "fi"])
async def test_fresh_install_translates_names_but_keeps_default_ids(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_electricity_pro: Callable[..., Awaitable[MockConfigEntry]],
    language: str,
) -> None:
    """All entities keep their existing IDs in Swedish and with English fallback."""
    hass.config.language = language
    freezer.move_to("2026-11-06T20:00:00+00:00")
    entry = await setup_electricity_pro(
        price_value="1.25",
        energy_value="3.5",
        accumulated_cost_today_value="4.2",
        fixed_supplier_fee_monthly=10,
        fixed_grid_fee_monthly=20,
        current_l1_value="1",
        current_l2_value="2",
        current_l3_value="3",
        voltage_l1_value="230",
        voltage_l2_value="230",
        voltage_l3_value="230",
        monthly_peak_hour_consumption_value="3",
        monthly_peak_hour_time_value="2026-11-06T12:00:00+00:00",
        good_price_threshold=1,
        price_completeness=PriceCompleteness.COMPLETE,
        forecast_price_area="SE3",
        forecast_currency="SEK",
        forecast_nordpool_config_entry="forecast-entry-id",
        forecast_pricing_metadata=PricingMetadata(
            strategy=PricingStrategy.EXTERNAL_COMPLETE_PRICE,
            scope=PriceComponentScope(
                frozenset(PriceComponent), vat=VatTreatment.INCLUDED
            ),
            completeness=PriceCompleteness.COMPLETE,
        ),
        forecast_intervals=[
            {
                "start": "2026-11-06T21:00:00+00:00",
                "end": "2026-11-06T22:00:00+00:00",
                "price": 600,
            }
        ],
        include_flow_sources=True,
    )
    registry = er.async_get(hass)
    english = _entity_names("translations/en.json")
    swedish = _entity_names("translations/sv.json")
    assert english.keys() == swedish.keys()
    names = swedish if language == "sv" else english
    registered_entries = er.async_entries_for_config_entry(registry, entry.entry_id)
    assert len(registered_entries) == len(names)

    for (platform, key), name in names.items():
        english_name = english[platform, key]
        object_id = key if key in _FIXED_FORECAST_IDS else slugify(english_name)
        entity_id = f"{platform}.{DOMAIN}_{object_id}"
        state = hass.states.get(entity_id)
        registered = registry.async_get(entity_id)
        assert state is not None
        assert state.name == f"Electricity Pro {name}"
        assert registered is not None
        assert registered.translation_key == key
        assert registered.unique_id == f"{entry.entry_id}_{key}"


@pytest.mark.parametrize("customize", [False, True])
async def test_upgrade_preserves_existing_entity_identity(
    hass: HomeAssistant, customize: bool
) -> None:
    """A v1.7.1 registry entry acquires a translation without being replaced."""
    hass.config.language = "sv"
    source = "sensor.test_power"
    hass.states.async_set(source, "1234", {"unit_of_measurement": "W"})
    entry = MockConfigEntry(
        domain=DOMAIN, title="Electricity Pro", data={CONF_POWER_ENTITY: source}
    )
    entry.add_to_hass(hass)

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **device_info_for_entry(entry.entry_id)
    )
    registry = er.async_get(hass)
    original = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_current_power",
        config_entry=entry,
        device_id=device.id,
        has_entity_name=True,
        object_id_base="Current power",
        original_name="Current power",
    )
    assert original.entity_id == f"sensor.{DOMAIN}_current_power"
    if customize:
        original = registry.async_update_entity(
            original.entity_id,
            new_entity_id="sensor.my_grid_power",
            name="My grid power",
        )
    assert original.translation_key is None

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registered = registry.async_get(original.entity_id)
    assert registered is not None
    assert registered.id == original.id
    assert registered.device_id == original.device_id
    assert registered.unique_id == original.unique_id
    assert registered.name == original.name
    assert registered.translation_key == "current_power"
    assert registered.original_name == "Aktuell effekt"
    state = hass.states.get(original.entity_id)
    assert state is not None
    assert state.state == "1234"
    assert state.name == (
        "My grid power" if customize else "Electricity Pro Aktuell effekt"
    )
