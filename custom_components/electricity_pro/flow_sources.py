"""Explicit, independent AC generation, export and non-storage load sources."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from homeassistant.core import HomeAssistant

CHANNELS = ("production", "grid_export", "household")
FLOW_KEYS = tuple(
    f"{channel}_{quantity}_entity"
    for channel in CHANNELS
    for quantity in ("power", "energy")
)
CONF_CONFIGURE_FLOWS = "configure_energy_flows"


@dataclass(frozen=True)
class FlowReading:
    """A normalized directional reading with receipt-time provenance."""

    value: Decimal | None
    source: str | None
    reason: str
    observed_at: datetime | None = None
    original_unit: str | None = None


class FlowSources:
    """Read only explicitly selected compatible sources; never infer a flow."""

    def __init__(self, hass: HomeAssistant, settings: dict) -> None:
        self.hass = hass
        self.bindings = {key: settings.get(key) for key in FLOW_KEYS}

    @property
    def entity_ids(self) -> tuple[str, ...]:
        return tuple(value for value in self.bindings.values() if value)

    def read(self, channel: str, quantity: str, now: datetime) -> FlowReading:
        source = self.bindings[f"{channel}_{quantity}_entity"]
        if not source:
            return FlowReading(None, None, "not_configured")
        state = self.hass.states.get(source)
        if state is None:
            return FlowReading(None, source, "unavailable")
        unit = state.attributes.get("unit_of_measurement")
        at = state.last_reported
        age = (now - at).total_seconds()
        if age < 0 or age > (300 if quantity == "power" else 900):
            return FlowReading(None, source, "stale", at, unit)
        factors = (
            {"W": Decimal(1), "kW": Decimal(1000)}
            if quantity == "power"
            else {"Wh": Decimal("0.001"), "kWh": Decimal(1)}
        )
        if unit not in factors:
            return FlowReading(None, source, "unsupported_unit", at, unit)
        try:
            value = Decimal(state.state) * factors[unit]
        except (InvalidOperation, ValueError):
            return FlowReading(None, source, "unavailable", at, unit)
        if not value.is_finite() or value < 0:
            return FlowReading(None, source, "invalid", at, unit)
        return FlowReading(value, source, "measured", at, unit)
