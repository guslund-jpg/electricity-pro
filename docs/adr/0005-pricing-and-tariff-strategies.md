# ADR-0005: Pricing Sources and Tariff Strategies

## Status

Proposed

## Date

2026-08-15

## Context

Electricity Pro accepts Home Assistant entities for power, energy, price, and
accumulated cost. This works particularly well with Tibber because the Tibber
integration can expose contracted price, accumulated cost, energy, and live
meter measurements.

Many electricity suppliers do not expose a contracted customer price through
an API. Their customers may still have a compatible meter and access to native
Home Assistant Nord Pool market prices. Electricity Pro must not require one
supplier or one meter product to deliver useful pricing and insight features.

The v1.1 configuration does not explicitly say whether a selected price entity
is a market price, a supplier price, or an already-complete variable price.
Adding configured fees to an ambiguous source can count the same component
twice. Authoritative provider cost and locally calculated cost are also not yet
distinguished in the public model.

## Decision

Electricity Pro will separate measurement, market, supplier, tariff, and cost
roles. Feature availability will depend on declared capabilities rather than
provider identity.

### Source roles

- **Metering source** supplies live power and accumulated energy.
- **Market-price source** supplies an unadjusted exchange price, initially
  through native Home Assistant Nord Pool.
- **Supplier-price source** supplies the customer's contracted variable price.
- **Supplier tariff** defines configured markup and fixed supplier charges.
- **Grid tariff** defines variable, time-of-use, fixed, and future capacity
  charges.
- **Authoritative cost source** optionally supplies provider-calculated
  accumulated cost.

One installation may combine sources from different integrations. A generic
HAN/P1 meter, Nord Pool, and a configured tariff is a valid combination.
Tibber remains a convenient source combination, not a dependency.

### Pricing strategies

Configuration will eventually select an explicit strategy instead of inferring
semantics from an entity name.

#### Supplier-provided contracted price

Use a supplier price that already contains the components declared by its
adapter or configuration. Electricity Pro must not add those components again.
Separate grid charges may still be configured when they are not included.

#### Market price plus tariff

Build the customer variable price from a market-price source and configured
supplier and grid components. This strategy supports customers whose supplier
does not expose a contracted-price API.

#### External complete-price entity

Use an externally calculated price entity. Its included components must be
declared explicitly before Electricity Pro adds anything to it.

### Canonical terminology

- **Market price** is the unadjusted exchange price for a delivery interval.
- **Supplier price** is the customer's contracted variable supplier price.
- **Effective variable price** is the per-kWh price Electricity Pro uses for
  live rates and interval calculations after known variable components.
- **Fixed charge** is a time-based amount and is never hidden inside a per-kWh
  price without an explicitly documented estimate.
- **Total cost** is accumulated cost for a defined period and component scope.

### Inclusion and VAT rules

Every price or cost value must have a known component scope. Components may be
added only when they are not already included.

Inputs must eventually declare whether they are gross or net of VAT. Until the
configuration and regional behavior are explicit, Electricity Pro must not
extract or add a separate VAT component automatically.

### Cost provenance

Authoritative supplier cost and locally calculated cost must be distinguishable
in internal data and user-visible attributes or diagnostics.

Local accumulated cost requires time-aligned consumption and price data.
Electricity Pro must not claim accounting precision when only sparse energy
updates or instantaneous power estimates are available.

### Capability-based behavior

Useful partial configurations are supported:

- price forecasts without a meter;
- live power without cost accounting;
- current cost rate from power and an effective variable price;
- local accumulated cost from sufficiently frequent energy and price data;
- authoritative accumulated cost from a supplier;
- detailed cost components when a complete tariff is configured.

Missing optional inputs disable only the dependent capability.

## Compatibility and migration

This ADR does not change v1.1 behavior by itself.

Existing entity IDs and unique IDs remain stable. Existing config entries must
continue to load while a later implementation introduces an explicit strategy
and migration. No stored option may silently change meaning.

The legacy `current_price` input remains accepted during migration. Before new
fees are applied to it, the implementation must obtain explicit inclusion
semantics from migration defaults or user confirmation.

## Consequences

### Advantages

- Tibber users retain a simple setup.
- Other users can combine Nord Pool, a compatible meter, and their tariff.
- Calculations can prevent component double counting.
- Forecast and recommendation logic consumes one normalized effective price.
- Provider independence becomes capability-based and testable.

### Trade-offs

- Configuration becomes more structured.
- Local cost accounting requires interval-aware state and persistence.
- Regional taxes and tariffs cannot be generalized without explicit models.
- Some installations will expose fewer capabilities than others.

## Implementation sequence

1. Introduce pricing-strategy and component-inclusion models without changing
   public entities.
2. Add provenance and completeness metadata.
3. Migrate existing configurations conservatively.
4. Implement market price plus supplier markup.
5. Add grid tariff strategies.
6. Add local interval cost accumulation where source resolution is sufficient.
7. Build cost composition and recommendation features on the normalized model.

## Related issues

- #166 defines and tracks the pricing architecture.
- #162 covers time-of-use grid fees.
- #163 covers fixed supplier fees.
- #165 covers monthly cost composition and presentation.
