"""Fixed fee accrual and separately billed household demand charges."""

import hashlib
import json
import re
from calendar import monthrange
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum

from .const import (
    CONF_ENERGY_SOURCE_TYPE,
    CONF_ENERGY_TAX_PER_KWH,
    CONF_FIXED_GRID_FEE_MONTHLY,
    CONF_FIXED_SUPPLIER_FEE_MONTHLY,
    CONF_GRID_FEE_HIGH_END,
    CONF_GRID_FEE_HIGH_PER_KWH,
    CONF_GRID_FEE_HIGH_SEASON_END,
    CONF_GRID_FEE_HIGH_SEASON_START,
    CONF_GRID_FEE_HIGH_START,
    CONF_GRID_FEE_PER_KWH,
    CONF_GRID_FEE_WORKDAY_ENTITY,
    CONF_PRICE_COMPLETENESS,
    CONF_PRICE_ENTITY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICE_VAT_RATE,
    CONF_PRICING_STRATEGY,
    CONF_SUPPLIER_MARKUP_PER_KWH,
)

TARIFF_SCOPE_CONFIG_KEYS = (
    CONF_PRICE_ENTITY,
    CONF_PRICING_STRATEGY,
    CONF_PRICE_INCLUDED_COMPONENTS,
    CONF_PRICE_VAT_TREATMENT,
    CONF_PRICE_VAT_RATE,
    CONF_PRICE_COMPLETENESS,
    CONF_SUPPLIER_MARKUP_PER_KWH,
    CONF_ENERGY_TAX_PER_KWH,
    CONF_GRID_FEE_PER_KWH,
    CONF_GRID_FEE_HIGH_PER_KWH,
    CONF_GRID_FEE_HIGH_START,
    CONF_GRID_FEE_HIGH_END,
    CONF_GRID_FEE_HIGH_SEASON_START,
    CONF_GRID_FEE_HIGH_SEASON_END,
    CONF_GRID_FEE_WORKDAY_ENTITY,
)


class DemandChargeCoverage(StrEnum):
    """What the user confirmed about the existing household estimate."""

    EXCLUDED = "excluded"
    INCLUDED = "included"
    UNKNOWN = "unknown"


def parse_billing_period(start: object, end: object) -> tuple[date, date]:
    """Read the invoice's inclusive local dates."""
    if not isinstance(start, str) or not isinstance(end, str):
        raise ValueError("Invalid billing dates")
    period_start, period_end = date.fromisoformat(start), date.fromisoformat(end)
    if period_end < period_start:
        raise ValueError("Invalid billing period")
    return period_start, period_end


@dataclass(frozen=True, slots=True)
class BilledDemandCharge:
    """One VAT-inclusive invoice amount for an inclusive range of local dates."""

    meter: str
    period_start: date
    period_end: date
    amount: Decimal
    currency: str
    coverage: DemandChargeCoverage
    basis: str

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> BilledDemandCharge:
        """Validate both submitted and saved amounts using the same rules."""
        meter = value["meter"]
        period_start, period_end = parse_billing_period(
            value["period_start"], value["period_end"]
        )
        amount = value["amount"]
        currency = value["currency"]
        coverage = value["coverage"]
        basis = value["basis"]
        if (
            not isinstance(meter, str)
            or not meter
            or not isinstance(amount, str)
            or not re.fullmatch(r"-?[0-9]{1,12}(?:[.,][0-9]{1,2})?", amount.strip())
            or not isinstance(currency, str)
            or not re.fullmatch(r"[A-Z]{3}", currency.strip().upper())
            or not isinstance(coverage, str)
            or not isinstance(basis, str)
        ):
            raise ValueError("Invalid billed demand charge")
        return cls(
            meter,
            period_start,
            period_end,
            Decimal(amount.strip().replace(",", ".")),
            currency.strip().upper(),
            DemandChargeCoverage(coverage),
            basis,
        )

    def as_dict(self) -> dict[str, str]:
        """Serialize the invoice without converting its amount to float."""
        return {
            "meter": self.meter,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "amount": str(self.amount),
            "currency": self.currency,
            "coverage": self.coverage.value,
            "basis": self.basis,
        }

    def matches_estimate(self, day: date, currency: str | None, basis: str) -> bool:
        """Allow a change to the breakdown only for the confirmed cost basis."""
        last_day = monthrange(day.year, day.month)[1]
        return (
            self.coverage is not DemandChargeCoverage.UNKNOWN
            and self.currency == currency
            and self.basis == basis
            and self.period_start == day.replace(day=1)
            and self.period_end == day.replace(day=last_day)
        )


def billed_demand_charges(value: object) -> tuple[BilledDemandCharge, ...]:
    """Read valid invoices even if one saved record is malformed."""
    charges = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                try:
                    charges.append(BilledDemandCharge.from_dict(item))
                except KeyError, ValueError:
                    continue
    return tuple(charges)


def demand_charge_basis(settings: Mapping[str, object], timezone: str) -> str:
    """Invalidate overlap confirmation when the underlying cost settings change."""
    keys = (
        *TARIFF_SCOPE_CONFIG_KEYS,
        CONF_ENERGY_SOURCE_TYPE,
        CONF_FIXED_SUPPLIER_FEE_MONTHLY,
        CONF_FIXED_GRID_FEE_MONTHLY,
    )
    serialized = json.dumps(
        [timezone, {key: settings[key] for key in keys if key in settings}],
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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
