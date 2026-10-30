# Development

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
./scripts/validate.sh
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
`.markdownlint.json` settings. Python formatting, Python linting and static type
checking are not configured yet; that incremental work is tracked in
[#287](https://github.com/guslund-jpg/electricity-pro/issues/287).

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
