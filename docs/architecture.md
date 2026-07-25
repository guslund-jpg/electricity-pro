# Architecture

## Purpose

Electricity Pro is built around a simple principle:

> Measurements are collected once, analytics are calculated once, and results are presented many times.

This separation keeps the project maintainable, testable and easy to extend.

---

## Architecture Overview

```text
Home Assistant
       │
       ▼
Provider
       │
       ▼
ElectricityProData
       │
       ▼
Analytics
       │
       ▼
Presentation
```

---

## Layers

### Provider

Responsibilities

- Read Home Assistant entities
- Validate measurements
- Normalise units
- Populate ElectricityProData

The provider never performs business calculations.

---

### ElectricityProData

Responsibilities

Store trusted measurements required by the analytics layer.

Examples

- Current power
- Current price
- Daily energy
- Accumulated cost

The data model contains measurements, not calculated values.

---

### Analytics

Responsibilities

Perform all business calculations.

Examples

- Remaining Cost Today
- Estimated Cost Today
- Monthly Projection
- Budget Tracking

The analytics layer should be pure Python and independent of Home Assistant.

---

### Presentation

Responsibilities

Expose analytics through:

- Sensors
- Services
- Dashboards

Presentation should never contain business logic.

---

## Dependency Direction

Dependencies always flow downward.

```text
Home Assistant
      │
      ▼
Provider
      │
      ▼
Data Model
      │
      ▼
Analytics
      │
      ▼
Presentation
```

No layer should depend on a layer below it.

---

## Design Principles

### Single Responsibility

Each module has one responsibility.

## Pure Analytics

Business logic belongs in the analytics layer.

### Trusted Measurements

Measurements are never invented.

If required data is unavailable, analytics should report unavailable rather than guessing.

### Explainability

Every calculation should eventually be explainable.

---

## Future Growth

New capabilities should extend the analytics layer without requiring changes to the overall architecture.

Examples include:

- Forecasting
- Recommendation Engine
- Solar Analytics
- Battery Optimisation
- I put in a line here just to undestand how git works
