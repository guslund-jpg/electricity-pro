# Development

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
./scripts/validate.sh
python -m ruff check custom_components tests scripts
python -m ruff format --check custom_components tests scripts
python -m mypy --config-file mypy.ini
python -m pytest -q --tb=short
```

Use Python 3.14 and the dependencies in `requirements-dev.txt`, including the
pinned Home Assistant test harness. Run the full suite before submitting changes;
repository validation alone checks structure, YAML, JSON and syntax, not behaviour.

## Automated checks

The **Python test suite** check runs the complete `tests/` suite on every pull
request, including dependency updates, and on pushes to `main` and `release/**`.
It uses a clean Linux runner and the same development requirements as above.
A test failure, collection error or no collected tests fails the check.
JUnit results are uploaded as `python-test-results` for 14 days, including on test
failure; the job log contains pytest's failure details. An installation failure
can prevent a report from being created but still fails the job.

The **Minimum supported Home Assistant** job also runs the full suite, using
the isolated pin in `requirements-minimum-core.txt`. It asserts the installed Core
version matches `hacs.json` and uploads `minimum-core-test-results` for 14 days.
Both jobs record their Python, Core and test-harness versions. A full development
suite and a full minimum-Core suite remain separate evidence.

Keep **Python test suite** required in the target branch's GitHub protection
settings alongside any existing required checks. The workflow supplies the check;
branch protection controls whether it blocks merging.

Repository quality, HACS, Hassfest and Home Assistant configuration validation
remain separate checks. Configuration validation is not a substitute for the
integration's Python tests. Automated tests also do not replace a smoke test on a
development Home Assistant instance or real solar/battery validation.

For v1.6, use the existing [energy-flow test plan](../validation/energy-flow-test-plan.md#v16-test-system-release-checklist),
[disposable synthetic package](../../examples/testing/README.md) and
[evidence record](../validation/v1.6.md). The package is tested with real HA helpers
and templates in `tests/test_validation_fixture.py`; manual test-system and
hardware results remain separate. Repository YAML checks include
`examples/dashboards/`, `examples/testing/` and `examples/automations/`.
`tests/test_automation_examples.py` executes the
optional one-shot scripts with HA's script engine and simulated timing; it does
not certify appliance hardware. `tests/test_automation_followups.py` exercises
the optional daily notice and humidity simulation with HA automations and helpers.
Manual checks are in the
[automation examples guide](../../examples/automations/README.md#test-before-connecting-a-device).

## Home Assistant support and release review

Electricity Pro v1.7.x and `main` require **Home Assistant 2026.9.0** and Python 3.14.
Released v1.6.0 keeps its original 2025.9.0 minimum. Historical release notes
and validation records describe those releases, not the current development floor.

Review the minimum at **every Electricity Pro release**, including maintenance
releases. This is a review requirement, not an automatic version increase.
Choose the floor based on required Core APIs and dependencies, maintenance cost,
upstream support/security information and the versions we can actually test.
Do not promise indefinite support for older Core versions.

Release checklist:

- [ ] Record the retained or raised minimum and the reason in the release review.
- [ ] Test the exact minimum and review the main test-harness pin against the
  current stable Core release. Record the actual Core/Python versions and results;
  a passing pinned development baseline is not proof of testing current stable.
- [ ] Keep `hacs.json`, `requirements-minimum-core.txt`, CI Python versions,
  `ruff.toml`, the README and release requirements consistent. The minimum-Core
  CI job asserts that installed Core matches the HACS declaration.
- [ ] Audit compatibility adapters, fallback branches and dependency pins.
  Remove only those made obsolete by the new floor, with regression tests.
  Preserve saved-data migrations and user-setting compatibility independently
  of the supported Home Assistant versions.
- [ ] Check upgrade, reload and restart on a test installation: settings, entity
  IDs and accumulated totals must remain intact and readings must continue.
- [ ] Announce a raised floor in the changelog and new release notes, including
  the instruction to upgrade Home Assistant first. Users unable to upgrade can
  remain on the last compatible Electricity Pro release.
- [ ] Retain historical evidence unchanged and obtain release approval before
  publishing. A minimum-version change alone does not validate a release.

Core 2026.9 provides Probatio, so validation imports it directly rather than
using the older Voluptuous name or an action-schema compatibility adapter.
See the [Home Assistant validation-engine announcement](https://contributors.home-assistant.io/blog/2026/09/30/probatio-validation-engine/).

### Baseline review — 5 November 2026

Retain the Core **2026.9.0** minimum: the scoped consolidation work introduces no
API requiring a newer floor. The switch to native Probatio and removal of the
schema adapter shipped in v1.7.0. Older saved settings, storage formats and flow compatibility
are separate contracts; a newer Core floor alone does not justify removing them.

Current stable Core is [2026.11.0](https://github.com/home-assistant/core/releases/tag/2026.11.0).
The latest [published test harness, 0.13.375](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component/releases/tag/0.13.375),
also listed on [PyPI](https://pypi.org/project/pytest-homeassistant-custom-component/),
still targets Core **2026.10.4**. Retain that development pin and the separate
0.13.363 / Core 2026.9.0 minimum pin until a matching current-Core harness is
available and validated. Do not force an incompatible Core override.

Full automated integration coverage on Core 2026.11 remains pending. The stable
HA configuration workflow validates only the minimal YAML fixture; it does not
load an Electricity Pro entry. The maintainer-reported 2026.11 compatibility check
is recorded in the [v1.7.0 notes](../releases/1.7.0.md#candidate-smoke-review--5-november-2026)
and does not establish a full suite on that version. Recheck the harness and
current stable Core during release preparation.

### v1.7.2 review — 7 November 2026

Retain **Core 2026.9.0** and Python 3.14. The maintenance scope reorganizes
existing configuration and display resources; it introduces no API that requires
a higher floor. Native Probatio is already used. The former setup submission
paths and saved-area/settings fallbacks protect existing callers and saved data,
so the supported-Core floor does not make them obsolete. No additional
HA-version adapter removal is justified by this patch.

The latest stable Core was rechecked as
[2026.11.0](https://github.com/home-assistant/core/releases/tag/2026.11.0).
[PyPI](https://pypi.org/project/pytest-homeassistant-custom-component/) still lists
harness **0.13.375** as the latest release, targeting Core **2026.10.4** in its
[package metadata](https://pypi.org/pypi/pytest-homeassistant-custom-component/json).
Keep that development pin and the isolated 0.13.363 / Core 2026.9.0 minimum pin.
The full suites pass 1,801 tests on each baseline with Python 3.14.6.
Full automated integration coverage on 2026.11 remains a separate gap; the
maintainer's 2026.11 UI/runtime checks and the minimal stable-HA YAML workflow
are different evidence. See the [v1.7.2 record](../releases/1.7.2.md).

## Check scope and documentation

`./scripts/validate.sh` checks YAML, JSON, Python syntax, unique IDs and repository
policy. CI additionally runs Markdown lint using the repository's
`.markdownlint.json` settings and Python lint and formatting with the commands above.
The pinned Ruff version is installed from `requirements-dev.txt`; its rules and
Python target are in `ruff.toml`. The local pre-commit hooks run the same full
Python scope. Activate the development environment before committing, and
reinstall requirements after tool-version updates.

### Python lint baseline

The **Repository quality** CI check fails when Ruff reports a violation in
`custom_components/`, `tests/` or `scripts/`. It does not auto-fix files.
The explicit baseline is:

- `E4`: import/statement structure;
- `E7`: statement and comparison mistakes;
- `E9`: runtime/syntax-related errors; and
- `F`: Pyflakes checks, including unused imports/locals and undefined names.

No module-wide or test-wide suppressions are configured. Ruff's normal
generated-directory and Git-ignore handling still applies; the three explicit
source directories are checked in full, not just changed lines. Do not hide
tracked source files behind ignore patterns. Any necessary future suppression
must be narrowly scoped and explain its reason.

Review fixes rather than running unsafe automated fixes. In tests, seemingly
unused imports can register fixtures; preserve intentional side effects.
See [Ruff's rule-selection guidance](https://docs.astral.sh/ruff/linter/#rule-selection).
These checks complement, not replace, pytest.

### Strict type-checking pilot

The **Repository quality** job and local pre-commit hook also run
`python -m mypy --config-file mypy.ini`. The checker is pinned in
`requirements-dev.txt`; use Python 3.14 and run from the repository root.
Do not append file paths to the normal command: the reviewed scope is listed
once in `mypy.ini`.

The current strict scope is:

| Module under `custom_components/electricity_pro/` | Checked contract |
| --- | --- |
| `statistics.py` | Remaining-cost projection and optional Decimal values |
| `pricing.py` | Price/component/VAT enums and immutable metadata |
| `grid_tariff.py` | Grid tariff fields, date/time boundaries and fee selection |
| `adaptive_price.py` | Comparable history, adaptive thresholds and forecast refinement |
| `good_time.py` | Fixed/adaptive decisions over normalized inputs and explicit time |
| `settings.py` | Saved-data/options overlay with explicit clearing and no normalization |
| `base_load.py` | Duration-weighted power, base-load estimates and bounded power history |
| `timing_score.py` | Consumption-timing scores, completed-day result ownership, matched intervals and bounded timing history |
| `statistics_engine.py` | Cumulative counters, calendar periods and persisted snapshots |
| `history_storage.py` | Runtime narrowing of stored history values |
| `flow_compatibility.py` | Normalized power observations and the supported diagnostic result statuses |
| `energy_flows.py` | Directional lifetime counters and their persisted state |
| `flow_sources.py` | Explicit source bindings, normalized readings and freshness checks |
| `cost_ledger.py` | Observed cost allocation, currency resets and validated persisted totals |
| `nordpool.py` | Native action response validation, interval normalization and delivery dates |
| `forecast.py` | Forecast interval validation, complete-day averages and serialization |
| `calculations.py` | Supplier/effective pricing, VAT conversion and cost arithmetic |
| `forecast_insights.py` | Continuous price windows and duration-weighted two-hour trend |
| `coordinator.py` | Explicit provider inputs, field-specific result updates, flow metadata and persisted flow scope |
| `__init__.py` | Integration lifecycle and action dispatch to the selected loaded coordinator |
| `binary_sensor.py` | Good Time entity state, explanatory attributes and numeric settings |
| `device.py` | Fresh, entry-scoped Home Assistant device metadata |
| `sensor.py` | Sensor registration, phase readers, availability and entity attributes |
| `provider.py` | Optional source states, unit normalization and configured adjustments |
| `data.py` | Immutable source/context/result contracts and the grouped published snapshot |
| `source_adapters.py` | Registry metadata, per-home Tibber discovery and capability mappings |
| `const.py` | Shared integration constants and defaults |
| `household_cost.py` | Calendar-based fixed-fee accrual and missing-fee metadata |
| `markup_estimate.py` | Matched Tibber/Nord Pool intervals and validated price responses |
| `pricing_config.py` | Saved price semantics and VAT normalization |
| `vat_suggestions.py` | Confirmed VAT assistance shared by setup and options flows |
| `workday.py` | Public Workday action responses and non-working dates |
| `config_flow.py` | Setup/options steps, typed selectors and confirmed forecast estimate navigation |
| `measurement_config.py` | Shared measurement selection, source validation and energy-period confirmation |
| `market_config.py` | Shared native Nord Pool selection, area resolution and inherited metadata display |
| `supplier_config.py` | Shared supplier declarations, fees, explicit clears and VAT/estimate navigation |
| `grid_config.py` | Shared grid tariff selection, clearable charges and schedule validation |
| `production_config.py` | Shared optional-source selection, draft installation review and scoped clears |
| `insight_config.py` | Shared Good Time method review, applicable controls and scoped numeric validation |
| `review_config.py` | Read-only setup/options overview and pricing-contract coverage |

The calculation modules form a pure dependency graph: `good_time.py` uses
`adaptive_price.py`, which uses `pricing.py`. `flow_sources.py` also uses Home
Assistant's typed state API; `nordpool.py` uses its service API and datetime
parser, plus the forecast interval model. `calculations.py` uses Home Assistant's
energy-unit constants. The coordinator and integration setup use Home Assistant's
entry, lifecycle and service APIs. Sensors, the Good Time entity and device metadata helper
use Home Assistant's entity and device APIs. The provider uses typed Home Assistant
states; source discovery accepts a registry-field protocol. The remaining checked modules depend
only on the standard library and each other. Mypy follows
imports normally and does not ignore missing imports or errors. Strict mode,
`disallow_any_unimported` and unused-configuration warnings are enabled; the
checked scope runs without an incremental cache. The extracted Good Time result
uses an explicit attribute-value union; calculation behaviour is unchanged.

The three history/statistics modules accept stored records as
`Mapping[str, object]`. Shared readers check string, decimal, array and record
shapes before the owning model validates dates, finiteness, ranges and consistency.
The base-load history writer has an explicit `TypedDict` result. Storage format
and calculations are unchanged; malformed collection shapes are now rejected
explicitly. Runtime validation and JSON round-trip tests remain necessary:
annotations alone do not validate stored data. Strict mode does not prohibit
explicit `Any` elsewhere in the checked scope.

The Nord Pool boundary builds a validated list of interval mappings before
normalization, then narrows timestamps and numeric prices at runtime. Boolean
prices and invalid inferred area names are rejected explicitly. Valid negative
prices, MWh-to-kWh conversion, configured area/currency selection and native
service errors retain their existing behaviour.

The forecast-insight result limits price direction to `rising`, `falling` or
`stable` with a `Literal` union. The two-hour boundaries, duration weighting,
inclusive symmetric 2% tolerance, missing-coverage handling and window selection
are unchanged. Existing forecast and calculation tests verify runtime behaviour;
the explicit CI scope protects these contracts on future changes.

The flow-compatibility result uses a `Literal` union of supported diagnostic
statuses, so misspelled or newly introduced statuses require an explicit contract
update. Input declarations remain strings: unknown or invalid declarations must
still reach the existing runtime validation. The coordinator's diagnostic payload
also has an explicit `TypedDict`, with a required status and optional explanatory
fields. Its sensor caller is checked without changing availability or calculations.

Directional energy counters also read `Mapping[str, object]` and write an explicit
`TypedDict`. Shared string/decimal readers narrow stored values before existing
period, total, timestamp and reset-generation validation. The eight-field storage
format, accepted numeric scalars, accumulation, rollover and reset behaviour are
unchanged. Tests cover JSON round trips, malformed shapes and missing fields.

The flow-source reader accepts `Mapping[str, object]`, narrowing entity bindings
and unit metadata to strings. Non-string bindings are treated as unconfigured;
non-string units cannot produce measured readings. Compatibility declarations
remain unmodified for the diagnostic's runtime validation. Valid bindings,
unit conversion, receipt-time provenance, and the 300-second power / 900-second
energy freshness limits are unchanged. Tests cover all three channels, malformed
inputs, availability and exact freshness boundaries.

Integration setup now joins the checked scope; there are no `follow_imports = skip`
overrides. Action handlers narrow `runtime_data` to the coordinator after checking
the entry's domain and loaded state. Setup owns that runtime-data assignment.
Action schemas use Probatio directly, provided by Core 2026.9 and newer.
No cross-version schema adapter or separately pinned runtime validator is needed.
Tests exercise the entry guards and schema validation on supported Core versions.
Explicit namespace-package bases keep module names consistent with repository
imports.
See [mypy import handling](https://mypy.readthedocs.io/en/stable/running_mypy.html).

Coordinator result replacements use a field-specific `TypedDict`. Tests check
its exact 30-field match to `IntegrationResults` and independently recorded
pre-migration field types, retaining the ten narrower Decimal update annotations
without losing optional snapshot values. `ElectricityProData` holds explicit
readings/context/results groups; action overlays replace nested results only.
The old 51-field publication fixtures remain unchanged as test-only comparison
oracles, with explicit paths into the grouped model. Production has no flat view,
dynamic field forwarding or compatibility re-export. Flow metadata
and persisted scope are typed without changing saved formats. Compatibility
declarations remain untrusted objects until runtime validation, including
non-string and unhashable values. Public forecast action responses have explicit
`TypedDict` contracts, including their interval rows. A JSON round-trip test and
an exact payload assertion protect their existing wire format. One documented
cast bridges the nested typed lists to Home Assistant's generic `ServiceResponse`;
it is not used to validate untrusted input.

Settings merging preserves the input value type. Pricing metadata accepts
`object` values and validates strings before constructing enums; malformed values
return no metadata. Coordinator source, scope and entity-attribute mappings use
`object` where their values are intentionally heterogeneous.

Sensor registration explicitly accepts the different sensor subclasses. Phase
readers use named snapshot fields rather than dynamic attribute lookup, with
availability bound to the same reader. Tests exercise all six phases independently,
including zero, unavailable readings and recovery. Entity attribute dictionaries
use `object` values rather than `Any`; this does not validate their runtime contents.

Provider normalization explicitly checks missing states before reading attributes.
Unit metadata enters as `object` and is narrowed where strings are required;
malformed units cannot become measured readings. Tests cover missing states,
non-string units and discovery entries with missing or unrelated registry metadata.
Valid unit conversions, pricing and per-home discovery behaviour are unchanged.

Supporting helpers retain explicit `Any` for heterogeneous Home Assistant form
and settings dictionaries. The VAT helper shares Home Assistant's base flow
contract, types its navigation state and results, and uses one documented cast
for dispatch back to a named setup/options step. Existing flow tests cover both
paths, confirmation, manual escape and preservation of saved rates. Tibber price
rows enter as objects and must be mappings before their fields are validated.

The main configuration flow is also checked. Selector choices and form fields
use Home Assistant's selector types; estimate steps share its base flow contract.
Missing pending estimate settings return to forecast pricing, while missing
Tibber sources are rejected without requesting an estimate. Registry fields are
read-only protocol properties, matching their use during discovery.
Heterogeneous framework form/settings dictionaries deliberately retain explicit
`Any`; individual values are narrowed where needed.

The remaining explicit `Any` boundaries are deliberate limits of this scope:

- Home Assistant form/settings dictionaries contain heterogeneous framework
  selectors and submitted values. Runtime validation still owns input checking.
- The coordinator's `Store` payload and `_statistics_data` aggregate optional
  snapshots from several persistence schemas, including older saved formats.
  Component restore routines retain their runtime checks; the aggregate is not
  asserted to be a fully validated typed object.
- Adaptive price history serialization/restoration retains dynamic dictionaries
  for its nested persisted scope and observations. Its restore checks and tests,
  rather than these annotations, guard malformed saved data.

These exceptions do not establish that every persisted value is validated. A
complete typed persistence schema would be separate work. Strict checking covers
the 40 explicitly listed integration modules, not the tests or whole integration;
it is not a claim of complete typing or additional manual Home Assistant testing.

### Python formatting

The **Repository quality** job and local pre-commit hook check formatting across
`custom_components/`, `tests/` and `scripts/` using the pinned Ruff formatter.
The policy in `ruff.toml` uses 88 columns, double quotes, spaces and LF endings.
Its Python 3.14 syntax target matches the minimum supported Home Assistant
environment and the main development environment.
Both checks are read-only: they report formatting differences without changing files.

To apply formatting locally, run:

```bash
python -m ruff format custom_components tests scripts
```

Review the resulting diff and run the full tests. Keep broad mechanical formatting
changes separate from calculation or other behaviour changes. The formatter uses
the same normal generated-directory and Git-ignore handling as the lint check.

### Further typing

The bounded formatting and incremental typing work was completed in
[#287](https://github.com/guslund-jpg/electricity-pro/issues/287).
The agreed module list includes the main configuration flow. The boundary review
and remaining exceptions are documented above. Its completion included formatting,
lint, strict typing, repository validation and behavioural tests on both pinned
Home Assistant environments. This does not establish that every framework-supplied
`Any` was eliminated or that the entire test suite is strictly typed. Further
persistence schema work and unrelated refactoring should be tracked separately.

### Documentation and fixture checks

For documentation-only changes, check relative links and headings, run repository
validation and require the normal CI checks. Update the architecture and sensor
catalogue whenever module ownership or entity semantics change.

The HA configuration workflow validates the minimal `config/` fixture directly.
It does not install example packages or exercise the Python integration's config
flow or runtime. Those behaviours belong to pytest and development-instance tests.
The repository policy check rejects provider-specific entity references in the
maintained `examples/dashboards/`; dashboard templates also have dedicated tests.

## Development instance

Deploy only to a separate development Home Assistant instance. Before every restart:

```bash
ha core check
```

## Defining a capability

Before implementation, document its purpose, inputs, outputs, calculation,
edge cases, architectural ownership, required tests and documentation impact.
Use the [design proposal template](design-proposal-template.md) for substantial
changes and the [ADR index](../adr/README.md) for lasting decisions.
