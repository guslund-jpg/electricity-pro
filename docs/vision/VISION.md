# Electricity Pro Vision

Version: 1.0
Status: Accepted
Last updated: 2026-08-03

---

## Why Electricity Pro Exists

Electricity Pro exists to help Home Assistant users understand, optimize and
reduce the cost of their electricity consumption.

Modern electricity systems are becoming increasingly complex. Dynamic
electricity prices, grid tariffs, demand charges, batteries, solar production
and electric vehicles make it difficult to know when electricity should be
used.

Most existing integrations expose measurements.

Electricity Pro aims to transform those measurements into meaningful
information and actionable recommendations.

---

## Vision

Electricity Pro should become the most capable provider-independent electricity
analytics platform for Home Assistant.

The project should support multiple electricity providers while presenting one
consistent set of measurements, statistics and insights.

---

## What Electricity Pro Is

Electricity Pro is an analytics layer.

It receives measurements from one or more providers and transforms them into
statistics and insights that help users make better decisions.

```
Provider
        ↓
 Measurements
        ↓
 Normalization
        ↓
 Statistics
        ↓
 Insights
        ↓
 Home Assistant
```

---

## What Electricity Pro Is Not

Electricity Pro is not intended to replace electricity providers.

It should not duplicate provider-specific functionality unless doing so creates
additional value.

Electricity Pro is also not intended to become an accounting application.

While estimated electricity costs are useful, the primary goal is helping users
make better energy decisions rather than reproducing electricity invoices.

---

## Target Users

Electricity Pro should be useful for both beginners and advanced users.

A beginner should be able to configure the integration using only:

- Current power
- Electricity price

Advanced users may optionally configure:

- Energy sensors
- Grid tariffs
- Demand tariffs
- Solar production
- Battery systems
- Electric vehicles

No advanced configuration should be required for the core experience.

---

## Long-Term Goals

Electricity Pro should eventually provide three layers of functionality.

### Measurements

Normalized provider-independent measurements.

Examples:

- Power
- Voltage
- Current
- Energy

---

### Statistics

Calculated information derived from measurements.

Examples:

- Monthly energy
- Daily averages
- Peak consumption
- Estimated costs

---

### Insights

Recommendations based on statistics.

Examples:

- Best time to run appliances
- EV charging recommendations
- Peak-demand warnings
- Battery optimization
- Solar self-consumption optimisation

---

## Non-goals

Electricity Pro does not aim to replace:

- Electricity providers
- Grid providers
- Billing systems
- Energy Management Systems

Instead, Electricity Pro complements these systems by providing
provider-independent statistics, insights and recommendations.

---

## Guiding Principle

Electricity Pro should always answer one question:

> "What should I do next to use electricity more intelligently?"

Every feature should help users understand or optimise their energy usage.

If a feature does not contribute to that goal, it probably belongs in an
optional module rather than the core project.
