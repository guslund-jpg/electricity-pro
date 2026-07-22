"""Config flow for Electricity Pro."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class ElectricityProConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle the Electricity Pro config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, object] | None = None,
    ) -> FlowResult:
        """Handle the initial configuration step."""
        if user_input is not None:
            return self.async_create_entry(
                title="Electricity Pro",
                data={},
            )

        return self.async_show_form(
            step_id="user",
        )
