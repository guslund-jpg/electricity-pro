"""Tests for provider-independent grid-tariff schedules."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from custom_components.electricity_pro.grid_tariff import HighLowGridTariff

STOCKHOLM = ZoneInfo("Europe/Stockholm")


@pytest.fixture
def western_orust_tariff() -> HighLowGridTariff:
    """Return the verified 2026 Västra Orust high/low schedule."""
    return HighLowGridTariff(
        low_fee_per_kwh=Decimal("0.125"),
        high_fee_per_kwh=Decimal("0.250"),
        high_start_time=time(6),
        high_end_time=time(22),
        high_season_start=(11, 1),
        high_season_end=(3, 31),
        excluded_dates=frozenset({date(2026, 12, 25)}),
    )


@pytest.mark.parametrize(
    ("local_at", "expected"),
    [
        (datetime(2026, 11, 2, 6, 0, tzinfo=STOCKHOLM), Decimal("0.250")),
        (datetime(2026, 3, 31, 21, 59, tzinfo=STOCKHOLM), Decimal("0.250")),
        (datetime(2026, 11, 2, 5, 59, tzinfo=STOCKHOLM), Decimal("0.125")),
        (datetime(2026, 11, 2, 22, 0, tzinfo=STOCKHOLM), Decimal("0.125")),
        (datetime(2026, 10, 30, 12, 0, tzinfo=STOCKHOLM), Decimal("0.125")),
        (datetime(2026, 4, 1, 12, 0, tzinfo=STOCKHOLM), Decimal("0.125")),
        (datetime(2026, 11, 7, 12, 0, tzinfo=STOCKHOLM), Decimal("0.125")),
        (datetime(2026, 12, 25, 12, 0, tzinfo=STOCKHOLM), Decimal("0.125")),
    ],
)
def test_western_orust_schedule(
    western_orust_tariff: HighLowGridTariff,
    local_at: datetime,
    expected: Decimal,
) -> None:
    """The real tariff should honor season, hours, weekdays, and holidays."""
    assert western_orust_tariff.fee_at(local_at) == expected


def test_supports_non_wrapping_seasons_and_overnight_periods() -> None:
    """The core should support other providers without provider branches."""
    tariff = HighLowGridTariff(
        low_fee_per_kwh=Decimal("0.10"),
        high_fee_per_kwh=Decimal("0.20"),
        high_start_time=time(22),
        high_end_time=time(6),
        high_season_start=(4, 1),
        high_season_end=(10, 31),
        high_weekdays=frozenset(range(7)),
    )

    assert tariff.fee_at(
        datetime(2026, 7, 1, 23, 0, tzinfo=STOCKHOLM)
    ) == Decimal("0.20")
    assert tariff.fee_at(
        datetime(2026, 7, 2, 5, 59, tzinfo=STOCKHOLM)
    ) == Decimal("0.20")
    assert tariff.fee_at(
        datetime(2026, 7, 2, 6, 0, tzinfo=STOCKHOLM)
    ) == Decimal("0.10")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"low_fee_per_kwh": Decimal("-0.01")},
        {"high_fee_per_kwh": Decimal("NaN")},
        {"high_start_time": time(6), "high_end_time": time(6)},
        {"high_season_start": (2, 30)},
        {"high_weekdays": frozenset()},
        {"high_weekdays": frozenset({7})},
    ],
)
def test_rejects_invalid_schedules(kwargs: dict[str, object]) -> None:
    """Invalid or ambiguous tariff schedules should fail clearly."""
    settings: dict[str, object] = {
        "low_fee_per_kwh": Decimal("0.10"),
        "high_fee_per_kwh": Decimal("0.20"),
        "high_start_time": time(6),
        "high_end_time": time(22),
        "high_season_start": (11, 1),
        "high_season_end": (3, 31),
    }
    settings.update(kwargs)

    with pytest.raises(ValueError):
        HighLowGridTariff(**settings)  # type: ignore[arg-type]


def test_requires_timezone_aware_local_datetime(
    western_orust_tariff: HighLowGridTariff,
) -> None:
    """Naive datetimes must not be silently interpreted in the wrong timezone."""
    with pytest.raises(ValueError, match="local timezone"):
        western_orust_tariff.fee_at(datetime(2026, 11, 2, 12, 0))
