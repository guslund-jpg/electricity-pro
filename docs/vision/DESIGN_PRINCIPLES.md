# Provider Independence

## Principle

Electricity Pro should consume normalized measurements rather than provider APIs
whenever practical.

## Rationale

Supporting multiple providers should require minimal changes outside the
Provider layer.

## Implications

- Statistics consume normalized measurements.
- Insights consume statistics.
- Sensors never communicate directly with providers.
