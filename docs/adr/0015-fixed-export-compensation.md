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

## Follow-up

Report priced kWh and coverage alongside separate export day and month totals.
Keep booked amounts at their original rate and scope persistence to the export
meter and price contract. Follow the export meter's existing local-day baseline
rules.
Import uses its own sources and totals.

Supplier-provided export prices with explicit validity and market-based export
prices with declared adjustments require a later design. Verify the physical
export register and settlement basis before claiming agreement with a bill.
