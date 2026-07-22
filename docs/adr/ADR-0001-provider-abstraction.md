# ADR-0001: Provider Abstraction Layer

- Status: Accepted
- Date: 2026-07-22
- Decision owners: Electricity Pro maintainers

## Context

Electricity data can originate from many Home Assistant integrations,
including Tibber, Nord Pool, MQTT, ESPHome, Shelly, REST sensors, and
utility-meter integrations.

Provider-specific entity names and attributes are not stable enough to
form the public interface of Electricity Pro. Dashboards, alerts, and
statistics would become tightly coupled to a particular provider if they
referenced those entities directly.

That coupling would make provider changes difficult and would cause
provider-specific behavior to spread throughout the project.

## Decision

Electricity Pro will use a provider abstraction layer.

Only source adapters may reference provider-specific entities.

Source adapters translate provider data into canonical Electricity Pro
entities. All higher-level modules must use those canonical entities.

The architectural dependency direction is:

```text
Provider integrations
        |
        v
Source adapters
        |
        v
Canonical Electricity Pro entities
        |
        +--> Core calculations
        +--> Statistics
        +--> Health and diagnostics
        +--> Alerts
        +--> Dashboards

Examples of provider-specific entities include:

sensor.tibber_*
sensor.nordpool_*
sensor.shelly_*
sensor.esphome_*

Examples of canonical entities include:

sensor.electricity_pro_current_power
sensor.electricity_pro_current_price
sensor.electricity_pro_energy_today
sensor.electricity_pro_cost_today

Provider-specific entities must not be referenced outside:

packages/10_sources/
Consequences
Positive
Providers can be changed without redesigning dashboards.
Core calculations remain independent of integration naming.
Tests can validate a stable public data contract.
New providers can be introduced through isolated adapters.
Provider-specific workarounds remain contained.
Negative
The project contains an additional abstraction layer.
Initial setup requires mapping source entities.
Some provider-specific features may not fit the canonical contract.
Adapter availability must be handled carefully to avoid stale values.
Alternatives considered
Reference provider entities directly

Rejected because provider details would spread across the project and
make provider changes expensive.

Create a separate complete package for every provider

Rejected because most core calculations, dashboards, and alerts would be
duplicated.

Build only for Tibber and Nord Pool

Rejected because provider independence is a foundational project goal.

Enforcement

Continuous integration should eventually reject:

provider-specific references outside packages/10_sources/;
duplicate canonical entity identifiers;
dashboards that reference provider-specific entities;
core modules that depend directly on provider integrations.
