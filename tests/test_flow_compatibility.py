"""Pure alignment checks do not imply a complete balance or structural zeros."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from custom_components.electricity_pro.flow_compatibility import (
    PowerInput, check_power_compatibility,
)

NOW = datetime(2026, 9, 16, 12, tzinfo=UTC)


def inputs():
    return (
        PowerInput("production", "p", Decimal(1000), NOW, "net_across_phases"),
        PowerInput("household", "h", Decimal(500), NOW, "net_across_phases"),
    )


def assess(values=None, generation="present", storage="absent", now=NOW):
    return check_power_compatibility(inputs() if values is None else values, generation, storage, now)


@pytest.mark.parametrize("storage", ["present", "absent"])
def test_aligned_is_only_a_receipt_time_input_check(storage):
    assert assess(storage=storage).status == "aligned"
    assert assess(tuple(replace(p, value=Decimal(0)) for p in inputs()), storage=storage).status == "aligned"


@pytest.mark.parametrize("generation,storage,expected", [
    ("unknown", "absent", "unknown_topology"),
    ("present", "unknown", "unknown_topology"),
    ("absent", "absent", "contradictory_topology"),
    ("invalid", "present", "invalid_declaration"),
])
def test_topology_is_explicit(generation, storage, expected):
    assert assess(generation=generation, storage=storage).status == expected


def test_absence_never_inserts_a_missing_flow():
    assert assess((), "absent", "absent").status == "insufficient_sources"
    assert assess((inputs()[1],), "absent", "absent").status == "insufficient_sources"


@pytest.mark.parametrize("changes,expected", [
    ({"source": "p"}, "duplicate_source"),
    ({"boundary": "dc"}, "incompatible_boundary"),
    ({"boundary": "subsystem_ac"}, "incompatible_boundary"),
    ({"phase_convention": "unknown"}, "unknown_convention"),
    ({"phase_convention": "gross_directional"}, "incompatible_conventions"),
    ({"value": None}, "invalid_or_unavailable_source"),
    ({"value": Decimal("-1")}, "invalid_or_unavailable_source"),
    ({"value": Decimal("NaN")}, "invalid_or_unavailable_source"),
    ({"value": Decimal("Infinity")}, "invalid_or_unavailable_source"),
    ({"received_at": None}, "missing_timestamp"),
    ({"received_at": NOW.replace(tzinfo=None)}, "missing_timestamp"),
    ({"received_at": NOW + timedelta(microseconds=1)}, "future_timestamp"),
])
def test_unsafe_input_blocks_assessment(changes, expected):
    p, h = inputs()
    assert assess((p, replace(h, **changes))).status == expected


@pytest.mark.parametrize("age,expected", [
    (299.999, "aligned"), (300, "aligned"), (300.001, "stale_source"),
])
def test_freshness_boundaries(age, expected):
    assert assess(tuple(replace(p, received_at=NOW - timedelta(seconds=age)) for p in inputs())).status == expected


@pytest.mark.parametrize("skew,expected", [
    (29.999, "aligned"), (30, "aligned"), (30.001, "time_skew"),
])
def test_alignment_boundaries(skew, expected):
    p, h = inputs()
    assert assess((p, replace(h, received_at=NOW - timedelta(seconds=skew)))).status == expected


def test_dst_elapsed_time_is_utc_not_wall_clock():
    zone = ZoneInfo("Europe/Stockholm")
    first = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=0)
    second = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=1)
    values = tuple(replace(p, received_at=first) for p in inputs())
    assert assess(values, now=second).status == "stale_source"


def test_two_gross_directional_sources_are_compatible_without_assuming_exclusivity():
    values = tuple(replace(p, phase_convention="gross_directional") for p in inputs())
    assert assess(values).status == "aligned"
