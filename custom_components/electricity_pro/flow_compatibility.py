"""Pure compatibility checks, not a site balance or energy attribution."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

PRESENCE_OPTIONS = ("unknown", "absent", "present")
PHASE_OPTIONS = ("unknown", "net_across_phases", "gross_directional")
CONF_GENERATION = "flow_generation_presence"
CONF_STORAGE = "flow_storage_presence"
CONF_ENABLED = "flow_compatibility_enabled"
CONF_CONFIGURE_COMPATIBILITY = "configure_flow_compatibility"
PHASE_KEYS = tuple(
    f"{channel}_power_phase_convention"
    for channel in ("production", "grid_export", "household")
)
COMPATIBILITY_KEYS = (CONF_GENERATION, CONF_STORAGE, CONF_ENABLED, *PHASE_KEYS)


@dataclass(frozen=True)
class PowerInput:
    """Normalized, explicitly bound whole-site directional power."""

    channel: str
    source: str
    value: Decimal | None
    received_at: datetime | None
    phase_convention: str = "unknown"
    boundary: str = "site_ac"
    reason: str = "measured"


@dataclass(frozen=True)
class CompatibilityResult:
    """Bounded diagnostic that must never be used as balance readiness."""

    status: str
    problem_channels: tuple[str, ...] = ()


def check_power_compatibility(
    inputs: tuple[PowerInput, ...], generation: str, storage: str, now: datetime,
) -> CompatibilityResult:
    """Check only the supplied power observations; never introduce zeros.

    Even 'aligned' says nothing about missing grid/battery flows, energy
    periods, physical sensor accuracy, conservation or solar attribution.
    """
    if generation not in PRESENCE_OPTIONS or storage not in PRESENCE_OPTIONS:
        return CompatibilityResult("invalid_declaration")
    if generation == "absent" and any(p.channel == "production" for p in inputs):
        return CompatibilityResult("contradictory_topology", ("production",))
    if "unknown" in (generation, storage):
        return CompatibilityResult("unknown_topology")
    if len(inputs) < 2:
        return CompatibilityResult("insufficient_sources")
    if len({p.source for p in inputs}) != len(inputs):
        return CompatibilityResult("duplicate_source")
    wrong_boundary = tuple(p.channel for p in inputs if p.boundary != "site_ac")
    if wrong_boundary:
        return CompatibilityResult("incompatible_boundary", wrong_boundary)
    unknown_phase = tuple(
        p.channel for p in inputs
        if p.phase_convention not in PHASE_OPTIONS or p.phase_convention == "unknown"
    )
    if unknown_phase:
        return CompatibilityResult("unknown_convention", unknown_phase)
    if len({p.phase_convention for p in inputs}) != 1:
        return CompatibilityResult("incompatible_conventions")
    if now.tzinfo is None:
        return CompatibilityResult("invalid_timestamp")
    times = []
    for p in inputs:
        if p.received_at is None or p.received_at.tzinfo is None:
            return CompatibilityResult("missing_timestamp", (p.channel,))
        received = p.received_at.astimezone(UTC)
        age = (now.astimezone(UTC) - received).total_seconds()
        if age < 0:
            return CompatibilityResult("future_timestamp", (p.channel,))
        if age > 300:
            return CompatibilityResult("stale_source", (p.channel,))
        if p.value is None:
            return CompatibilityResult("invalid_or_unavailable_source", (p.channel,))
        if not p.value.is_finite() or p.value < 0:
            return CompatibilityResult("invalid_or_unavailable_source", (p.channel,))
        times.append(received)
    if (max(times) - min(times)).total_seconds() > 30:
        return CompatibilityResult("time_skew")
    return CompatibilityResult("aligned")
