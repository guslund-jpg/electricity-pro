"""Calendar-based accrual of VAT-inclusive fixed household charges."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class AccruedFixedFees:
    """Fixed fee totals and the separately known monthly amounts to date."""

    today: Decimal
    month: Decimal
    supplier_month: Decimal | None
    grid_month: Decimal | None
    missing: tuple[str, ...]


def accrued_fixed_fees(
    now: datetime,
    supplier: Decimal | None,
    grid: Decimal | None,
) -> AccruedFixedFees:
    """Allocate monthly fees by local calendar days and elapsed fraction of today."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Fixed fees require local timezone-aware time")
    configured = {
        name: value
        for name, value in (
            ("fixed_supplier_fee", supplier),
            ("fixed_grid_fee", grid),
        )
        if value is not None and value.is_finite() and value >= 0
    }
    fee = sum(configured.values(), Decimal(0))
    midnight = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
    tomorrow = datetime.combine(
        now.date() + timedelta(days=1), time.min, tzinfo=now.tzinfo
    )
    fraction = Decimal(str(now.timestamp() - midnight.timestamp())) / Decimal(
        str(tomorrow.timestamp() - midnight.timestamp())
    )
    month_days = Decimal(monthrange(now.year, now.month)[1])
    elapsed_days = Decimal(now.day - 1) + fraction
    # Prorate the combined fee for the totals to preserve Decimal precision.
    daily_share = fee / month_days
    monthly_amounts = {
        name: value / month_days * elapsed_days for name, value in configured.items()
    }
    return AccruedFixedFees(
        today=daily_share * fraction,
        month=daily_share * elapsed_days,
        supplier_month=monthly_amounts.get("fixed_supplier_fee"),
        grid_month=monthly_amounts.get("fixed_grid_fee"),
        missing=tuple(
            name
            for name in ("fixed_supplier_fee", "fixed_grid_fee")
            if name not in configured
        ),
    )
