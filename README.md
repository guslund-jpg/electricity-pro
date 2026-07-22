# Electricity Pro

A modular, provider-agnostic electricity monitoring suite for Home Assistant.

This repository starts with engineering foundations only. Production entities are added incrementally after CI and clean-instance testing are in place.

## Rules

- Provider-specific entity IDs exist only in `packages/10_sources/`.
- Dashboards consume canonical `electricity_pro_*` entities.
- `unique_id` values are stable.
- Optional modules never break the core.
- Secrets, `.storage`, logs, and databases are never committed.
