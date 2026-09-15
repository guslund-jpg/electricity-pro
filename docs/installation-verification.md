# Verify a meter installation after an update or restore

Use this checklist for a meter supplying lifetime imported energy, such as P1IB.
It checks observed behaviour, not complete bill accuracy.

## Before testing

- Confirm the installed integration contains the intended changes. Development
  builds can share a version number; a restored backup may contain older code.
- Select the correct import-energy source, its unit and Total accumulated energy.
- Verify price units, VAT treatment, supplier markup, grid charges and fixed fees.
- Leave the optional daily cost source empty unless an external sensor actually
  provides that total. Fixed monthly fees are not daily cost sources.
- Record restart, restore and configuration-change times. Restoring a backup
  may restore older totals; an upgrade does not repair previous overcounting.

## Compare a short interval

Capture the raw meter counter and Electricity Pro dashboard together, then
repeat after approximately 15 minutes without restarting or changing settings.

- Raw meter increase should closely match Energy today and Energy this month
  increases. Allow for display rounding and different screenshot times.
- Divide energy increase by elapsed hours to check average power is plausible.
- Current cost rate should approximately equal import power in kW multiplied
  by the current effective price. It excludes fixed fees.
- Total cost changes also include accrued fixed fees; they need not equal the
  change in supplier cost. Changing prices require interval-based comparison,
  not multiplying all consumption by the latest price.

## Check the next local midnight

- Energy today and daily priced-consumption totals should start a new day.
- Monthly energy should continue, except at a calendar-month boundary.
- Daily fixed fees accrue from the new midnight; monthly fixed fees continue
  from month start. A partial installation does not reconstruct earlier usage.
- To verify the exact daily consumption, compare with the raw meter reading at
  midnight. Yesterday afternoon's counter alone cannot verify today's total.
- Capture the source history and coverage attributes if any total looks wrong.

## If a backward reading occurs naturally

Do not inject bad readings into a live billing/energy setup. Note the event
time and retain the source history. A drop and recovery to the previous counter
must not add energy or cost. Energy resumes above the trusted baseline; local
costs exclude the uncertain interval and can therefore cover less energy.

Do not run Confirm meter reset for an outage or temporary dip. That action is
only for an independently verified meter replacement/reset. See
[meter reading protection](meter-reading-protection.md).

Normal accumulation, midnight rollover, and dip recovery are separate checks.
Passing one does not establish that all three have been observed live.
