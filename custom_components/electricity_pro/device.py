"""Shared Home Assistant device metadata for Electricity Pro entities."""

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def device_info_for_entry(entry_id: str) -> DeviceInfo:
    """Return fresh metadata with the existing entry-scoped device identity.

    Do not cache this mutable mapping or its identifiers set: each entity owns
    its metadata, while Home Assistant groups them by the stable identifier.
    """
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="Electricity Pro",
        manufacturer="Electricity Pro",
        model="Electricity monitor",
    )
