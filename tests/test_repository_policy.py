"""Exercise the policy check against maintained example paths."""

from pathlib import Path
import subprocess
import sys

import pytest


CHECK = Path(__file__).resolve().parents[1] / "scripts" / "check_repository.py"


@pytest.mark.parametrize(
    "source", ["sensor.nordpool_price", "sensor.tibber_price", "sensor.tibber_pulse_power"]
)
def test_dashboard_policy_rejects_provider_entities(tmp_path, source):
    dashboard = tmp_path / "examples" / "dashboards" / "nested" / "test.yaml"
    dashboard.parent.mkdir(parents=True)
    dashboard.write_text(f"entity: {source}\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CHECK)], cwd=tmp_path, capture_output=True, text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Provider entity outside source layer" in result.stdout
    assert "examples/dashboards/nested/test.yaml" in result.stdout


def test_dashboard_policy_accepts_canonical_entities_without_legacy_folders(tmp_path):
    dashboard = tmp_path / "examples" / "dashboards" / "test.yaml"
    dashboard.parent.mkdir(parents=True)
    dashboard.write_text("entity: sensor.electricity_pro_current_power\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CHECK)], cwd=tmp_path, capture_output=True, text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Repository policy checks passed." in result.stdout


def test_repository_policy_still_rejects_private_configuration(tmp_path):
    (tmp_path / "secrets.yaml").write_text("example: not-a-secret\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CHECK)], cwd=tmp_path, capture_output=True, text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Forbidden file: secrets.yaml" in result.stdout
