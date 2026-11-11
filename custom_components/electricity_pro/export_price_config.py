"""Validation and effective periods for the fixed export price."""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import TypedDict

import probatio as vol
from homeassistant.helpers import config_validation as cv


EXPORT_PRICE_PERIODS = "export_price_periods"
EXPORT_ENERGY_SOURCE = "grid_export_energy_entity"
EXPORT_VAT_OPTIONS = ("included", "excluded", "not_applicable")
EXPORT_COMPONENTS = (
    "supplier_compensation",
    "grid_compensation",
    "variable_deductions",
)


class ExportPriceTerms(TypedDict):
    """Declared terms in the currency of the export agreement per kWh."""

    meter: str
    amount_per_kwh: str
    currency: str
    vat_treatment: str
    components: list[str]


class ExportPricePeriod(ExportPriceTerms):
    """Terms effective from a UTC instant up to an exclusive end."""

    valid_from: str
    valid_until: str | None


def parse_export_price_terms(
    meter: str,
    amount: str,
    currency: str,
    vat_treatment: str,
    components: list[str],
) -> tuple[ExportPriceTerms | None, dict[str, str]]:
    """Normalize a declared export price or return its field errors."""
    errors = {}
    try:
        rate = Decimal(amount.strip().replace(",", "."))
    except InvalidOperation:
        rate = None
    if rate is None or not rate.is_finite():
        errors["export_price_amount"] = "invalid_export_price"
    currency = currency.strip().upper()
    try:
        cv.currency(currency)
    except vol.Invalid:
        errors["export_price_currency"] = "invalid_export_currency"
    if vat_treatment not in EXPORT_VAT_OPTIONS:
        errors["export_price_vat_treatment"] = "export_vat_required"
    included = set(components)
    if not included.issubset(EXPORT_COMPONENTS) or not included.intersection(
        EXPORT_COMPONENTS[:2]
    ):
        errors["export_price_components"] = "export_component_required"
    if errors or rate is None:
        return None, errors
    return {
        "meter": meter,
        "amount_per_kwh": str(rate),
        "currency": currency,
        "vat_treatment": vat_treatment,
        "components": sorted(included),
    }, {}


def updated_export_price_periods(
    periods: list[ExportPricePeriod],
    terms: ExportPriceTerms | None,
    now: datetime,
) -> list[ExportPricePeriod]:
    """Keep saved periods and close or replace the active one as needed."""
    active = periods[-1] if periods and periods[-1]["valid_until"] is None else None
    if active is None and terms is None:
        return periods
    if (
        active is not None
        and terms is not None
        and (
            active["meter"] == terms["meter"]
            and Decimal(active["amount_per_kwh"]) == Decimal(terms["amount_per_kwh"])
            and active["currency"] == terms["currency"]
            and active["vat_treatment"] == terms["vat_treatment"]
            and active["components"] == terms["components"]
        )
    ):
        return periods

    change = now.astimezone(UTC)
    if periods:
        last = periods[-1]
        # A repeated instant or a clock correction cannot create an overlap.
        change = max(
            change, datetime.fromisoformat(last["valid_until"] or last["valid_from"])
        )
    boundary = change.isoformat()
    result = periods.copy()
    if active is not None:
        result.pop()
        if active["valid_from"] != boundary:
            result.append({**active, "valid_until": boundary})
    if terms is not None:
        result.append({**terms, "valid_from": boundary, "valid_until": None})
    return result
