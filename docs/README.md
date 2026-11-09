# Documentation

Start with [configuration](guides/configuration.md) after installing Electricity
Pro using the [root README](../README.md#installation).

These documents describe maintained behaviour on `main`.
The [latest published release](https://github.com/guslund-jpg/electricity-pro/releases/latest)
identifies the stable version; `main` can move ahead of that tag. The
[v1.7.2 notes](releases/1.7.2.md) describe the current maintenance scope. Optional energy-flow features remain experimental.
Test evidence is not a claim of real solar/battery hardware validation.

## Setup and troubleshooting

- [Configuration](guides/configuration.md): Tibber fast track, mixed sources,
  source verification and tariff settings.
- [VAT and forecast pricing](guides/vat-pricing.md): regional suggestions,
  explicit overrides and reviewed Tibber additions.
- [Costs and pricing](guides/costs-and-pricing.md): supplier versus household
  totals, coverage, fixed fees and meters without supplier cost sensors.
- [Production, export and household sources](guides/production-export.md):
  optional measured channels and source declarations.
- [Flow compatibility](guides/flow-compatibility.md): installation facts,
  diagnostic states and their limits.
- [Meter reading protection](guides/meter-reading-protection.md): dips,
  outages and confirmed meter resets.
- [Energy and cost recovery](guides/monthly-energy-recovery.md): evidence,
  safe reset scope and limits of historical repair.
- [Installation verification](guides/installation-verification.md): checking
  observed accumulation and rollover.
- [Recorder and database writes](guides/recorder.md): retain the history you
  need without unnecessarily recording duplicate live values.

## Reference

- [Sensor catalogue](reference/sensors.md): entity meanings, calculations,
  availability and update behaviour.
- [Source contract](reference/source-contract.md): units, price scope and
  normalized source semantics.
- [Forecast retrieval](reference/forecast-retrieval.md): upstream contracts,
  refresh timing and retries.

## Examples

Copyable configuration belongs in `examples/`, not in the integration package.

- [Dashboards](../examples/dashboards/README.md)
- [Automation examples](../examples/automations/README.md)
- [Synthetic test system](../examples/testing/README.md)

## Development and decisions

- [Development and tests](development/contributing.md)
- [Current architecture](development/architecture.md)
- [Product vision](development/vision.md) and
  [design principles](development/design-principles.md)
- [Design proposal template](development/design-proposal-template.md)
- [Architecture decision records](adr/README.md)

For substantial proposals, use the template in a reviewed issue or proposal.
Record lasting decisions in an ADR and implemented behaviour in the guides.
Remove superseded delivery checklists rather than maintaining forwarding pages;
Git history preserves previous versions.

## Validation and releases

- [ADR-0014 manual continuity and tariff verification](validation/adr-0014.md)
- [v1.7.2 maintenance update, upgrade notes and validation](releases/1.7.2.md)
- [v1.7.1 release, upgrade notes and validation](releases/1.7.1.md)
- [English/Swedish wording and standard entity-ID review](validation/translation-review-sv.md)
- [Post-v1.7 consolidation: development build and pending manual checks](validation/post-v1.7.md)
- [v1.7.0 release, upgrade notes and validation](releases/1.7.0.md)
- [Home Assistant support and per-release review checklist](development/contributing.md#home-assistant-support-and-release-review)
- [Energy-flow test plan](validation/energy-flow-test-plan.md)
- [v1.6 validation evidence](validation/v1.6.md)
- [v1.6.0 release notes and completed publication checklist](releases/1.6.0.md)
- Released notes: [v1.5.2](releases/1.5.2.md), [v1.5.1](releases/1.5.1.md)
- [Changelog](../CHANGELOG.md): delivered changes
- [Roadmap](../ROADMAP.md): upcoming direction

Guides explain how to use current features; reference documents define their
contracts; development documents explain ownership and contribution practices.
ADRs retain decision rationale and status. Validation records retain what was
actually tested, separately from release approval.
