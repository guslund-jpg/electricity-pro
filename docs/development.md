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

## Development instance

Deploy only to a separate development Home Assistant instance. Before every restart:

```bash
ha core check
```
