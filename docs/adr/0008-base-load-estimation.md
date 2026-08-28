# ADR-0008: Provider-Independent Base-Load Estimation

## Status

Accepted

## Context

Electricity Pro reports live household power, daily peaks, energy, cost, and
consumption timing. These values do not answer how much power the home appears
to use continuously when discretionary loads are quiet.

The first base-load feature should answer:

> What is the household's estimated continuous background demand?

The estimate must work with any supported whole-home Current Power source. It
must not depend on Tibber, a provider-specific history API, a price source, or
Home Assistant Recorder. It must also avoid presenting a single unusually low
measurement as a stable household characteristic.

## Decision

Introduce one retrospective calculated sensor:

- **Estimated Base Load**;
- entity key `estimated_base_load`;
- unit W;
- whole-watt display precision; and
- unavailable until enough recent, quality-approved local days exist.

The first version estimates imported household base load only. It does not
claim to identify individual appliances or distinguish avoidable standby power
from essential continuous loads.

## Estimation model

### Daily estimate

Build duration-weighted 15-minute mean-power buckets from normalized Current
Power observations. For each quality-approved completed local day, calculate
the duration-weighted 10th percentile of its bucket means.

The 10th percentile represents a repeatedly observed low-demand level rather
than the absolute minimum. It is therefore less sensitive to one transient
zero, a meter glitch, or a brief outage.

Percentiles use linear interpolation between the surrounding cumulative
duration positions. All calculations retain decimal precision; the public
sensor rounds to the nearest whole watt.

### Multi-day estimate

Keep the seven most recent completed local days. Publish the median of the
eligible daily estimates when at least five eligible days are present.

The median prevents one unusual day—such as travel, a party, or prolonged EV
charging—from dominating the household estimate. The result updates only when
a local day is finalized, so it remains stable during the day.

## Why quiet hours are not required

The first version does not ask users to configure quiet hours. Fixed clock
windows make assumptions about sleep, work shifts, EV charging, heating, and
household routines. Searching the full day for a repeatedly observed low
demand is simpler and more portable.

A future optional schedule may narrow the analysis if real-world validation
shows that the automatic model is systematically misleading. It must not be
introduced before that need is demonstrated.

## Observation and persistence contract

A coordinator-owned power-history accumulator will:

1. receive normalized, timezone-aware Current Power observations;
2. receive the existing five-minute coordinator tick;
3. hold a power observation for at most ten minutes;
4. integrate valid power over elapsed time;
5. split observations at 15-minute and local-day boundaries; and
6. retain energy-equivalent power duration and covered duration, not raw
   high-frequency samples.

The base-load accumulator is independent of the Consumption Timing Score
accumulator because base-load estimation requires Current Power only. Missing
or unavailable price data must not reduce base-load coverage.

Persist only the current day, the seven most recent completed daily summaries,
and the latest estimate through the coordinator's existing Home Assistant
`Store`. Write at 15-minute bucket boundaries, local midnight, and integration
unload. Do not query Recorder.

## Coverage and availability

A completed local day is eligible only when:

- at least 90% of its actual duration has valid Current Power coverage;
- no uncovered gap exceeds 60 minutes;
- all accepted power values are finite and non-negative; and
- at least one covered bucket exists.

The actual 23-hour or 25-hour duration is used across daylight-saving
transitions.

The public sensor is unavailable until at least five eligible days exist in
the rolling seven-day window. Ineligible days remain represented in the window
as missing days rather than being replaced by older history. This prevents a
stale estimate from appearing current after several days of source failure.

Internal unavailability reasons are:

- `insufficient_history`;
- `insufficient_coverage`;
- `long_data_gap`; and
- `unsupported_bidirectional_power`.

## Supporting metadata

When available, the entity exposes:

- `window_start`;
- `window_end`;
- `eligible_days`;
- `required_days`;
- `daily_estimates_w`; and
- `method`, fixed to `median_of_daily_p10`.

The daily estimates make the result explainable without storing or exposing
raw power samples. A confidence score, annual energy, and annual cost are not
part of the first version.

## Provider independence

The input is normalized whole-home Current Power in watts. No provider name,
entity naming convention, tariff, price source, currency, or country-specific
rule enters the model.

The same calculation must work with Tibber Pulse and compatible non-Tibber
meter sources. Source adapters remain responsible only for discovering and
normalizing measurements.

## Boundaries

The first version does not include:

- appliance or circuit identification;
- a judgment that the base load is good or bad;
- a configurable quiet-hours schedule;
- annual standby energy or cost projections;
- change detection or alerts;
- forecast input;
- automatic device control;
- Recorder reconstruction before observation began; or
- exported energy and negative power.

ADR-0010 later defined signed Current Power. The estimator rejects any local
day containing export as `unsupported_bidirectional_power`; it must not clamp
negative values to zero because that would create an artificially low estimate.

## Testing strategy

Pure calculation tests cover:

- duration-weighted percentile interpolation;
- median calculation for odd and even day counts;
- transient minima and outlier days;
- insufficient history;
- missing coverage and long gaps;
- invalid and negative power; and
- rounding boundaries.

Accumulator tests cover interval splitting, maximum hold time, local midnight,
23-hour and 25-hour days, bounded retention, persistence, restart restoration,
and unavailable sources.

Entity tests cover state, attributes, stable identity, update timing, and
availability before five eligible days.

## Consequences

### Positive

- The estimate requires no provider-specific history API or user schedule.
- Multiple days and robust statistics reduce sensitivity to isolated minima.
- Power-only coverage keeps pricing outages unrelated to the result.
- Bounded aggregate storage avoids unbounded history and Recorder coupling.
- The model is deterministic, explainable, and independently testable.

### Trade-offs

- The first estimate requires five eligible days and may take up to a week to
  appear.
- Homes with continuously variable heating or charging may receive an estimate
  that includes some flexible demand.
- Whole-home data cannot identify which devices create the estimated load.
- Seven days describe recent behavior and may change with seasons or occupancy.
