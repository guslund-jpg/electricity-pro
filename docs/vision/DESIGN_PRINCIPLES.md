# Design Principles

These principles guide design decisions in Electricity Pro. They describe the
boundaries that keep measurements trustworthy, calculations reusable, and the
integration maintainable as new providers and capabilities are added.

## 1. Model electrical concepts, not provider products

### Principle

Public concepts should describe electricity, energy, prices, tariffs, and time
periods rather than a particular provider's product or API.

### Rationale

Users should receive the same meaning from an entity regardless of which
compatible meter or price provider supplies its inputs.

### Practical implications

- Name models and entities after the electrical quantity they represent.
- Do not expose provider payload structures as public contracts.
- Add provider-specific capabilities only after defining their normalized
  meaning.

### Example

Use **Current power** for instantaneous whole-home power instead of naming the
entity after Tibber Pulse, HomeWizard, or another meter.

## 2. Normalize values and semantics at the provider boundary

### Principle

Providers translate source entities into canonical units and explicit metadata
before the data enters shared calculations.

### Rationale

A numeric value is not sufficient by itself. `500` may mean watts, kilowatts,
energy since midnight, or a lifetime meter register. Normalization prevents
downstream code from guessing.

### Practical implications

- Convert supported units at ingestion rather than inside every calculation.
- Preserve price components, VAT treatment, currency, and period semantics.
- Reject incompatible or ambiguous inputs instead of silently interpreting
  them.

### Example

A total accumulated-energy register is normalized as a total source and then
converted to Energy Today from a persisted local-midnight baseline; it is not
treated as a native daily value.

## 3. Keep provider-specific behaviour in the provider layer

### Principle

Discovery, source quirks, and provider API behaviour belong in provider
adapters, not in analytics or entity classes.

### Rationale

Containing provider knowledge prevents one integration's conventions from
becoming assumptions throughout the project.

### Practical implications

- Sensors must not query provider APIs or inspect provider-specific attributes.
- Provider adapters produce the common `ElectricityProData` contract.
- Shared features must not branch on provider names when a capability or
  semantic check can express the requirement.

### Example

Tibber entity discovery belongs in the Tibber setup path, while the calculation
of Current Cost Rate consumes only normalized power and price values.

## 4. Keep analytics pure, deterministic, and provider-independent

### Principle

Business calculations should be pure functions or isolated state models whose
inputs, outputs, and time reference are explicit.

### Rationale

Deterministic analytics are easier to test, review, reuse, and explain than
calculations mixed with Home Assistant callbacks or entity state updates.

### Practical implications

- Keep Home Assistant framework code at the integration boundary.
- Pass the evaluation time into time-dependent calculations.
- Test algorithms directly, including missing data, negative values, local
  midnight, and daylight-saving transitions.

### Example

Adaptive Good Time classification receives comparable historical summaries and
an evaluation time; it does not read Recorder or the system clock itself.

## 5. Give every entity one explicit semantic contract

### Principle

Each entity must be identifiable as a normalized measurement, a calculated
statistic, or an intelligence result, with one documented meaning.

### Rationale

Similar-looking values can have different authority and lifecycle. Clear
categories prevent a mirrored provider total, a local calculation, and a
recommendation from being presented as interchangeable facts.

### Practical implications

- Document inputs, calculation, unit, time period, and availability behaviour.
- Use Home Assistant device classes and state classes only when their semantics
  are fully satisfied.
- Keep recommendations explainable through attributes such as method, reason,
  threshold, and data coverage.

### Example

Average Market Price Today is a retrospective statistic. It must not silently
become the threshold for a Good Time recommendation.

## 6. Prefer unavailable over misleading

### Principle

When required data is missing, stale, incomplete, or semantically incompatible,
withhold the result instead of inventing precision.

### Rationale

An unavailable entity is visible and diagnosable. A plausible but invalid value
can lead to incorrect cost conclusions or automations.

### Practical implications

- Validate required inputs before calculating.
- Do not combine prices with different currencies, components, VAT treatment,
  or tariff definitions.
- Define conservative fallbacks explicitly and expose when they are active.

### Example

An incomplete market-only forecast cannot suppress an Adaptive Good Time result
that is based on a complete Effective Price.

## 7. Preserve stable Home Assistant behaviour and evolve deliberately

### Principle

Entity identity, configuration, and statistics semantics are public contracts
that should change only through an explicit, documented decision.

### Rationale

Users build dashboards, automations, and long-term statistics around these
contracts. An apparently small change can otherwise cause data loss or silent
behaviour changes.

### Practical implications

- Prefer additive changes and migration paths over replacement.
- Record consequential design decisions in an ADR before implementation.
- Update tests, user documentation, contributor documentation, and the
  changelog with user-visible behaviour.

### Example

If a sensor becomes temporarily inapplicable, preserve its unique identity so
Home Assistant can restore the same entity when compatible inputs later become
available.

## Applying the principles

Use these principles when reviewing an issue or pull request. If a proposed
feature conflicts with one of them, document the trade-off and agree on the
exception before implementation. Significant or lasting exceptions belong in
an Architecture Decision Record under [`docs/adr/`](../adr/).
