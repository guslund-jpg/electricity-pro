"""Exercise the fixed-rate export calculation with synthetic meter increments."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from custom_components.electricity_pro.export_compensation import (
    FixedExportPrice,
    calculate_export_compensation,
)

START = datetime(2026, 11, 11, 12, tzinfo=UTC)
END = START + timedelta(minutes=15)


@pytest.mark.parametrize(
    ("exported_kwh", "rate", "expected"),
    [
        ("2.125", "0.365", "0.775625"),
        ("2", "-0.20", "-0.40"),
        ("2", "0", "0"),
        ("0", "0.30", "0"),
        ("0", "-0.20", "0"),
        (None, "0", None),
        ("-2", "0.30", None),
        ("NaN", "0.30", None),
        ("Infinity", "0.30", None),
        ("2", "NaN", None),
        ("2", "Infinity", None),
        ("1e999999", "10", None),
    ],
)
def test_fixed_export_compensation(exported_kwh, rate, expected):
    amount = calculate_export_compensation(
        Decimal(exported_kwh) if exported_kwh is not None else None,
        START,
        END,
        FixedExportPrice(Decimal(rate), START),
    )
    assert amount == (Decimal(expected) if expected is not None else None)
    if amount == 0:
        assert not amount.is_signed()


def test_fixed_price_can_cover_a_measured_increment_after_a_gap():
    later = START + timedelta(hours=2)
    price = FixedExportPrice(Decimal("0.30"), START)

    assert calculate_export_compensation(None, START, later, price) is None
    assert calculate_export_compensation(Decimal(2), START, later, price) == Decimal(
        "0.60"
    )


def test_price_change_requires_coverage_of_entire_increment():
    old = FixedExportPrice(Decimal("0.30"), START, END)
    new = FixedExportPrice(Decimal("-0.20"), END)
    later = END + timedelta(minutes=15)

    assert calculate_export_compensation(Decimal(2), START, END, old) == Decimal("0.60")
    assert calculate_export_compensation(Decimal(2), END, later, new) == Decimal(
        "-0.40"
    )
    assert calculate_export_compensation(Decimal(2), START, later, old) is None
    assert calculate_export_compensation(Decimal(2), START, later, new) is None


@pytest.mark.parametrize(
    ("start", "end", "price"),
    [
        (START, END, None),
        (END, START, FixedExportPrice(Decimal(1), START)),
        (START, START, FixedExportPrice(Decimal(1), START)),
        (START.replace(tzinfo=None), END, FixedExportPrice(Decimal(1), START)),
        (START, END.replace(tzinfo=None), FixedExportPrice(Decimal(1), START)),
        (START, END, FixedExportPrice(Decimal(1), START.replace(tzinfo=None))),
        (START, END, FixedExportPrice(Decimal(1), START, END.replace(tzinfo=None))),
    ],
)
def test_missing_price_or_invalid_observation_interval(start, end, price):
    assert calculate_export_compensation(Decimal(2), start, end, price) is None


def test_repeated_local_hour_uses_actual_price_change_instant():
    stockholm = ZoneInfo("Europe/Stockholm")
    earlier = datetime(2026, 10, 25, 2, 15, tzinfo=stockholm)
    later = earlier.replace(fold=1)
    change = datetime(2026, 10, 25, 1, tzinfo=UTC)
    old = FixedExportPrice(Decimal("0.30"), earlier, change)
    new = FixedExportPrice(Decimal("-0.20"), change)

    assert calculate_export_compensation(Decimal(2), earlier, change, old) == Decimal(
        "0.60"
    )
    assert calculate_export_compensation(Decimal(2), change, later, new) == Decimal(
        "-0.40"
    )
    assert calculate_export_compensation(Decimal(2), earlier, later, old) is None
    assert calculate_export_compensation(Decimal(2), earlier, later, new) is None
