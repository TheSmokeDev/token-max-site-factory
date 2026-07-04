"""Static list entity adapter — CSV or JSON entity rows.

CSV: header row required; ``name`` and ``slug`` columns required, all other
columns pass through as string fields. JSON: a list of objects with at least
``name`` and ``slug``. Paths are factory-repo-relative when they start with
``sites/`` (per-site facts live beside the config), otherwise target-repo
relative; absolute paths pass through.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .. import factory_path, target_root


def _resolve(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    if raw.replace("\\", "/").startswith("sites/"):
        return factory_path(raw)
    return target_root() / path


def load_entities(spec: dict) -> dict[str, dict]:
    path = _resolve(str(spec.get("path") or ""))
    if not path.exists():
        raise SystemExit(f"entities list not found: {path}")

    rows: list[dict]
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("entities", [])
    else:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

    entities: dict[str, dict] = {}
    for row in rows:
        name = str(row.get("name") or "").strip()
        slug = str(row.get("slug") or "").strip()
        if not (name and slug):
            continue
        entity = {key: value for key, value in row.items() if value not in (None, "")}
        entity["name"] = name
        entity["slug"] = slug
        if "population" in entity:
            try:
                entity["population"] = int(float(str(entity["population"])))
            except ValueError:
                pass
        entities[slug] = entity
    return entities
