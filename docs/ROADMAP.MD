# Electricity Pro Roadmap

> Understand. Predict. Optimise.

Electricity Pro helps Home Assistant users understand, predict and optimise their electricity usage through provider-independent analytics.

---

# Vision

Electricity data alone is rarely useful.

People want answers.

Electricity Pro transforms measurements into insights that help users understand what is happening now, what is likely to happen next, and how to reduce electricity costs.

---

# Guiding Principles

Every feature should satisfy at least one of these goals:

✓ Understand electricity usage

✓ Predict future consumption or cost

✓ Optimise energy usage

If a feature does not support one of these goals, it probably does not belong in Electricity Pro.

---

# Product Journey

Measure
    │
    ▼
Understand
    │
    ▼
Predict
    │
    ▼
Optimise

---

# Version 0.6 — Foundation

Status: Complete

Focus

• Stable architecture

• Provider abstraction

• Event-driven coordinator

• Pure analytics

• Test suite

• CI/CD

Outcome

A stable foundation for future analytics.

---

# Version 0.7 — Understand

Theme

Understand electricity usage.

Features

• Base load detection

• Remaining cost improvements

• Daily projections

• Historical analytics

• Recorder integration

Questions answered

• What is my standby consumption?

• How much will today cost?

• How much energy remains today?

---

# Version 0.8 — Predict

Theme

Explain and predict electricity usage.

Features

• Trend analysis

• Cost anomalies

• Consumption anomalies

• Daily summaries

• Insight entities

Questions answered

• Why was yesterday expensive?

• Is my consumption increasing?

• What changed?

---

# Version 0.9 — Optimise

Theme

Reduce electricity cost.

Features

• Cheapest hours

• Peak detection

• Load shifting

• Smart recommendations

Questions answered

• When should I run appliances?

• How can I reduce today's bill?

---

# Version 1.0 — Stable

Goals

• Stable public API

• Complete documentation

• Excellent automated tests

• HACS ready

• Community reviewed

---

# Future

Possible future areas

• Solar

• Battery

• EV charging

• Carbon intensity

• Multi-home

These are ideas rather than commitments.

---

# Architecture Promise

Electricity Pro values maintainability over rapid feature growth.

New features should

• Build on the existing architecture

• Remain provider-independent

• Use pure analytics

• Include automated tests

• Improve understanding, prediction or optimisation

Large rewrites should be exceptional.

---

# Guiding Philosophy

Electricity Pro should answer questions—not merely expose data.
