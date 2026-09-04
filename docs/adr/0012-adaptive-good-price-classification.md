# ADR-0012: Adaptive Good-Price Classification

## Status

Proposed

## Date

2026-09-04

## Context

Electricity Pro currently classifies **Good Time to Use Electricity** with a
fixed user-configured Effective Price threshold. The rule is predictable and
useful, but one amount cannot describe a favourable price equally well across
different hours, weekdays, seasons, or market conditions.

An adaptive classification can describe whether the current price is
relatively favourable for a comparable time. It must not silently change the
meaning of existing configurations, call an objectively expensive price
inexpensive, or compare values with different price components or VAT
treatment.

The feature must also remain useful when users exclude price entities from
Recorder to reduce database writes. Electricity Pro therefore cannot depend on
Recorder history. The calculation and its fallback behaviour must be visible
and deterministic.

## Decision

### Preserve two explicit modes

The Good Time configuration will offer two modes:

1. **Fixed threshold** preserves the existing rule: the current Effective
   Price is good when it is at or below the configured threshold.
2. **Adaptive** compares the current Effective Price with compact historical
   observations from comparable local times.

Existing entries remain in Fixed threshold mode without migration or changed
behaviour. Switching to Adaptive is an explicit user choice.

Adaptive mode has these settings:

- a target percentile, defaulting to the cheapest 25 percent;
- the existing fixed threshold as a cold-start fallback when one is present;
  and
- an optional absolute ceiling that can prevent a high price from being
  classified as good.

The first version retains 28 completed local days and applies recency weighting
with a seven-day half-life. This provides four complete weeks of weekday and
weekend observations while allowing current weather and market conditions to
dominate older observations. The six-hour forecast look-ahead is also an
implementation constant rather than an additional configuration field.

### Comparable price contract

The adaptive basis is the normalized Effective Price used by the existing
Good Time calculation. Every stored observation belongs to a compatibility
partition identified by:

- currency and canonical unit;
- included price components;
- VAT treatment;
- price completeness; and
- the configured supplier and grid tariff definition that produced it.

Only complete Effective Price values from the active compatibility partition
are evaluated together. Market-only, supplier-only, partially composed, or
unknown-VAT values are not mixed with a complete Effective Price merely
because their numeric units match.

A pricing or tariff configuration change creates a new partition. Data from
the previous partition is not used for classification. The integration records
when comparable history restarted and why, so a temporary fallback is
explainable.

### Compact historical observations

A coordinator-owned accumulator builds one duration-weighted Effective Price
summary for each elapsed local clock hour. It stores aggregates, not raw state
changes:

- timezone-aware absolute start and end instants;
- local date, local hour, and weekday/weekend class;
- duration-weighted mean Effective Price;
- covered duration; and
- the compatibility-partition identifier.

An hourly summary is eligible only when at least 90 percent of the actual hour
has a valid, compatible Effective Price. Repeated or skipped local hours during
daylight-saving transitions remain distinct through their absolute start and
end instants.

The store retains the current partial hour plus eligible summaries from the
28 most recently completed local dates. It is written when an hour closes, at
local midnight, on integration unload, and after a compatibility reset. Normal
source updates do not cause a persistent write for every price state change.
Recorder is neither queried nor required.

### Historical comparison cohort

The current price is first compared with historical summaries having the same
local hour and the same weekday/weekend class. That preferred cohort is used
when it contains at least eight eligible observations.

If the preferred cohort is too small, the calculation falls back to the same
local hour across all day types when at least 14 eligible observations exist.
It does not broaden the cohort further. This hierarchy accounts for recurring
daily and weekly patterns when the data supports doing so without pretending
that a small sample is reliable.

Each historical summary receives a recency factor calculated as:

```text
recency_weight = 2 ^ (-age_in_days / 7)
```

An observation seven days old therefore has half the influence of a current
observation, one 14 days old has one-quarter, and one 28 days old has
one-sixteenth. Its percentile weight is covered duration multiplied by this
recency factor. Minimum cohort sizes continue to count raw eligible
observations, so weighting cannot make a small cohort appear sufficiently
populated.

The current percentile is its duration-and-recency-weighted empirical
percentile within the selected cohort. Tied prices use the midpoint of their
combined weight. The adaptive threshold is the lowest price whose cumulative
weight reaches the configured target percentile. Negative prices are valid and
sort normally.

The current price is adaptively good when all of these conditions hold:

- a valid cohort is available;
- the current Effective Price is at or below the adaptive threshold;
- the current Effective Price does not exceed an optional absolute ceiling;
  and
- no materially better comparable price is available in the forecast
  look-ahead.

Adaptive means relatively favourable within the selected cohort. It does not
mean affordable, cheap in an absolute sense, or suitable for every household.

### Cold-start behaviour

Before a valid adaptive cohort exists:

- use the configured fixed threshold when one is available;
- otherwise make the recommendation unavailable.

The entity reports `adaptive_fallback` rather than `adaptive` while the fixed
threshold is being used. It exposes the current sample count and required
sample count. The integration never silently evaluates a smaller unsupported
cohort or substitutes today's forecast distribution for historical data.

Using the fixed threshold as a fallback preserves useful behaviour during the
first weeks and after a tariff change while keeping the methodology explicit.

### Absolute ceiling

The optional absolute ceiling is applied after the relative classification.
If the current Effective Price exceeds the ceiling, the result is not good
even when the price falls inside the target historical percentile.

The ceiling uses the same currency-per-kWh unit and complete Effective Price
scope as the classification basis. It is not applied to a partial market-price
forecast.

### Forecast-aware suppression

Forecast awareness is a safety refinement, not a requirement for adaptive
history. It is used only when a future series has complete pricing metadata
compatible with the current and historical Effective Price partition.

Within the next six hours, a future interval suppresses a good-now result only
when:

- its price qualifies under the adaptive threshold for its own local-time
  cohort; and
- it is materially lower than the current price.

Material difference is measured against the compatible historical price
distribution. A future price is materially lower when the reduction is at
least 10 percent of the distribution's 90th-to-10th-percentile range. If that
range is zero or unavailable, forecast suppression is withheld.

This scale-relative rule works with negative prices and different currencies
without embedding a currency-specific amount. The entity exposes the future
interval, price difference, reference range, and suppression reason.

The native Nord Pool series currently represents partial Market Price rather
than complete forecast Effective Price. It therefore does not participate in
this suppression rule. Cheapest-window sensors may continue ranking that
series because relative scheduling does not claim live-equivalent price
completeness.

### Public entity behaviour

The existing Good Time entity and stable identity are retained. Its state
remains a boolean when the selected method has enough valid information and is
unavailable otherwise.

Its attributes explain the evaluation with compact values including:

- `configured_mode`;
- `evaluation_method` (`fixed`, `adaptive`, or `adaptive_fallback`);
- `reason`;
- `current_price`;
- `fixed_threshold` when configured;
- `adaptive_threshold` when available;
- `absolute_ceiling` when configured;
- `target_percentile` and `current_percentile`;
- `cohort_type`, `historical_days`, `sample_count`, and
  `required_sample_count`;
- `history_restarted_at` and `history_restart_reason` when applicable;
- `forecast_look_ahead_hours` and `forecast_comparison_status`; and
- the next materially cheaper interval when one suppresses the result.

The human-readable reason must distinguish at least:

- below or above the fixed threshold;
- within or outside the adaptive target percentile;
- above the absolute ceiling;
- fixed fallback during adaptive warm-up;
- insufficient comparable history;
- incompatible or incomplete current pricing; and
- suppressed because a materially better comparable interval is forecast.

Large historical collections are not exposed as entity attributes.

### Configuration and migration

Existing configurations receive no new required fields and remain fixed. The
options flow allows users to select Adaptive, choose the target percentile, and
optionally add an absolute ceiling. The current fixed threshold remains stored
as the fallback unless the user explicitly removes it.

Returning from Adaptive to Fixed takes effect immediately and leaves the
compact history available for a later return to Adaptive while its
compatibility partition remains valid.

## Testing strategy

Pure calculation tests cover:

- fixed and adaptive classification boundaries;
- duration-and-recency-weighted percentile and quantile behaviour, including
  ties and exact half-life boundaries;
- negative, zero, and flat price distributions;
- preferred and fallback cohort selection;
- minimum sample counts;
- optional ceiling behaviour;
- material forecast differences; and
- incompatible price metadata.

Accumulator and persistence tests cover:

- duration-weighted hourly summaries and 90-percent coverage;
- restart restoration and unload writes;
- bounded retention without Recorder;
- source changes inside an hour;
- local midnight;
- 23-hour and 25-hour days, including repeated local hours;
- corrupt or older store versions; and
- tariff and price-metadata partition changes.

Config-flow and entity tests cover backward compatibility, explicit mode
selection, fallback behaviour, stable entity identity, attributes, translated
reasons, and unavailable states. Forecast tests verify that partial native Nord
Pool data never suppresses an Effective Price recommendation.

## Alternatives considered

### Exact corresponding period last year

Rejected for the first version. One prior observation is weak, requires a year
of retained history, and may have incompatible tariff or tax semantics.

### Recorder-backed history

Rejected. Users may intentionally exclude price entities, Recorder retention
varies, and raw state history would couple classification to database volume.

### Today's forecast percentile during cold start

Rejected. It changes the meaning from historically favourable to favourable
within one incomplete forecast horizon and is unavailable to configurations
without a comparable forecast.

### Seven-day hard history cutoff

Rejected. It follows a short weather regime quickly but provides only five
weekday and two weekend observations for each local hour. A 25th-percentile
threshold would then depend on too few values and could move sharply because
of one unusual day. Four retained weeks with a seven-day half-life preserves
weekly coverage while still emphasizing current conditions.

### One cohort containing every hour

Rejected. It would routinely call daytime or evening prices bad merely because
overnight prices are lower, instead of comparing equivalent opportunities.

### Machine-learning prediction

Rejected. A deterministic empirical method is easier to explain, test, and
operate locally with bounded data.

## Consequences

### Positive

- Existing users retain the fixed rule unchanged.
- Adaptive classification follows daily, weekly, and gradual seasonal price
  changes without provider-specific logic.
- Every decision has an inspectable threshold, cohort, and reason.
- Compact local persistence avoids Recorder dependencies and high-frequency
  database writes.
- Compatibility partitions prevent misleading comparisons after price-scope or
  tariff changes.
- The design handles negative prices and daylight-saving transitions.

### Trade-offs

- A fully time-matched weekend cohort can take roughly four weeks to warm up.
- A tariff change temporarily returns adaptive users to their fixed fallback or
  an unavailable result.
- Twenty-eight recency-weighted days follows current conditions without
  modelling longer seasonal or annual patterns.
- Forecast-aware suppression remains inactive with the current partial native
  Nord Pool forecast.
- Additional configuration and explanatory attributes increase UI and
  translation work.

## References

- [ADR-0005: Pricing Sources and Tariff Strategies](0005-pricing-and-tariff-strategies.md)
- [ADR-0011: Provider-Independent Market Price Series](0011-market-price-series-contract.md)
- [Issue #237](https://github.com/guslund-jpg/electricity-pro/issues/237)
