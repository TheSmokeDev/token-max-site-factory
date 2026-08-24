import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _cli() -> list[str]:
    installed = shutil.which("tokenmax")
    if installed:
        return [installed]
    if os.environ.get("TOKENMAX_FORCE_INSTALLED") == "1":
        raise RuntimeError("tokenmax is not installed on PATH")
    return [sys.executable, str(ROOT / "engine" / "token_max_site_factory.py")]


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(_cli() + list(args), cwd=cwd or ROOT, capture_output=True, text=True, check=False)


def test_installed_help_and_version():
    assert run_cli("--help").returncode == 0
    result = run_cli("--version")
    assert result.returncode == 0
    assert "0.6.0" in result.stdout


def test_doctor_json_is_safe():
    result = run_cli("doctor", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["external_mutations"] == "none"


def test_list_sites_json():
    result = run_cli("list-sites", "--json")
    assert result.returncode == 0
    assert "example" in json.loads(result.stdout)["sites"]


def test_owner_map_validation_json():
    fixture = ROOT / "tests" / "fixtures" / "owner-map.valid.json"
    result = run_cli("owner-map", "--input", str(fixture), "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["ok"] is True
