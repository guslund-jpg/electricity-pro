"""Exercise translated entity names through Home Assistant's entity registry."""

from collections.abc import Awaitable, Callable
import json
from pathlib import Path

import pytest
from freezegun.api import FrozenDateTimeFactory

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import slugify
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

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
    hass.config_entries.async_update_entry(
        entry,
        options={
            "billed_demand_charges": [
                {
                    "meter": "sensor.test_energy",
                    "period_start": "2026-10-01",
                    "period_end": "2026-10-31",
                    "amount": "150",
                    "currency": "SEK",
                    "coverage": "unknown",
                    "basis": "",
                }
            ]
        },
    )
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    english = _entity_names("translations/en.json")
    swedish = _entity_names("translations/sv.json")
    assert english.keys() == swedish.keys()
    names = swedish if language == "sv" else english
    # Recorder is not loaded in this fixture.
    names = {
        entity: name
        for entity, name in names.items()
        if not entity[1].startswith("variable_cost_")
    }
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
async def test_upgrade_preserves_existing_entity_identity_and_automation(
    hass: HomeAssistant, customize: bool
) -> None:
    """An existing automation follows the same entity through naming and reload."""
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

    # Model the old entity's state and an already-working ID-based automation.
    old_name = original.name or "Electricity Pro Current power"
    hass.states.async_set(original.entity_id, "1234", {"friendly_name": old_name})
    actions = async_mock_service(hass, "test", "record_power_alert")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": [
                {
                    "alias": "Existing power alert",
                    "triggers": [
                        {
                            "trigger": "numeric_state",
                            "entity_id": original.entity_id,
                            "above": 2000,
                        }
                    ],
                    "actions": [
                        {
                            "action": "test.record_power_alert",
                            "data": {
                                "entity_id": "{{ trigger.entity_id }}",
                                "reading": "{{ trigger.to_state.state }} W",
                                "display_name": "{{ trigger.to_state.name }}",
                            },
                        }
                    ],
                }
            ]
        },
    )
    await hass.async_start()
    await hass.async_block_till_done()
    hass.states.async_set(original.entity_id, "2345", {"friendly_name": old_name})
    await hass.async_block_till_done()
    assert [call.data for call in actions] == [
        {
            "entity_id": original.entity_id,
            "reading": "2345 W",
            "display_name": old_name,
        }
    ]
    hass.states.async_set(original.entity_id, "1234", {"friendly_name": old_name})
    await hass.async_block_till_done()

    # Unload the old runtime state, retaining the registry and automation.
    hass.states.async_remove(original.entity_id)
    await hass.async_block_till_done()
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
    expected_name = "My grid power" if customize else "Electricity Pro Aktuell effekt"
    assert state.name == expected_name
    assert len(actions) == 1

    # Real source updates must still reach the untouched automation after upgrade.
    hass.states.async_set(source, "2345", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    assert len(actions) == 2
    assert actions[-1].data == {
        "entity_id": original.entity_id,
        "reading": "2345 W",
        "display_name": expected_name,
    }

    hass.states.async_set(source, "1234", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(original.entity_id).id == original.id
    assert hass.states.get(original.entity_id).name == expected_name
    assert hass.states.get("automation.existing_power_alert").state == "on"
    assert len(actions) == 2

    hass.states.async_set(source, "3456", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    assert len(actions) == 3
    assert actions[-1].data == {
        "entity_id": original.entity_id,
        "reading": "3456 W",
        "display_name": expected_name,
    }


@pytest.mark.parametrize("language", ["en", "sv", "fi"])
@pytest.mark.parametrize(
    ("second_price", "raw_state"),
    [(2000, "rising"), (500, "falling"), (1000, "stable")],
)
async def test_price_direction_translations_keep_raw_states_and_identity(
    hass, freezer, setup_electricity_pro, language, second_price, raw_state
):
    from homeassistant.helpers import translation

    hass.config.language = language
    freezer.move_to("2026-11-07T12:00:00Z")
    entry = await setup_electricity_pro(
        forecast_price_area="SE3",
        forecast_currency="SEK",
        forecast_nordpool_config_entry="native-forecast",
        forecast_pricing_metadata=PricingMetadata(
            strategy=PricingStrategy.EXTERNAL_COMPLETE_PRICE,
            scope=PriceComponentScope(
                frozenset(PriceComponent), vat=VatTreatment.INCLUDED
            ),
            completeness=PriceCompleteness.COMPLETE,
        ),
        forecast_intervals=[
            {
                "start": "2026-11-07T12:00:00Z",
                "end": "2026-11-07T13:00:00Z",
                "price": 1000,
            },
            {
                "start": "2026-11-07T13:00:00Z",
                "end": "2026-11-07T14:00:00Z",
                "price": second_price,
            },
        ],
    )
    entity_id = "sensor.electricity_pro_price_direction"
    state = hass.states.get(entity_id)
    assert state.state == raw_state
    assert state.attributes["device_class"] == "enum"
    assert state.attributes["options"] == ["rising", "falling", "stable"]
    assert "unit_of_measurement" not in state.attributes
    assert "state_class" not in state.attributes
    registered = er.async_get(hass).async_get(entity_id)
    assert registered.unique_id == f"{entry.entry_id}_price_direction"
    labels = await translation.async_get_translations(
        hass, language, "entity", {DOMAIN}
    )
    expected = (
        {"rising": "Stigande", "falling": "Fallande", "stable": "Stabil"}
        if language == "sv"
        else {"rising": "Rising", "falling": "Falling", "stable": "Stable"}
    )
    for key, text in expected.items():
        assert (
            labels[f"component.{DOMAIN}.entity.sensor.price_direction.state.{key}"]
            == text
        )
