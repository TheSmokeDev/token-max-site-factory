"""token-max-site-factory engine.

Generalized port of a production SR-22 insurance token-max lane. Local-only by design: prepares
entity/topic packets for a fresh-context Archon writer loop, tracks batch
state, and validates generated page quality gates. It never deploys, submits
URLs, changes DNS, or touches Google/Vercel account state.

Path model:
- FACTORY_ROOT: this repo (configs, prompts, templates) — read-only at run time
- target repo: resolved from Path.cwd() (the Archon worktree) for every
  batch/output path, so the engine is portable across target repos.

Ledger vocabulary note: the batch page field ``city`` is the ENTITY slot
(kept as-is from the SR22 lane for byte-compatible batch/packet schemas);
for non-geo sites it simply holds the entity slug.
"""

from __future__ import annotations

import os
import sysconfig
from pathlib import Path

__version__ = "0.6.0"

SOURCE_ROOT = Path(__file__).resolve().parents[2]
INSTALLED_ROOT = Path(sysconfig.get_path("data")) / "share" / "token-max-site-factory"


def _has_resources(path: Path) -> bool:
    return (path / "prompts" / "base-writer.md").is_file() and (path / "workflow-templates").is_dir()


def _resource_root() -> Path:
    override = os.environ.get("TOKENMAX_FACTORY_ROOT")
    candidates = [Path(override)] if override else []
    candidates.extend([SOURCE_ROOT, INSTALLED_ROOT])
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if _has_resources(resolved):
            return resolved
    raise RuntimeError(
        "TokenMax resources not found; install the package or set TOKENMAX_FACTORY_ROOT to a source checkout"
    )


FACTORY_ROOT = _resource_root()


def workspace_root() -> Path:
    override = os.environ.get("TOKENMAX_WORKSPACE")
    if override:
        return Path(override).expanduser().resolve()
    if FACTORY_ROOT == SOURCE_ROOT and (SOURCE_ROOT / "sites").is_dir():
        return SOURCE_ROOT
    return Path.home() / ".tokenmax-factory"


def factory_path(rel: str) -> Path:
    relative = Path(rel)
    if relative.parts and relative.parts[0] == "sites":
        return workspace_root() / relative
    return FACTORY_ROOT / relative


def target_root() -> Path:
    """The target repo root = the process cwd (Archon runs nodes at the
    worktree root). Manual invocations must cd into the target repo first."""
    return Path.cwd()
