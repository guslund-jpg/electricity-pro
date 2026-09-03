# Electricity Pro Source Contract

## Purpose

This document defines the public interface between source adapters and the
rest of Electricity Pro. Dashboards, statistics, alerts, health logic, and
derived calculations consume canonical entities rather than provider-specific
entities.

## Contract maturity

This is the accepted v1.2 source contract defined by
[ADR-0005](../adr/0005-pricing-and-tariff-strategies.md). Existing entity IDs
and unique IDs remain stable. Price-dependent features require explicit source
semantics rather than inferring them from entity names.

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

Each price input declares its strategy, included components, VAT treatment, and
completeness. A component may be added only when it is not already included.
Unknown or partial semantics disable calculations that require a complete
price while leaving independent measurement capabilities available.

### Pricing metadata

| Field | Meaning |
| --- | --- |
| Strategy | Supplier contracted price, market price plus tariff, or external complete price |
| Components | Market energy, supplier markup, energy tax, and variable grid fee when included |
| VAT treatment | Included, excluded, or unknown |
| Completeness | Complete, partial, or unknown for the intended calculation |

Fixed supplier and grid charges remain separate from all per-kWh prices.

## Canonical entities

### Current power

| Property | Contract |
| --- | --- |
| Entity | `sensor.electricity_pro_current_power` |
| Meaning | Current whole-home net grid exchange power |
| Canonical unit | W |
| Expected value | Finite numeric; positive import and negative export |
| Update behavior | As frequently as the source provides |
| Missing source | Entity becomes unavailable |
| Required | Yes for live-power features |

The adapter converts kilowatts to watts when required. The source must measure
whole-home net exchange rather than generation alone. Export revenue and
separate gross import/export channels require additional source contracts.

### Current price

| Property | Contract |
| --- | --- |
| Entity | `sensor.electricity_pro_current_price` |
| Meaning | Configured variable price source with declared semantics |
| Canonical unit | Currency per kWh |
| Expected value | Numeric |
| Update behavior | When the active price period changes |
| Missing source | Entity becomes unavailable |
| Required | Yes for pricing features |

The source may represent market price, contracted supplier price, or a complete
external variable price, but its metadata makes that meaning explicit. Entries
with a configured price source and missing or invalid metadata fail setup and
must be corrected through integration options.

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

### Forecast scheduling price

| Property | Contract |
| --- | --- |
| Meaning | Forecast comparison value used for relative scheduling |
| Initial source | Native Home Assistant Nord Pool action |
| Canonical unit | Currency per kWh |
| Included components | Market energy plus configured supplier markup, variable grid fee, and Energy Tax when applicable |
| Completeness | Partial for native Nord Pool |
| VAT treatment | Unknown unless the source contract declares it |

A partial forecast scheduling price can select cheapest windows and show price
direction because all compared intervals share the same scope. It must not be
called Effective Price or compared with the live Good Price threshold. Absolute
threshold advice requires matching, complete live and forecast price scopes.

### Current market price

| Property | Contract |
| --- | --- |
| Proposed entity | `sensor.electricity_pro_current_market_price` |
| Meaning | Unadjusted exchange price for the delivery interval covering now |
| Canonical unit | Source currency per kWh |
| Expected value | Finite signed numeric |
| Interval rule | Exactly one normalized interval satisfies `start <= now < end` |
| Missing source | Entity becomes unavailable |
| Required | For market-price comparison features only |

Current Market Price remains distinct from Current Price, Supplier Price, and
Effective Price. It exposes market energy only and retains the source's declared
VAT treatment and completeness. The first adapter is native Nord Pool, but the
entity contract contains no provider-specific fields.

### Market price forecast series

| Property | Contract |
| --- | --- |
| Proposed action | `electricity_pro.get_market_price_forecast` |
| Meaning | Ordered normalized market-price delivery intervals |
| Canonical unit | One declared source currency per kWh |
| Boundaries | Timezone-aware start-inclusive, end-exclusive timestamps |
| Horizon | Complete bounded source horizon; not guaranteed to be 24 hours |
| Missing source | Empty or unavailable response with a Home Assistant error |
| Required | For market-price forecast graphs and interval analytics |

The response-only action is the authoritative bulk interface. A bounded
`forecast` state attribute may support the enhanced dashboard, but it is
excluded from Recorder and never becomes an unbounded price-history store.
Detailed validation and presentation rules are defined by
[ADR-0011](../adr/0011-market-price-series-contract.md).

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
accumulation, detailed monthly cost composition, capacity tariffs, complete
supplier forecast adapters, and regional tariff adapters.
