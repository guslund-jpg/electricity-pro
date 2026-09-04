# Electricity Pro Roadmap

> **Electricity Pro helps homeowners understand, optimize and forecast household energy usage through native Home Assistant sensors, statistics and intelligent insights.**

---

## Vision

Electricity Pro extends Home Assistant by transforming raw energy measurements into meaningful information.

The project is designed to feel like a natural part of Home Assistant while providing capabilities beyond the built-in Energy Dashboard.

Our long-term ambition is to evolve from displaying measurements to delivering intelligent insights that help homeowners make better energy decisions.

---

## Core Values

### Native First

Electricity Pro should always integrate naturally with Home Assistant.

- Standard sensor entities
- Standard device classes
- Standard state classes
- Recorder compatible
- Long-term statistics compatible

Users should never feel they are using a separate platform.

---

### Accuracy

Every calculation should be transparent, reproducible and thoroughly tested.

Users should always be able to understand how a value has been calculated.

---

### Practicality

Electricity Pro should solve real homeowner problems.

Features should exist because they provide value—not simply because they are technically interesting.

---

### Transparency

The project should remain open and understandable.

Calculations, assumptions and design decisions should be documented whenever practical.

---

### Sustainability

The architecture should remain modular, maintainable and easy to extend as new capabilities are introduced.

---

## Design Principles

### Build on Home Assistant

Electricity Pro extends Home Assistant rather than replacing it.

The integration should work naturally with:

- Dashboards
- Automations
- Recorder
- Long-term statistics
- Existing energy integrations

---

### Intelligence Layer

Electricity Pro sits above existing providers.

Examples include:

- Tibber
- Nord Pool
- Smart meters
- Solar systems
- Battery systems

Provider integrations supply data.

Electricity Pro transforms that data into insight.

---

### Modular Architecture

Capabilities should be added as independent modules.

Examples include:

- Calculations
- Statistics
- Forecasting
- Recommendations
- Dashboards

Each module should remain independently testable.

---

## Roadmap

### v0.6 — Foundation ✅

Completed.

Highlights:

- Home Assistant integration
- Derived sensors
- Automated testing
- Continuous Integration
- Documentation
- Home Assistant validation

---

### v0.7 — Traditional Sensors & Statistics ✅

#### Goal

Expand Electricity Pro with native Home Assistant sensors and provider
abstractions.

Delivered:

- Cost Today
- Remaining Cost Today
- Peak Power Today
- Monthly Peak Hour Consumption
- Three-phase current and voltage
- Provider abstraction and configuration improvements

---

### v0.8 — Statistics Foundation & First Insight ✅

#### Goal

Establish reusable monthly statistics and turn electricity prices into the
first actionable insight.

Delivered:

- Persistent monthly statistics foundation
- Energy This Month
- Cost This Month
- Effective Price with optional variable grid-fee adjustments
- Good Time to Use Electricity insight

---

### v0.9 — Daily Statistics & Dashboard Experience ✅

#### Goal

Complete the core daily statistics and present measurements, statistics and
insights through polished dashboards.

Delivered:

- Energy Today
- Monthly Peak Hour Time
- Consumption-Weighted Average Price Today
- Standard dashboard using built-in Home Assistant cards
- Enhanced optional dashboard using Mushroom and ApexCharts Card

Dashboard examples:

#### Standard

Uses only built-in Home Assistant cards. Delivered.

#### Enhanced

Uses optional custom cards for richer visualisations and analytics. Delivered.

Average Market Price Today and Average Power Today were intentionally deferred
from v0.9 and delivered in v1.4 and v1.3 respectively.

---

### v1.0 — Stable Release ✅

#### Goal

A mature Home Assistant integration suitable for broad adoption.

Delivered:

- HACS custom-repository installation support
- Hassfest and HACS CI validation workflows
- Brand icon
- Phase sensor abstraction (`PHASES` refactor)
- Measurement normalisation consolidation (`_parse_state` helper)
- Full canonical MIT licence
- Complete architecture and roadmap documentation

---

### v1.1 — Forecast Prices & Scheduling Insights ✅

#### Goal

Introduce Nord Pool-based future-price insights and scheduling windows while
keeping the internal design clean enough to support broader forecast sources
later.

Delivered:

- Normalized `ForecastInterval` internal model with timezone-aware validation
  and resolution derived from interval boundaries (not assumed)
- Nord Pool forecast ingestion via the native `nordpool.get_prices_for_date`
  action with MWh → kWh normalization
- Cheapest upcoming 1h, 2h and 3h continuous window sensors
- Companion average scheduling-price sensors for each window duration
- Near-term price direction sensor (rising / falling / stable)
- Optional next inexpensive 1h window sensor gated on both the good-price
  threshold and comparable complete live/forecast price semantics
- Explicit gap, overlap and unavailable-data handling throughout
- DST and timezone edge cases covered by dedicated tests
- Forecast features require Nord Pool; insight calculations are provider-agnostic

---

### v1.2 — Provider-Independent Pricing & Tariff Foundation ✅

#### Goal

Make price and cost semantics explicit so Tibber users retain a simple setup
while other users can combine Nord Pool, compatible meters, and configured
supplier and grid tariffs without double counting.

Delivered:

- Guided setup with independent measurement-source and price-source choices
- Automatic, reviewable discovery for a Tibber home using Tibber Pulse and a
  Tibber electricity contract
- A custom/mixed path for other dongles, suppliers, Nord Pool, and manually
  selected entities, resolving to the same normalized source contracts
- Explicit supplier-price, market-price, and complete-price strategies
- Component inclusion and VAT semantics
- Cost provenance and tariff completeness metadata
- Metadata-aware Effective Price, Current Cost Rate, and Good Time calculations
- Time-of-use grid fees with weekday, seasonal, and optional Workday holiday
  rules ([#162](https://github.com/guslund-jpg/electricity-pro/issues/162))
- Separate fixed grid-provider and electricity-supplier fees
  ([#163](https://github.com/guslund-jpg/electricity-pro/issues/163))
- A normalized foundation for future cost composition

The architecture is defined by
[ADR-0005](docs/adr/0005-pricing-and-tariff-strategies.md) and tracked by
[#166](https://github.com/guslund-jpg/electricity-pro/issues/166). Existing
entity IDs remain stable. Automatic device control and broad regional tariff
catalogues are outside this release. Source adapters simplify discovery and
configuration; they do not introduce provider-specific calculation branches.

---

### v1.3 — Recommendation Intelligence ✅

#### Goal

Turn normalized price data, reliable forecasts, and household statistics into
explainable, actionable recommendations.

Delivered:

- Provider-independent Peak Power Today and peak-time statistics implemented
  from [ADR-0006](docs/adr/0006-provider-independent-daily-power-statistics.md)
  under [#64](https://github.com/guslund-jpg/electricity-pro/issues/64)
- Minimal persisted history primitives introduced only as required by the first
  recommendation designs
- Consumption Timing Score Yesterday, defined by
[ADR-0007](docs/adr/0007-consumption-timing-score.md) and tracked by
[#115](https://github.com/guslund-jpg/electricity-pro/issues/115), with
retrospective quality and price-variation metadata
- Provider-independent Estimated Base Load, defined by
[ADR-0008](docs/adr/0008-base-load-estimation.md) and tracked by
[#34](https://github.com/guslund-jpg/electricity-pro/issues/34), using bounded
Current Power history without claiming appliance identity or annual cost
- Provider-independent Average Power Today, defined by
[ADR-0009](docs/adr/0009-average-power-today.md) and tracked by
[#82](https://github.com/guslund-jpg/electricity-pro/issues/82), with explicit
elapsed-day coverage
- Tibber fast-track access to optional native Nord Pool forecast selection

Forward-looking coaching, expected savings, appliance scheduling guidance, and
automatic device control remain future, separately designed capabilities.

---

### v1.4 — Market Price Intelligence ✅

Completed.

#### Goal

Expose provider-independent current and forecast market-price data so users can
understand the underlying spot market, see the available future price horizon,
and build retrospective market statistics on one normalized interval contract.

Highlights:

- Current Market Price with explicit component and VAT semantics
- A bounded provider-independent market-price forecast series
- A forward-looking dashboard graph with a visible current-time position
- Market Price alongside Supplier Price and Effective Price in the live chart
- Average Market Price Today after complete-day behavior is defined

The architecture is proposed by
[ADR-0011](docs/adr/0011-market-price-series-contract.md) and tracked by
[#217](https://github.com/guslund-jpg/electricity-pro/issues/217) and
[#57](https://github.com/guslund-jpg/electricity-pro/issues/57). Forecast
Effective Price remains a separate design because every future supplier, tax,
VAT, and time-dependent grid component must be projected correctly.

---

### v1.5 — Adaptive Price Intelligence 📋

#### Goal

Replace a purely fixed definition of a good electricity price with an optional,
explainable classification that can adapt to changing market conditions while
preserving the existing fixed threshold.

Planned direction:

- retain the fixed Good Price threshold as a backward-compatible mode;
- add an adaptive mode based on compact, comparable historical price summaries;
- consider available forecast prices only when their component and VAT scope is
  genuinely comparable;
- define deterministic cold-start, negative-price and tariff-change behaviour;
- expose the calculated threshold, data coverage and reason for each result;
- resolve the confusing unavailable Next Inexpensive 1h Window entity; and
- reconcile roadmap, sensor and architecture documentation with delivered
  capabilities.

Supplier markup, total accumulated-energy sources and the expanded Standard
dashboard are already present in the unreleased development line and form part
of the v1.5 release baseline.

The adaptive classification contract is proposed by
[ADR-0012](docs/adr/0012-adaptive-good-price-classification.md).

Tracked work: [adaptive good-price threshold #237](https://github.com/guslund-jpg/electricity-pro/issues/237),
[unavailable recommendation sensor #232](https://github.com/guslund-jpg/electricity-pro/issues/232),
and [contributor design guidance #70](https://github.com/guslund-jpg/electricity-pro/issues/70).

Automatic device control is outside v1.5. Adaptive means relatively favourable
under a documented method; it does not determine what an individual household
can afford.

---

### v1.6 — Production & Bidirectional Energy Foundation 🔭

#### Goal

Extend Electricity Pro from consumption-oriented net-grid analysis to explicit,
provider-independent production, import and export energy flows.

Planned direction:

- define normalized source contracts for grid import, grid export, local
  production and household consumption;
- support both daily and total accumulated energy counters where the source
  semantics are known;
- expose useful production, export, self-consumption and self-sufficiency
  statistics;
- retain signed Current Power for compatible net-grid meters without pretending
  that one net value reveals every underlying flow;
- add export compensation and revenue only from an explicitly configured export
  price contract; and
- allow existing consumption analytics to use gross household demand when the
  required source data is available.

The v1.6 foundation must work without solar, a battery or an EV and must not
infer missing flows. Device control and vendor-specific integrations remain out
of scope.

Tracked work: [energy-flow contract #239](https://github.com/guslund-jpg/electricity-pro/issues/239),
[production analytics #240](https://github.com/guslund-jpg/electricity-pro/issues/240),
and [export pricing and revenue #241](https://github.com/guslund-jpg/electricity-pro/issues/241).

---

### v1.7 — Flexible-Load Recommendations 🔭

#### Goal

Build advisory, explainable scheduling recommendations for flexible household
loads after price forecasts and energy-flow semantics are reliable.

Candidate capabilities:

- EV charging windows that account for required energy, departure time and
  charging-power constraints;
- heat-pump operating windows that respect comfort boundaries, minimum run
  times and user-defined constraints; and
- reusable load definitions for appliances with duration and energy needs.

Recommendations come before automatic control. Electricity Pro must degrade
safely when a device, forecast or price component is unavailable and must not
assume that a recommended device can be controlled.

Tracked work: [EV charging recommendations #242](https://github.com/guslund-jpg/electricity-pro/issues/242)
and [heat-pump recommendations #243](https://github.com/guslund-jpg/electricity-pro/issues/243).

---

### v1.8 — Storage & Whole-Home Optimisation 🔭

#### Goal

Use the production foundation and complete import/export price semantics to
plan storage and coordinate flexible household energy use.

Candidate capabilities:

- battery charge and discharge scheduling using state of charge, usable
  capacity, power limits and round-trip efficiency;
- comparison of self-consumption, export and later grid import;
- coordination with solar forecasts, EV requirements and flexible loads; and
- transparent fallback behaviour when forecasts or device data are incomplete.

Battery scheduling is deliberately later than the production foundation. A
safe schedule cannot be derived from net power and an import price alone.

Tracked work: [battery scheduling and whole-home optimisation #244](https://github.com/guslund-jpg/electricity-pro/issues/244).

---

## Beyond v1.8

Potential later capabilities include appliance-specific models, richer solar
forecast integration, automatic control behind explicit opt-in safeguards, and
broader whole-home energy intelligence.

---

## The Three Questions

Every feature should help answer one of these questions.

### What is happening?

Live measurements.

---

### Why is it happening?

Statistics and analysis.

---

### What should I do next?

Forecasts, optimisation and intelligent recommendations.

These three questions guide the long-term evolution of Electricity Pro.

---

## Status

This roadmap represents the current long-term direction of the project.

Priorities may evolve as Home Assistant develops and as new contributors help shape Electricity Pro.
