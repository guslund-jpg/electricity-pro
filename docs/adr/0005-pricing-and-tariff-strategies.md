# ADR-0005: Pricing Sources and Tariff Strategies

## Status

Accepted

## Date

2026-08-15

Accepted 2026-08-17 after the live and forecast pricing paths adopted explicit
component scope, VAT treatment, and completeness metadata.

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

Configuration selects an explicit strategy instead of inferring semantics from
an entity name.

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
and VAT as already included. Swedish energy tax and grid fees are grid-company
charges and remain explicit configuration outside the Tibber source price.

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
- **Forecast scheduling price** is a forecast-derived comparison value. For
  native Nord Pool it contains market energy plus any configured variable grid
  fee and must not be presented as a complete Effective Price.
- **Fixed charge** is a time-based amount and is never hidden inside a per-kWh
  price without an explicitly documented estimate.
- **Total cost** is accumulated cost for a defined period and component scope.

### Inclusion and VAT rules

Every price or cost value must have a known component scope. Components may be
added only when they are not already included.

Inputs declare whether they are gross or net of VAT. Electricity Pro does not
extract or add a separate VAT component automatically because regional tax
behavior is outside the provider-independent core.

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

Absolute forecast thresholds require the forecast and live price to have
matching, complete component scopes and VAT treatment. Partial market
forecasts may still drive relative cheapest-window and direction insights.

## Compatibility and migration

Existing entity IDs and unique IDs remain stable. Entries created or confirmed
through the v1.2 configuration flow store explicit pricing metadata. An entry
with a configured price source and missing or invalid metadata fails setup with
a clear instruction to confirm its price source in integration options. Price
semantics are never inferred during setup or calculation.

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

## Implementation status

Delivered in the v1.2 foundation:

1. Pricing-strategy, component-inclusion, VAT, provenance, and completeness
   models.
2. Separate measurement-source and price-source adapter contracts.
3. Guided Tibber price and Tibber Pulse setup with a custom/mixed fallback.
4. Metadata-aware Effective Price, Current Cost Rate, and Good Time behavior.
5. Fixed, variable, and weekday/seasonal grid-tariff foundations.
6. Explicit partial-price semantics for native Nord Pool forecasts.
7. Optional Home Assistant Workday-supplied non-working dates for high grid tariffs.

Deferred capabilities remain separate follow-up work: configurable supplier
markup, local interval cost accumulation, capacity tariffs, and monthly cost
composition.

## Related issues

- #166 defines and tracks the pricing architecture.
- #162 covers time-of-use grid fees.
- #163 covers fixed supplier fees.
- #165 covers monthly cost composition and presentation.
- #173 removed the temporary legacy pricing compatibility path.
- #187 normalizes forecast price semantics and completeness.
