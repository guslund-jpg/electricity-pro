# ADR-0013: Production and Bidirectional Energy Flows

## Status

Accepted via PR #270 — design for
[#239](https://github.com/guslund-jpg/electricity-pro/issues/239).
The ADR itself introduced no runtime changes. Implementation is incremental
under #240; see [currently implemented sources and limits](../production-export.md).
Export-price and revenue contracts remain separate work in #241.

## Context

Current Power already means signed whole-home net grid exchange. Energy Today
means imported energy, not total household demand. Solar generation can supply
the home without crossing the grid meter; batteries can charge from the grid
or generation and later supply the home or export. Neither a signed net value
nor the difference between two lifetime net-energy readings identifies all flows.

The first implementation must remain useful to import-only homes, preserve
1.5.1 counter protection, and be testable without solar or battery hardware.

## Decision

### Measurement boundary and channels

Use a declared whole-site AC boundary. Units are W for instantaneous power and
kWh for energy. Each directional channel is non-negative; net grid power alone
is signed. Source adapters convert supported W/kW and Wh/kWh units without
rounding calculation inputs. Unsupported units or unclear directions are invalid.

| Channel | Direction and meaning | Power | Energy |
| --- | --- | --- | --- |
| Grid net | Positive import, negative export across the site grid connection | Signed | Not accepted as directional energy |
| Grid import, I | Grid to site, using the declared meter aggregation convention | Non-negative | Daily or lifetime import register |
| Grid export, X | Site to grid, using the same declared convention | Non-negative | Daily or lifetime export register |
| Local production, P | All declared local generation delivered to the site AC bus, excluding battery discharge | Non-negative | Daily or lifetime generation register |
| Household demand, H | Site non-storage load, including ordinary EV charging and downstream distribution losses | Non-negative | Daily or lifetime load register |
| Battery charge, C | Site AC bus into storage | Non-negative | Daily or lifetime AC charge register |
| Battery discharge, D | Storage into site AC bus | Non-negative | Daily or lifetime AC discharge register |

Storage conversion losses lie inside the storage boundary; AC charge/discharge
already reflect those losses. Do not multiply measured flows by an assumed
efficiency. A DC production counter, battery cell counter, inverter net output
including battery discharge, or a whole-site load sensor including battery
charging is not interchangeable with the channels above.

An adapter may normalize a documented signed battery power source into C/D
only when its boundary, direction and single bidirectional-port semantics are
known. That does not derive directional energy registers from net energy.
Hybrid DC-coupled systems without separable AC generation/storage measurements
can still report valid independent grid or directly measured load channels;
the balance calculations requiring missing channels remain unavailable.

### Source declarations and provenance

Each optional power and energy source has its own immutable binding. Do not
assume an entity that supplies power also supplies an energy counter.

Required normalized metadata:

- channel and quantity (power or energy), canonical and original units;
- opaque source identity, source-binding revision and meter generation;
- measurement boundary and scope (whole site or explicitly disjoint subsystem);
- direction and phase aggregation (net across phases, gross directional sum,
  or unknown); unknown conventions block cross-channel balance calculations;
- origin: measured or derived, with input identities and equation version;
- counter kind for energy: daily-reset or lifetime, plus reset timezone;
- observation timestamp, receipt timestamp and timestamp provenance;
- daily source period identifier when provided, or an explicit adapter/config
  declaration that the source resets at installation-local midnight;
- quality, reason, coverage start/end and whether the coverage is complete.

Adapters retain provider/entity lookup details. Pure calculations consume
normalized values and opaque identities, never branch on provider names.
An adapter must not claim measurement timestamps when it only knows when HA
received an update. Receipt-time sampling is marked as an estimate.

Installation topology declares generation and storage independently as
`absent`, `present` or `unknown`. A missing entity never implies absent equipment.
Only explicit absence permits a structural zero in a balance equation. A
configured source reporting unavailable is not a structural zero.

### Selection, redundancy and double counting

Use one explicitly selected authoritative source per channel and quantity.
Do not silently switch between direct and derived sources during an outage.
Both can be inspected diagnostically, but never added together.

- Preserve signed Current Power as a distinct net-grid measurement. Do not
  clip it to manufacture authoritative import/export channels or counters.
- A compatible explicit directional pair can derive a net diagnostic I - X;
  it does not replace the existing Current Power source automatically.
- Reject one entity bound to contradictory directional roles, own-output
  feedback, and dependency cycles. Signed-port normalization is one declared
  derivation, not two independent measurements of the same source.
- Multiple generators may be aggregated only when their scopes are explicitly
  disjoint and measured on the same boundary. Never sum an inverter total with
  its child PV strings or a site total with its component generators.
- Simultaneous positive I/X is not automatically invalid: phase-gross meters
  can report both. Never mix phase-netted and phase-gross conventions for a
  balance or self-consumption calculation.

No power-to-energy integration or historical net-energy decomposition is part
of this first contract. An energy counter is required for energy analytics.

### Availability and time alignment

States distinguish not configured, unavailable, stale, invalid, contradictory,
partial and complete. Finite zero remains a valid observation. Unavailable
derived values expose a reason and do not disable unrelated measured channels.

For first-version live balances, require every input to be no older than five
minutes and observation timestamps within 30 seconds of each other. These are
conservative initial policy limits, not electrical guarantees. Receipt-time
only inputs can yield an explicitly estimated live balance, not a claim of
simultaneous sampling. Faster/slower source policies require an explicit adapter
declaration and tests; do not silently widen the limits to make data available.

Period arithmetic requires matching start/end, timezone, meter convention,
boundary and complete coverage of that shared period. Do not subtract two
partial daily totals that started at different times, or divide a complete
production total by a partial household total. Scalar totals do not reveal
their overlapping consumption. First-version ratios therefore require complete
aligned local days/months; partial independent energy totals remain useful.

### Equations and minimum inputs

For aligned values on the declared boundary, conservation gives:

```text
P + I + D = H + X + C
H = P + I + D - X - C
```

The same equation applies to energy only for compatible aligned periods.
Do not estimate H by multiplying a momentary power value by a day length.

| Result | Minimum safe sources and conditions |
| --- | --- |
| Production power/energy | Corresponding valid P source; no grid or battery source required |
| Import or export power/energy | Corresponding explicit directional source; no generation required |
| Household demand | Valid directly measured H, or full compatible balance below |
| Import-only derived H | I with generation and storage explicitly absent |
| Generation without storage: H | P + I - X, storage explicitly absent; X may be structural zero only for a declared non-exporting installation |
| Generation with storage: H | P + I + D - X - C, every flow measured or explicitly absent |
| Self-consumed generation, S | P - X over an aligned period, storage absent and all export attributable to declared local generation |
| Self-consumption percentage | 100 × S / P; P must be greater than zero |
| Self-sufficiency percentage | 100 × S / H; H must be greater than zero, with the same non-storage attribution conditions |

If P is zero and H positive, supported non-storage self-sufficiency is zero;
self-consumption percentage is unavailable because its denominator is zero.
For storage homes, even complete C/D totals do not reveal whether discharge
originated from solar or grid charging, or from a previous day. Do not publish
solar self-consumption/self-sufficiency from simple P - X or 1 - I/H formulas.
Explicit energy-origin accounting is deferred. Direct demand, production and
grid-flow totals still work independently when valid.

Reject materially negative derived H/S, X > P in the non-storage attribution
case, or ratios outside 0–100%. Never clip a contradictory result to make it
look plausible. Before implementation, configure a documented measurement-error
budget per input: normalized resolution plus any declared meter accuracy.
Derived arithmetic uses the sum of propagated absolute input error budgets.
Only residuals within that budget may round to zero/bounds, with a quality
flag. If no accuracy budget is known, use zero tolerance rather than inventing
one. Compare redundant direct/balance demand only with aligned observations;
a mismatch preserves direct measurements but withholds dependent derived ratios.

### Counter lifecycle and persistence

Maintain separate bounded state per directional energy source: trusted lifetime
high-water mark, local period, daily/monthly increments, coverage, provenance
revision and explicit meter-generation identifier. Shared helpers should reuse
1.5.1 protection semantics; importing a provider total as one new delta is forbidden.

- Lifetime: first reading establishes a baseline, not consumption. Lower
  readings cannot lower the trusted baseline. Recovery to that baseline adds
  nothing. Above it, count only the genuine increment and flag uncertain coverage.
- Outages/restarts: persist the trusted baseline. Same-period energy catch-up
  can be retained with gap provenance, but its time distribution is unknown.
  Cost intervals remain governed by their separate conservative ledger rules.
- Boundaries: use installation-local calendar days/months and timezone-aware
  timestamps; elapsed durations use UTC, including 23/25-hour DST days. Never
  assign an entire cross-midnight outage delta to the new day. Without an actual
  boundary reading, establish a new-period baseline, preserving the high-water
  rejection guard, and mark coverage partial. Do not infer a midnight reading.
- Native daily: accept a valid current-day provider total as that day's value,
  not a lifetime baseline. A drop within the same declared day is suspect, not
  another reset. Hold the last accepted value and flag the drop. A lower value
  at local midnight is accepted only as a new-day reading under the source's
  declared reset contract; stale prior-day readings are withheld. Daily sources
  without a trustworthy reset/period contract are unsupported for new analytics.
- Monthly aggregation: add accepted daily increments, never repeated snapshots.
  A new daily total cannot make prior-day energy count again. If a daily source
  resets while HA is offline, do not reconstruct the lost prior-day remainder.
- Replacement: require explicit confirmation targeted to a specific channel
  and binding revision, accept its current valid reading, and preserve known
  totals with partial coverage. Do not reset unrelated import/export/generation
  channels. The existing import reset action remains compatible; new channel
  selection must not change the meaning of old calls.
- Changed source, direction, boundary, units/scale, counter kind or timezone:
  invalidate incompatible baselines and dependent derived statistics, start
  partial tracking, and do not merge unlike history under one unchanged meaning.
  Equivalent declared unit conversions must be distinguished from scale changes.

No automatic repair of earlier totals, unbounded sample history, Recorder
backfill or guessing energy from time gaps. Only publish changed values or
meaningful quality/coverage changes; avoid accumulating metadata per update.

### Compatibility and delivery

No new settings are required for existing import-only configurations. Optional
production/storage sections are explicit opt-ins. Unknown topology on migration
does not disable existing import measurements, costs or recommendations.

Preserve Current Power, Energy Today, monthly import energy, unique IDs and
import-cost semantics. Energy Today must not silently become Household Energy
Today. New household-demand entities are additive. Existing export-day exclusions
for average power, base load and timing score remain until a separate reviewed
consumer migration uses compatible gross demand; never change recorded meanings
by substituting H for net power under existing statistics.

Future power sensors use power/measurement semantics; directional energy
outputs must have documented reset and statistics semantics. #240 will finalize
public names, state classes and dashboard layout before implementation. Existing
sensor classes remain unchanged in this design. Export energy can exist without
an export price; no import price is reused to value it. No device control,
battery scheduling, production forecasting or country-specific logic is added.

## Alternatives rejected

- Infer all flows from signed net power: loses production and storage detail.
- Treat missing generation/storage as zero: produces plausible but false demand.
- Use battery balance alone to attribute solar savings: cannot track energy origin.
- Require solar/battery hardware before design: blocks deterministic testing;
  synthetic tests can validate mathematics, not real adapter compatibility.
- Guess genuine lifetime resets from drop size/time: can bill stale recoveries.

## Validation and consequences

The [test and beta plan](../specification/energy-flow-test-plan.md) specifies
normal and invalid combinations, unit conversion, persistence and boundaries.
The current maintainer installation has no solar or battery. Real solar/storage
adapter timing, inverter boundaries and phase conventions remain field-validation
gaps; a prospective beta tester is not a confirmed validation environment.

This design deliberately exposes fewer derived metrics when data is ambiguous.
That costs convenience but preserves the source-independent accuracy contract.
Acceptance confirms the design, not completion of #240 or hardware certification.
