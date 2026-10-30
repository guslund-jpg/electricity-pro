# Architecture decision records

Statuses below describe recorded decision status, not release or hardware
validation status. An accepted design can include unimplemented capabilities.
See [architecture](../architecture.md) for current ownership and
[roadmap](../../ROADMAP.md) for release scope.

| Record | Recorded status / interpretation |
| --- | --- |
| [0001: provider normalization](ADR-0001-provider-normalization.md) | Accepted |
| [0002: event-driven coordinator](0002-event-driven-coordinator.md) | Unwritten historical placeholder; current implementation linked |
| [0003: pure analytics](0003-pure-analytics.md) | Unwritten historical placeholder; current implementation linked |
| [0004: insight model](0004-insight-model.md) | Unwritten historical placeholder; later designs linked |
| [0005: pricing and tariffs](0005-pricing-and-tariff-strategies.md) | Accepted |
| [0006: daily power statistics](0006-provider-independent-daily-power-statistics.md) | Accepted |
| [0007: timing score](0007-consumption-timing-score.md) | Accepted |
| [0008: base load](0008-base-load-estimation.md) | Accepted |
| [0009: average power](0009-average-power-today.md) | Accepted |
| [0010: signed values](0010-signed-power-and-negative-values.md) | Accepted |
| [0011: market-price series](0011-market-price-series-contract.md) | Proposed status retained; public series implemented, formal acceptance not established by this cleanup |
| [0012: adaptive classification](0012-adaptive-good-price-classification.md) | Accepted |
| [0013: energy flows](0013-production-and-bidirectional-energy-flows.md) | Accepted design; only part implemented, unreleased |

Do not infer approval dates or decisions from placeholder filenames. Formal
acceptance or a superseding design should be recorded in a reviewed change,
with implementation and validation limits kept separate.
