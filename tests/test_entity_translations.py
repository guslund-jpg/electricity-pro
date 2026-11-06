"""Exercise translated entity names through Home Assistant's entity registry."""

from collections.abc import Awaitable, Callable
import json
from pathlib import Path

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electricity_pro.const import CONF_POWER_ENTITY, DOMAIN
from custom_components.electricity_pro.device import device_info_for_entry

_ENGLISH_NAMES = {
    "current_power": "Current power",
    "current_supplier_price": "Current supplier price",
    "effective_price": "Effective price",
}
_SWEDISH_NAMES = {
    "current_power": "Aktuell effekt",
    "current_supplier_price": "Aktuellt elhandelspris",
    "effective_price": "Effektivt elpris",
}


def test_english_entity_names_match_source_strings() -> None:
    """The custom integration's English resource follows its source strings."""
    root = Path(__file__).resolve().parents[1] / "custom_components/electricity_pro"
    source = json.loads((root / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((root / "translations/en.json").read_text(encoding="utf-8"))
    assert source["entity"] == english["entity"]


@pytest.mark.parametrize(
    ("language", "names"),
    [("en", _ENGLISH_NAMES), ("sv", _SWEDISH_NAMES), ("fi", _ENGLISH_NAMES)],
)
async def test_fresh_install_translates_names_but_keeps_default_ids(
    hass: HomeAssistant,
    setup_electricity_pro: Callable[..., Awaitable[MockConfigEntry]],
    language: str,
    names: dict[str, str],
) -> None:
    """Built-in dashboard IDs work in Swedish and with English fallback."""
    hass.config.language = language
    entry = await setup_electricity_pro(price_value="1.25")
    registry = er.async_get(hass)

    for key, name in names.items():
        entity_id = f"sensor.{DOMAIN}_{key}"
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
