# ADR-0006: Provider-Independent Daily Power Statistics

## Status

Accepted

## Context

Electricity Pro currently exposes Peak Power Today by mirroring an optional
provider entity. This works for Tibber Pulse but makes the statistic depend on
a provider choosing to publish the same value with compatible semantics.

The integration already has the inputs and architectural layers needed to
calculate the statistic itself:

- the provider normalizes configured instantaneous power to watts;
- the coordinator receives event-driven source updates;
- the statistics engine contains pure state machines with serializable
  snapshots; and
- the coordinator persists statistics through Home Assistant `Store`.

Recommendation intelligence will need more historical information later, but
the first implementation should solve the concrete daily-peak requirement
without creating a general-purpose analytics framework.

## Decision

Add one small, pure daily-peak state machine to `statistics_engine.py`. It will
consume normalized power observations and a timezone-aware local timestamp.
It will not read Home Assistant entities, the clock, Recorder, or storage.

The coordinator will own the state machine, feed it observations, handle local
day rollover, persist its snapshot, and publish its result through the existing
coordinator data model.

### Public outputs

The first implementation will expose:

- **Peak Power Today**, retaining the existing entity key
  `peak_power_today`; and
- **Peak Power Time Today**, using the new entity key
  `peak_power_time_today`.

Peak Power Today becomes a calculated statistic. It no longer requires a
provider-specific daily-peak source.

### Snapshot model

The daily-peak snapshot contains exactly:

- `period_start`: the local calendar date;
- `peak_power_w`: the highest accepted power observation in watts; and
- `peak_time`: the timezone-aware timestamp of that observation.

Values use storage-safe decimal and ISO-8601 representations. Restoration
validates every field and ignores corrupt snapshots with a warning.

### Update rules

For each valid normalized current-power observation:

1. Convert the supplied timestamp to the configured Home Assistant timezone.
2. If its local date differs from `period_start`, start a new snapshot from the
   observation.
3. If the value is greater than the stored peak, replace the peak and time.
4. If it equals the stored peak, retain the earliest observation time.
5. If it is lower, keep the existing snapshot unchanged.

The provider continues to reject unavailable, unknown, malformed, non-finite,
negative, and unsupported-unit values. A missing observation never clears a
valid peak.

### Local-midnight rollover

The coordinator schedules a local-midnight callback in addition to handling
rollover during observations. At midnight it discards the previous day's
snapshot and publishes both sensors as unavailable until the first valid
observation of the new day.

This prevents a stale previous-day peak from remaining visible when a power
source is quiet or unavailable across midnight. Date comparisons use the Home
Assistant timezone and therefore follow local DST transitions.

### Persistence and restart behavior

The daily peak is stored alongside the existing monthly statistics using the
same coordinator-owned `Store`. Storage is scheduled only when the snapshot
changes or is cleared.

On startup:

- a valid snapshot for the current local date is restored before coordinator
  entities publish their first state;
- a snapshot for an earlier date is discarded; and
- absent or invalid state leaves the outputs unavailable until a valid current
  observation arrives.

Recorder history is not scanned to reconstruct an unobserved part of the day.
The statistic is therefore explicitly based on observations made or restored
by Electricity Pro. This avoids startup latency and an implicit dependency on
Recorder retention settings.

### Configuration transition

The provider-specific Peak Power Today selector is removed from setup and
options when the calculated statistic is implemented. A previously stored
selector key may be tolerated but is not used by the calculation. The existing
Electricity Pro Peak Power Today entity ID remains stable.

## Boundaries

This decision does not introduce:

- Average Power Today;
- price, cost, forecast, or Consumption Timing Score calculations;
- long-term base-load estimation;
- automatic device control or recommendations;
- reconstruction from Home Assistant Recorder;
- solar-export or bidirectional-power semantics; or
- a registry or plugin system for arbitrary statistics.

Bidirectional semantics remain tracked by issue #69. Consumption Timing Score
remains tracked by issue #115.

## Testing strategy

The pure state machine receives focused tests for:

- first observation;
- higher, lower, and equal observations;
- deterministic earliest-time tie handling;
- local-date rollover and a DST boundary;
- snapshot serialization and invalid restoration; and
- equivalent watt and kilowatt source normalization at the provider boundary.

Coordinator tests cover startup restoration, midnight clearing, delayed
storage, invalid source updates, and publication of the two output fields.
Sensor tests cover stable Peak Power Today identity, the new timestamp entity,
and unavailable behavior before the first valid daily observation.

## Consequences

### Positive

- Daily peak statistics work with any compatible power source.
- Existing provider and sensor boundaries remain intact.
- The pure state machine is small and independently testable.
- Restart behavior is deterministic without Recorder queries.
- The design provides one proven historical primitive before v1.3 intelligence
  requires broader history.

### Trade-offs

- A new installation cannot claim a peak for the earlier, unobserved part of
  its first day.
- A long outage that outlives delayed storage could miss observations since the
  most recently saved peak.
- The provider-specific selector becomes obsolete and must be removed from the
  configuration UI.

## Follow-up

Implement this ADR under issue #64 before designing the Consumption Timing
Score in issue #115. Average Power Today should only return through a separate
design that defines its time-weighting, coverage, and user value.
