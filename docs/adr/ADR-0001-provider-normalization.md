# ADR-0001: Provider Normalization Layer

## Status

Accepted

## Date

2026-07-25

## Context

Electricity Pro receives measurements from Home Assistant entities.

These entities may:

- use different units
- contain unavailable values
- contain unknown values
- contain invalid numeric values

The analytics layer should not be responsible for validating or normalizing
external measurements.

## Decision

All external measurements are normalized by the Provider layer before they
enter the application.

The provider is responsible for:

- reading Home Assistant entity states
- validating values
- converting supported units
- returning immutable `ElectricityProData`

Invalid or unsupported measurements are represented as `None`.

## Consequences

Advantages

- Analytics receives trusted data.
- Calculations remain independent of Home Assistant.
- Validation logic exists in one place.
- Unit handling is centralized.

Trade-offs

- The Provider becomes the only place where external data may enter the
  application.
- New measurement types require provider support.

## Alternatives Considered

Validation inside sensors

Rejected because presentation should not contain business logic.

Validation inside calculations

Rejected because analytics should assume trusted input.
