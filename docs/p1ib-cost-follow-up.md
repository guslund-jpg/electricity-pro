# Meter-independent consumption and cost follow-up

Status: implementation review for the 1.5.1 stabilisation candidate. Local cost
estimates, household totals, pricing normalization and monthly source scoping
are implemented. Backward-reading protection was merged in PR #267. Normal
15-minute accumulation and overnight energy continuity have been checked on a
P1IB installation. This is not a release announcement.

A meter with current import power and total imported energy already supports
daily and monthly energy, plus local cost totals when a supplier does not
provide daily accumulated cost.

## Implemented scope

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
Household estimates are covered in [household cost estimates](household-cost-estimates.md).
Backward-reading handling and genuine meter resets are covered in
[meter reading protection](meter-reading-protection.md).

## Remaining follow-ups

- Derive monthly peak-hour consumption and its time from suitable readings.
- Review recovery of already-inflated daily energy and cost totals separately;
  no automatic historical cost reconstruction is currently provided.
- Continue using the [installation verification checklist](installation-verification.md).
  Normal accumulation and overnight continuity have been checked; recovery from
  a naturally occurring dip after the fix has not yet been observed live.
