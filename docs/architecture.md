# Electricity Pro Architecture

Electricity Pro is an analytics engine for Home Assistant.

It consumes electricity measurements from existing integrations and
produces higher-level analytics.

Electricity Pro intentionally does not replace:

- Home Assistant Energy Dashboard
- Utility Meter
- Recorder

Instead it builds on them.

---

## Layers

Provider
↓

Coordinator
↓

Pure calculation modules

- calculations.py
- statistics.py

↓

Sensor layer

---

## Design principles

- Provider independent
- Pure functions whenever possible
- Thin Home Assistant entities
- Comprehensive tests
- One responsibility per module
