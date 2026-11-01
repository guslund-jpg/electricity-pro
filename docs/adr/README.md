# Architecture decision records

Statuses below describe recorded decision status, not release or hardware
validation status. An accepted design can include unimplemented capabilities.
See [architecture](../development/architecture.md) for current ownership and
[roadmap](../../ROADMAP.md) for release scope.

| Record | Recorded status / interpretation |
| --- | --- |
| [0001: provider normalization](ADR-0001-provider-normalization.md) | Accepted |
| [0005: pricing and tariffs](0005-pricing-and-tariff-strategies.md) | Accepted |
| [0006: daily power statistics](0006-provider-independent-daily-power-statistics.md) | Accepted |
| [0007: timing score](0007-consumption-timing-score.md) | Accepted |
| [0008: base load](0008-base-load-estimation.md) | Accepted |
| [0009: average power](0009-average-power-today.md) | Accepted |
| [0010: signed values](0010-signed-power-and-negative-values.md) | Accepted |
| [0011: market-price series](0011-market-price-series-contract.md) | Proposed status retained; public series implemented, formal acceptance not established by this cleanup |
| [0012: adaptive classification](0012-adaptive-good-price-classification.md) | Accepted |
| [0013: energy flows](0013-production-and-bidirectional-energy-flows.md) | Accepted design; only part implemented, unreleased |

Numbers 0002–0004 were unused placeholders and have been removed; existing
records retain their numbers. Do not infer decisions from numbering gaps. Formal
acceptance or a superseding design should be recorded in a reviewed change,
with implementation and validation limits kept separate.
