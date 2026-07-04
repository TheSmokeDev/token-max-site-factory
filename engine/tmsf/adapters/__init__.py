"""Entity inventory adapters.

Each adapter loads the site's entity universe and returns
``dict[slug] -> public-context dict``. The public-context dict is what the
writer packet exposes (the SR22 lane's ``city_public_context`` shape for
ts_array; row fields for static_list).
"""

from __future__ import annotations

from . import static_list, ts_array

ADAPTER_REGISTRY = {
    "ts_array": ts_array.load_entities,
    "static_list": static_list.load_entities,
}


def load_entities(cfg: dict) -> dict[str, dict]:
    spec = cfg["inventory"].get("entities") or {}
    adapter = str(spec.get("adapter") or "static_list")
    if adapter not in ADAPTER_REGISTRY:
        raise SystemExit(f"Unknown entities adapter: {adapter}")
    return ADAPTER_REGISTRY[adapter](spec)
