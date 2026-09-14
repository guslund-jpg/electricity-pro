# Household cost estimates

The main dashboard totals now use two separate sensors:

- sensor.electricity_pro_total_cost_estimate_today
- sensor.electricity_pro_total_cost_estimate_this_month

They combine observed effective variable costs with accrued fixed supplier
and grid fees, including VAT. Supplier-only cost sensors keep their existing
meaning and remain visible as a breakdown. No existing sensor is renamed.

## Variable costs and coverage

Variable costs use the meter-delta estimates described in
[local cost estimates](local-cost-estimates.md): market energy, supplier markup,
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

## Fixed fees

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

## Breakdown and installation

Each total exposes variable_cost, accrued_fixed_fees, priced_energy_kwh,
missing_components and excluded_charges attributes. All variable costs use the
same currency as the configured normalized price.

Update the integration, verify pricing and fixed fees, and update the example
dashboard YAML. Both examples place household estimates before supplier costs.
The effective average price remains a variable-cost measure, excluding fixed fees.
