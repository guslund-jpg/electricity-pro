# Roadmap

This document owns upcoming release direction, not release history.
See the [changelog](CHANGELOG.md) for delivered changes and the
[product vision](docs/development/vision.md) and
[design principles](docs/development/design-principles.md) for project boundaries.

The stable release is [v1.6.0](docs/releases/1.6.0.md). Work on `main` is not
automatically released or hardware-validated. Release scope and priorities may
change as testing and source availability improve.

## v1.7.0 — Validation and maintenance (planned)

Prepare the merged validation/type-checking improvements and Enhanced forecast
chart fix for release. Home Assistant Core 2026.9.0 becomes the minimum, allowing
native Probatio validation and removal of obsolete compatibility code. Review
the minimum and test baselines at each release; do not raise them automatically.

See the [draft release notes and readiness checklist](docs/releases/1.7.0.md).
Publication requires the final upgrade smoke test and maintainer approval.
This release does not promise flexible-load recommendations, battery control
or completion of every architecture follow-up in #288.

## Energy-flow follow-up after v1.6 🔭

The [v1.6.0 release notes](docs/releases/1.6.0.md) describe the delivered
measured-channel foundation and its validation limits. Follow-up work builds on
independent AC production/export/household channels, protected partial counters
and opt-in power compatibility diagnostics.

Calculated site balances, self-consumption/self-sufficiency and export revenue
remain future work, not delivered by those independent channels. Solar/battery
hardware validation is still outstanding; track release evidence in
[#290](https://github.com/guslund-jpg/electricity-pro/issues/290) and the
[validation plan](docs/validation/energy-flow-test-plan.md).

### Goal

Extend Electricity Pro from consumption-oriented net-grid analysis to explicit,
provider-independent production, import and export energy flows.

The delivered v1.6 scope is the measured-channel foundation above. Broader
energy-flow work includes separate import/export contracts, self-consumption
and self-sufficiency, explicit export-price/revenue contracts, and use of gross
household demand in suitable analytics. These are follow-up directions, not
promises for a particular release.

The v1.6 foundation must work without solar, a battery or an EV and must not
infer missing flows. Device control and vendor-specific integrations remain out
of scope.

Tracked work: [energy-flow contract #239](https://github.com/guslund-jpg/electricity-pro/issues/239),
[production analytics #240](https://github.com/guslund-jpg/electricity-pro/issues/240),
and [export pricing and revenue #241](https://github.com/guslund-jpg/electricity-pro/issues/241).

---

## Future — Flexible-Load Recommendations 🔭

### Goal

Build advisory, explainable scheduling recommendations for flexible household
loads after price forecasts and energy-flow semantics are reliable.

Candidate capabilities:

- EV charging windows that account for required energy, departure time and
  charging-power constraints;
- heat-pump operating windows that respect comfort boundaries, minimum run
  times and user-defined constraints; and
- reusable load definitions for appliances with duration and energy needs.

Recommendations come before automatic control. Electricity Pro must degrade
safely when a device, forecast or price component is unavailable and must not
assume that a recommended device can be controlled.

Tracked work: [EV charging recommendations #242](https://github.com/guslund-jpg/electricity-pro/issues/242)
and [heat-pump recommendations #243](https://github.com/guslund-jpg/electricity-pro/issues/243).

---

## Future — Storage & Whole-Home Optimisation 🔭

### Goal

Use the production foundation and complete import/export price semantics to
plan storage and coordinate flexible household energy use.

Candidate capabilities:

- battery charge and discharge scheduling using state of charge, usable
  capacity, power limits and round-trip efficiency;
- comparison of self-consumption, export and later grid import;
- coordination with solar forecasts, EV requirements and flexible loads; and
- transparent fallback behaviour when forecasts or device data are incomplete.

Battery scheduling is deliberately later than the production foundation. A
safe schedule cannot be derived from net power and an import price alone.

Tracked work: [battery scheduling and whole-home optimisation #244](https://github.com/guslund-jpg/electricity-pro/issues/244).

---

## Longer-term possibilities

Potential later capabilities include appliance-specific models, richer solar
forecast integration, automatic control behind explicit opt-in safeguards, and
broader whole-home energy intelligence.

---

## Maintenance alongside feature work

Reliability, documentation and compatibility fixes can proceed independently
of new capabilities. Outstanding follow-ups include
[meter-derived monthly peak-hour statistics (#312)](https://github.com/guslund-jpg/electricity-pro/issues/312)
and [recovery policy for inflated historical totals (#313)](https://github.com/guslund-jpg/electricity-pro/issues/313).
Their existence does not imply implementation or a committed release date.

The next release raises the Home Assistant minimum to **2026.9.0** and removes
compatibility code made obsolete by that floor. Review the minimum at every
release without automatically increasing it.

Use the [support and release-review checklist](docs/development/contributing.md#home-assistant-support-and-release-review)
when evaluating release readiness. The completed
[v1.6 release checklist](docs/releases/1.6.0.md) and
[validation evidence](docs/validation/v1.6.md) remain historical records.
