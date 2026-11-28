"""Explicit ordered adapters for the existing statistics checkpoint sections."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# Stored JSON remains untrusted; the owning models validate each section.
type Checkpoint = Mapping[str, Any]


def section(key: str, value: object | None) -> dict[str, Any]:
    """Omit only a missing value; preserve known zero and empty collections."""
    return {} if value is None else {key: value}


def _empty_dump() -> dict[str, Any]:
    return {}


@dataclass(frozen=True, slots=True)
class StatisticsComponent:
    """Pair a section's keys, scope, load/dump and invalid-state recovery."""

    keys: tuple[str, ...]
    load: Callable[[Checkpoint], None]
    dump: Callable[[], dict[str, Any]] = _empty_dump
    warning: str | None = None
    scope: Callable[[Checkpoint], bool] | None = None
    recover: Callable[[Checkpoint], None] | None = None

    def applies(self, stored: Checkpoint) -> bool:
        return self.scope(stored) if self.scope is not None else self.keys[0] in stored


def restore_components(
    stored: Checkpoint,
    components: Sequence[StatisticsComponent],
    warn: Callable[[str], None],
) -> None:
    """Isolate expected invalid payloads, retaining each owner's recovery rule."""
    for component in components:
        if not component.applies(stored):
            continue
        try:
            component.load(stored)
        except KeyError, ValueError, TypeError, ArithmeticError:
            # Components such as export own their more specific pause policy.
            # Their unexpected failures must not fall back to empty statistics.
            if component.warning is None:
                raise
            if component.recover is not None:
                component.recover(stored)
            warn(component.warning)


def dump_components(components: Sequence[StatisticsComponent]) -> dict[str, Any]:
    """Serialize in registration order without changing keys or payloads."""
    data: dict[str, Any] = {}
    for component in components:
        data.update(component.dump())
    return data
