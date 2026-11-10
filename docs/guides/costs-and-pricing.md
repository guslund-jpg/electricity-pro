# Costs and pricing

Supplier costs and household estimates have different component and coverage
scopes. Use the sections below to choose the right total; none is a guaranteed bill.

## Supplier cost estimates

When no external daily cost sensor is configured, Electricity Pro can estimate
cost from an import-energy sensor and a configured price source. Both daily
and lifetime energy sensors are supported. No additional helper is required.

### What the sensors mean

- **Cost today** and **Cost this month** estimate variable supplier cost,
  including known supplier markup and VAT, not grid charges or fixed fees.
- **Total supplier cost this month** adds the configured fixed supplier fee once.
- **Consumption-weighted average price today** uses estimated effective cost
  divided by the energy covered by those same prices. It includes configured
  variable grid charges and energy tax. It requires complete effective-price
  components; configure explicit zero for a component that does not apply.

Supplier-only prices must be identifiable. A complete household price cannot
be assumed to be a supplier price. Missing VAT information or missing supplier
markup can therefore prevent supplier cost estimates.

The sensors expose local_estimate as their source, partial coverage, and the
amount of priced energy. Do not treat these values as a replacement for a bill.
Fixed fees are not included in the consumption-weighted average.

### Coverage and timing

Calculation begins with the first observed meter baseline, never the full
lifetime meter value. Each subsequent delta is allocated uniformly over the
observed price intervals between readings. This estimates when energy was used;
the meter does not reveal its exact distribution within an interval.

Intervals are split at local day/month boundaries using actual elapsed time.
Negative prices can reduce costs. Daily-counter rollover is handled separately
from lifetime meters: a backward lifetime reading is rejected, and its recovery
is not billed as new consumption. Genuine meter replacement/reset requires
explicit confirmation. See [meter reading protection](meter-reading-protection.md).

Missing prices leave the corresponding energy unpriced. Meter outages, restart
gaps, and intervals longer than 15 minutes are excluded; the next suitable
reading establishes a fresh baseline. There is no historical backfill. Very
slow-updating meters may therefore provide insufficient cost coverage.

Bounded totals and the trusted lifetime-meter baseline are persisted. Open
pricing intervals are not restored after a
restart. Source, currency, timezone or pricing-configuration changes start new
compatible totals rather than mixing different cost definitions.

If an external daily cost sensor is configured, it remains authoritative.
Electricity Pro does not switch to local estimates during a temporary outage.

### P1IB installation check

1. Select the import energy counter and Total accumulated energy.
2. Configure your price source, VAT and VAT-inclusive supplier markup.
3. Leave Today's accumulated cost sensor empty.
4. Configure grid charges and energy tax for the effective average price.
5. Allow at least two distinct valid energy readings, no more than 15 minutes
   apart, and check Cost today and Cost this month.

The average-price sensor updates on its existing five-minute schedule.
Meter-derived monthly peak-hour consumption/time remains
[separate follow-up work (#312)](https://github.com/guslund-jpg/electricity-pro/issues/312);
the existing monthly peak-hour sensors mirror provider values.
Installing an update does not repair already-inflated energy or cost totals.
Follow the [recovery policy](monthly-energy-recovery.md) for evidence, reset
scope and historical limitations. See the
[installation verification checklist](installation-verification.md) for observed
accumulation, rollover and naturally occurring dip checks.

## Household cost estimates

The main dashboard totals now use two separate sensors:

- sensor.electricity_pro_total_cost_estimate_today
- sensor.electricity_pro_total_cost_estimate_this_month

They combine observed effective variable costs with accrued fixed supplier
and grid fees, including VAT. Supplier-only cost sensors keep their existing
meaning and remain visible as a breakdown. No existing sensor is renamed.

### Variable costs and coverage

Variable costs use the meter-delta estimates described in
[local cost estimates](costs-and-pricing.md#supplier-cost-estimates): market energy, supplier markup,
variable grid charges and energy tax, with VAT applied only once. Effective
pricing must include all those components. Configure explicit zero where a
component does not apply.

Household totals are calculated locally even when an external supplier daily
cost exists. That external total is not added to locally priced consumption:
doing so would double-count supplier charges and mix coverage periods.

Coverage is always labelled partial. It includes only energy with known complete
effective prices; outage and restart gaps are not backfilled. Supplier totals,
energy totals and household estimates may therefore cover different periods.

On upgrade, saved effective costs for the current day can seed a partial monthly
effective total. Earlier monthly supplier totals cannot reconstruct effective
costs and are not reused as if they included grid charges.

### Fixed fees

Enter VAT-inclusive fixed monthly supplier and grid fees. The monthly fee is
divided by the number of local calendar days in that month. Today's share accrues
gradually from midnight, based on elapsed time within the actual local day.
This handles leap years and 23/25-hour daylight-saving days.

The monthly estimate includes fixed fees accrued from the start of the calendar
month, even if variable tracking started later. The dashboard states this
difference. It is not the full future monthly fee.

Example: combined fixed fees of 90 SEK in a 30-day month accrue at 3 SEK per day.
At noon on day 14 of an ordinary day, today's share is 1.50 SEK and the month's
accrued share is 40.50 SEK. These are added to the respective observed variable
costs. The one-minute sensor update schedule limits display writes.

Missing fixed fees are listed in the sensor's missing_components attribute and
dashboard notes; they are not silently confirmed as zero. Explicit zero means
no such fee. Changing a configured monthly fee recalculates its accrued portion.

The totals remain partial estimates of the configured charges.

### Billed demand charges

In Electricity Pro's **Configure** menu, select **Billed demand charge**
(**Fakturerad effektavgift** in Swedish). The entry uses the configured import
energy source as the meter point. Enter the first and last dates printed on
the grid bill, the amount including VAT, and its currency code. Enter zero
when the bill specifies zero. Use the same dates to replace the amount, or
select **Remove** to delete the charge for those dates.

Choose how the existing cost estimate covers that exact charge. For the
current calendar month and the same currency, Electricity Pro adds the charge
when the underlying costs exclude it. If you confirm that the full billed
amount already belongs to that month's estimate, the breakdown shows the
charge and the remainder as separate amounts with the same total. For example,
SEK 1,000 in other costs and a billed SEK 150 make SEK 1,150 in either case.

The latest saved charge for the meter source is shown with its dates when
the estimate cannot include it. This covers an earlier bill, a period across
month boundaries, a different currency, a change to the cost settings or
unknown overlap. A late November bill stays with its November dates in
December. Recheck the overlap setting if you change the prices or fees.
The variable-cost chart and its archive cover priced energy intervals.

### Breakdown and installation

Each total exposes variable_cost, accrued_fixed_fees, priced_energy_kwh,
missing_components and excluded_charges attributes. All variable costs use the
same currency as the configured normalized price.

The monthly dashboard breakdown shows the variable cost of priced energy and
separate fixed supplier and grid fees accrued since the start of the month.
The monthly estimate exposes these two amounts in `accrued_fixed_fee_breakdown`
as `supplier` and `grid`. A missing fee is unavailable and an explicitly
configured zero is shown as an amount. The displayed amounts are rounded
individually. Dashboards paired with an older integration show the combined
fixed fees. The partial estimate reports how many kWh were priced.

The local ledger records VAT-inclusive variable cost components for the same
observed intervals and priced energy as the variable total. A supplier price
that combines market energy and markup stays together, as does an externally
calculated complete price. Separately known rates are recorded when they are
added to the source price.

The monthly estimate populates `variable_cost_breakdown` once priced consumption
has component data. `components`, `covered_cost`, `unallocated_cost` and
`priced_energy_kwh` are decimal strings when known. The nested `priced_energy_kwh`
counts energy with a breakdown. The sensor's existing `priced_energy_kwh`
counts all energy included in the variable total. `started_at` is the first
covered interval, and there may be gaps after it. The dashboard shows both
energy amounts. Earlier priced consumption appears as an unsplit cost, including
a known zero. When no breakdown is available yet, the dashboard shows the
variable total on its own.

The `display` amounts use two decimal places with ties rounded to the nearest
even cent. If the rounded rows differ from the rounded variable total, a signed
rounding line reconciles them. The original amounts remain available at full
precision. The fixed fees still accrue separately from the variable cost.
The monthly card adds a separate signed adjustment when the rounded variable
subtotal and the known fixed fees add up to a different amount than the rounded
household estimate. The card shows the reconciled estimate alongside that
adjustment. A missing fee is still marked unavailable.

The monthly card shows **VAT on specified items** for intervals where
Electricity Pro applied a configured VAT rate to a declared VAT-exclusive
source. It shows that part of the source cost excluding VAT, with any
remaining gross cost on its own row. Earlier costs, VAT-inclusive sources
and separately configured fees stay at their recorded gross amounts.
The applicable VAT is recorded when the interval is priced and saved with
the monthly breakdown. The optional `vat_display` attribute contains the
itemized view, including any display rounding. Both views reconcile to the
same gross subtotal, and the chart continues to show gross variable costs.

Update the integration, verify pricing and fixed fees, and update the example
dashboard YAML. Both examples place household estimates before supplier costs.
The effective average price remains a variable-cost measure, excluding fixed fees.

### Monthly chart data

The integration saves up to twelve local calendar months of variable costs in
its statistics checkpoint. It starts with newly priced intervals. Each record
contains its currency, component amounts, priced kWh, first and last covered
times and an indicator for gaps between covered intervals. The first currency
used in a month identifies that month's record.

A checkpoint written after midnight retains each amount under the local month
where it was booked. When a valid meter interval crosses midnight, the archive
keeps the priced portion on each side. Costs saved before restart remain in their
original month.
A month is fully covered only when priced intervals reach both month boundaries
without gaps. Months without priced intervals have no entry, and a known zero
cost remains available as a zero amount.

The Enhanced dashboard's Trends view shows the archive as stacked columns in
the current cost currency. Combined supplier and variable prices have their own
series, and negative amounts extend below zero. The coverage table below the
chart shows the month, priced kWh and net total. It marks the current month as
to date and incomplete closed months as partial. A missing month has no column.
The chart appears when the archive has an amount in the selected currency,
including a known zero. The history sensor reports the latest archived total.
The chart uses full-precision amounts for its columns. The tooltip and coverage
table use the same two-decimal rounding as the monthly estimate. The tooltip
adds a signed rounding line when all cost items are shown and their displayed
amounts differ from the table total.
