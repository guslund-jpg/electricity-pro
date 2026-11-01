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

Demand charges and other unconfigured charges are excluded and explicitly listed.
These totals are estimates of configured charges, not a complete bill guarantee.

### Breakdown and installation

Each total exposes variable_cost, accrued_fixed_fees, priced_energy_kwh,
missing_components and excluded_charges attributes. All variable costs use the
same currency as the configured normalized price.

Update the integration, verify pricing and fixed fees, and update the example
dashboard YAML. Both examples place household estimates before supplier costs.
The effective average price remains a variable-cost measure, excluding fixed fees.
