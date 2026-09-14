"""Calendar-based accrual of VAT-inclusive fixed household charges."""

from calendar import monthrange
from datetime import datetime, time, timedelta
from decimal import Decimal


def accrued_fixed_fees(
    now: datetime, supplier: Decimal | None, grid: Decimal | None,
) -> tuple[Decimal, Decimal, tuple[str, ...]]:
    """Allocate monthly fees by local calendar days and elapsed fraction of today."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Fixed fees require local timezone-aware time")
    missing = tuple(
        name for name, value in (
            ("fixed_supplier_fee", supplier), ("fixed_grid_fee", grid),
        )
        if value is None or not value.is_finite() or value < 0
    )
    fee = sum((
        value for value in (supplier, grid)
        if value is not None and value.is_finite() and value >= 0
    ), Decimal(0))
    midnight = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
    tomorrow = datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=now.tzinfo)
    fraction = Decimal(str(now.timestamp() - midnight.timestamp())) / Decimal(
        str(tomorrow.timestamp() - midnight.timestamp())
    )
    daily_share = fee / Decimal(monthrange(now.year, now.month)[1])
    return (
        daily_share * fraction,
        daily_share * (Decimal(now.day - 1) + fraction),
        missing,
    )
