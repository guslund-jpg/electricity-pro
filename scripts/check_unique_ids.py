#!/usr/bin/env python3
from collections import defaultdict
from pathlib import Path
import re
import sys

pattern = re.compile(r"^\\s*unique_id:\\s*[\"']?([^\"'#\\s]+)", re.MULTILINE)
found = defaultdict(list)

for raw in sys.argv[1:] or ["."]:
    path = Path(raw)
    files = [path] if path.is_file() else list(path.rglob("*.yaml")) + list(path.rglob("*.yml"))
    for file in files:
        text = file.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            line = text.count("\\n", 0, match.start()) + 1
            found[match.group(1)].append(f"{file}:{line}")

duplicates = {key: value for key, value in found.items() if len(value) > 1}
if duplicates:
    for key, locations in sorted(duplicates.items()):
        print(f"Duplicate unique_id: {key}")
        for location in locations:
            print(f"  {location}")
    raise SystemExit(1)

print("No duplicate unique_id values.")
