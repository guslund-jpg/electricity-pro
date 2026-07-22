# Architecture

1. Source adapters map provider-specific entities into stable Electricity Pro entities.
2. Core exposes canonical power, price, energy, and cost entities.
3. Statistics, health, and alerts consume only canonical entities.
4. Dashboards consume only canonical entities.

Provider-specific entity IDs must not appear outside `packages/10_sources/`.
