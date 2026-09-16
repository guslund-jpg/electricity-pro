# Optional production, grid export and household demand

Status: unreleased first increment of v1.6 issue #240. These features are not
part of v1.5.1. Validation is automated with synthetic sources; real solar
and battery installations have not yet been beta-tested.

## What this increment provides

You can independently add measured AC production power, directional grid-export
power, non-storage household-demand power, and lifetime energy counters for each
channel. Nothing is inferred
from signed Current Power, and no optional source is required for import-only
homes or Tibber fast-track setup.

| Optional source | Meaning | Accepted units | Resulting sensors |
| --- | --- | --- | --- |
| AC production power | Whole-site generation delivered on the AC side, excluding battery discharge | W, kW | Production power |
| Lifetime AC production energy | Lifetime AC generation register, excluding battery discharge | Wh, kWh | Production today; Production this month |
| Directional grid-export power | Non-negative export to the grid, separate from signed net power | W, kW | Grid export power |
| Lifetime grid-export energy | Lifetime energy delivered to the grid, separate from imported energy | Wh, kWh | Grid export today; Grid export this month |
| Measured household demand power | Whole-site non-storage AC load, including ordinary EV charging and distribution losses, excluding battery charging | W, kW | Household demand power |
| Lifetime household energy | Lifetime register for the same non-storage AC load boundary | Wh, kWh | Household energy today; Household energy this month |

Power is published in W and energy in kWh. A missing or invalid configured
source makes that channel's sensors unavailable, not zero. A valid zero is
displayed as zero. Unconfigured channels do not create new sensors.

These are independent measurements, not a reconciled site balance. Export
may include battery discharge; it is not labelled solar export. Existing
Current Power, import energy, prices and costs keep their existing meanings.
Both example dashboards include optional Production, Grid export and Household demand groups
on Overview, with power and partial daily/monthly energy tiles. Absent or
unknown entities are hidden, while zero and unavailable readings remain
visible. Tap a tile for history and source/coverage attributes.
Copy the updated example YAML to your dashboard to see these cards;
updating the integration alone does not update a manually copied dashboard.

## Configure

1. Open **Settings → Devices & services → Electricity Pro → Configure**.
2. Select **Configure optional production, export and household sources**, then submit.
3. Select only the sources whose meaning you can verify. Leave other fields empty.
4. Confirm the source meanings and submit.

This additional step is available in both custom and Tibber options, but not
inserted into initial fast-track setup. Saving ordinary options preserves
existing optional bindings. To remove a binding, open the optional step and
clear that selection.

Do not select Electricity Pro outputs, the import meter, signed net power,
daily-reset energy, DC measurements, per-phase readings masquerading as
whole-site totals, or hybrid inverter output that mixes generation with battery
discharge. The selectors exclude Electricity Pro entities; saving also checks
device classes, supported units and duplicate/import-source selections.
Software cannot establish physical measurement semantics from an entity name:
the confirmation is your declaration of compatible whole-site AC sources.

### Household demand is not grid import

A direct household-load source may remain useful even when production/storage
topology is unknown, provided its measurement boundary is verified. It measures
the non-storage loads regardless of whether their electricity comes from the
grid, local generation or storage discharge. Battery charging must be excluded;
ordinary EV charging and downstream distribution losses are included.

Do not use a hybrid inverter's vaguely labelled "load" reading until its meaning
is confirmed. It may include battery charging or only a subset of circuits.
Do not select net grid power or the import-energy register for these fields.
No balance is derived from other channels, and no fallback occurs during an
outage. Power and lifetime energy sources are selected independently.

The default new entity IDs are:

- `sensor.electricity_pro_household_demand_power`
- `sensor.electricity_pro_household_energy_today`
- `sensor.electricity_pro_household_energy_this_month`

Daily/monthly household energy follows the partial counter equation and reset
rules below. It does not replace Energy Today or monthly import energy, nor
feed import costs, Average Power, base-load, timing-score or Good Time calculations.
Multiplying all household energy by an import tariff would incorrectly charge
for energy supplied locally; no such calculation is introduced here.

## Coverage and meter protection

Energy totals count only observed, accepted increments after a baseline is
established. They are **always marked partial in this increment**, even after
midnight. There is no historical backfill or guarantee of complete coverage.

For each accepted same-day observation, the increment is
`reading_kWh − previous_high_water_kWh`. Both daily and monthly totals add
that increment; baseline observations add nothing. Calculations use decimals
without input rounding; energy has a suggested display precision of three
decimal places. Power has a suggested display precision of zero decimals.

- A lower lifetime reading does not lower the trusted high-water mark.
  Recovery to the old reading is not counted again.
- Each channel persists its own high-water mark and totals. An outage or reset
  in production, export or household load does not reset another channel or
  import tracking.
- A same-day gap can contribute its unambiguous lifetime increment when the
  source returns; no interval price or energy origin is inferred.
- At a local calendar-day boundary, the first accepted reading received in
  the new day establishes a fresh daily baseline. Energy between the last
  accepted prior-day reading and this baseline is excluded from both totals.
  This avoids assigning an overnight outage entirely to the new day.
- Known monthly increments survive daily rollover. Monthly totals reset at
  the local calendar-month boundary. Restarting with the same source scope
  restores the totals; changing the energy source or timezone starts new tracking.

Power becomes stale after five minutes without a Home Assistant report;
energy after fifteen minutes. Receipt timestamps are used, not guaranteed
meter acquisition timestamps. Delayed frames with plausible high values
cannot be identified reliably without trustworthy source timestamps.
Power is not integrated to fill missing energy, and no automatic fallback
source is chosen.

Entity attributes explain the source, original unit, declared boundary,
measured/derived origin, receipt-time provenance, current reason, period,
partial coverage and meter generation. Tracking state is bounded and does
not store a sample history.

Power entities use Home Assistant's `measurement` state class. The daily/monthly
energy entities use `total_increasing`, with calendar resets. These support
long-term statistics, but Recorder statistics cannot reconstruct excluded gaps
or turn partial values into a full-period total. Do not add the daily and
monthly versions together: they represent overlapping energy periods.
Only meaningful value/metadata changes cause entity state changes; heartbeat
timestamps are not published as changing attributes.

## Genuine meter replacement or reset

Do not use a reset action for temporary dips, outages or stale readings.
Once you have verified a real replacement/reset, open **Developer tools →
Actions → Electricity Pro: Confirm optional energy meter reset**.
Select the configuration, channel and its currently configured energy entity,
then confirm.
Use channel `household` for a verified non-storage load meter replacement.
The action ID remains `electricity_pro.confirm_flow_meter_reset`; existing
production/export calls retain their meaning.

The action requires a fresh valid reading received in the current local day.
It changes only that channel's trusted baseline, increments its meter generation,
and preserves already-counted totals. It does not repair historical data,
delete Recorder history or change other channels.

## Still to come

Optional [installation declarations and power compatibility checks](flow-compatibility.md)
are available as a separate diagnostic step. They do not affect the independent
readings described here and do not establish complete balance readiness.

Calculated household-demand balances, synchronized
balance checks, self-consumption/self-sufficiency ratios, native daily-reset
sources and export-price/revenue accounting are not
provided here. In particular, this increment makes no claim about the origin
of stored or exported energy.

See the [energy-flow design](adr/0013-production-and-bidirectional-energy-flows.md)
and [validation plan](specification/energy-flow-test-plan.md) for the broader
contracts and future test requirements.
