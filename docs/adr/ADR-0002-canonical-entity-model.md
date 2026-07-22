# ADR-0002: Canonical Entity Model

- Status: Accepted
- Date: 2026-07-22
- Decision owners: Electricity Pro maintainers

## Context

Electricity Pro needs a stable public interface between source adapters
and higher-level functionality.

Without a defined entity model, dashboards and modules may make different
assumptions about names, units, availability, precision, and update
behavior.

## Decision

Electricity Pro will expose a small set of canonical entities.

Canonical entity IDs use the prefix:

```text
electricity_pro_

The initial contract contains four primary measurements:

sensor.electricity_pro_current_power
sensor.electricity_pro_current_price
sensor.electricity_pro_energy_today
sensor.electricity_pro_cost_today

The contract also contains source-health entities:

binary_sensor.electricity_pro_power_source_healthy
binary_sensor.electricity_pro_price_source_healthy

Canonical entities are divided into:

required entities;
conditionally required entities;
optional entities.

The exact definitions are maintained in:

docs/specification/source-contract.md
Naming rules

Canonical entity names must:

use lowercase snake case;
begin with electricity_pro_;
describe the value rather than its provider;
avoid location-specific names;
avoid integration-specific terminology;
remain stable after release unless a documented migration exists.
Availability rules

A canonical entity must not invent a numeric value when its source is
unavailable or invalid.

Unavailable input should normally produce an unavailable canonical
entity rather than zero.

Zero is a valid measurement and must not be used as a substitute for
missing data.

Unit rules

Source adapters are responsible for converting source values into the
canonical unit required by the contract.

Higher-level modules may assume that canonical entities already use the
documented units.

Consequences
Positive
Higher-level modules have a stable interface.
Unit conversion happens in one predictable layer.
Missing-data behavior can be tested consistently.
Dashboards can work with multiple providers.
Negative
Adapters may need conversion and normalization logic.
Backward compatibility becomes important once entity names are
released.
The canonical model cannot expose every provider-specific feature.
Compatibility

After the first stable release, canonical entity IDs are part of the
public API.

Breaking changes require:

an architecture decision record;
a migration guide;
a major version change when appropriate.
