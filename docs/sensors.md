# Electricity Pro Sensor Catalog

This document defines the current and planned Electricity Pro sensors.

Its purpose is to keep sensor naming, semantics, units, Home Assistant metadata,
and implementation strategy consistent as the integration grows.

## Sensor types

Electricity Pro sensors fall into three categories.

### Mirrored sensors

Mirrored sensors expose a value supplied by an existing Home Assistant entity.

Electricity Pro may validate the value, normalize supported units, and provide
consistent naming and metadata.

Examples:

- Current power
- Current price
- Cost today
- Peak power today
- Phase current

### Calculated sensors

Calculated sensors derive a new value from one or more normalized inputs.

Calculations should be provider-independent and implemented as deterministic,
testable functions.

Examples:

- Current cost rate
- Remaining cost today

### Intelligence sensors

Intelligence sensors use statistics, forecasts, tariffs, or consumption
patterns to estimate future outcomes or recommend actions.

Examples:

- Estimated cost today
- Projected demand charge
- Cheapest remaining hours
- Peak warning

## Design rules

Each sensor should have:

- a clear and provider-independent meaning;
- a stable entity key;
- an appropriate device class;
- an appropriate state class;
- a documented native unit;
- defined availability behaviour;
- automated tests;
- a clear implementation category.

Provider-specific names should not appear in Electricity Pro entity names.

A provider value should only be mirrored when its semantics are sufficiently
clear and broadly useful.

## Current sensors

| Category | Sensor | Entity key | Type | Unit | Device class | State class | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Live | Current power | `current_power` | Mirrored | W | Power | Measurement | Available |
| Live | Current price | `current_price` | Mirrored | Currency/kWh | None | Measurement | Available |
| Live | Current cost rate | `current_cost_rate` | Calculated | Currency/h | None | Measurement | Available |
| Consumption | Energy | `current_energy` | Mirrored | Wh or kWh | Energy | Total increasing | Available |
| Daily | Cost today | `cost_today` | Mirrored | Currency | Monetary | Total | Available |
| Daily | Remaining cost today | `remaining_cost_today` | Calculated | Currency | None | Measurement | Available |
| Daily | Peak power today | `peak_power_today` | Mirrored | W | Power | Measurement | Available |


| Sensor     | Proposed entity key | Type     | Native unit | Device class | State class | Priority |
| ---------- | ------------------- | -------- | ----------- | ------------ | ----------- | -------- |
| Current L1 | `current_l1`        | Mirrored | A           | Current      | Measurement | High     |
| Current L2 | `current_l2`        | Mirrored | A           | Current      | Measurement | High.    |
| Current L3 | `current_l3`        | Mirrored | A           | Current      | Measurement | High     |


| Sensor     | Proposed entity key | Type     | Native unit | Device class | State class | Priority |
| ---------- | ------------------- | -------- | ----------- | ------------ | ----------- | -------- |
| Voltage L1 | `voltage_l1`        | Mirrored | V           | Voltage      | Measurement | Medium   |
| Voltage L2 | `voltage_l2`        | Mirrored | V           | Voltage      | Measurement | Medium   |
| Voltage L3 | `voltage_l3`        | Mirrored | V           | Voltage      | Measurement | Medium   |

## Planned live electrical measurements



### Power factor

| Sensor       | Proposed entity key | Type.    | Native unit | Device class | State class | Priority |
| ------------ | ------------------- | -------- | ----------- | ------------ | ----------- | -------- |
| Power factor | `power_factor`      | Mirrored | None or %   | Power factor | Measurement | Medium   |

Purpose:

- expose an advanced electrical diagnostic value;
- support motors, heat pumps, chargers, solar, and other reactive loads;
- provide an input for future diagnostics.

The source semantics and normalized representation must be reviewed before
implementation because integrations may expose power factor as either a ratio
or a percentage.

## Planned daily and monthly statistics

| Sensor | Proposed entity key | Type | Unit | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| Energy today | `energy_today` | Mirrored or calculated | kWh | Future | Requires explicit daily semantics |
| Average power today | `average_power_today` | Calculated | W | Future | Requires statistics implementation |
| Average price today | `average_price_today` | Calculated | Currency/kWh | Future | Requires price history |
| Cost this month | `cost_this_month` | Mirrored or calculated | Currency | Medium | Provider semantics must be documented |
| Energy this month | `energy_this_month` | Mirrored or calculated | kWh | Medium | Provider semantics must be documented |
| Monthly peak-hour consumption | `monthly_peak_hour_consumption` | Mirrored initially | kWh | High | Highest hourly consumption in current month |
| Time of monthly peak hour | `monthly_peak_hour_time` | Mirrored initially | Timestamp | Medium | Optional companion sensor |

### Monthly peak-hour consumption

This sensor is relevant for demand-based grid tariffs.

The initial implementation may mirror a provider sensor when its semantics are
clear.

The sensor should represent:

> The largest energy consumption recorded during a single hourly interval in
> the current billing month.

It should not be mislabeled as instantaneous power.

A future provider-independent implementation may calculate billing peaks from
historical interval data and configurable tariff rules.

## Planned intelligence sensors

| Sensor                       | Proposed entity key        | Type         | Priority |
| ---------------------------- | -------------------------- | ------------ | -------- |
| Estimated cost today         | `estimated_cost_today`     | Intelligence | High     |
| Estimated energy today       | `estimated_energy_today`   | Intelligence | High     |
| Projected demand charge      | `projected_demand_charge`  | Intelligence | Future   |
| Cheapest remaining hours     | `cheapest_remaining_hours` | Intelligence | Future   |
| Peak warning                 | `peak_warning`             | Intelligence | Future   |
| Phase imbalance              | `phase_imbalance`          | Calculated   | Future   |

These sensors require additional architecture for history, forecasting,
tariffs, or recommendations and are outside the scope of simple mirrored
sensor additions.

## Configuration growth

As the number of optional sources grows, a single configuration form may
become difficult to use.

Future configuration may be divided into sections such as:

### Basic

- Current power
- Current price
- Energy
- Accumulated cost

### Electrical measurements

- Current L1, L2, and L3
- Voltage L1, L2, and L3
- Power factor

### Statistics

- Peak power today
- Monthly peak-hour consumption
- Monthly cost
- Monthly energy

The configuration experience should remain understandable even when only the
required power source is selected.

## Priorities for v0.7

The remaining recommended sensor work for v0.7 is:

1. Phase current sensors L1, L2, and L3
2. Phase voltage sensors L1, L2, and L3
3. Monthly peak-hour consumption
4. Power factor

Each group should be implemented in a separate issue and pull request.

## Future provider-independent work

Mirrored sensors are a pragmatic first implementation.

Electricity Pro should gradually replace provider dependence where doing so
adds meaningful consistency or coverage.

Future work may include:

- calculating daily and monthly statistics from generic source sensors;
- restoring statistics after Home Assistant restarts;
- using Recorder history safely and efficiently;
- supporting configurable billing periods;
- supporting configurable demand-tariff rules;
- calculating phase imbalance;
- comparing provider values with calculated values.

These improvements should be tracked as enhancement issues rather than mixed
into the initial mirrored-sensor pull requests.
