"""Batch state machine — port of sr22_token_max.py bootstrap/prepare/resume/
next-page/packet/remaining/pending-ids/mark-generated (L356-612, L873-898).

State lives on disk (batch.json) so the fresh-context Archon loop can resume
after any interruption. All output paths are target-repo-relative, resolved
against cwd."""

from __future__ import annotations

import json
import re
import shlex
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import target_root
from .adapters import load_entities
from .matrix import build_pages, entity_order, resolve_topics
from .packet import page_prompt_packet
from .validators.text_quality import word_count

RESUME_PAGE_FIELDS = {
    "status",
    "word_count",
    "written_at",
    "validation_failures",
    "regenerate_with",
    "retry_count",
}


def page_source_rel(page: dict) -> str:
    """The file the WRITER produces: staging markdown for html sites, the
    final output for markdown sites."""
    return str(page.get("staging") or page.get("output") or "")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def load_batch(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _status_counts(batch: dict) -> dict:
    return dict(Counter(p.get("status") for p in batch.get("pages", []) if isinstance(p, dict)))


def merge_existing_batch(output_path: Path, batch: dict) -> dict:
    if not output_path.exists():
        return batch
    try:
        existing = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"RESUME_SKIPPED=invalid_existing_batch:{exc}", file=sys.stderr)
        return batch

    existing_pages = {
        str(page.get("id")): page
        for page in existing.get("pages", [])
        if isinstance(page, dict) and page.get("id")
    }
    resumed = 0
    for page in batch.get("pages", []):
        if not isinstance(page, dict):
            continue
        previous = existing_pages.get(str(page.get("id")))
        if not isinstance(previous, dict) or previous.get("output") != page.get("output"):
            continue
        if str(previous.get("status") or "") not in {"generated", "regenerated", "held_back"}:
            continue
        for field_name in RESUME_PAGE_FIELDS:
            if field_name in previous:
                page[field_name] = previous[field_name]
        resumed += 1

    batch["resumed_page_count"] = resumed
    batch["status_counts"] = _status_counts(batch)
    return batch


def merge_existing_outputs(batch: dict) -> dict:
    resumed = 0
    for page in batch.get("pages", []):
        if not isinstance(page, dict) or page.get("status") != "pending_generation":
            continue
        output = target_root() / page_source_rel(page)
        if not output.exists():
            continue
        raw = output.read_text(encoding="utf-8")
        page["status"] = "generated"
        page["word_count"] = word_count(raw)
        page["written_at"] = page.get("written_at") or now_iso()
        page["resumed_from_existing_output"] = True
        resumed += 1

    batch["resumed_existing_output_count"] = resumed
    batch["status_counts"] = _status_counts(batch)
    return batch


def parse_bootstrap_input(cfg: dict, raw_input: str) -> dict:
    """Port of bootstrap() token parsing (L475-536), phase presets now coming
    from config.phases instead of hardcoded phase2/phase3 branches."""
    tokens = shlex.split(raw_input or "")
    inventory = cfg["inventory"]
    phases: dict[str, dict] = cfg.get("phases") or {}
    topics_default = ",".join(str(t["key"]) for t in inventory["topics"])
    pilot_entities = ",".join(inventory.get("pilot_entities") or [])

    default_phase = str(cfg.get("default_phase") or "pilot")
    limit = 45
    products = topics_default
    cities = pilot_entities
    phase = default_phase
    dry_run = False
    if default_phase in phases:
        preset = phases[default_phase]
        limit = int(preset.get("limit") or limit)
        products = str(preset.get("topics") or products)
        cities = _preset_entities(preset, pilot_entities)

    def _phase_lookup(token: str) -> tuple[str, dict, int | None] | None:
        for name, preset in phases.items():
            names = [name, *[str(a) for a in preset.get("aliases") or []]]
            if token in names:
                return name, preset, None
            for candidate in names:
                match = re.match(rf"^{re.escape(candidate)}-tranche-([0-9]+)$", token)
                if match:
                    return name, preset, int(match.group(1))
        return None

    topic_words = set()
    for topic in inventory["topics"]:
        topic_words.add(str(topic["key"]).lower())
        topic_words.update(str(a).lower() for a in topic.get("aliases") or [])

    for idx, token in enumerate(tokens):
        if token == "--dry-run":
            dry_run = True
        elif token == "--limit" and idx + 1 < len(tokens):
            limit = int(tokens[idx + 1])
        elif token.startswith("--limit="):
            limit = int(token.split("=", 1)[1])
        elif token in {"--products", "--topics"} and idx + 1 < len(tokens):
            products = tokens[idx + 1]
        elif token.startswith("--products=") or token.startswith("--topics="):
            products = token.split("=", 1)[1]
        elif token in {"--cities", "--entities"} and idx + 1 < len(tokens):
            cities = tokens[idx + 1]
        elif token.startswith("--cities=") or token.startswith("--entities="):
            cities = token.split("=", 1)[1]
        elif token in {"all-cities", "--all-cities", "all-entities", "--all-entities"}:
            cities = ""
        elif (hit := _phase_lookup(token)) is not None:
            name, preset, tranche = hit
            phase = name
            products = str(preset.get("topics") or topics_default)
            cities = _preset_entities(preset, pilot_entities)
            limit = tranche if tranche is not None else int(preset.get("limit") or limit)
        elif re.match(r"^pilot-?[0-9]+$", token):
            limit = int(re.search(r"[0-9]+", token).group(0))  # type: ignore[union-attr]
        elif re.match(r"^[0-9]+$", token):
            limit = int(token)
        elif not token.startswith("--") and any(word in token.lower() for word in topic_words):
            products = token

    return {
        "products": ",".join(resolve_topics(cfg, products)),
        "limit": limit,
        "cities": cities,
        "phase": phase,
        "dry_run": dry_run,
    }


def _preset_entities(preset: dict, pilot_entities: str) -> str:
    value = preset.get("entities")
    if value in (None, "pilot"):
        return pilot_entities
    if value == "all":
        return ""
    return str(value)


def prepare_batch(
    cfg: dict,
    *,
    products: str,
    limit: int,
    cities: str,
    phase: str,
    dry_run: bool,
    output: Path,
    resume: bool,
    resume_existing_outputs: bool,
    skip_existing_routes: bool = False,
) -> dict:
    entities = load_entities(cfg)
    requested = [slug.strip() for slug in (cities or "").split(",") if slug.strip()]
    selected_slugs = entity_order(cfg, entities, requested)
    topic_keys = resolve_topics(cfg, products)

    skip_routes: set[str] | None = None
    if skip_existing_routes:
        skip_routes = _existing_routes(cfg)

    pages = build_pages(cfg, entities, selected_slugs, topic_keys, limit, skip_routes)
    fm = cfg.get("frontmatter") or {}
    batch = {
        "kind": cfg["batch_kind"],
        "generated_at": now_iso(),
        "products": topic_keys,
        "limit": limit,
        "phase": phase or "custom",
        "dry_run": bool(dry_run),
        "published": fm.get("published") or "",
        "updated": fm.get("updated") or "",
        "pages": pages,
    }
    if resume:
        batch = merge_existing_batch(output, batch)
    if resume_existing_outputs:
        batch = merge_existing_outputs(batch)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(batch, indent=2) + "\n", encoding="utf-8")
    print(f"BATCH={output}")
    print(f"PAGES={len(pages)}")
    print("PRODUCTS=" + ",".join(topic_keys))
    print("CITIES=" + ",".join(dict.fromkeys(str(page["city"]) for page in pages)))
    if resume:
        print(f"RESUMED={batch.get('resumed_page_count', 0)}")
    if resume_existing_outputs:
        print(f"RESUMED_EXISTING_OUTPUTS={batch.get('resumed_existing_output_count', 0)}")
    return batch


def _existing_routes(cfg: dict) -> set[str]:
    """Routes already live on the site per the cached scan inventory (used to
    avoid regenerating pages the site already has)."""
    from . import factory_path

    inventory_path = factory_path(f"sites/{cfg['site_id']}/inventory.json")
    if not inventory_path.exists():
        return set()
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    routes: set[str] = set()
    host = str(cfg.get("canonical_host") or "").rstrip("/")
    for item in payload.get("existing_urls", []):
        url = str(item.get("url") or "")
        if host and url.startswith(host):
            routes.add(url[len(host):] or "/")
    return routes


def next_page(cfg: dict, batch_path: Path, statuses: str, max_retries: int, output: str) -> None:
    batch = load_batch(batch_path)
    status_set = {part.strip() for part in statuses.split(",") if part.strip()}
    if batch.get("dry_run"):
        payload = {"complete": True, "dry_run": True, "reason": "dry_run"}
        if output:
            write_json(Path(output), payload)
        print(json.dumps(payload, indent=2))
        return

    entities = load_entities(cfg)
    for page in batch.get("pages", []):
        if page.get("status") not in status_set:
            continue
        if page.get("status") == "held_back" and int(page.get("retry_count") or 0) >= max_retries:
            continue
        payload = page_prompt_packet(cfg, page, batch, entities)
        if output:
            write_json(Path(output), payload)
        print(json.dumps(payload, indent=2, default=str))
        return

    payload = {"complete": True, "statuses": sorted(status_set)}
    if output:
        write_json(Path(output), payload)
    print(json.dumps(payload, indent=2))


def packet_by_id(cfg: dict, batch_path: Path, page_id: str, output: str) -> None:
    batch = load_batch(batch_path)
    entities = load_entities(cfg)
    for page in batch.get("pages", []):
        if str(page.get("id")) == str(page_id):
            payload = page_prompt_packet(cfg, page, batch, entities)
            if output:
                write_json(Path(output), payload)
            print(json.dumps(payload, indent=2, default=str))
            return
    raise SystemExit(f"Unknown page id: {page_id}")


def remaining(batch_path: Path, statuses: str, exit_zero_when_done: bool) -> None:
    batch = load_batch(batch_path)
    status_set = {part.strip() for part in statuses.split(",") if part.strip()}
    count = sum(1 for page in batch.get("pages", []) if page.get("status") in status_set)
    print(count)
    if exit_zero_when_done:
        raise SystemExit(0 if count == 0 else 1)


def pending_ids(batch_path: Path, statuses: str, max_retries: int) -> None:
    batch = load_batch(batch_path)
    status_set = {part.strip() for part in statuses.split(",") if part.strip()}
    for page in batch.get("pages", []):
        if page.get("status") not in status_set:
            continue
        if page.get("status") == "held_back" and int(page.get("retry_count") or 0) >= max_retries:
            continue
        print(page.get("id"))


def mark_generated(batch_path: Path, page_id: str, status: str) -> None:
    batch = load_batch(batch_path)
    for page in batch.get("pages", []):
        if page.get("id") != page_id:
            continue
        output = target_root() / page_source_rel(page)
        if not output.exists():
            raise SystemExit(f"Cannot mark generated; file missing: {output}")
        raw = output.read_text(encoding="utf-8")
        previous_status = str(page.get("status") or "")
        if status == "regenerated" or previous_status == "held_back":
            page["retry_count"] = int(page.get("retry_count") or 0) + 1
            page["status"] = "regenerated"
        else:
            page["status"] = "generated"
        if page.get("validation_failures"):
            page["last_validation_failures"] = page.get("validation_failures")
        page["validation_failures"] = []
        page["regenerate_with"] = ""
        page["word_count"] = word_count(raw)
        page["written_at"] = now_iso()
        batch_path.write_text(json.dumps(batch, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"page_id": page_id, "status": page["status"], "word_count": page["word_count"]}, indent=2))
        return
    raise SystemExit(f"Unknown page id: {page_id}")
