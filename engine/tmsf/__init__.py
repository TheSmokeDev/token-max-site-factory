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

from pathlib import Path

__version__ = "0.6.0"

FACTORY_ROOT = Path(__file__).resolve().parents[2]


def factory_path(rel: str) -> Path:
    return FACTORY_ROOT / rel


def target_root() -> Path:
    """The target repo root = the process cwd (Archon runs nodes at the
    worktree root). Manual invocations must cd into the target repo first."""
    return Path.cwd()
