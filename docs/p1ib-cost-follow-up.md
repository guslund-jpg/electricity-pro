# Meter-independent consumption and cost follow-up

Status: proposed implementation scope following P1IB installation review.

A meter with current import power and total imported energy already supports
daily and monthly energy. It should also support local cost totals when a
supplier does not provide daily accumulated cost.

## Required behavior

- Accumulate consumption against the price applicable to each interval.
- Normalize VAT consistently before combining market price and configured
  supplier markup, grid charges and energy tax. Require an explicit VAT rate
  when conversion is needed; do not infer it from currency.
- Keep supplier-only costs distinguishable from effective variable costs and
  fixed monthly fees, and prevent adding components twice.
- Expose daily and monthly calculated costs and a consumption-weighted price
  with matching energy and cost coverage.
- Identify authoritative supplier totals versus locally calculated estimates.
- Define handling of sparse readings across price boundaries, missing prices,
  source outages, negative prices, midnight, DST, restarts and meter resets.
- Preserve partial-period coverage and avoid claiming historical consumption
  before installation or pricing accuracy during unobserved intervals.
- Associate persisted statistics with their source and accumulation semantics.
  Define a recovery path for totals contaminated by a previous configuration.
- Correct the supplier-price dashboard label or supply an explicitly calculated
  supplier price for market-source configurations.
- Derive monthly peak-hour consumption and its time from suitable readings.
- Keep storage bounded and avoid unnecessary Recorder and persistence writes.

## Configuration improvement in this change

Custom setup groups supplier markup after price type, included components and
VAT. The daily cost selector excludes registered Electricity Pro outputs and
explains that an external daily cost sensor is optional. Other integrations'
monetary sensors still need user verification: monetary units alone cannot
establish that a sensor represents today's variable electricity cost.

Local supplier cost accumulation and matching-coverage effective averages are
now described in [local cost estimates](local-cost-estimates.md). Monthly energy
recovery is covered in [monthly energy recovery](monthly-energy-recovery.md).
Monthly peak-hour derivation and historical cost reconstruction remain follow-ups.
