"""Immutable runtime data contracts without Home Assistant dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .pricing import PricingMetadata


@dataclass(frozen=True, slots=True)
class SourceReadings:
    """Normalized source values, before integration result selection."""

    current_power: Decimal | None
    current_power_bidirectional: bool
    current_price: Decimal | None
    current_price_unit: str | None
    import_energy_value: Decimal | None
    import_energy_unit: str | None
    energy_source_type: str
    external_cost_today: Decimal | None
    external_cost_today_unit: str | None
    current_l1: Decimal | None
    current_l2: Decimal | None
    current_l3: Decimal | None
    voltage_l1: Decimal | None
    voltage_l2: Decimal | None
    voltage_l3: Decimal | None
    monthly_peak_hour_consumption: Decimal | None
    monthly_peak_hour_consumption_unit: str | None
    monthly_peak_hour_time: datetime | None


@dataclass(frozen=True, slots=True)
class CalculationContext:
    """Already-resolved pricing and settings values for one provider read."""

    pricing_metadata: PricingMetadata | None
    fixed_supplier_fee_this_month: Decimal | None
    fixed_grid_fee_this_month: Decimal | None
    grid_fee_per_kwh: Decimal | None
    supplier_markup_per_kwh: Decimal | None
    energy_tax_per_kwh: Decimal | None
    good_price_threshold: Decimal | None


@dataclass(frozen=True, slots=True)
class ProviderSnapshot:
    """Immutable inputs from one provider read, without analytics placeholders."""

    readings: SourceReadings
    context: CalculationContext


@dataclass(frozen=True, slots=True)
class IntegrationResults:
    """Selected and derived values for one read, separate from raw inputs."""

    current_energy: Decimal | None
    current_energy_unit: str | None
    energy_today_period_complete: bool
    accumulated_cost_today: Decimal | None
    accumulated_cost_today_unit: str | None
    peak_power_today: Decimal | None = None
    peak_power_time_today: datetime | None = None
    energy_this_month: Decimal | None = None
    energy_this_month_unit: str | None = None
    cost_this_month: Decimal | None = None
    cost_this_month_unit: str | None = None
    fixed_supplier_fee_this_month_unit: str | None = None
    fixed_grid_fee_this_month_unit: str | None = None
    total_supplier_cost_this_month: Decimal | None = None
    total_supplier_cost_this_month_unit: str | None = None
    local_cost_estimate: bool = False
    local_effective_cost_today: Decimal | None = None
    local_priced_energy_today: Decimal | None = None
    local_supplier_energy_today: Decimal | None = None
    local_supplier_energy_month: Decimal | None = None
    household_cost_today: Decimal | None = None
    household_cost_this_month: Decimal | None = None
    household_cost_unit: str | None = None
    household_variable_today: Decimal | None = None
    household_variable_month: Decimal | None = None
    household_fixed_today: Decimal | None = None
    household_fixed_month: Decimal | None = None
    household_fixed_supplier_month: Decimal | None = None
    household_fixed_grid_month: Decimal | None = None
    household_priced_energy_today: Decimal | None = None
    household_priced_energy_month: Decimal | None = None
    household_missing_fees: tuple[str, ...] = ()

    @classmethod
    def from_inputs(cls, inputs: ProviderSnapshot) -> IntegrationResults:
        """Start fresh with the established source pass-through/default semantics."""
        readings = inputs.readings
        return cls(
            current_energy=readings.import_energy_value,
            current_energy_unit=readings.import_energy_unit,
            energy_today_period_complete=readings.energy_source_type == "daily",
            accumulated_cost_today=readings.external_cost_today,
            accumulated_cost_today_unit=readings.external_cost_today_unit,
        )


@dataclass(frozen=True, slots=True)
class ElectricityProData:
    """Published inputs and selected results from one coordinator read."""

    readings: SourceReadings
    context: CalculationContext
    results: IntegrationResults
