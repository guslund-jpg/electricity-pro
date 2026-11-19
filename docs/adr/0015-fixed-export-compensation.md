# ADR-0015: Fixed-rate export compensation

## Status

Proposed for [#241](https://github.com/guslund-jpg/electricity-pro/issues/241).
The calculation and configuration are covered by synthetic tests. Live validation
of physical energy sources is tracked separately in
[#335](https://github.com/guslund-jpg/electricity-pro/issues/335).

## Design

Use non-negative energy delivered to the grid, measured at the connection
covered by the export agreement. Normalize Wh or kWh to kWh and accept only
increments from the selected directional export register, following the
[energy-flow contract](0013-production-and-bidirectional-energy-flows.md).
The calculation accepts the measured increment and its timestamps. Production,
battery and net-power readings are outside that input contract.

A configured fixed export price is a signed amount in the declared currency
per kWh. Its validity starts when the rate takes effect and ends at the next
price change or known expiry. Multiply a measured increment by the rate only
when the entire measurement interval is covered by one price. An interval
ending exactly at a price change uses the old rate. Compare timestamps as
instants, including during a repeated local hour.

For example, 2 kWh at a price of −0.20 SEK/kWh yields −0.40 SEK. A known zero
price or export increment yields zero. A missing or invalid value, or an
increment spanning a price change, leaves the amount unavailable. A gap between
reads can be priced when the meter delta is trustworthy and one fixed rate
covers the whole interval. Keep full Decimal precision until display.

## Configuration

In the Production and export options, confirm the directional lifetime export
register to open the optional Fixed export price form. Set the signed amount
per kWh, currency, VAT treatment and the components already included in the
amount. The form requires supplier or grid operator compensation. It records
the declaration for the entered price.

Save each price with its meter and UTC validity. Saving equivalent terms
keeps the existing period. A price or declaration change closes the active
period at the save time and starts the next one at that boundary. Disabling the
price or removing or changing its meter closes the period. A different meter
requires an explicit price declaration. Closed periods remain available.

## Observed interval pricing

The coordinator exposes the latest internal `ExportIntervalResult` through
`export_compensation`. `ExportObservation` consumes accepted increments from the
existing directional counter, pairs them with HA report receipt times, and
selects one saved period for the same meter covering the entire interval.
The result includes observed and priced kWh, signed amount, declared price,
currency, VAT treatment, included components and the pricing reason. The amount
uses the declared rate directly and retains Decimal precision.

Repeated reads of a cached report retain the same result and interval start.
A new report with the same meter value can establish a measured zero interval.
Missing, partial or overlapping price coverage leaves the measured increment
unpriced. The counter's accepted energy continues to contribute to its existing
partial totals. A trustworthy same-day increment after a source gap can be
priced when one saved period covers it.

Observation state and interval results are transient. After startup or reload,
pricing waits for a fresh source report as its baseline. A cached pre-start
report cannot price downtime. A source change, confirmed meter reset or local
day boundary also establishes a new pricing baseline. Existing persisted energy
counters retain their recovery and calendar rules. Real acquisition times can
differ from HA receipt times, so source delays remain a validation limitation.

Tests exercise HA source normalization, price boundaries, duplicate reads, source
gaps, local calendar boundaries, the repeated hour, meter reset and restoration.
The integration reload test uses HA's config-entry lifecycle and verifies import
and export energy continuity alongside the new pricing baseline.

## Persistent booking

`ExportLedger` consumes each interval result once and keeps observed kWh and
already-valued amounts for the current and last closed local day and month.
Amounts are grouped by meter, meter generation, currency, VAT declaration and
included components. Rate changes within one group accumulate their original
signed amounts. Other declarations retain separate groups. Price configuration
changes leave existing bookings intact.

Each source/generation has a last processed UTC endpoint. Duplicate, older and
overlapping intervals are rejected, including an attempted later valuation of
an interval already consumed as unpriced. Calendar rollover rejects prior-day
intervals and clears obsolete markers. The ledger retains summaries and replay
markers rather than individual samples. Empty current periods have zero observed
coverage and the retained closed periods carry their actual calendar IDs.

The coordinator checkpoints the ledger's decimal strings, calendar periods and
replay protection alongside the energy counters in the existing atomic storage
file. A new zero-valued report also schedules a write. Reload and orderly
shutdown flush pending state. After restart, booked totals restore together
with their markers, while pricing continues to require a fresh report baseline.
An abrupt power loss can lose updates since the last successful checkpoint,
normally up to one minute with functioning storage. A failed write leaves the
previous checkpoint intact, and a later save retries the current state.

Local calendar periods advance even while the source is silent. Day-boundary
measurement gaps retain the counter's existing partial-coverage rule. Closed
day/month summaries survive a delayed write or restart across the boundary.
UTC ordering handles the repeated local hour. The configured timezone determines
calendar membership. An incompatible timezone or malformed ledger checkpoint
pauses new booking and preserves that checkpoint for recovery. Older snapshots
without a ledger start with empty export booking while retaining energy history.

## Daily and monthly sensors

A configured lifetime export register creates **Export compensation estimate
today** and **Export compensation estimate this month**, translated into Swedish
as **Uppskattad exportersättning i dag** and **Uppskattad exportersättning den här
månaden**. Their default IDs are `sensor.electricity_pro_export_compensation_today`
and `sensor.electricity_pro_export_compensation_this_month`. Unique IDs use the
config-entry ID and fixed period key. Import retains its own sources and totals.

Both sensors are monetary `total` sensors. Their `last_reset` is local midnight
for the day or the first of the month, represented as a UTC instant. The native
amount retains Decimal precision with two suggested display decimals. Energy
attributes display three decimals, while pricing coverage uses unrounded values.
The bounded attributes include period, timezone, source/generation declarations,
VAT treatment, included components, observed/priced/unpriced kWh and history start.
Coverage remains `partial` even when all observed energy is priced. Zero observed
energy has no pricing percentage. A known zero amount is available after a valid
priced interval; missing initial pricing is unavailable.

Publication sums compatible declarations across meter generations and pins each
series' currency. Mixed currency/VAT/component declarations or a changed currency
make the period unavailable. A source gap or disabled price preserves already
booked values with source status and price-enabled attributes. Paused booking
or an invalid publication checkpoint makes the sensor unavailable.

`ExportHistory` checkpoints the current and pending closing snapshots alongside
the ledger. The Store's successful-write notification publishes a closing period
before a later reset and preserves this order across restart. A failed write
keeps the previous published value. New first amounts receive a zero baseline
for Recorder, including a first amount after an entirely unavailable period.
Existing checkpointed bookings at sensor introduction form the start balance:
they remain visible, while Recorder sums begin with subsequent changes. Restored
publication retains its currency and history start. Recorder tests verify first,
negative and zero amounts, precision, delayed rollover and an actual Core restart.

## Follow-up

Supplier-provided export prices with explicit validity and market-based export
prices with declared adjustments require a later design. Verify the physical
export register and settlement basis before claiming agreement with a bill.
