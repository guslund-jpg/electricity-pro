# Development

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
./scripts/validate.sh
python -m ruff check custom_components tests scripts
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

## Check scope and documentation

`./scripts/validate.sh` checks YAML, JSON, Python syntax, unique IDs and repository
policy. CI additionally runs Markdown lint using the repository's
`.markdownlint.json` settings and Python lint with the same command shown above.
The pinned Ruff version is installed from `requirements-dev.txt`; its rules and
Python target are in `ruff.toml`. The local pre-commit hook runs the same full
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

### Formatting and staged type checking

Formatting and static type checking are **not CI gates yet**. Remaining work
stays tracked in [#287](https://github.com/guslund-jpg/electricity-pro/issues/287):

1. **Formatting-only PR:** use the pinned Ruff formatter with the policy in
   `ruff.toml` (88 columns, double quotes, spaces, LF). Review a mechanical
   formatting diff separately from logic changes, run the full tests, then
   enable `ruff format --check` for the agreed scope in CI and pre-commit.
   Until then, preserve surrounding style and do not reformat whole files
   as part of a bug fix.
2. **Small typing pilot:** assess `statistics.py`, `pricing.py` and
   `grid_tariff.py` first. Pin the chosen checker, list exactly which modules
   it checks, include their relevant dependencies and fix reported errors
   before adding a local/CI command. Do not claim the whole integration is
   checked or use blanket ignores to manufacture a green result.
3. **Expand typing gradually:** calculation/history modules next, then HA-facing
   provider/coordinator/entities and configuration flows as their boundaries
   improve. Record uncovered modules and narrowly justified exceptions in that
   follow-up. Strict whole-integration typing is not a v1.6 prerequisite.

Keep each stage reviewable, retain the behavioural test gate, and document
commands only once the corresponding check is actually configured.

### Documentation and fixture checks

For documentation-only changes, check relative links and headings, run repository
validation and require the normal CI checks. Update the architecture and sensor
catalogue whenever module ownership or entity semantics change.

The HA configuration workflow validates the minimal `config/` fixture and copies
any YAML under `packages/`. The latter currently contains only layout
placeholders, so this check does not exercise the Python integration's config
flow or runtime. Those behaviours belong to pytest and development-instance tests.

## Development instance

Deploy only to a separate development Home Assistant instance. Before every restart:

```bash
ha core check
```
