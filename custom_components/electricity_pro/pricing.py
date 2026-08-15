"""Normalized pricing models for Electricity Pro."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PricingStrategy(StrEnum):
    """Supported ways to obtain an effective variable electricity price."""

    SUPPLIER_CONTRACTED_PRICE = "supplier_contracted_price"
    MARKET_PRICE_PLUS_TARIFF = "market_price_plus_tariff"
    EXTERNAL_COMPLETE_PRICE = "external_complete_price"


class PriceComponent(StrEnum):
    """Variable components that may already be included in a price source."""

    MARKET_ENERGY = "market_energy"
    SUPPLIER_MARKUP = "supplier_markup"
    ENERGY_TAX = "energy_tax"
    VARIABLE_GRID_FEE = "variable_grid_fee"


class VatTreatment(StrEnum):
    """Whether values from a price source include VAT."""

    UNKNOWN = "unknown"
    EXCLUDED = "excluded"
    INCLUDED = "included"


@dataclass(frozen=True, slots=True)
class PriceComponentScope:
    """Describe the variable components included in one price source."""

    included: frozenset[PriceComponent]
    vat: VatTreatment = VatTreatment.UNKNOWN

    def __post_init__(self) -> None:
        """Normalize component collections to an immutable set."""
        components = frozenset(self.included)
        if any(not isinstance(component, PriceComponent) for component in components):
            raise ValueError("price scope contains an unsupported component")
        object.__setattr__(self, "included", components)

    def includes(self, component: PriceComponent) -> bool:
        """Return whether the source already includes a component."""
        return component in self.included

    def overlaps(self, other: PriceComponentScope) -> bool:
        """Return whether two sources include any of the same components."""
        return not self.included.isdisjoint(other.included)
