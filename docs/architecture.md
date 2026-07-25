# Electricity Pro Architecture

Electricity Pro is an analytics engine for Home Assistant.

It does not collect electricity data.

It interprets electricity data provided by other integrations.

## Layers

Provider
↓

Coordinator
↓

Pure calculations
↓

Pure statistics
↓

Sensors

## Design principles

- Provider independent
- Pure calculation modules
- Thin sensor layer
- Comprehensive unit tests
- Home Assistant idioms
