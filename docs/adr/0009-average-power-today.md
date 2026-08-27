# ADR-0009: Provider-Independent Average Power Today

## Status

Proposed

## Context

Electricity Pro exposes Current Power, Peak Power Today, and Estimated Base
Load. These describe the instantaneous, highest, and recent background demand,
but not the representative demand level so far today.

Average Power Today should answer:

> What has my household's mean imported power been during the observed part of
> the current local day?

An arithmetic mean of sensor states would be incorrect because entity updates
are irregular. A value must be weighted by the duration for which each power
observation remains valid, and it must not imply complete-day coverage after a
restart or outage.

## Decision

Introduce one calculated sensor:

- **Average Power Today**;
- entity key `average_power_today`;
- native unit W;
- Power device class and Measurement state class; and
- whole-watt display precision.

The result is the duration-weighted mean of normalized Current Power over the
covered portion of the elapsed local day:

```text
average power = sum(power × covered duration) / sum(covered duration)
```

The calculation uses decimal precision internally. It is not the arithmetic
mean of observations and does not depend on an Energy Today source.

## Observation and coverage contract

Reuse the power-only 15-minute aggregates introduced for Estimated Base Load.
Current Power is held for at most ten minutes, segments are split at local-day
boundaries, and no raw high-frequency samples are retained.

The coverage denominator is elapsed real time from local midnight to the
calculation timestamp. This correctly follows 23-hour and 25-hour local days.
The sensor is available only when:

- at least 90% of elapsed local-day time has valid Current Power coverage;
- no uncovered gap in the elapsed day exceeds 60 minutes;
- at least one covered interval exists; and
- no negative power was observed during the local day.

At midnight the value becomes unavailable until a valid interval has been
observed. A new installation or restart late in the day remains unavailable if
the earlier missing time prevents the coverage threshold from being met.

## Persistence

No new raw-history store is introduced. The coordinator uses the existing
restart-safe, bounded current-day power aggregates owned by the base-load
runtime. Persistence remains independent of Home Assistant Recorder.

## Supporting metadata

When available, the entity exposes:

- `period_start`;
- `coverage_percent`;
- `covered_duration_minutes`; and
- `method`, fixed to `duration_weighted_mean`.

## Provider independence

The only input is normalized whole-home Current Power in watts. No provider,
price source, tariff, currency, Nord Pool forecast, or country rule enters the
calculation.

## Boundaries

The first version does not include:

- a completed-day Average Power Yesterday sensor;
- weekly or monthly averages;
- Recorder reconstruction before Electricity Pro observed the source;
- billing-grade energy derivation;
- exported energy or net-power semantics; or
- recommendations based on whether the value is high or low.

Bidirectional power remains tracked by issue #69 and must not be silently
clamped to zero.

## Testing strategy

Pure tests cover duration weighting, coverage, long gaps, empty history, and
negative-power rejection. Coordinator tests cover quiet-source expiry,
restart restoration, midnight reset, and DST-aware elapsed duration. Entity
tests cover identity, state, attributes, and unavailable behavior.

## Consequences

### Positive

- The statistic works with any supported whole-home power source.
- Duration weighting remains correct for irregular source updates.
- Existing power-only aggregates avoid duplicate history and storage.
- Coverage metadata makes partial observation explicit.

### Trade-offs

- The value may be unavailable for the rest of a day after installation or a
  long outage.
- It describes only the time Electricity Pro observed with sufficient quality.
- Imported-power semantics do not yet support solar export or batteries.
