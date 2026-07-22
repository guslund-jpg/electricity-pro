# Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
./scripts/validate.sh
```

Deploy only to a separate development Home Assistant instance. Before every restart:

```bash
ha core check
```
