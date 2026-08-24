#!/usr/bin/env python3
"""Exercise the installed tokenmax command from an isolated workspace."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(command: list[str], *, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, check=True)


def main() -> None:
    tokenmax = shutil.which("tokenmax")
    if not tokenmax:
        raise SystemExit("installed tokenmax command not found on PATH")

    with tempfile.TemporaryDirectory(prefix="tokenmax-wheel-smoke-") as temp:
        root = Path(temp)
        workspace = root / "workspace"
        target = root / "target"
        target.mkdir()
        subprocess.run(["git", "init", "--quiet", str(target)], check=True)
        env = dict(os.environ)
        env["TOKENMAX_WORKSPACE"] = str(workspace)

        doctor = json.loads(run([tokenmax, "doctor", "--json"], env=env, cwd=root).stdout)
        if not doctor["ok"] or doctor["factory_root"] == str(Path.cwd()):
            raise SystemExit(f"installed doctor failed: {doctor}")

        run([tokenmax, "new-site", "--site", "smoke", "--target-repo", str(target)], env=env, cwd=root)
        sites = json.loads(run([tokenmax, "list-sites", "--json"], env=env, cwd=root).stdout)
        if sites["sites"] != ["smoke"]:
            raise SystemExit(f"isolated workspace did not retain site: {sites}")

        run([tokenmax, "install", "--site", "smoke", "--run-input", "pilot-1"], env=env, cwd=root)
        workflow = target / ".archon" / "workflows" / "token-max-site-factory-smoke.yaml"
        marker = target / ".token-max" / "sites" / "smoke.json"
        if not workflow.is_file() or not marker.is_file():
            raise SystemExit("installed CLI did not create workflow and marker")
        raw = workflow.read_text(encoding="utf-8")
        if "Live mutation: none" in raw or "allow_deploy: true" in raw:
            raise SystemExit("unexpected live-mutation content in installed workflow")
        print(json.dumps({"ok": True, "workflow": str(workflow), "marker": str(marker)}, indent=2))


if __name__ == "__main__":
    main()
