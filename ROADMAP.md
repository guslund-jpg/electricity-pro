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

Average Market Price Today and Average Power Today remain future candidates
outside the committed v0.9 scope.

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

### v1.2 — Provider-Independent Pricing & Tariff Foundation

#### Goal

Make price and cost semantics explicit so Tibber users retain a simple setup
while other users can combine Nord Pool, compatible meters, and configured
supplier and grid tariffs without double counting.

Planned capabilities:

- Guided setup with independent measurement-source and price-source choices
- Automatic, reviewable discovery for a Tibber home using Tibber Pulse and a
  Tibber electricity contract
- A custom/mixed path for other dongles, suppliers, Nord Pool, and manually
  selected entities, resolving to the same normalized source contracts
- Explicit supplier-price, market-price, and complete-price strategies
- Component inclusion and VAT semantics
- Cost provenance and tariff completeness metadata
- Conservative migration of existing v1.1 configurations
- Nord Pool plus configured supplier-markup pricing
- Time-of-use grid fees ([#162](https://github.com/guslund-jpg/electricity-pro/issues/162))
- Fixed supplier charges ([#163](https://github.com/guslund-jpg/electricity-pro/issues/163))
- A normalized foundation for future cost composition

The architecture is defined by
[ADR-0005](docs/adr/0005-pricing-and-tariff-strategies.md) and tracked by
[#166](https://github.com/guslund-jpg/electricity-pro/issues/166). Existing
entity IDs remain stable. Automatic device control and broad regional tariff
catalogues are outside this release. Source adapters simplify discovery and
configuration; they do not introduce provider-specific calculation branches.

---

### v1.3 — Recommendation Intelligence

#### Goal

Turn normalized price data, reliable forecasts, and household statistics into
explainable, actionable recommendations.

Potential capabilities:

- Best start time for a flexible appliance or charging session
- Expected cost for a planned power level and duration
- Estimated savings from waiting for a better window
- EV charging, dishwasher and washing-machine scheduling guidance
- Heat-pump preheating opportunities
- Consumption Timing Score with historical and forward-looking coaching
- Recommendation entities suitable for dashboards and Home Assistant
  automations

Recommendations should explain the price window, duration, assumptions and
estimated benefit behind their advice. Automatic device control remains a
separate, explicitly designed capability.

---

## Beyond v1.3

Potential future capabilities include:

- Solar optimisation
- Battery optimisation
- EV charging optimisation
- Heat pump optimisation
- Whole-home energy intelligence

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
