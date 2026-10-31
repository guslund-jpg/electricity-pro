# Electricity Pro Sensor Catalog

This catalogue describes implemented entities on `main`. The stable release is
[v1.5.2](releases/1.5.2.md); optional flow/compatibility entities below are
**unreleased v1.6 development**, not hardware-validated features.

Keys identify implementation/unique-ID suffixes, not guaranteed entity IDs.
Home Assistant derives IDs from names and retains user renames. For example,
Energy Today retains key `current_energy`; dashboard labels can also differ.

Configured inputs control entity creation, while valid data and sufficient
coverage control availability. “Available” below means implemented, not that
every installation always has a reading. See the focused guides for coverage
attributes and reset rules.

Its purpose is to keep sensor naming, semantics, units, Home Assistant metadata,
and implementation strategy consistent as the integration grows.

## Sensor types

Electricity Pro sensors fall into three categories.

### Mirrored sensors

Mirrored sensors expose a value supplied by an existing Home Assistant entity.

Electricity Pro may validate the value, normalize supported units, and provide
consistent naming and metadata.

Examples:

- Current power
- Current price
- Cost today
- Phase current

### Calculated sensors

Calculated sensors derive a new value from one or more normalized inputs.

Calculations should be provider-independent and implemented as deterministic,
testable functions.

Examples:

- Current cost rate
- Remaining cost today

### Intelligence sensors

Intelligence sensors use statistics, forecasts, tariffs, or consumption
patterns to estimate future outcomes or recommend actions.

Examples:

- Consumption Timing Score Yesterday
- Estimated Base Load
- Cheapest continuous price windows
- Fixed/adaptive Good Time

## Design rules

Each sensor should have:

- a clear and provider-independent meaning;
- a stable entity key;
- an appropriate device class;
- an appropriate state class;
- a documented native unit;
- defined availability behaviour;
- automated tests;
- a clear implementation category.

Provider-specific names should not appear in Electricity Pro entity names.

A provider value should only be mirrored when its semantics are sufficiently
clear and broadly useful.

## Core sensors (stable release line)

| Category | Sensor | Entity key | Type | Unit | Device class | State class | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Live | Current power | `current_power` | Mirrored | W | Power | Measurement | Available |
| Live | Current price | `current_price` | Mirrored | Currency/kWh | None | Measurement | Available |
| Live | Current supplier price | `current_supplier_price` | Calculated | Currency/kWh | None | Measurement | Source dependent |
| Live | Current market price | `current_market_price` | Forecast-derived | Currency/kWh | None | Measurement | Forecast dependent |
| Statistic | Average market price today | `average_market_price_today` | Calculated | Currency/kWh | None | Measurement | Forecast dependent |
| Live | Effective price | `effective_price` | Calculated | Currency/kWh | None | Measurement | Available |
| Live | Current cost rate | `current_cost_rate` | Calculated | Currency/h | None | Measurement | Available |
| Daily | Energy today | `current_energy` | Mirrored or total-accumulated-derived | kWh for derived values; source unit otherwise | Energy | Total increasing | Available |
| Monthly | Energy this month | `energy_this_month` | Calculated | kWh | Energy | Total | Available |
| Daily | Cost today | `cost_today` | External supplier total or local supplier estimate | Currency | Monetary | Total | Source/coverage dependent |
| Daily | Consumption-weighted average price today | `consumption_weighted_average_price_today` | Calculated | Currency/kWh | None | Measurement | Available |
| Monthly | Cost this month | `cost_this_month` | Calculated | Currency | Monetary | Total | Available |
| Daily | Total cost estimate today | `total_cost_today` | Local effective variable cost plus accrued fixed fees | Currency | Monetary | Total | Price/coverage dependent |
| Monthly | Total cost estimate this month | `total_cost_this_month` | Local effective variable cost plus accrued fixed fees | Currency | Monetary | Total | Price/coverage dependent |
| Daily | Remaining cost today | `remaining_cost_today` | Calculated | Currency | None | Measurement | Available |
| Daily | Peak power today | `peak_power_today` | Calculated | W | Power | Measurement | Available |
| Daily | Peak power time today | `peak_power_time_today` | Calculated | Timestamp | Timestamp | None | Available |
| Daily | Average power today | `average_power_today` | Calculated | W | Power | Measurement | Coverage dependent |
| Rolling | Estimated base load | `estimated_base_load` | Calculated | W | Power | Measurement | Available after 5 eligible days |
| Monthly | Monthly peak-hour time | `monthly_peak_hour_time` | Mirrored | Timestamp | Timestamp | None | Available |

The example dashboards label the existing Cost today/Cost this month sensors
as supplier costs. Their primary totals use the separate household estimates;
those include configured variable grid charges, energy tax and accrued fixed
fees. The consumption-weighted effective average excludes fixed fees and uses
matching priced-energy coverage, not necessarily all Energy today.
See [household cost estimates](household-cost-estimates.md).

### Current Power and signed flow

`current_power` represents whole-home net grid exchange in watts. Positive
values mean import from the grid and negative values mean export. The configured
source must measure whole-home net exchange rather than solar generation alone.

Current Cost Rate uses the configured import price only while power is
non-negative; it becomes unavailable during export because Electricity Pro has
no export-compensation source. Peak Power Today remains peak import. Average
Power Today, Estimated Base Load, and Consumption Timing Score reject local days
containing export rather than treating export as household consumption.

Finite negative Current Price and Effective Price values are valid. During
positive import they may produce a negative Current Cost Rate.

### Current Supplier Price

`current_supplier_price` is the VAT-inclusive market energy plus supplier markup,
excluding grid fees, energy tax and fixed fees. It is used for the supplier line
in both example dashboards. For a market-price source, the VAT rate and a markup
(including an explicit zero) must be configured. A supplier price declared to
already include markup uses that component once. VAT-included supplier inputs
are not taxed again.

The sensor remains unavailable if VAT or markup is unknown, or if the source
includes grid fees or energy tax that cannot safely be separated. Complete
household-price sources are not reverse-calculated into supplier prices.
`current_price` continues to expose the original source value for compatibility.
The new supplier sensor starts its own history when installed; it does not
rewrite the old source-price history.

### Current Market Price

`current_market_price` is the unadjusted exchange price for the unique
normalized forecast interval covering the current instant. It is separate from
Current Price, which remains the configured live supplier, market, or complete
price source, and from Effective Price, which includes applicable configured
variable components.

The sensor is created when a native market-price forecast source is configured.
It accepts finite negative prices and exposes the delivery interval, resolution,
currency, price area, publication time, included components, VAT treatment, and
price completeness. It is unavailable when the current interval is missing or
the normalized series is ambiguous because of overlaps, conflicting duplicate
prices, or mixed metadata.

The sensor's bounded `forecast` attribute contains the current and next
retained delivery dates for dashboard presentation. Electricity Pro excludes
that bulk attribute from Recorder while retaining normal Current Market Price
state history. Automations should use the authoritative response-only
`electricity_pro.get_market_price_forecast` action and explicitly select the
Electricity Pro configuration to query.

### Average Market Price Today

`average_market_price_today` is the duration-weighted mean of the raw market
price intervals covering the complete local calendar day. It preserves the
forecast source's currency, price area, component scope, and VAT treatment.
The sensor is unavailable if the normalized series contains any gap or does
not cover local midnight through the following local midnight; a partial day
is never presented as a daily average. This also makes 23-hour and 25-hour
daylight-saving days behave correctly.

This sensor is intended for Home Assistant Recorder and long-term retrospective
statistics of market-price levels. It is **not a recommendation**, does not
describe the household's achieved price, and is not used by Good Time, cheapest
window, price-direction, or other scheduling insights. For recommendations,
use the dedicated forward-looking forecast insights instead.

It differs from Consumption-Weighted Average Price Today: this sensor weights
each market interval by its duration only, whereas the consumption-weighted
sensor reflects when the household actually used electricity and includes its
configured effective-price scope.

### Next inexpensive 1h window

`next_inexpensive_1h_window_start` is an absolute-threshold recommendation. It
is exposed only when the configured live and forecast Effective Prices are
complete and have matching component and VAT semantics. The currently
supported native Nord Pool forecast is market-only and VAT-excluded with partial
component coverage, so this recommendation is not created from that source.

This safety rule does not affect Cheapest 1h, 2h, and 3h Window. Those sensors
rank the available forecast scheduling prices relative to one another and do
not claim that those prices equal the household's complete Effective Price.

On upgrade, an existing unusable Next Inexpensive entity is disabled by the
integration rather than left as a permanently unavailable state. Its registry
identity is retained so Electricity Pro can restore it if a future forecast
source supplies compatible complete pricing.

## Other implemented entities (stable release line)

| Entity key(s) | Meaning and prerequisites | Unit | Device class / state class |
| --- | --- | --- | --- |
| `current_l1`, `current_l2`, `current_l3` | Optional mirrored phase currents; each needs its own source | A | Current / Measurement |
| `voltage_l1`, `voltage_l2`, `voltage_l3` | Optional mirrored phase voltages | V | Voltage / Measurement |
| `monthly_peak_hour_consumption` | Provider's highest hourly energy this month; not instantaneous power | Source energy unit | Energy / Total |
| `fixed_supplier_fee_this_month` | Full configured monthly supplier fee, not accrued fraction | Currency | Monetary / Total |
| `fixed_grid_fee_this_month` | Full configured monthly grid fee, separate from supplier cost | Currency | Monetary / Total |
| `total_supplier_cost_this_month` | Monthly supplier variable cost plus full configured supplier fee; excludes grid | Currency | Monetary / Total |
| `consumption_timing_score_yesterday` | Yesterday's consumption/price timing; coverage rules below | % | None / Measurement |
| `cheapest_1h_window_start`, `cheapest_2h_window_start`, `cheapest_3h_window_start` | Forecast-derived continuous-window starts, with a sufficiently long gap-free horizon | Timestamp | Timestamp / None |
| `cheapest_1h_window_average_effective_price`, `cheapest_2h_window_average_effective_price`, `cheapest_3h_window_average_effective_price` | Average **scheduling price** for each window; historical keys retained, not a complete household Effective Price claim | Currency/kWh | None / None |
| `price_direction` | Two-hour scheduling-price trend: rising/falling/stable (unreleased v1.6 behaviour) | None | None / None |
| `next_inexpensive_1h_window_start` | Complete comparable forecast plus configured threshold required; not exposed for current partial Nord Pool scope | Timestamp | Timestamp / None |
| `good_time_to_use_electricity` | **Binary sensor** created for fixed-threshold or adaptive configuration; incomplete inputs can leave it unknown | On/off | None / Not applicable |

Forecast entities require a configured native Nord Pool entry. Window averages
use the configured VAT rate and applicable per-kWh additions; no fixed fees.
Missing/short/gapped forecasts can make individual insights unavailable.
[Forecast retrieval](forecast-retrieval.md) explains publication and retry timing.

### Price trend — next 2 hours (unreleased v1.6)

The existing `sensor.electricity_pro_price_direction` entity now compares the
duration-weighted average scheduling price from **now to one hour ahead** with
the average from **one to two hours ahead**. Its default entity name remains
Price direction to preserve identity; both example dashboards label it
**Price trend — next 2 hours**. No additional sensor is created.

Partial forecast intervals are clipped at now, the hour split and the end;
weights use elapsed seconds in UTC, including across midnight and DST. Configured
high/low grid-tariff changes split the averages even inside an hourly price interval.
The trend recalculates with cached forecast insights, including the existing
15-minute forecast tick and forecast/tariff refreshes; it does not make extra
forecast requests. The hour-boundary attributes show the last calculation's
anchor, rather than promising a continuously moving, second-by-second result.

Let A be the first hourly average and B the second. `delta = B - A`.
The state is `stable` when `abs(delta) <= 0.02 * max(abs(A), abs(B))`;
otherwise it is `rising` for a positive delta and `falling` for a negative one.
This inclusive 2% tolerance is symmetric and independent of currency scale.
Negative prices are not clamped: -2 to -3 is falling. There is no arbitrary
currency-specific absolute floor; near zero even a small absolute change can
be rising/falling, while two zero averages are stable. This is a tolerance band,
not stateful hysteresis or a guarantee that the classification never changes.

Both hours need contiguous, non-overlapping forecast coverage starting at now,
with matching currency, area and pricing metadata and consistent derived component
scope. Missing coverage, unresolved VAT, non-finite adjustments or a scope change
make the sensor unavailable; it does not jump ahead to a later available window.
Complete **time coverage** does not imply a complete bill: consistently partial
component scope is allowed and remains labelled partial. Prices include VAT and
configured supplier markup, variable grid fees and energy tax, without double
counting components already included. Fixed fees are excluded.

Attributes expose `first_hour_start`, `first_hour_end`, `second_hour_start`,
`second_hour_end`, `first_hour_average_scheduling_price`,
`second_hour_average_scheduling_price`, `delta`, `stable_tolerance`,
`stable_tolerance_percent` (2), `trend_duration_minutes` (120), currency, area
and price scope. Prices, delta and the absolute tolerance are in currency/kWh.
`published_at` is the oldest included publication timestamp, or unknown if any
included timestamp is missing; it is not a guarantee of a fresh upstream fetch.

**Changed meaning:** before v1.6 this entity compared two individual intervals,
with exact equality required for stable. The old `current_interval_*`,
`next_interval_*`, `current_scheduling_price` and `next_scheduling_price`
attributes are replaced by the hourly attributes above. Review personal
automations using this entity or its attributes. Good Time, costs and cheapest
windows do not consume its result and retain their existing behaviour.

## Optional flow entities (unreleased v1.6)

These are independent measured channels, not derived balances or battery controls.
Power sources create power entities; lifetime energy sources independently create
daily/monthly totals. Unconfigured channels create no new entities.

| Entity key(s) | Displayed meaning | Unit | Device class / state class |
| --- | --- | --- | --- |
| `production_power` | AC production excluding battery discharge | W | Power / Measurement |
| `production_today`, `production_this_month` | Observed partial AC production energy | kWh | Energy / Total increasing |
| `grid_export_power` | Directional grid export, possibly including storage discharge | W | Power / Measurement |
| `grid_export_today`, `grid_export_this_month` | Observed partial exported energy; not necessarily solar | kWh | Energy / Total increasing |
| `household_power` | Household demand power, excluding battery charging | W | Power / Measurement |
| `household_today`, `household_this_month` | Household energy for the same non-storage load boundary | kWh | Energy / Total increasing |
| `flow_power_compatibility` | Opt-in diagnostic of configured optional power inputs; not balance readiness | None | None / None |

Flow counters preserve high-water marks across temporary dips and restore
compatible saved totals. They always report partial coverage in this increment;
daily rollover excludes the ambiguous boundary increment. Sources use HA receipt
timestamps, not verified acquisition times. Power is stale after five minutes,
energy after fifteen. See [sources and reset rules](production-export.md).

The compatibility sensor reports declaration/freshness/alignment reasons and
`quality: receipt_time_estimate`; even `aligned` always carries
`complete_balance_available: false`. It neither verifies energy conservation nor
changes existing import costs or analytics. See [diagnostic scope](flow-compatibility.md).

## Daily and monthly statistics

Average Power Today and Average Market Price Today are implemented and listed
in the current sensor catalog above. Monthly peak-hour consumption and time are
currently mirrored from compatible source integrations. Future production,
import and export statistics require separate source contracts; they must not
be inferred from signed net Current Power alone.

### Consumption-weighted average price today

This sensor has two paths:

- Without an external daily supplier-cost source, it divides locally observed
  complete-effective variable cost by the energy covered by those same prices.
  It can be available for a partial day; its denominator is not necessarily
  all Energy Today.
- With an external daily supplier-cost source, it uses Cost Today / Energy Today
  (energy converted to kWh), plus configured variable grid fee and Energy Tax.
  It requires complete daily energy coverage and a positive denominator.
  The external cost and energy must represent the same day and compatible scope.

Fixed fees are excluded. Missing or unsupported inputs make the result
unavailable. See [local estimates](local-cost-estimates.md) and
[household totals](household-cost-estimates.md).

The value is retrospective and is not a recommendation to consume electricity
now. It differs from Average Market Price Today, which would average the day's
market prices without considering when the household used electricity.

Cost Today and Energy Today must cover the same local calendar-day period. On
the first day, the result is only as complete as those source values; no
historical values are reconstructed by Electricity Pro.

Live Effective Price, Current Cost Rate, and Good Time require explicit pricing
metadata. Electricity Pro adds configured supplier markup, variable grid fee,
and Energy Tax only when those components are not already declared as part of
the selected source price. A configured supplier markup also enriches
market-only forecast scheduling prices. An entry with a configured price source
cannot load until its source type, included components, and VAT treatment are
confirmed in integration options.

### Monthly peak-hour consumption

This sensor is relevant for demand-based grid tariffs.

The current implementation mirrors a configured provider sensor; it does not
calculate a demand tariff or billing peak from interval history.

The sensor should represent:

> The largest energy consumption recorded during a single hourly interval in
> the current billing month.

It should not be mislabeled as instantaneous power.

### Energy this month

This sensor accumulates changes from the configured cumulative energy source,
persists its state across Home Assistant restarts, and resets at the start of
the local calendar month. Values are normalized to kWh.

The first reading establishes the baseline. The first month may therefore be
partial when Electricity Pro is installed or the energy source is configured
after the month has started. Later months are not automatically guaranteed
complete: rejected readings, gaps or resets can affect coverage. Inspect
period attributes and the [monthly recovery guide](monthly-energy-recovery.md).

### Cost this month

Without an external daily cost source, this sensor estimates supplier costs from
observed energy deltas and VAT-inclusive supplier prices. It starts with observed
consumption only and reports partial coverage. See
[local cost estimates](local-cost-estimates.md) for daily totals, matching-coverage
effective average prices, and limits on gaps and sparse readings.

With an external daily cost source, the behavior below is unchanged.

This sensor accumulates changes from the configured Cost Today source,
persists its state across Home Assistant restarts, and handles the source's
daily reset. It resets at the start of the local calendar month and preserves
the source currency.

On first setup, the current Cost Today value seeds the monthly total so Cost
This Month includes the whole current day. The first month may still be partial
because costs from earlier days are unavailable. Completeness depends on source
continuity and coverage, not simply reaching the next month.

A future provider-independent implementation may calculate billing peaks from
historical interval data and configurable tariff rules.

## Current insights

### Average Power Today

`average_power_today` is the duration-weighted mean of Current Power during the
observed portion of the current local day. It does not average irregular sensor
updates as if they were equally spaced, and it does not require price, forecast,
or Energy Today data.

The sensor becomes available when Electricity Pro has valid Current Power for
at least 90% of elapsed real time since local midnight and no uncovered gap
exceeds one hour. It resets to unavailable at midnight until a valid interval
has accumulated. Its attributes show the local date, coverage percentage,
covered minutes, and the method `duration_weighted_mean`.

### Estimated Base Load

`estimated_base_load` estimates the home's recent continuous background demand
from Current Power only. It does not require a price provider, Nord Pool, or
Home Assistant Recorder.

Electricity Pro calculates each completed local day's duration-weighted 10th
percentile from 15-minute mean-power buckets. The published value is the median
of at least five eligible days in the latest seven-day window. A day is eligible
when Current Power covered at least 90% of its actual duration, no uncovered gap
exceeded one hour, and no negative power was observed.

The sensor therefore remains unavailable for at least five completed days after
installation. Its attributes show the rolling window, eligible and required day
counts, daily estimates, and the fixed method `median_of_daily_p10`. It describes
observed whole-home demand and does not identify appliances or judge whether the
result is good or bad.

### Consumption Timing Score Yesterday

`consumption_timing_score_yesterday` is a retrospective score from 0 through
100. A high score means more of yesterday's electricity was consumed during
that day's relatively inexpensive Effective Price periods. It is not a
forecast and does not measure total energy efficiency.

The sensor becomes available after a completed local day only when Electricity
Pro observed at least 90% of the day, no data gap exceeded one hour, energy was
consumed, and prices varied enough for timing to be meaningful. Its attributes
include the date, coverage, energy, achieved and time-weighted prices, price
variation, and a plain-language rating. When a completed day fails these
quality rules, the entity is unavailable; Home Assistant does not expose
custom attributes while an entity is unavailable.

### Good time to use electricity

The optional `good_time_to_use_electricity` binary sensor supports two methods:

- **Fixed** preserves the original rule. It is on when Effective Price is at or
  below the configured threshold and off above it.
- **Adaptive** compares the current complete Effective Price with comparable
  historical prices from the same local hour. It first prefers the same
  weekday/weekend class and uses a recency-weighted target percentile. The
  default target is the cheapest 25 percent.

Adaptive history is maintained by Electricity Pro as compact hourly summaries;
it does not depend on Recorder. Only prices with compatible currency,
components, VAT treatment, completeness, and tariff configuration are mixed.
Changing price or tariff configuration restarts the comparable history.

While adaptive history is warming up, the configured fixed threshold is used
as an explicitly reported fallback. Without a fallback, the state is unknown
until sufficient comparable history exists. An optional absolute ceiling can
prevent a relatively favourable but objectively high price from being called
good.

Attributes explain the selected method, reason, thresholds, percentile,
historical cohort and sample counts. Adaptive describes a price as relatively
favourable; it is not financial advice or a recommendation to consume energy.

When a complete forecast has the same currency, components, VAT treatment, and
tariff definition, Adaptive also checks the next six hours. A future interval
suppresses a good-now result only when it qualifies for its own local-hour
cohort and is lower by at least 10 percent of the compatible history's
90th-to-10th-percentile range. A flat historical range, missing forecast, or
the currently supported partial Nord Pool market forecast never suppresses the
result. Attributes expose the comparison status and any materially better
interval.

## Not implemented / future work

Power factor, phase imbalance, projected demand charges, budget forecasts,
whole-day consumption prediction and automatic device control are not current
entities. Neither are calculated household balances, self-consumption or
self-sufficiency ratios, export revenue and battery charge/discharge scheduling.

Daily/monthly measurements and partial accumulated cost estimates must not be
confused with predictions of the rest of the day or a complete future bill.
See the authoritative [roadmap](../ROADMAP.md) and
[energy-flow design](adr/0013-production-and-bidirectional-energy-flows.md).
