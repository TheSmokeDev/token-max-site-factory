"""No-live-mutation preflight — the hard boundary, enforced in code.

1. Asserts every live_mutation flag in the site config is false.
2. Greps the factory engine source for live-mutation command patterns
   (port of the sr22 workflow's grep-guard node).
3. Verifies the target repo's .token-max/sites/<id>.json marker matches
   --site, so the wrong config can never be pointed at the wrong repo. The
   legacy .token-max/site.json path remains a read-only fallback.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import FACTORY_ROOT, target_root

LIVE_MUTATION_PATTERN = re.compile(
    r"(vercel deploy|vercel alias|gcloud|searchconsole|indexing api|netlify deploy|dns record)",
    re.I,
)


def check_live_mutation_flags(cfg: dict) -> list[str]:
    problems = []
    for name, value in (cfg.get("live_mutation") or {}).items():
        if value:
            problems.append(f"live_mutation.{name} is enabled — the factory never mutates live state")
    return problems


def grep_engine_sources() -> list[str]:
    problems = []
    roots = [Path(__file__).resolve().parent, FACTORY_ROOT / "engine"]
    seen: set[Path] = set()
    for engine_dir in roots:
        if not engine_dir.exists():
            continue
        for path in sorted(engine_dir.glob("**/*.py")):
            resolved = path.resolve()
            if resolved in seen or path.name == "preflight.py":
                continue
            seen.add(resolved)
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if LIVE_MUTATION_PATTERN.search(line):
                    problems.append(f"live-mutation pattern in {path}:{lineno}")
    return problems


def check_marker(site_id: str) -> list[str]:
    marker_root = target_root() / ".token-max"
    marker = marker_root / "sites" / f"{site_id}.json"
    if not marker.exists():
        legacy = marker_root / "site.json"
        if legacy.exists():
            marker = legacy
    if not marker.exists():
        return [f"missing marker {marker} — run the factory 'install --site {site_id}' first"]
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"unreadable marker {marker}: {exc}"]
    if str(payload.get("site_id")) != site_id:
        return [f"marker site_id {payload.get('site_id')!r} != --site {site_id!r} (wrong repo for this config?)"]
    return []


def run_preflight(cfg: dict, *, require_marker: bool = True) -> None:
    problems = check_live_mutation_flags(cfg)
    problems += grep_engine_sources()
    if require_marker:
        problems += check_marker(str(cfg["site_id"]))
    if problems:
        for problem in problems:
            print(f"PREFLIGHT_FAIL: {problem}")
        raise SystemExit(1)
    print("NO_LIVE_MUTATION_COMMANDS")
