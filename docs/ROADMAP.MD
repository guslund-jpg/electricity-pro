# Electricity Pro Roadmap

> **Understand. Predict. Optimise.**

Electricity Pro transforms electricity measurements into meaningful analytics and actionable insights for Home Assistant.

Rather than exposing more raw data, Electricity Pro aims to answer practical questions such as:

- What is my electricity costing right now?
- How much will today probably cost?
- What is my normal background consumption?
- Is my electricity usage changing?
- How can I reduce my electricity costs?

---

## Vision

Electricity Pro is designed around a provider-independent analytics engine that complements Home Assistant.

The project evolves through four stages:

**Foundation → Understand → Insight → Optimise**

Each release builds upon a stable architecture instead of adding isolated features.

---

## Release Roadmap

### v0.6 — Foundation

**Status:** In Progress

#### Goal

Build a stable and maintainable architecture for future analytics.

#### Scope

- Provider-independent data model
- Event-driven coordinator
- Declarative sensor platform
- Pure analytics layer
- Automated testing
- Continuous Integration
- Repository quality improvements
- Project documentation

#### Outcome

A solid foundation that allows new analytics to be added without redesigning the architecture.

---

### v0.7 — Understanding

#### Goal

Help users understand their electricity usage.

#### Planned Features

- Base-load detection
- Standby consumption estimates
- Improved remaining-cost calculation
- Daily energy projection
- Daily cost projection
- Historical consumption analysis
- Recorder integration improvements

#### Questions Answered

- What is my standby consumption?
- What does my standby consumption cost?
- How much energy will I probably use today?
- How much is today likely to cost?

---

### v0.8 — Insights

#### Goal

Explain electricity usage.

#### Planned Features

- Trend analysis
- Cost anomaly detection
- Consumption anomaly detection
- Daily summaries
- Weekly summaries
- Insight entities
- Confidence indicators

#### Questions Answered

- Why was yesterday expensive?
- Has my consumption changed?
- Is my background load increasing?
- Was today unusual?

---

### v0.9 — Optimisation

#### Goal

Help users reduce electricity costs.

#### Planned Features

- Peak-load detection
- Cheapest-hour analysis
- Cheapest time-window analysis
- Load-shifting suggestions
- Smart recommendations
- Appliance scheduling guidance

#### Questions Answered

- When should I run the dishwasher?
- Which electricity usage could be moved to cheaper hours?
- How can I reduce today's cost?

---

### v1.0 — Stable

#### Goal

Deliver a mature production-ready release.

#### Objectives

- Stable public API
- Comprehensive documentation
- Excellent automated tests
- Reliable upgrades
- HACS-ready
- Community feedback incorporated

---

## Future Possibilities

Potential future areas include:

- Solar analytics
- Battery analytics
- EV charging analytics
- Carbon-intensity integration
- Multi-home support
- Advanced forecasting

These ideas are intentionally unscheduled.

---

## Architecture Principles

### Provider Independence

Providers collect and normalise measurements.

Analytics should remain independent of the underlying provider.

---

### Event-Driven Updates

The coordinator reacts to relevant source updates.

Entities should not poll unnecessarily.

---

### Pure Analytics

Business logic should be implemented using deterministic Python functions wherever practical.

Analytics should remain independently testable without Home Assistant.

---

### Presentation-Only Entities

Entities expose analytics.

Business logic belongs in the analytics layer.

---

### Immutable State

Shared integration state should be represented using explicit immutable data structures.

---

### Behaviour-Focused Tests

Tests should verify observable behaviour rather than implementation details.

---

## Feature Criteria

New functionality should normally satisfy at least one of these goals:

- Help users understand electricity usage.
- Help users predict future consumption or costs.
- Explain meaningful changes or patterns.
- Help users optimise electricity usage.

New features should also:

- preserve the existing architecture;
- remain provider-independent where practical;
- include automated tests;
- update documentation where appropriate.

---

## Non-Goals

Electricity Pro is **not** intended to become:

- a replacement for the Home Assistant Energy Dashboard;
- a cloud analytics service;
- a vendor-specific integration;
- a general automation platform;
- a collection of unrelated sensors.

Instead, Electricity Pro complements Home Assistant by providing reusable electricity analytics.

---

## Development Process

Significant features generally follow this workflow:

1. Define the user problem.
2. Create a GitHub issue with acceptance criteria.
3. Review the architecture.
4. Add or update tests.
5. Implement the feature.
6. Validate locally.
7. Verify CI.
8. Review against the acceptance criteria.
9. Update documentation.

---

## Guiding Principle

> **Electricity Pro should answer useful questions, not merely expose more data.**
