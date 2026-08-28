# ADR-0010: Signed Power and Negative Electrical Values

## Status

Accepted

## Context

Electricity Pro currently rejects negative Current Power even though a
whole-home meter may legitimately report net export from solar, a home battery,
or a bidirectional charger. Live negative electricity prices are also rejected
by parts of the calculation path despite being valid market and contract data.

Allowing every negative value indiscriminately would be equally incorrect.
Electrical current is commonly an unsigned RMS magnitude, cumulative energy
counters have monotonic semantics, and an import contract price does not define
the compensation paid for exported energy.

The integration therefore needs a field-by-field signed-value contract rather
than one global rule.

## Decision

### Signed Current Power

Redefine normalized Current Power as signed whole-home net grid exchange:

- positive watts mean net import from the grid;
- zero means no net exchange; and
- negative watts mean net export to the grid.

The existing `current_power` entity, entity ID, unit, device class, and state
class remain unchanged. Negative W and kW source values become valid and are
converted normally. Malformed, non-finite, unavailable, and unsupported-unit
values remain invalid.

This is a semantic expansion of the existing entity rather than a separate
export-power entity. A future source contract may add separate import and export
channels when providers expose gross flows rather than one net measurement.

### Negative prices

Current Price and Effective Price accept finite negative values. Configured
grid fees, energy tax, and other additive adjustments remain non-negative and
are added to the signed base price. The resulting Effective Price may remain
negative.

For positive imported power, Current Cost Rate may therefore be negative. This
correctly represents a negative variable consumption price. Good Time and the
Consumption Timing Score continue to compare and rank negative prices normally.

### Downstream behavior during export

An import price must never be multiplied by negative net power to claim export
income. While Current Power is negative:

- Current Cost Rate is unavailable;
- Peak Power Today ignores the observation and continues to mean peak import;
- Average Power Today is unavailable for a day containing export;
- Estimated Base Load rejects a day containing export; and
- Consumption Timing Score Yesterday rejects a day containing export.

The three historical calculations record
`unsupported_bidirectional_power` rather than silently clamping export to zero
or misclassifying it as missing source data.

### Other measurement classes

| Measurement | First-version negative-value rule |
| --- | --- |
| Current Power | Accepted as signed net grid exchange |
| Current Price | Accepted |
| Effective Price | Accepted after non-negative additions |
| Phase Current | Rejected; treated as an unsigned magnitude |
| Voltage | Rejected |
| Accumulated Energy | Rejected; counters remain non-negative |
| Accumulated Cost | Rejected pending a signed cumulative-cost design |
| Grid fees and taxes | Rejected |

Phase-current sign varies by meter and wiring convention and cannot be assumed
to represent export direction. Accumulated cost also feeds monthly delta logic
that currently requires non-negative cumulative readings. Both require their
own explicit contracts before expansion.

## Configuration and compatibility

No migration or new user setting is required. Existing non-negative power
sources behave as before. A source that previously made Current Power
unavailable when negative will now publish the signed value, so dashboards and
automations can observe export directly.

Documentation must call the source a whole-home net grid-power sensor. Selecting
a generation-only sensor does not satisfy that contract.

## Provider independence

The sign convention belongs to the normalized source contract, not to Tibber,
Nord Pool, a country, or a device name. Source adapters may help discover a
compatible entity but must output the same signed net-power semantics.

## Boundaries

This first version does not include:

- export energy or export revenue sensors;
- an export compensation price source;
- separate gross import and export power channels;
- self-consumption or solar-production calculations;
- battery charge-state interpretation;
- signed phase-current semantics; or
- signed accumulated monthly cost.

These capabilities require explicit source provenance and must not be inferred
from one signed net-power value.

## Testing strategy

Provider tests cover signed W and kW normalization while retaining rejection of
non-finite and unsupported values. Calculation tests cover negative prices,
negative Effective Price, negative imported cost rate, and unavailable export
cost rate.

Coordinator and entity tests verify signed Current Power publication, peak
import behavior, export-day rejection for historical analytics, persistence of
the rejection marker, and unchanged behavior for ordinary import-only sources.

## Consequences

### Positive

- Solar and battery homes can see truthful signed net power.
- Negative electricity prices work consistently across live and historical
  price features.
- Export is not falsely presented as consumption, base load, or revenue.
- Existing entity identities and import-only behavior remain stable.

### Trade-offs

- Historical demand insights become unavailable on days containing export.
- The integration still cannot report gross household demand behind solar.
- Export income remains unavailable until a separate price contract is added.
