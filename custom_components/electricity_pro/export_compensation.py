"""Value observed grid-export energy at a declared fixed export price."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, DecimalException


@dataclass(frozen=True, slots=True)
class FixedExportPrice:
    """A signed price in the declared currency per kWh and its validity window."""

    amount_per_kwh: Decimal
    valid_from: datetime
    valid_until: datetime | None = None


def calculate_export_compensation(
    exported_kwh: Decimal | None,
    start: datetime,
    end: datetime,
    price: FixedExportPrice | None,
) -> Decimal | None:
    """Price a measured export increment over [start, end), when fully covered."""
    if (
        exported_kwh is None
        or not exported_kwh.is_finite()
        or exported_kwh < 0
        or price is None
        or not price.amount_per_kwh.is_finite()
    ):
        return None

    valid_until = price.valid_until
    if (
        start.utcoffset() is None
        or end.utcoffset() is None
        or price.valid_from.utcoffset() is None
        or (valid_until is not None and valid_until.utcoffset() is None)
    ):
        return None

    # Compare instants across daylight-saving folds and timezone offsets.
    start_utc, end_utc = start.astimezone(UTC), end.astimezone(UTC)
    if not price.valid_from.astimezone(UTC) <= start_utc < end_utc:
        return None
    if valid_until is not None and end_utc > valid_until.astimezone(UTC):
        return None

    try:
        compensation = exported_kwh * price.amount_per_kwh
    except DecimalException:
        return None
    if compensation.is_zero():
        return Decimal(0)
    return compensation if compensation.is_finite() else None
