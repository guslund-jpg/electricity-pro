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

The next release and `main` require **Home Assistant 2026.9.0** and Python 3.14.
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
| `timing_score.py` | Consumption-timing scores, matched intervals and bounded timing history |
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
| `coordinator.py` | Field-specific snapshot updates, flow metadata and persisted flow scope |
| `__init__.py` | Integration lifecycle and action dispatch to the selected loaded coordinator |
| `binary_sensor.py` | Good Time entity state, explanatory attributes and numeric settings |
| `device.py` | Fresh, entry-scoped Home Assistant device metadata |
| `sensor.py` | Sensor registration, phase readers, availability and entity attributes |
| `provider.py` | Optional source states, unit normalization and configured adjustments |
| `source_adapters.py` | Registry metadata, per-home Tibber discovery and capability mappings |
| `const.py` | Shared integration constants and defaults |
| `household_cost.py` | Calendar-based fixed-fee accrual and missing-fee metadata |
| `markup_estimate.py` | Matched Tibber/Nord Pool intervals and validated price responses |
| `pricing_config.py` | Saved price semantics and VAT normalization |
| `vat_suggestions.py` | Confirmed VAT assistance shared by setup and options flows |
| `workday.py` | Public Workday action responses and non-working dates |
| `config_flow.py` | Setup/options steps, typed selectors and confirmed forecast estimate navigation |

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

Coordinator snapshot replacements now use a field-specific `TypedDict`; a test
checks that its keys and value types match `ElectricityProData`. Flow metadata
and persisted scope are typed without changing saved formats. Compatibility
declarations remain untrusted objects until runtime validation, including
non-string and unhashable values. Existing persistence and action-response dictionaries
still contain explicit `Any`; strict checking is not a claim of complete typing.

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

This does not yet strictly check tests or the whole integration.
Remaining work includes narrowing the explicit `Any` in serialized action responses
and other dynamic boundaries. These findings require review; they
are not by themselves proof of runtime failures. The whole integration is not
yet type-clean.

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

Incremental typing work remains tracked in
[#287](https://github.com/guslund-jpg/electricity-pro/issues/287).
The agreed module list now includes the main configuration flow. Review
remaining dynamic coordinator, configuration and serialization data:
narrow application-owned values and document any justified framework-boundary
exceptions. Closing #287 requires the agreed scope and checks to be documented
and the behavioural tests to pass on both pinned Home Assistant environments;
it does not require eliminating every framework-supplied `Any` or strictly typing
the entire test suite. Unrelated refactoring should be tracked separately.

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
