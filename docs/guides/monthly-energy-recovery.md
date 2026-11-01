# Recover incorrect energy and cost totals

## Recovery policy

Correcting a source or installing meter-reading protection prevents some new
errors; it does **not** reconstruct previously inflated energy or costs.
Electricity Pro does not offer automatic historical repair or a blanket reset
of daily energy and cost totals. Preserve the evidence, correct the cause, and
use only the narrowly scoped actions described below. This is the recovery
policy for [#313](https://github.com/guslund-jpg/electricity-pro/issues/313), not
a promise of a future repair action.

## First establish what is wrong

1. Check the same entity in a freshly loaded browser and Developer tools →
   States. An old dashboard display alone does not prove that saved accounting
   is wrong. Compare timestamps, configuration and entity IDs; different
   installations or price scopes are not interchangeable.
2. Record the affected day/month, local timezone, source entity, units and
   daily/lifetime interpretation. Capture source and Electricity Pro readings,
   relevant attributes, and history around the suspected jump. Record the
   installed release or commit and recent configuration changes. Redact
   credentials and personal identifiers before sharing evidence.
3. Compare like-for-like coverage using [costs and pricing](costs-and-pricing.md).
   A partial estimate, accrued fixed fees or different priced-energy coverage
   can explain a difference without an accounting fault.
4. Take a Home Assistant backup that includes configuration, integration saved
   state and any Recorder data you need to retain; verify its contents and keep
   a copy outside the affected installation before a destructive recovery.
5. Correct the source configuration or upstream fault, then verify new meter
   increments and costs. Use the [installation checklist](installation-verification.md).
   Do not introduce deliberate meter dips in a real installation.

### Separate the accounting layers

| Layer | Recovery boundary |
| --- | --- |
| Source readings and external supplier costs | Correct the upstream source. Electricity Pro cannot repair a meter or supplier's records. A configured external daily cost source remains authoritative; removing it is not a repair. |
| Electricity Pro live and saved totals | Existing actions have limited scope. Neither a restart nor an update subtracts previously overcounted consumption. |
| Recorder state history | Previous recorded readings are separate from the integration's current totals. Reset actions do not rewrite or delete them. |
| Long-term statistics | These are separate historical aggregates. Correcting a live value does not establish that these statistics are repaired. Review them separately. |

Do not use Developer tools → Set state, edit `.storage` or the database, remove
and re-add the integration, or change source/price settings solely to force a
reset. These are not supported accounting repairs and can lose evidence or
create misleading history. Source changes can legitimately start a new partial
scope, but cannot recover the old scope's missing or incorrect consumption.

## Discard only incorrect monthly import energy

If **Energy this month** is known to be wrong and you accept losing its entire
current total, use the existing action. It starts a new partial total, not a
corrected month-to-date estimate.

1. Confirm the correct energy source and its daily/lifetime accumulation mode.
2. Wait for a valid Energy today reading.
3. Open **Developer tools → Actions**.
4. Select **Electricity Pro: Reset monthly energy**.
5. Select the affected Electricity Pro configuration, enable the confirmation
   checkbox, and run the action once.

This discards that configuration's current monthly import-energy total and
starts at zero from the current reading. With a healthy source, subsequent
consumption is accumulated normally. The discarded total cannot be restored
through this action; take the backup described above before running it.

Daily energy, cost totals, production/export/household channels, meter readings
and other configurations are not reset.
Recorder history and long-term statistics are not deleted or repaired. Existing
bad historical readings may therefore remain in historical charts.

The monthly sensor exposes a tracking start timestamp and a coverage attribute:
partial for the starting month, tracked for later months, or unverified
for a total restored from an older version without source metadata. Tracked
does not guarantee uninterrupted observations.

Newly saved monthly baselines are associated with the energy entity and its
daily/lifetime interpretation. Changing either starts a fresh partial total
instead of mixing incompatible readings. Older unscoped totals are preserved
and marked unverified; they are not automatically discarded during an upgrade.
Use the action only if your total is incorrect.

## Incorrect daily energy or cost totals

There is no supported action to replace or clear these totals independently.
After correcting the cause, retain the affected period as unreliable and check
new accumulation. Local daily totals start a new period at the next local day;
monthly totals start a new period at the next local month. A day rollover does
not remove bad consumption already included in that month's total. External
source readings follow their provider's rollover, not a local repair policy.

Rollover is **not** a guarantee of recovery: a bad source, incorrect units or an
erroneously high trusted lifetime baseline can still affect subsequent periods.
The trusted baseline survives midnight and restart. If valid readings remain
below it after a faulty upward jump, retain the evidence and request a scoped
investigation; do not declare a fictitious meter replacement to bypass it.
Old Recorder history and statistics remain unchanged at rollover.

Fixed fees and variable costs also have different meanings. Do not subtract the
full configured monthly fee from an accrued total or combine a corrected
external supplier cost with locally priced consumption to compensate for an
error. See [cost components and coverage](costs-and-pricing.md).

## Genuine meter replacement is a different operation

- `electricity_pro.confirm_meter_reset` accepts a new lifetime import baseline
  after a verified meter replacement/reset. It preserves existing energy and
  cost totals; it does not remove overcounting.
- `electricity_pro.confirm_flow_meter_reset` (unreleased v1.6) accepts a new
  lifetime baseline for the explicitly selected production, grid-export or
  household channel and currently configured source. It preserves known totals
  and other channels.

Neither action is appropriate for a temporary dip, outage or incorrect total.
Read [meter reading protection](meter-reading-protection.md) and
[optional channel recovery](production-export.md) before confirming a genuine
replacement. Unobserved consumption is not reconstructed.

## What can be reconstructed from evidence?

Reliable cumulative readings at two known boundaries can establish net energy
between those boundaries, provided units, meter identity and any resets are
known. They do not reveal exactly when that energy was consumed or how to split
it across missing day/month boundaries.

Reconstructing costs additionally requires consumption timing, historical price
intervals, currency, VAT and the applicable supplier/grid/tax settings for each
period. A single current price multiplied by the disputed energy is not a
historical cost correction. Even interval-based reconstruction may be an
estimate when the meter's reporting interval spans changing prices. Missing
evidence must remain unknown, not silently filled or labelled complete.

A prior backup is evidence and a possible disaster-recovery checkpoint, not a
targeted accounting undo. Restoring it can discard valid later configuration,
history and totals; a physical meter does not roll back with the backup. Missing
observations and pricing gaps are not automatically backfilled. Review that
trade-off before restoring an installation.

Any future repair tool needs a separate reviewed implementation: explicit
configuration/channel/period selection, verified evidence, a preview of values
being discarded or replaced, backup guidance and confirmation. Regression
tests must cover restart, rollover, costs, unrelated channels/configurations
and the boundary with Recorder history and statistics. No such tool or database
rewrite is introduced by this policy.
