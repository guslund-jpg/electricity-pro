# Electricity Pro Source Contract

## Purpose

This document defines the public interface between source adapters and the
rest of Electricity Pro. Dashboards, statistics, alerts, health logic, and
derived calculations consume canonical entities rather than provider-specific
entities.

## Contract maturity

The v1.1 contract remains compatible while the explicit pricing model in
[ADR-0005](../adr/0005-pricing-and-tariff-strategies.md) is introduced.
Existing entity IDs and unique IDs must remain stable during migration.

## Input roles

Inputs describe capabilities, not brands. An installation may combine several
integrations.

- **Metering source:** live power and accumulated energy.
- **Market-price source:** an unadjusted exchange price, such as Nord Pool.
- **Supplier-price source:** the customer's contracted variable price.
- **Supplier tariff:** configured markup and fixed supplier charges.
- **Grid tariff:** variable, time-of-use, fixed, and future capacity charges.
- **Authoritative cost source:** provider-calculated accumulated cost.

Tibber may fulfil several roles at once. It is a convenient adapter path, not
a requirement. A generic meter plus Nord Pool and configured tariff data is
also a valid source combination.

## Pricing terminology

- **Market price** is the unadjusted exchange price for a delivery interval.
- **Supplier price** is the contracted variable supplier price.
- **Effective variable price** is the normalized per-kWh price used for live
  rates and interval calculations after known variable components.
- **Fixed charge** is time-based and must not be hidden in a per-kWh price
  unless clearly presented as an estimate.
- **Total cost** is accumulated cost for a defined period and component scope.

Each price and cost input must eventually declare its included components and
whether it is gross or net of VAT. A component may be added only when it is not
already included.

## Canonical entities

### Current power

| Property | Contract |
| --- | --- |
| Entity | `sensor.electricity_pro_current_power` |
| Meaning | Current whole-home electricity import power |
| Canonical unit | W |
| Expected value | Numeric and greater than or equal to zero |
| Update behavior | As frequently as the source provides |
| Missing source | Entity becomes unavailable |
| Required | Yes for live-power features |

The adapter converts kilowatts to watts when required. Export and signed
bidirectional power may be introduced as separate capabilities later.

### Current price

| Property | Contract |
| --- | --- |
| Entity | `sensor.electricity_pro_current_price` |
| Meaning | Configured variable price source, retained for compatibility |
| Canonical unit | Currency per kWh |
| Expected value | Numeric |
| Update behavior | When the active price period changes |
| Missing source | Entity becomes unavailable |
| Required | Yes for pricing features |

In v1.1 this input may represent market price, contracted supplier price, or a
complete external variable price. That ambiguity is legacy behavior, not the
target contract. The v1.2 migration must obtain explicit strategy and component
inclusion semantics before adding new fees.

### Effective price

| Property | Contract |
| --- | --- |
| Entity | `sensor.electricity_pro_effective_price` |
| Meaning | Normalized effective variable price used by Electricity Pro |
| Canonical unit | Currency per kWh |
| Expected value | Numeric |
| Missing inputs | Entity becomes unavailable |
| Required | For effective-rate and recommendation features |

The calculation depends on the selected pricing strategy. It must add each
variable component exactly once and expose sufficient provenance to explain
the result. Fixed charges do not belong in this value.

### Energy today

| Property | Contract |
| --- | --- |
| Entity | `sensor.electricity_pro_energy_today` |
| Meaning | Imported electrical energy accumulated today |
| Canonical unit | kWh |
| Expected value | Numeric and greater than or equal to zero |
| Reset behavior | Resets at the installation's local day boundary |
| Missing source | Entity becomes unavailable |
| Required | For daily energy features |

A reset at the start of a new local day is expected. The internal entity key
remains `current_energy` for compatibility with recorded history.

### Cost today

| Property | Contract |
| --- | --- |
| Entity | `sensor.electricity_pro_cost_today` |
| Meaning | Electricity cost accumulated today |
| Canonical unit | Configured currency |
| Expected value | Numeric and normally greater than or equal to zero |
| Reset behavior | Resets at the installation's local day boundary |
| Missing source | Entity becomes unavailable |
| Required | For daily cost features |

The value may be authoritative supplier cost or locally calculated cost. Its
provenance and included components must be distinguishable. Local accounting
requires time-aligned energy and price data; instantaneous power alone must not
be presented as accounting-accurate accumulated cost.

### Consumption-weighted average price today

| Property | Contract |
| --- | --- |
| Entity | `sensor.electricity_pro_consumption_weighted_average_price_today` |
| Meaning | Average price achieved by today's actual energy use |
| Canonical unit | Configured currency per kWh |
| Expected value | Numeric and greater than or equal to zero |
| Update behavior | When cost or energy today changes |
| Missing source | Entity becomes unavailable |
| Required | Compatible cost-today and energy-today sources |

The current compatibility calculation uses Cost Today divided by Energy Today
and applies configured adjustments once. Under the explicit pricing model it
must instead use a normalized cost scope, so authoritative cost and configured
components cannot overlap. It is unavailable when Energy Today is zero and is
retrospective, not a recommendation.

### Monthly peak-hour time

| Property | Contract |
| --- | --- |
| Entity | `sensor.electricity_pro_monthly_peak_hour_time` |
| Meaning | Start time of the highest-consumption hour in the current month |
| Canonical unit | Timestamp |
| Expected value | ISO 8601 timestamp with a timezone offset |
| Missing source | Not created when unconfigured; unavailable when invalid |
| Required | No |

The timestamp remains timezone-aware so Home Assistant can display local time.

## Source-health entities

`binary_sensor.electricity_pro_power_source_healthy` is on only when the
configured power source exists, is available, contains a valid numeric value,
and is fresh enough for that source type.

`binary_sensor.electricity_pro_price_source_healthy` is on only when the
configured price source exists, is available, contains a valid numeric value,
corresponds to the active price period, and is fresh enough.

## Missing and invalid data

Canonical entities become unavailable when source data is missing or invalid.
`unknown`, `unavailable`, `none`, `null`, an empty string, and non-numeric text
must not be treated as zero. A valid numeric zero remains zero.

## Precision and freshness

Adapters preserve meaningful source precision. Display rounding belongs in
the presentation layer unless calculation requirements justify normalization.

| Measurement | Recommended display precision |
| --- | --- |
| Power | 0 W |
| Price | 3 currency/kWh decimals |
| Energy today | 3 kWh decimals |
| Cost today | 2 currency decimals |

| Source type | Suggested freshness threshold |
| --- | --- |
| Live power | 5 minutes |
| Period price | Current period plus 5 minutes |
| Daily accumulated energy | 15 minutes |
| Daily accumulated cost | 15 minutes |

Adapters may override thresholds when their source has a different documented
update model.

## Provider isolation

Provider-specific entity IDs may appear only in source adapters. They must not
leak into core calculations, statistics, health, alerts, or dashboards.

Feature availability is capability-based. Missing optional inputs disable only
the dependent capability.

## Future extensions

Potential additions include export measurements, local interval cost
accumulation, detailed cost provenance, tariff completeness, price forecasts,
and regional tariff adapters. These are not part of the v1.1 contract.
