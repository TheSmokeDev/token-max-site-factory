"""Matrix builder — entity ordering and page-candidate construction.
Port of sr22_token_max.py normalize_product/resolve_products (L220-240),
city_order (L243-255), and the prepare() page loop (L419-445)."""

from __future__ import annotations

import re

from .config import topic_aliases, topics_by_key


def normalize_topic(cfg: dict, raw: str) -> str:
    clean = raw.strip().lower()
    return topic_aliases(cfg).get(clean, clean)


def resolve_topics(cfg: dict, raw: str | None) -> list[str]:
    topics = topics_by_key(cfg)
    default = list(topics)
    value = (raw or ",".join(default)).strip()
    if value in {"all", "*"} | {",".join(default), "/".join(default)}:
        return default
    keys = [normalize_topic(cfg, part) for part in re.split(r"[,/]", value) if part.strip()]
    unknown = [key for key in keys if key not in topics]
    if unknown:
        raise SystemExit(f"Unknown topic(s): {', '.join(unknown)}")
    return list(dict.fromkeys(keys)) or default


def entity_order(cfg: dict, entities: dict[str, dict], requested: list[str]) -> list[str]:
    if requested:
        missing = [slug for slug in requested if slug not in entities]
        if missing:
            raise SystemExit(f"Unknown entity slug(s): {', '.join(missing)}")
        return requested
    pilot = [slug for slug in cfg["inventory"].get("pilot_entities") or [] if slug in entities]
    rest = [
        entity["slug"]
        for entity in sorted(
            entities.values(),
            key=lambda item: (-int(item.get("population") or 0), str(item.get("name") or "")),
        )
        if entity["slug"] not in set(pilot)
    ]
    return pilot + rest


def page_output(cfg: dict, entity_slug: str, topic: dict) -> str:
    return cfg["output_template"].format(entity=entity_slug, topic_file_key=topic["file_key"])


def page_route(cfg: dict, entity_slug: str, topic: dict) -> str:
    return cfg["route_template"].format(entity=entity_slug, topic_route_segment=topic["route_segment"])


def page_staging(cfg: dict, entity_slug: str, topic: dict) -> str:
    template = cfg.get("staging_template") or ""
    if not template:
        return ""
    return template.format(entity=entity_slug, topic_file_key=topic["file_key"])


def page_sources(cfg: dict) -> list[str]:
    sources: list[str] = []
    entities_path = (cfg["inventory"].get("entities") or {}).get("path")
    if entities_path:
        sources.append(str(entities_path))
    sources.extend(str(f) for f in cfg["inventory"].get("facts_files") or [])
    sources.extend(str(source["url"]) for source in cfg.get("authority_sources") or [])
    return sources


def build_pages(
    cfg: dict,
    entities: dict[str, dict],
    selected_slugs: list[str],
    topic_keys: list[str],
    limit: int,
    skip_routes: set[str] | None = None,
) -> list[dict]:
    topics = topics_by_key(cfg)
    sources = page_sources(cfg)
    pages: list[dict] = []
    for slug in selected_slugs:
        entity = entities[slug]
        for key in topic_keys:
            if len(pages) >= limit:
                break
            topic = topics[key]
            route = page_route(cfg, slug, topic)
            if skip_routes and route in skip_routes:
                continue
            page = {
                "id": f"{slug}-{topic['file_key']}-en",
                "city": slug,
                "city_name": entity.get("name"),
                "county": entity.get("county"),
                "product": key,
                "locale": "en",
                "status": "pending_generation",
                "output": page_output(cfg, slug, topic),
                "route": route,
                "sources": list(sources),
            }
            staging = page_staging(cfg, slug, topic)
            if staging:
                page["staging"] = staging
            pages.append(page)
        if len(pages) >= limit:
            break
    return pages
