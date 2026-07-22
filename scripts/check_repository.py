#!/usr/bin/env python3
from pathlib import Path

errors = []
forbidden_names = {"secrets.yaml", "home-assistant_v2.db", "home-assistant.log",
                   "core.entity_registry", "core.config_entries"}
provider_tokens = ("sensor.nordpool_", "sensor.tibber_", "sensor.tibber_pulse_")

for path in Path(".").rglob("*"):
    if path.is_file() and ".git" not in path.parts and path.name in forbidden_names:
        errors.append(f"Forbidden file: {path}")

for base in ("packages/20_core", "packages/30_statistics",
             "packages/40_health", "packages/50_alerts", "dashboards"):
    directory = Path(base)
    for path in directory.rglob("*.yaml") if directory.exists() else []:
        text = path.read_text(encoding="utf-8")
        for token in provider_tokens:
            if token in text:
                errors.append(f"Provider entity outside source layer: {path}: {token}")

if errors:
    print("\\n".join(errors))
    raise SystemExit(1)

print("Repository policy checks passed.")
