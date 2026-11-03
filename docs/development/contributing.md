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

These modules form a pure dependency graph: `good_time.py` uses
`adaptive_price.py`, which uses `pricing.py`; external dependencies are only
the standard library. Mypy follows
imports normally and does not ignore missing imports or errors. Strict mode,
`disallow_any_unimported` and unused-configuration warnings are enabled; the
small pilot runs without an incremental cache. The extracted Good Time result
uses an explicit attribute-value union; calculation behaviour is unchanged.

The three history/statistics modules accept stored records as
`Mapping[str, object]`. Shared readers check string, decimal, array and record
shapes before the owning model validates dates, finiteness, ranges and consistency.
The base-load history writer has an explicit `TypedDict` result. Storage format
and calculations are unchanged; malformed collection shapes are now rejected
explicitly. Runtime validation and JSON round-trip tests remain necessary:
annotations alone do not validate stored data. Strict mode does not prohibit
explicit `Any` elsewhere in the checked scope.

There is one explicit boundary: the exact parent module
`custom_components.electricity_pro` (`__init__.py`) has `follow_imports = skip`.
Mypy otherwise discovers that parent while resolving these files and follows
its HA startup imports into the coordinator. The checked modules do not
use the parent's exported types. This is **not** a wildcard exclusion of its
submodules: their bodies and imported dependencies remain checked normally.
Explicit namespace-package bases keep module names consistent with repository
imports, so the exception cannot accidentally target a different package name.
See [mypy import handling](https://mypy.readthedocs.io/en/stable/running_mypy.html).

This does not check HA setup, callers in the coordinator/entities, tests, or the
whole integration. The initial broader scan found work outside the pilot:
typed counter/source dictionaries (`energy_flows.py`, `flow_sources.py`),
ledger parameter/reset typing (`cost_ledger.py`), action-response narrowing
(`nordpool.py`), snapshot/update dictionaries (`coordinator.py`), and HA
action schema/return typing (`__init__.py`). These findings require review;
they are not by themselves proof of runtime failures and have not been fixed
or suppressed as if the whole integration were clean.

### Python formatting

The **Repository quality** job and local pre-commit hook check formatting across
`custom_components/`, `tests/` and `scripts/` using the pinned Ruff formatter.
The policy in `ruff.toml` uses 88 columns, double quotes, spaces and LF endings.
Its Python 3.13 syntax target preserves compatibility with the minimum supported
Home Assistant version, even though the main development environment uses Python 3.14.
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
Expand calculation/history modules next, then HA-facing provider/coordinator/entities
and configuration flows as their boundaries improve. Add modules to the explicit
list, include their dependencies, and resolve errors before expanding the gate.
Address the findings above and remove the parent-module boundary when setup joins
the checked scope. Record remaining uncovered modules and any narrowly justified
exceptions. Keep each stage reviewable and retain the behavioural test gate.

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
