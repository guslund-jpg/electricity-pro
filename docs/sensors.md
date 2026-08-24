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
| Live | Effective price | `effective_price` | Calculated | Currency/kWh | None | Measurement | Available |
| Live | Current cost rate | `current_cost_rate` | Calculated | Currency/h | None | Measurement | Available |
| Daily | Energy today | `current_energy` | Mirrored | Wh or kWh | Energy | Total increasing | Available |
| Monthly | Energy this month | `energy_this_month` | Calculated | kWh | Energy | Total | Available |
| Daily | Cost today | `cost_today` | Mirrored | Currency | Monetary | Total | Available |
| Daily | Consumption-weighted average price today | `consumption_weighted_average_price_today` | Calculated | Currency/kWh | None | Measurement | Available |
| Monthly | Cost this month | `cost_this_month` | Calculated | Currency | Monetary | Total | Available |
| Daily | Remaining cost today | `remaining_cost_today` | Calculated | Currency | None | Measurement | Available |
| Daily | Peak power today | `peak_power_today` | Calculated | W | Power | Measurement | Planned provider-independent calculation |
| Daily | Peak power time today | `peak_power_time_today` | Calculated | Timestamp | Timestamp | None | Planned |
| Monthly | Monthly peak-hour time | `monthly_peak_hour_time` | Mirrored | Timestamp | Timestamp | None | Available |

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
| Average power today | `average_power_today` | Calculated | W | Future | Requires statistics implementation |
| Average market price today | `average_price_today` | Calculated | Currency/kWh | Future | Requires price history |
| Monthly peak-hour consumption | `monthly_peak_hour_consumption` | Mirrored initially | kWh | High | Highest hourly consumption in current month |

### Consumption-weighted average price today

This calculated sensor shows the average effective price achieved by the
household's actual consumption pattern today:

> Cost Today / Energy Today + configured variable grid fee + configured Energy Tax

Energy is normalized to kWh before division. The configured VAT-inclusive
per-kWh adjustments are then applied exactly once. The sensor is unavailable
when either daily source is unavailable, the energy unit is unsupported, or
Energy Today is zero.

The value is retrospective and is not a recommendation to consume electricity
now. It differs from Average Market Price Today, which would average the day's
market prices without considering when the household used electricity.

Cost Today and Energy Today must cover the same local calendar-day period. On
the first day, the result is only as complete as those source values; no
historical values are reconstructed by Electricity Pro.

Live Effective Price, Current Cost Rate, and Good Time require explicit pricing
metadata. Electricity Pro adds configured variable grid fee and Energy Tax only
when those components are not already declared as part of the selected source
price. An entry with a configured price source cannot load until its source
type, included components, and VAT treatment are confirmed in integration
options.

### Monthly peak-hour consumption

This sensor is relevant for demand-based grid tariffs.

The initial implementation may mirror a provider sensor when its semantics are
clear.

The sensor should represent:

> The largest energy consumption recorded during a single hourly interval in
> the current billing month.

It should not be mislabeled as instantaneous power.

### Energy this month

This sensor accumulates changes from the configured cumulative energy source,
persists its state across Home Assistant restarts, and resets at the start of
the local calendar month. Values are normalized to kWh.

The first reading establishes the baseline. The first month may therefore be
partial when Electricity Pro is installed or the energy source is configured
after the month has started. Subsequent full months are complete.

### Cost this month

This sensor accumulates changes from the configured Cost Today source,
persists its state across Home Assistant restarts, and handles the source's
daily reset. It resets at the start of the local calendar month and preserves
the source currency.

On first setup, the current Cost Today value seeds the monthly total so Cost
This Month includes the whole current day. The first month may still be partial
because costs from earlier days are unavailable. Subsequent full months are
complete.

A future provider-independent implementation may calculate billing peaks from
historical interval data and configurable tariff rules.

## Current insights

### Good time to use electricity

The optional `good_time_to_use_electricity` binary sensor compares Effective
Price with a user-configured good-price threshold in the same currency per
kWh. It is on at or below the threshold and off above it.

The insight is unavailable without current price data and is not created until
a threshold is configured. This first version uses an absolute threshold;
future forecast adapters may add relative and forward-looking recommendations.

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
