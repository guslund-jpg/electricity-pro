# ADR-0011: Provider-Independent Market Price Series

## Status

Proposed

## Context

Electricity Pro already normalizes native Nord Pool day-ahead data into ordered
`ForecastInterval` values. The coordinator uses those intervals for cheapest
windows and price direction, but Home Assistant exposes neither the market
price covering the current instant nor the underlying interval series.

Users therefore cannot compare Market Price, Supplier Price, and Effective
Price through stable Electricity Pro entities. The enhanced dashboard also
cannot show the available future price horizon without referring directly to a
provider-specific entity or duplicating source-normalization rules in YAML.

The public contract must preserve three different meanings:

- **Market Price** is unadjusted exchange energy for one delivery interval;
- **Supplier Price** is the configured contracted variable price; and
- **Effective Price** is the live price after applicable configured variable
  components.

A market forecast with partial component scope must not be labelled forecast
Effective Price merely because Electricity Pro can add some known charges.

Home Assistant's sensor guidance recommends separate entities instead of large,
frequently changing attributes because Recorder can otherwise grow quickly.
Its action-response guidance identifies a JSON-serializable object stream as a
good use of response data. The dashboard currently uses ApexCharts Card, which
generates forecast series from an entity attribute rather than an action
response. The contract therefore needs an authoritative automation interface
and a bounded presentation bridge.

## Decision

### Reuse the normalized interval model

`ForecastInterval` remains the provider-independent internal price-series
model. A source adapter must provide:

- timezone-aware `start` and `end` boundaries;
- finite signed `market_price` in currency per kWh;
- non-empty `currency` and price `area`;
- optional timezone-aware `published_at`; and
- explicit pricing metadata.

Negative market prices are valid. Interval duration comes from the boundaries
and is never assumed to be one hour. Source adapters perform provider-specific
unit conversion before returning intervals.

All intervals in one published series must share currency, area, component
scope, VAT treatment, and completeness. They are ordered by start time and
deduplicated by the tuple `(start, end, currency, area)`. Conflicting duplicate
values, overlaps, invalid boundaries, or mixed metadata make the affected
series unavailable rather than silently selecting one value.

### Current Market Price sensor

Introduce one sensor:

- name **Current Market Price**;
- entity key `current_market_price`;
- state equal to the market price for the unique interval where
  `start <= now < end`;
- unit `<currency>/kWh`;
- suggested display precision of two decimals; and
- Measurement state class.

The sensor is available only when exactly one valid interval covers the current
instant. It becomes unavailable for a missing interval, an overlap, stale data,
mixed series metadata, or an unconfigured market-price source. The source area,
interval boundaries, publication timestamp, price components, VAT treatment,
and completeness are transparent metadata.

This entity is separate from the existing Current Price sensor. Current Price
continues to mean the configured live price source and may be a supplier,
market, or externally complete price. Existing entity IDs and semantics remain
unchanged.

### Authoritative forecast response action

Introduce `electricity_pro.get_market_price_forecast` as a response-only Home
Assistant action. It targets one Electricity Pro config entry and returns a
JSON-serializable ordered interval list. Each item contains:

- `start` and `end` as ISO 8601 timestamps with explicit offsets;
- `price` as a finite number in currency per kWh; and
- shared series metadata supplied once at response level: currency, area,
  component scope, VAT treatment, completeness, and publication timestamp.

The response includes the complete bounded series held by the coordinator,
including today's intervals and tomorrow when published. It does not promise
exactly 24 future hours. Before tomorrow's series is available, the horizon may
end at local midnight; afterwards it may extend beyond 24 hours.

The action is the authoritative bulk-data interface for automations and future
frontends. It is registered at integration setup and requires an explicit
config-entry target so multiple Electricity Pro installations remain
unambiguous.

### Bounded dashboard bridge

Until the enhanced dashboard can consume an action response directly, Current
Market Price may expose a `forecast` attribute containing the same ordered,
compact interval items. This attribute is a presentation bridge with strict
limits:

- at most the retained current and next local delivery dates;
- no provider-specific fields;
- no derived supplier or Effective Price values;
- deterministic ordering and serialization; and
- exclusion from Recorder through the entity's unrecorded-attribute contract.

The sensor state and ordinary metadata remain recordable. Excluding only the
forecast payload prevents every interval-sized update from inflating Recorder
while keeping ApexCharts Card able to generate the forward-looking graph.

The bridge is not a replacement for the response action and must not grow into
an unbounded history API.

### Forecast graph behavior

The enhanced Forecast view consumes the normalized `forecast` items. It:

- shows the complete available horizon;
- includes a visible **Now** marker;
- distinguishes today and tomorrow through axis labels or annotations;
- uses local currency per kWh and supports negative prices;
- does not interpolate across missing intervals;
- remains readable on mobile; and
- describes the series as Market Price, not Effective Price.

The existing live price chart may add Current Market Price as a neutral third
line alongside blue Supplier Price and green Effective Price. Documentation
must state that the lines can have different component and VAT scopes.

### Refresh and time behavior

The existing coordinator lifecycle remains responsible for retrieval. It loads
the current delivery date on startup, retries tomorrow after the source's normal
publication period, refreshes on the existing forecast timer, and drops dates
older than the local current date.

The active interval is selected using absolute timezone-aware instants. Local
dates determine retrieval and retention only. A daylight-saving day may contain
23 or 25 hourly intervals, or the corresponding number of sub-hourly intervals;
no fixed interval count is required.

Entity updates occur when the active interval, series content, availability, or
metadata changes. A timer tick with identical content must not manufacture a
new semantic forecast revision.

### Average Market Price Today

The same normalized intervals support #57. Average Market Price Today is the
duration-weighted mean across a complete local delivery day. Its calculation is
separate from this ADR's live sensor and graph, and it must declare unavailable
behavior for incomplete days before implementation.

### Forecast Effective Price

Forecast Effective Price is explicitly deferred. A future design must project
every applicable component with live-equivalent semantics, including supplier
components, energy tax, VAT, time-of-use grid tariffs, seasons, weekends,
holidays, and Workday behavior. Adding one constant to Market Price is not a
general Effective Price forecast.

The market-price graph and response schema must permit a separately named
Effective Price forecast series later without reinterpreting Market Price.

## Testing strategy

Pure tests cover current-interval selection, gaps, overlaps, conflicting
duplicates, negative prices, mixed metadata, ordering, and 23-hour and 25-hour
local days.

Coordinator tests cover startup, day-ahead publication, retries, unchanged
refreshes, date retention, and active-interval transitions. Entity tests cover
identity, unit, state, metadata, availability, and Recorder exclusion of the
forecast payload. Action tests cover explicit config-entry targeting,
JSON-serializable responses, multiple entries, and unloaded entries.

Dashboard tests verify the Now marker, bounded attribute consumption, missing
interval behavior, colors, labels, and mobile-safe configuration.

## Consequences

### Positive

- Market Price gains stable provider-independent semantics.
- Automations receive a structured series without parsing provider entities.
- The dashboard can show the actual available horizon, not a guessed 24 hours.
- Recorder does not persist a repeated bulk forecast payload.
- Existing normalized intervals and refresh behavior are reused.
- #57 and future price sources can build on the same contract.

### Trade-offs

- The first source adapter remains native Nord Pool even though the public
  contract is provider-independent.
- The dashboard bridge duplicates the action response in Home Assistant state
  memory, although it is bounded and excluded from Recorder.
- Market, supplier, and Effective Price lines may not be directly comparable
  when their VAT or component scopes differ.
- Forecast Effective Price remains unavailable until a separate complete
  component-projection design is accepted.

## References

- [Home Assistant sensor entity guidance](https://developers.home-assistant.io/docs/core/entity/sensor/)
- [Home Assistant action response guidance](https://developers.home-assistant.io/docs/dev_101_services/#response-data)
- [ADR-0005: Pricing Sources and Tariff Strategies](0005-pricing-and-tariff-strategies.md)
- [Issue #217](https://github.com/guslund-jpg/electricity-pro/issues/217)
- [Issue #57](https://github.com/guslund-jpg/electricity-pro/issues/57)
