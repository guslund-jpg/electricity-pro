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
- Effective Price with optional variable grid-fee and tax/markup adjustments
- Good Time to Use Electricity insight

---

### v0.9 — Daily Statistics & Dashboard Experience

#### Goal

Complete the core daily statistics and present measurements, statistics and
insights through polished dashboards.

Delivered in current v0.9 development:

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

### v1.0 — Stable Release

#### Goal

A mature Home Assistant integration suitable for broad adoption.

Focus areas:

- HACS support
- Stable APIs
- Complete documentation
- Performance optimisation
- Long-term maintainability

---

## Beyond v1.0

Potential future capabilities include:

- Solar optimisation
- Battery optimisation
- EV charging optimisation
- Heat pump optimisation
- Dynamic electricity recommendations
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
