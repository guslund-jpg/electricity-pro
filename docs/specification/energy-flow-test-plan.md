# Energy-flow contract: implementation test and beta plan

Status: proposed alongside [ADR-0013](../adr/0013-production-and-bidirectional-energy-flows.md).
These are required fixtures for subsequent implementation, not tests already run.
No solar or battery hardware is currently available to the maintainer.

## First implementation coverage

The first #240 increment implements independent AC production/export sources
and partial lifetime-counter totals only. Automated coverage is in
`tests/test_energy_flows.py`, `tests/test_flow_options.py` and
`tests/test_flow_sensors.py`: normalization, missing/invalid/stale sources,
zero, dips, restoration, scoped reset, calendar boundaries, source changes,
optional configuration and unchanged import-only entities.

The balance, topology, ratios, source-acquisition timestamps and daily-reset
contracts below remain future requirements, not completed tests.
See [the current feature limits](../production-export.md).

The subsequent measured-household-demand increment reuses the same isolated
counter contract. `tests/test_household_demand.py` checks separate direct-load
sources, no grid fallback, unchanged import data, opt-in configuration and
scoped reset. Both dashboards' optional groups are tested in
`tests/test_dashboard_energy_flows.py`. A direct source does not imply that
calculated household balances or solar-origin ratios are implemented.

## Deterministic balance fixtures

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
