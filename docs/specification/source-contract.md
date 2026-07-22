# Electricity Pro Source Contract

## Purpose

This document defines the public interface between source adapters and
the rest of Electricity Pro.

Dashboards, statistics, alerts, health logic, and derived calculations
must consume canonical entities rather than provider-specific entities.

## Contract maturity

This is the initial pre-release contract.

The contract may evolve before version 1.0, but changes must be reviewed
and documented.

## Entity categories

### Required

At least one real-time power source and one price source are expected for
the complete Electricity Pro experience.

### Conditionally required

Daily energy and daily cost are required only for modules that use those
values.

### Optional

Future entities may include forecasts, import and export measurements,
tariff components, grid carbon intensity, and per-device consumption.

## Canonical entities

### Current power

```text
sensor.electricity_pro_current_power
Property	Contract
Meaning	Current whole-home electricity import power
Canonical unit	W
Expected value	Numeric and greater than or equal to zero
Update behavior	As frequently as the source provides
Missing source	Entity becomes unavailable
Required	Yes for live-power features

The source adapter must convert kilowatts to watts when required.

The initial contract represents imported power. Export and signed
bidirectional power may be introduced separately in a future contract.

Current price
sensor.electricity_pro_current_price
Property	Contract
Meaning	Current effective electricity price
Canonical unit	Currency per kWh
Expected value	Numeric
Update behavior	When the active price period changes
Missing source	Entity becomes unavailable
Required	Yes for pricing features

The configured currency must be consistent throughout one installation.

The price may represent a spot price or a complete customer price,
depending on adapter configuration. Adapters must document what their
value includes.

Energy today
sensor.electricity_pro_energy_today
Property	Contract
Meaning	Imported electrical energy accumulated today
Canonical unit	kWh
Expected value	Numeric and greater than or equal to zero
Reset behavior	Resets at the installation's local day boundary
Missing source	Entity becomes unavailable
Required	For daily energy features

A reset to zero at the beginning of a new local day is expected and is
not considered an error.

Cost today
sensor.electricity_pro_cost_today
Property	Contract
Meaning	Electricity cost accumulated today
Canonical unit	Configured currency
Expected value	Numeric and normally greater than or equal to zero
Reset behavior	Resets at the installation's local day boundary
Missing source	Entity becomes unavailable
Required	For daily cost features

Adapters or core calculation modules must document whether taxes, grid
fees, and fixed fees are included.

Source-health entities
Power source health
binary_sensor.electricity_pro_power_source_healthy

The entity is on only when the configured power source:

exists;
is available;
contains a valid numeric value;
has updated within its accepted freshness interval.
Price source health
binary_sensor.electricity_pro_price_source_healthy

The entity is on only when the configured price source:

exists;
is available;
contains a valid numeric value;
corresponds to the active pricing period;
has updated within its accepted freshness interval.
Missing and invalid data

Canonical entities must become unavailable when source data is missing
or invalid.

The following values must not automatically be treated as zero:

unknown
unavailable
none
null
empty string
non-numeric text

A valid numeric zero remains zero.

Precision

Adapters should preserve meaningful source precision.

Display rounding belongs in the presentation layer unless storage or
calculation requirements justify normalization.

Initial recommended display precision:

Measurement	Display precision
Power	0 W
Price	3 currency/kWh decimals
Energy today	3 kWh decimals
Cost today	2 currency decimals

These are presentation recommendations and not storage requirements.

Freshness

The health layer must support source-specific freshness thresholds.

Recommended initial defaults:

Source type	Suggested threshold
Live power	5 minutes
Period price	Current period plus 5 minutes
Daily accumulated energy	15 minutes
Daily accumulated cost	15 minutes

Adapters may override these defaults when their provider has a different
documented update model.

Provider isolation

Provider-specific entity IDs may appear only inside:

packages/10_sources/

They must not appear in:

packages/20_core/
packages/30_statistics/
packages/40_health/
packages/50_alerts/
dashboards/
Future extensions

Potential future contract additions include:

sensor.electricity_pro_power_export
sensor.electricity_pro_energy_export_today
sensor.electricity_pro_price_next_period
sensor.electricity_pro_price_daily_average
sensor.electricity_pro_cost_forecast_today
sensor.electricity_pro_grid_fee_current
sensor.electricity_pro_price_level

These are proposals only and are not part of the current contract.
