"""Scan orchestrator — the point-and-shoot entry point's first move.

Manual + factory-side by design: network access only happens when the
operator runs `scan --allow-network`; workflow runs consume the cached
sites/<id>/inventory.json offline (reproducible runs, no surprise traffic).

Pipeline: robots.txt -> sitemap.xml (recursive) -> bounded polite crawl of
discovered URLs (BFS fallback from the homepage when no sitemap) -> local
content scan of the target repo -> normalized inventory JSON."""

from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from . import factory_path
from .adapters.crawler import crawl
from .adapters.local_content import scan_local
from .adapters.sitemap import collect_sitemap_urls
from .config import load_site_config


def inventory_path(site_id: str) -> Path:
    return factory_path(f"sites/{site_id}/inventory.json")


def _write_inventory(site_id: str, existing_urls: list[dict], notes: list[str]) -> Path:
    payload = {
        "site_id": site_id,
        "scanned_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "existing_urls": existing_urls,
        "entities": [],
        "topics": [],
        "source_facts": [],
        "corpus_paths": [],
        "notes": notes,
    }
    out = inventory_path(site_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out


def run_scan(site_id: str, *, allow_network: bool) -> None:
    cfg = load_site_config(site_id)
    inventory = cfg["inventory"]
    crawl_cfg = inventory["crawl"]
    notes: list[str] = []
    pages: list[dict] = []

    if allow_network:
        host = str(cfg["canonical_host"]).rstrip("/")
        sitemap_url = str(inventory.get("sitemap_url") or "") or f"{host}/sitemap.xml"
        entries = collect_sitemap_urls(sitemap_url, timeout=int(crawl_cfg["timeout_seconds"]))
        lastmod = {e["url"]: e.get("lastmod", "") for e in entries}
        if entries:
            notes.append(f"sitemap {sitemap_url}: {len(entries)} urls")
            seeds = [e["url"] for e in entries]
            follow_links = False
        else:
            notes.append(f"no sitemap at {sitemap_url}; BFS crawl from {host}/")
            seeds = [host + "/"]
            follow_links = True
        pages = crawl(
            seeds,
            host,
            max_pages=int(crawl_cfg["max_pages"]),
            delay_seconds=float(crawl_cfg["delay_seconds"]),
            timeout_seconds=int(crawl_cfg["timeout_seconds"]),
            follow_links=follow_links,
        )
        for page in pages:
            page["lastmod"] = lastmod.get(page["url"], "")
            if not page.get("lang"):
                page["lang"] = "es" if "/es/" in urllib.parse.urlparse(page["url"]).path + "/" else "en"
    else:
        notes.append("network scan skipped (no --allow-network); local content only")

    local_pages = scan_local(Path(str(cfg["target_repo_root"])))
    notes.append(f"local content scan: {len(local_pages)} files")

    out = _write_inventory(site_id, pages + local_pages, notes)
    langs: dict[str, int] = {}
    for page in pages + local_pages:
        langs[page.get("lang") or "?"] = langs.get(page.get("lang") or "?", 0) + 1
    print(f"INVENTORY={out}")
    print(f"NETWORK_PAGES={len(pages)}")
    print(f"LOCAL_PAGES={len(local_pages)}")
    print(f"LANGS={json.dumps(langs)}")
    for note in notes:
        print(f"NOTE: {note}")


def scan_local_only(site_id: str) -> None:
    run_scan(site_id, allow_network=False)
