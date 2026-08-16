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

### Source adapters and guided setup

Electricity Pro will keep measurement-source discovery separate from
price-source discovery. A user may therefore combine a recognised meter or
dongle with any supported supplier, market source, or manually selected price
entity.

A small source-adapter contract may provide:

- a stable way to recognise compatible Home Assistant config entries and
  devices;
- discovered entity IDs for capabilities such as power, energy, current,
  voltage, price, and accumulated cost;
- declared price-component and VAT semantics;
- authoritative-versus-local cost provenance; and
- remaining questions that the user must answer.

Adapters must use Home Assistant config-entry, device-registry, entity-registry,
unique-ID, and capability information. They must not depend on user-editable
entity IDs or display names. Discovery must be presented for confirmation and
must always offer a manual fallback.

The first guided path supports a Tibber home with Tibber Pulse and a Tibber
electricity contract. When one compatible home is unambiguous, Electricity Pro
can prepopulate its known measurement and price entities. When several homes
or devices are available, the user selects the intended home before discovery.
Only unresolved settings, initially grid-company tariffs and optional insight
thresholds, remain visible in the normal path.

The custom/mixed path asks independently how electricity is measured and how
the electricity price is supplied. This preserves combinations such as Tibber
Pulse with Nord Pool, another HAN/P1 meter with Tibber pricing, or entirely
manual sources.

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

### Configuration experience

The normalized pricing model is an internal contract, not a requirement that
every user manually describes accounting components.

The normal setup will offer provider-aware presets when Electricity Pro can
state their semantics confidently. The first preset targets Tibber's
contracted-price sensor. It records market energy, supplier-side additions,
Swedish energy tax, and VAT as already included, while leaving grid-company
charges outside the source price.

Users of Nord Pool or another source can choose an advanced/manual path and
declare the components and VAT treatment explicitly. Presets and manual setup
must resolve to the same `PricingMetadata` model so downstream calculations do
not depend on provider-specific branches.

A preset must be visible and explainable: the configuration should show what
Electricity Pro assumes and allow the user to choose the manual path when the
source differs from the documented preset. Provider detection may improve the
suggested default, but must not silently reinterpret a stored configuration.

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
3. Define separate measurement-source and price-source adapter contracts.
4. Add a guided Tibber price and Tibber Pulse path with manual confirmation.
5. Add a custom/mixed path with independent meter and price choices.
6. Migrate existing configurations conservatively.
7. Implement market price plus supplier markup.
8. Add grid tariff strategies.
9. Add local interval cost accumulation where source resolution is sufficient.
10. Build cost composition and recommendation features on the normalized model.

## Related issues

- #166 defines and tracks the pricing architecture.
- #162 covers time-of-use grid fees.
- #163 covers fixed supplier fees.
- #165 covers monthly cost composition and presentation.
