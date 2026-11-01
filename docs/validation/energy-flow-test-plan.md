# Energy-flow contract: implementation test and beta plan

Status: current-scope release checklist plus broader design fixtures from
[ADR-0013](../adr/0013-production-and-bidirectional-energy-flows.md).
The checklist below is executable for implemented features; the later balance
fixtures remain future requirements, not tests already run.
No solar or battery hardware is currently available to the maintainer.

## First implementation coverage

The first #240 increment implements independent AC production/export sources
and partial lifetime-counter totals only. Automated coverage is in
`tests/test_energy_flows.py`, `tests/test_flow_options.py` and
`tests/test_flow_sensors.py`: normalization, missing/invalid/stale sources,
zero, dips, restoration, scoped reset, calendar boundaries, source changes,
optional configuration and unchanged import-only entities.

The balance, topology, ratios, source-acquisition timestamps and daily-reset
contracts below describe the broader target, not a completed balance implementation.
See [the current feature limits](../guides/production-export.md).

The subsequent measured-household-demand increment reuses the same isolated
counter contract. `tests/test_household_demand.py` checks separate direct-load
sources, no grid fallback, unchanged import data, opt-in configuration and
scoped reset. Both dashboards' optional groups are tested in
`tests/test_dashboard_energy_flows.py`. A direct source does not imply that
calculated household balances or solar-origin ratios are implemented.

The installation/compatibility increment adds unknown/absent/present
declarations and per-power-source phase conventions. Tests in
`tests/test_flow_compatibility.py` and
`tests/test_flow_compatibility_integration.py` cover optional diagnostics,
independent readings, conflicting declarations, binding changes, boundary/phase
mismatch, five-minute freshness, 30-second skew, future/naive timestamps,
DST elapsed time and stable metadata. Timestamp provenance is HA receipt time;
complete balances, acquisition-time validation and aligned energy periods
remain future requirements.

## v1.6 test-system release checklist

This is the execution plan for [#290](https://github.com/guslund-jpg/electricity-pro/issues/290).
Use the [disposable lab package](../../examples/testing/README.md) and record
results in the [evidence record](v1.6.md). Do not connect synthetic
sources to real accounting, modify real device readings, change the system clock,
or run reset actions against a real meter. Run steps in order; stop on unexplained
differences and retain the failing evidence. A skipped/unavailable test is not a pass.

### A. Installation and existing-user safety

- [ ] **A1 Stable upgrade:** on a backed-up separate test instance with stable
  v1.5.2, capture the import-only/Tibber entities, device IDs, sources and key
  readings. Install the candidate code, restart, and compare. Existing identities,
  source meanings and configured fees must remain unchanged; no unsolicited
  optional sources/entities. Confirm both dashboards still show the same inputs.
  Record absence of real Tibber connectivity as a limitation, not a passed discovery test.
- [ ] **A2 Minimal setup:** on a clean disposable configuration, select only lab
  import power. Missing price, energy and optional sources must not cause errors
  or invent those readings. Then add lab lifetime import energy and, optionally,
  lab price using the declared semantics in the package guide. Record baseline
  import readings and identities before configuring any optional sources.
- [ ] **A3 Options:** save ordinary options, reopen and cancel an optional step.
  Existing saved sources and values must remain unchanged. Exercise a deliberately
  invalid selection (same import source for an optional channel): the form must
  reject it while preserving the draft. Check both standard and Tibber options
  paths where available; never manufacture a Tibber account to claim a pass.

### B. Optional measurements (same local day)

- [ ] **B1 Configure:** bind the six lab optional sensors and confirm meanings.
  Installation-facts review must open automatically, with unknown answers allowed
  and the diagnostic off for a new configuration. Reopening must retain saved
  answers and diagnostic choice; cancelling must not commit pending changes.
  Expect power 1200/200/1800 W for production/export/household. Initial optional
  daily and monthly energy totals are 0 kWh, marked partial. Enable the diagnostic
  with the lab declarations: expect `aligned`, receipt-time provenance and
  `complete_balance_available: false`. Import values must be unchanged.
- [ ] **B2 Increment/units:** set production energy 101000 Wh, export 50.25 kWh,
  household 300.50 kWh, then Publish all. Expect daily and monthly increments
  of 1.000/0.250/0.500 kWh respectively. No production/export revenue or battery
  control should appear. Both example dashboards must show the optional groups;
  copy updated dashboard YAML explicitly, checking entity IDs if renamed.
- [ ] **B3 Dip protection:** heartbeat off; publish production readings 97000,
  100000, 101000, 102000 Wh in that order, waiting after each. Below high-water
  the production energy output is unavailable; recovery to 101000 adds nothing;
  102000 brings its total to 2 kWh, not 6. Export/household totals stay 0.25/0.50.
  Never use a meter-reset action for this dip.
- [ ] **B4 Zero/invalid:** publish production power 0 kW: expect valid 0 W and
  a visible dashboard tile. Publish -1 kW: expect unavailable, not negative
  production or zero. Restore 1.2 kW. For an unsupported-unit check, with heartbeat
  off change **only** `sensor.ep_lab_production_power` in Developer tools → States
  to state 1.2 and attributes `device_class: power`, `unit_of_measurement: VA`.
  Expect unavailable; Publish all restores the template. HA may omit custom
  attributes while an entity is unavailable.
- [ ] **B5 Outage/recovery:** turn production available off and Publish all.
  Both its power/energy outputs become unavailable; export, household and import
  continue independently. Increase production energy to 103000 while unavailable,
  restore availability and publish on the same day: total becomes 3 kWh. Confirm
  unavailable tiles remain visible in both dashboards, not hidden or shown as zero.
- [ ] **B6 Diagnostic:** temporarily use Unknown storage, then a mixed phase
  convention, then restore the lab declarations. Expect `unknown_topology`,
  `incompatible_conventions`, then `aligned`; independent readings remain usable.
  With heartbeat off, Publish all, wait over 30 seconds and publish only production:
  change lab import power by 1 W to trigger evaluation and expect `time_skew`.
  Publish all, then change import power again to evaluate recovery. Do not interpret aligned as verified
  site balance or sensor accuracy.
- [ ] **B7 Staleness:** heartbeat off; Publish all, wait over five minutes,
  then change lab import power (800 → 801 W) to trigger evaluation. Optional power
  becomes unavailable and diagnostic reports `stale_source`; energy remains valid
  until fifteen minutes. After over fifteen minutes, trigger evaluation again:
  optional energy is unavailable too. Publish all to recover without duplicate
  increments. Restore import power to 800 W.
- [ ] **B8 Binding removal:** clear household power in the optional options step;
  do not change household energy. Its power entity must no longer be actively
  supplied; registry/history remnants may remain unavailable. Energy binding and
  totals remain. Rebind the same power source; its phase declaration must return
  to Unknown and require review. Reconfirm before subsequent tests.

### C. Persistence and calendar boundaries

- [ ] **C1 Reload/restart:** capture accepted totals and all entity/device IDs.
  Reload the integration, then restart HA. Do not run Initialize. Publish unchanged
  readings; totals and identities must survive without duplication. Add 1000 Wh
  to production energy and publish: only production increases by 1 kWh.
- [ ] **C2 Restart during dip:** publish a production register below its trusted
  high-water, restart, then recover to the saved high-water and publish. No increment
  is counted twice. Then increase by 1000 Wh and verify exactly +1 kWh. Retain the
  already-counted monthly total through the dip and recovery.
- [ ] **C3 Midnight:** leave heartbeat on with fixed counters across real local
  midnight on the test system. After first fresh new-day report, daily totals are
  0; monthly totals are preserved unless it is a month boundary. Increment each
  meter and verify only new-day increments. Coverage remains partial. For a
  separate outage-over-midnight run, stop heartbeat before midnight, advance a
  meter and publish after midnight: the first new-day reading establishes the
  baseline and the ambiguous cross-day increment is excluded from both totals.
  Month/year/DST automated coverage is not a substitute for recording this run.
- [ ] **C4 Synthetic replacement only:** after recording totals, set production
  register to 1000 Wh and publish. Invoke **Confirm optional energy meter reset**
  for the test entry, channel production, source `sensor.ep_lab_production_energy`,
  with explicit confirmation. Then publish 2000 Wh. Existing totals plus 1 kWh
  are expected, meter generation increases once, and other channels are unchanged.
  Do not invoke this action outside the disposable lab.

### D. Evidence and release decision

- [ ] Record exact code SHA/tag, HA/Core/frontend versions, timezone, test date,
  source mapping, expected/actual readings and pass/fail/not-run for every item.
  Attach redacted screenshots or logs for failures. Do not commit account tokens,
  backups, `.storage`, serial numbers, addresses or raw source histories.
- [ ] Review both dashboards and Home Assistant logs for new errors.
- [ ] Approve a narrow stable-v1.6 scope explicitly: independent optional measured
  channels and compatibility diagnostics only. Until hardware evidence exists,
  mark these opt-in features **experimental / not hardware-verified** in user-facing
  documentation and release notes; do not claim GoodWe support as verified.
- [ ] Keep unsupported balances, battery control/scheduling, attribution ratios
  and export revenue out of the release claims. Hold release if required simulated
  checks fail or remain unperformed without an explicit scope reduction decision.

## Deterministic balance fixtures (future scope)

Values below are W for synchronized live inputs or kWh for complete aligned
periods. Use separate tests for the two quantities; do not convert W into kWh
without an observed duration/integration model.

| Scenario | Inputs | Expected result |
| --- | --- | --- |
| Import-only | I=4, generation/storage absent | H=4 |
| Solar importing | P=3, I=2, X=0, storage absent | H=5, S=3; self-consumption 100%, self-sufficiency 60% |
| Solar exporting | P=5, I=0, X=2, storage absent | H=3, S=3; self-consumption 60%, self-sufficiency 100% |
| Night, no storage | P=0, I=2, X=0 | H=2; self-consumption unavailable, self-sufficiency 0% |
| Zero demand/generation | P=I=X=0, storage absent | H=S=0; both percentages unavailable |
| Solar charging storage | P=5, I=0, X=1, C=2, D=0 | H=2; solar-attribution ratios unavailable |
| Grid charging storage | P=0, I=4, X=0, C=3, D=0 | H=1; no solar-origin inference |
| Storage discharge | P=0, I=0, X=1, C=0, D=3 | H=2; export origin unknown |
| Unknown storage | P=5, I=0, X=2; no C/D | P/I/X available, derived H and ratios unavailable |
| Direct load with unknown storage | H=2 measured, other flows incomplete | H available, balance/attribution unavailable |
| Net only | net=-2 | Existing Current Power=-2; production, directional counters and demand unavailable |
| Contradictory non-storage flow | P=1, I=0, X=2 | Derived H/S unavailable, no clamping |

## Required automated coverage

- W/kW and Wh/kWh conversion, exact decimal arithmetic, unsupported units,
  non-finite values, negative directional inputs and valid zero.
- Topology absent/present/unknown; missing source distinct from declared zero.
- Unknown/mixed AC/DC boundaries, hybrid inverter output including storage,
  phase-gross versus phase-netted meters and duplicate/overlapping sources.
- Authoritative selection, no outage fallback, no circular derivation or
  self-referencing Electricity Pro inputs; diagnostic disagreement handling.
- Freshness and 30-second skew limits immediately below/at/above boundaries,
  out-of-order samples and receipt-only estimated observations.
- Partial periods with different starts or gaps reject ratios even when daily
  labels match. Zero denominators and propagated error-budget limits are tested.
- Lifetime sequence 100, 101, 97, 100, 101, 102 totals 2, not 6. Repeat dips and
  serialize/restore during the dip; test availability gaps and boundary crossing.
- Confirmed replacement 100, 101, confirm new meter=1, 2 adds only 1 after
  confirmation; no historical repair or unrelated-channel reset.
- Daily reset versus same-day dip, delayed old-day frames, explicit source
  period metadata, reset-contract absence and missing final prior-day readings.
- Local midnight, month/year boundaries, leap day, DST spring/fall, restart
  before/after boundaries and source/scale/timezone changes.
- An outage crossing midnight never becomes entirely today's energy. Preserve
  known monthly totals, expose incomplete periods, and do not fabricate history.
- Import-only migrations preserve current entity identities, values and costs.
  Signed export does not become negative import cost or invented export revenue.
- Bounded persisted state and stable attributes; unrelated source updates do
  not create repeated energy deltas or unnecessary Recorder writes.

## Optional beta validation

When a volunteer is ready, collect only consented, redacted examples:

1. Inventory sensor meanings, units, timestamps, counter periods and device
   measurement boundaries. Establish whether inverter generation includes storage.
2. Confirm phase aggregation and which entities represent the same physical meter.
3. Capture near-simultaneous readings during import, solar surplus/export,
   storage charge and storage discharge when these occur naturally.
4. Compare counter increments across short intervals and local midnight; inspect
   daily/monthly coverage and compare aligned totals, not unrelated snapshots.
5. Validate restart restoration without clearing real history or forcing bad
   readings, battery operation, exports or device-control changes.
6. Record supported and unsupported combinations in the compatibility notes.

Do not request credentials, raw backups or full account data. Synthetic fixtures
must contain no personal identifiers. Automated tests establish contract logic;
field checks establish whether actual sources satisfy that contract. Neither
alone establishes billing accuracy or general compatibility with every inverter.
