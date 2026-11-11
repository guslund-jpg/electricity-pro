# Roadmap

This document owns upcoming release direction, not release history.
See the [changelog](CHANGELOG.md) for delivered changes and the
[product vision](docs/development/vision.md) and
[design principles](docs/development/design-principles.md) for project boundaries.

The [latest published release](https://github.com/guslund-jpg/electricity-pro/releases/latest)
identifies the stable version. Work on `main` is not
automatically released or hardware-validated. Release scope and priorities may
change as testing and source availability improve.

## After v1.7.0 — Maintenance direction

The validation/type-checking improvements and Enhanced forecast chart fix shipped
in v1.7.0, with Home Assistant Core 2026.9.0 as the minimum. Review the minimum
and test baselines at each release; do not raise them automatically.

The [v1.7.1 patch](docs/releases/1.7.1.md) preserves the selected Nord Pool
area and improves statistics checkpoints and coverage storage. The consolidation
also included the following work.

- Reviewed the current Core baseline and ran the full test suite on the minimum
  supported version.
- Shared Nord Pool area-resolution logic across standard/Tibber setup and options
  as one behaviour-preserving increment of #288.
- Recorded targeted catalogue-install, HACS-upgrade, Tibber options and
  forecast-chart refresh checks in #118, #335 and #224.

The [targeted validation record](docs/validation/post-v1.7.md) covers the
development build. The [v1.7.1 notes](docs/releases/1.7.1.md) record the
versioned package's Home Assistant smoke test.
The scope does not include flexible-load recommendations, battery
control, new accounting or completion of every architecture follow-up.

## v1.7.2 — Configuration and Swedish-language maintenance

The **1.7.2** maintenance scope groups existing configuration into shared
Custom/Tibber sections and a read-only overview, adds reviewed Swedish
entity/configuration text and
Standard/Enhanced dashboard examples, and uses Spot price consistently in the
English examples. Existing algorithms, accounting and persisted data contracts
remain unchanged. See the [release notes](docs/releases/1.7.2.md).

The configuration work in #373 and entity translation work in #289 are complete.
Real solar and battery hardware evidence is tracked in #335. The Core minimum
remains 2026.9.0 after review.
Versioned-package verification and publication approval are tracked in the
release-preparation PR; the published-release link above distinguishes source
changes from an actual release.

Post-v1.7.2 source maintenance completed the
[ADR-0014 source/result separation](docs/adr/0014-source-readings-and-integration-results.md)
and the follow-up refactors in #395–#399. Providers return normalized inputs,
and the coordinator publishes one grouped input/context/result snapshot for
entities. [Issue #288](https://github.com/guslund-jpg/electricity-pro/issues/288)
is closed. On the configured Core 2026.11.0 instance, the earlier `31d7fa6` run
passed overnight rollover and tariff checks. The combined `c3982e5` run verified
entity, history and forecast continuity across upgrade, reload and restart.
The maintainer skipped separate checks of live Nord Pool publication and
retries, overnight rollover on the combined build, and Adaptive Good Time.
[Manual verification record](docs/validation/adr-0014.md)

Live checks of the dashboard changes on `main` used Home Assistant Core
2026.11.0. The Swedish Enhanced preview confirmed the new tab layout and card
order in Electrical Details. The monthly variable cost legend showed only
components with recorded amounts in both Swedish and English Enhanced.
[Layout verification (#419)](https://github.com/guslund-jpg/electricity-pro/issues/419)
and [legend verification (#165)](https://github.com/guslund-jpg/electricity-pro/issues/165).

To apply these changes to an existing dashboard created from an example, copy
the updated YAML for its language and variant into the dashboard's raw
configuration editor. Carry over any local customizations.
[Dashboard installation guide](examples/dashboards/README.md#quick-installation)

## Energy-flow follow-up after v1.6 🔭

The [v1.6.0 release notes](docs/releases/1.6.0.md) describe the delivered
measured-channel foundation and its validation limits. Follow-up work builds on
independent AC production/export/household channels, protected partial counters
and opt-in power compatibility diagnostics.

Calculated site balances, self-consumption/self-sufficiency and export revenue
remain future work, not delivered by those independent channels. Solar/battery
hardware validation is still outstanding; track release evidence in
[#335](https://github.com/guslund-jpg/electricity-pro/issues/335) and the
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

Historical foundation issues:
[energy-flow contract #239](https://github.com/guslund-jpg/electricity-pro/issues/239)
and [measured production channels #240](https://github.com/guslund-jpg/electricity-pro/issues/240).
They do not establish delivery of the broader analytics above. Open design work
includes [export pricing and revenue #241](https://github.com/guslund-jpg/electricity-pro/issues/241).

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
of new capabilities. [Meter-derived monthly peak-hour statistics (#312)](https://github.com/guslund-jpg/electricity-pro/issues/312)
remain a separately designed feature candidate, with no committed release date.
The [recovery policy (#313)](https://github.com/guslund-jpg/electricity-pro/issues/313)
is complete and documented in the [energy and cost recovery guide](docs/guides/monthly-energy-recovery.md);
it does not add automatic historical repair.

v1.7.0 raised the Home Assistant minimum to **2026.9.0** and removed the obsolete
schema adapter and minimum-test dependency workaround. Review the minimum at
every release without automatically increasing it.

Use the [support and release-review checklist](docs/development/contributing.md#home-assistant-support-and-release-review)
when evaluating release readiness. The completed
[v1.6 release checklist](docs/releases/1.6.0.md) and
[validation evidence](docs/validation/v1.6.md) remain historical records.
