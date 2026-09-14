# Local cost estimates for meters without supplier cost totals

When no external daily cost sensor is configured, Electricity Pro can estimate
cost from an import-energy sensor and a configured price source. Both daily
and lifetime energy sensors are supported. No additional helper is required.

## What the sensors mean

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

## Coverage and timing

Calculation begins with the first observed meter baseline, never the full
lifetime meter value. Each subsequent delta is allocated uniformly over the
observed price intervals between readings. This estimates when energy was used;
the meter does not reveal its exact distribution within an interval.

Intervals are split at local day/month boundaries using actual elapsed time.
Negative prices can reduce costs. Daily-counter rollover and decreasing lifetime
meters are handled separately.

Missing prices leave the corresponding energy unpriced. Meter outages, restart
gaps, and intervals longer than 15 minutes are excluded; the next suitable
reading establishes a fresh baseline. There is no historical backfill. Very
slow-updating meters may therefore provide insufficient cost coverage.

Only bounded totals are persisted. Open intervals are not restored after a
restart. Source, currency, timezone or pricing-configuration changes start new
compatible totals rather than mixing different cost definitions.

If an external daily cost sensor is configured, it remains authoritative.
Electricity Pro does not switch to local estimates during a temporary outage.

## P1IB installation check

1. Select the import energy counter and Total accumulated energy.
2. Configure your price source, VAT and VAT-inclusive supplier markup.
3. Leave Today's accumulated cost sensor empty.
4. Configure grid charges and energy tax for the effective average price.
5. Allow at least two distinct valid energy readings, no more than 15 minutes
   apart, and check Cost today and Cost this month.

The average-price sensor updates on its existing five-minute schedule.
Monthly peak-hour consumption/time derivation and historical recovery are
separate follow-up work.
