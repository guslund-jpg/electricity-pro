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
    """Normalized Electricity Pro data."""

    current_power: Decimal | None
    current_power_bidirectional: bool
    current_price: Decimal | None
    current_price_unit: str | None
    pricing_metadata: PricingMetadata | None
    current_energy: Decimal | None
    current_energy_unit: str | None
    energy_source_type: str
    energy_today_period_complete: bool
    accumulated_cost_today: Decimal | None
    accumulated_cost_today_unit: str | None
    peak_power_today: Decimal | None
    peak_power_time_today: datetime | None
    current_l1: Decimal | None
    current_l2: Decimal | None
    current_l3: Decimal | None
    voltage_l1: Decimal | None
    voltage_l2: Decimal | None
    voltage_l3: Decimal | None
    monthly_peak_hour_consumption: Decimal | None
    monthly_peak_hour_consumption_unit: str | None
    monthly_peak_hour_time: datetime | None
    energy_this_month: Decimal | None
    energy_this_month_unit: str | None
    cost_this_month: Decimal | None
    cost_this_month_unit: str | None
    fixed_supplier_fee_this_month: Decimal | None
    fixed_supplier_fee_this_month_unit: str | None
    fixed_grid_fee_this_month: Decimal | None
    fixed_grid_fee_this_month_unit: str | None
    total_supplier_cost_this_month: Decimal | None
    total_supplier_cost_this_month_unit: str | None
    grid_fee_per_kwh: Decimal | None
    supplier_markup_per_kwh: Decimal | None
    energy_tax_per_kwh: Decimal | None
    good_price_threshold: Decimal | None
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
    household_priced_energy_today: Decimal | None = None
    household_priced_energy_month: Decimal | None = None
    household_missing_fees: tuple[str, ...] = ()


def legacy_provider_view(inputs: ProviderSnapshot) -> ElectricityProData:
    """Project inputs to the temporary flat provider contract, without calculation.

    Energy and cost fields retain raw source values here. This is not a
    publication view of coordinator-selected results.
    """
    readings, context = inputs.readings, inputs.context
    return ElectricityProData(
        current_power=readings.current_power,
        current_power_bidirectional=readings.current_power_bidirectional,
        current_price=readings.current_price,
        current_price_unit=readings.current_price_unit,
        pricing_metadata=context.pricing_metadata,
        current_energy=readings.import_energy_value,
        current_energy_unit=readings.import_energy_unit,
        energy_source_type=readings.energy_source_type,
        energy_today_period_complete=readings.energy_source_type == "daily",
        accumulated_cost_today=readings.external_cost_today,
        accumulated_cost_today_unit=readings.external_cost_today_unit,
        peak_power_today=None,
        peak_power_time_today=None,
        current_l1=readings.current_l1,
        current_l2=readings.current_l2,
        current_l3=readings.current_l3,
        voltage_l1=readings.voltage_l1,
        voltage_l2=readings.voltage_l2,
        voltage_l3=readings.voltage_l3,
        monthly_peak_hour_consumption=readings.monthly_peak_hour_consumption,
        monthly_peak_hour_consumption_unit=readings.monthly_peak_hour_consumption_unit,
        monthly_peak_hour_time=readings.monthly_peak_hour_time,
        energy_this_month=None,
        energy_this_month_unit=None,
        cost_this_month=None,
        cost_this_month_unit=None,
        fixed_supplier_fee_this_month=context.fixed_supplier_fee_this_month,
        fixed_supplier_fee_this_month_unit=None,
        fixed_grid_fee_this_month=context.fixed_grid_fee_this_month,
        fixed_grid_fee_this_month_unit=None,
        total_supplier_cost_this_month=None,
        total_supplier_cost_this_month_unit=None,
        grid_fee_per_kwh=context.grid_fee_per_kwh,
        supplier_markup_per_kwh=context.supplier_markup_per_kwh,
        energy_tax_per_kwh=context.energy_tax_per_kwh,
        good_price_threshold=context.good_price_threshold,
    )


def legacy_published_view(
    inputs: ProviderSnapshot, results: IntegrationResults
) -> ElectricityProData:
    """Project selected results for existing entity readers without calculation."""
    readings, context = inputs.readings, inputs.context
    return ElectricityProData(
        current_power=readings.current_power,
        current_power_bidirectional=readings.current_power_bidirectional,
        current_price=readings.current_price,
        current_price_unit=readings.current_price_unit,
        pricing_metadata=context.pricing_metadata,
        current_energy=results.current_energy,
        current_energy_unit=results.current_energy_unit,
        energy_source_type=readings.energy_source_type,
        energy_today_period_complete=results.energy_today_period_complete,
        accumulated_cost_today=results.accumulated_cost_today,
        accumulated_cost_today_unit=results.accumulated_cost_today_unit,
        peak_power_today=results.peak_power_today,
        peak_power_time_today=results.peak_power_time_today,
        current_l1=readings.current_l1,
        current_l2=readings.current_l2,
        current_l3=readings.current_l3,
        voltage_l1=readings.voltage_l1,
        voltage_l2=readings.voltage_l2,
        voltage_l3=readings.voltage_l3,
        monthly_peak_hour_consumption=readings.monthly_peak_hour_consumption,
        monthly_peak_hour_consumption_unit=readings.monthly_peak_hour_consumption_unit,
        monthly_peak_hour_time=readings.monthly_peak_hour_time,
        energy_this_month=results.energy_this_month,
        energy_this_month_unit=results.energy_this_month_unit,
        cost_this_month=results.cost_this_month,
        cost_this_month_unit=results.cost_this_month_unit,
        fixed_supplier_fee_this_month=context.fixed_supplier_fee_this_month,
        fixed_supplier_fee_this_month_unit=results.fixed_supplier_fee_this_month_unit,
        fixed_grid_fee_this_month=context.fixed_grid_fee_this_month,
        fixed_grid_fee_this_month_unit=results.fixed_grid_fee_this_month_unit,
        total_supplier_cost_this_month=results.total_supplier_cost_this_month,
        total_supplier_cost_this_month_unit=results.total_supplier_cost_this_month_unit,
        grid_fee_per_kwh=context.grid_fee_per_kwh,
        supplier_markup_per_kwh=context.supplier_markup_per_kwh,
        energy_tax_per_kwh=context.energy_tax_per_kwh,
        good_price_threshold=context.good_price_threshold,
        local_cost_estimate=results.local_cost_estimate,
        local_effective_cost_today=results.local_effective_cost_today,
        local_priced_energy_today=results.local_priced_energy_today,
        local_supplier_energy_today=results.local_supplier_energy_today,
        local_supplier_energy_month=results.local_supplier_energy_month,
        household_cost_today=results.household_cost_today,
        household_cost_this_month=results.household_cost_this_month,
        household_cost_unit=results.household_cost_unit,
        household_variable_today=results.household_variable_today,
        household_variable_month=results.household_variable_month,
        household_fixed_today=results.household_fixed_today,
        household_fixed_month=results.household_fixed_month,
        household_priced_energy_today=results.household_priced_energy_today,
        household_priced_energy_month=results.household_priced_energy_month,
        household_missing_fees=results.household_missing_fees,
    )
