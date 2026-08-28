# ADR-0007: Consumption Timing Score

## Status

Accepted

## Context

Electricity Pro shows current power, Effective Price, cost rate, and forecast
windows. These answer what is happening now and when electricity will be
cheaper, but they do not show whether a household actually shifts consumption
into inexpensive periods.

The Consumption Timing Score should answer:

> Did I use more of my electricity when electricity was relatively inexpensive?

The result must remain meaningful across currencies, price areas, seasons,
suppliers, and supported meter sources. It must also distinguish observed
behavior from forecasts and avoid claiming precision when historical coverage
is incomplete.

## Decision

Introduce one retrospective score for the last completed local calendar day.
The first public entity will be:

- **Consumption Timing Score Yesterday**;
- entity key `consumption_timing_score_yesterday`;
- unit `%`;
- a value from 0 through 100; and
- unavailable when the data-quality contract is not satisfied.

The first version will not publish a live score for the incomplete current
day. A live value changes meaning as future prices and consumption arrive and
could encourage an incorrect decision during the day.

## Scoring model

The score uses matched intervals containing:

- imported household energy `e_i` in kWh;
- duration `d_i`; and
- average Effective Price `p_i` during the interval.

For each interval, calculate its duration-weighted midrank price percentile
`r_i` within the completed local day:

- the cheapest observed price has a rank near 0;
- the most expensive observed price has a rank near 1; and
- tied prices share the midpoint of their combined duration.

The score is:

```text
score = 100 × (1 - Σ(e_i × r_i) / Σ(e_i))
```

Round the public value to the nearest whole number. Retain the unrounded value
internally for deterministic tests and future aggregation.

This model is currency-independent because it ranks prices within the same
local day. Negative prices are valid and naturally rank below higher prices.
Uniform power across a sufficiently variable day produces a score close to 50.

### Worked examples

For four equal-duration price intervals ranked `0.125`, `0.375`, `0.625`, and
`0.875`:

| Scenario | Energy by interval | Result |
| --- | --- | --- |
| Cheap-period use | 4, 0, 0, 0 kWh | 88 |
| Uniform use | 1, 1, 1, 1 kWh | 50 |
| Expensive-period use | 0, 0, 0, 4 kWh | 13 |

The midpoint ranks avoid presenting perfect 0 or 100 scores from a small
number of intervals and handle tied prices deterministically.

## Observation and history contract

The calculation core remains pure. A coordinator-owned accumulator will build
15-minute local buckets from normalized Current Power and Effective Price
observations.

The accumulator will:

1. receive timezone-aware observations whenever either source changes;
2. receive a five-minute coordinator tick so a quiet source does not leave an
   open segment indefinitely;
3. integrate the previous valid power over elapsed time;
4. split segments at bucket, price-change, and local-day boundaries; and
5. store energy, price-duration, and covered duration rather than raw samples.

A power observation is held for at most ten minutes. Time beyond that limit is
marked uncovered until another valid power value arrives. Missing Effective
Price is also uncovered. This prevents an unavailable or stalled source from
being silently projected across hours.

Only the in-progress day and the most recently completed result are persisted
through the coordinator's existing Home Assistant `Store`. Writes occur when
a 15-minute bucket closes, at local midnight, and during integration unload.
Recorder is not queried and raw high-frequency observations are not retained.

## Coverage and availability

The denominator for time coverage is the actual duration of the local day, so
daylight-saving transitions correctly produce 23-hour or 25-hour days.

Publish a score only when all of these conditions hold:

- at least 90% of the local day has matched power and Effective Price data;
- no uncovered gap exceeds 60 minutes;
- total imported energy is greater than zero; and
- the day contains meaningful price variation.

Price variation is meaningful when:

```text
(maximum price - minimum price) / mean absolute price >= 0.02
```

If every price is zero, variation is zero. The dimensionless two-percent rule
avoids a currency-specific threshold and withholds judgment for fixed or
nearly flat contracts.

An unavailable result records one internal reason:

- `insufficient_coverage`;
- `long_data_gap`;
- `no_consumption`; or
- `insufficient_price_variation`.

## Supporting metadata

The entity exposes compact attributes that explain the result:

- `period_start`;
- `coverage_percent`;
- `energy_kwh`;
- `consumption_weighted_price`;
- `time_weighted_price`;
- `price_variation_percent`; and
- `rating`.

The rating is presentation-only:

- 75–100: `well_timed`;
- 40–74: `mixed_timing`; and
- 0–39: `costly_timing`.

The number remains the primary state. Dashboard wording should explain that
the score compares yesterday's consumption with yesterday's relative prices;
it is not a forecast and does not measure total energy efficiency.

## Provider independence

The same calculation works with at least these source combinations:

1. Tibber Pulse Current Power plus Tibber's contracted supplier price, with
   configured grid and energy-tax components forming Effective Price.
2. A compatible non-Tibber whole-home power sensor plus a market-price source,
   with the same normalized pricing and tariff model forming Effective Price.

No provider name, entity naming convention, currency, or national tariff rule
enters the score calculation.

## Boundaries

The first version does not include:

- a live score for the current day;
- weekly or monthly score entities;
- forecast prices or future recommendations;
- appliance identification;
- automatic device control;
- Recorder reconstruction before Electricity Pro began observing;
- exported energy or negative power; or
- a base-load correction.

ADR-0010 later defined signed Current Power while retaining this score's
imported-consumption meaning. A local day containing export is explicitly
unavailable with `unsupported_bidirectional_power`. Base-load estimation in
issue #34 remains a separate explanation.

## Testing strategy

Pure calculation tests cover:

- cheap, uniform, and expensive timing;
- tied and negative prices;
- flat and nearly flat price days;
- zero consumption;
- missing coverage and long gaps;
- 23-hour and 25-hour local days; and
- rounding and rating boundaries.

Accumulator tests cover interval splitting, maximum hold time, price changes,
local midnight, persistence, restart restoration, and unavailable sources.
Entity tests cover state, attributes, stable identity, and unavailable reasons.

## Consequences

### Positive

- The score measures behavior rather than absolute regional price levels.
- A neutral baseline has a clear interpretation near 50.
- Coverage and flat-price rules prevent false precision.
- Bounded aggregate storage avoids Recorder and raw-sample growth.
- The model is independently testable and provider-independent.

### Trade-offs

- The first score appears only after one sufficiently covered day.
- Current Power integration estimates energy and depends on timely source
  observations; it is not a billing-grade meter.
- A daily rank measures timing within that day and cannot compare whether one
  day was absolutely cheaper than another.
- Users with flat contracts receive no score because shifting has no meaningful
  price benefit under the configured Effective Price.

## Follow-up

After this ADR is accepted, implementation should proceed in separate PRs:

1. pure score and bucket-accumulator models with focused tests;
2. coordinator observation, persistence, rollover, and coverage handling; and
3. the Home Assistant entity, dashboard example, and user documentation.

Weekly coaching, forecast-aware savings estimates, and appliance-specific
recommendations require their own designs after the daily score is proven.
