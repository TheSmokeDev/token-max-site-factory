"""Sitemap fetcher/parser — stdlib only. Handles urlset and recursive
sitemapindex documents. GET-only; network access is gated by the manual
`scan --allow-network` command (workflow runs never hit the network)."""

from __future__ import annotations

import gzip
import urllib.request
import xml.etree.ElementTree as ET

USER_AGENT = "token-max-site-factory/0.1 (+local content planning; GET-only)"
_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def fetch(url: str, timeout: int = 15) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    if url.endswith(".gz") or data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data


def parse_sitemap(data: bytes) -> tuple[list[dict], list[str]]:
    """Returns (url_entries, child_sitemap_urls)."""
    root = ET.fromstring(data)
    urls: list[dict] = []
    children: list[str] = []
    if root.tag == f"{_NS}sitemapindex":
        for node in root.findall(f"{_NS}sitemap"):
            loc = node.findtext(f"{_NS}loc")
            if loc:
                children.append(loc.strip())
    else:
        for node in root.findall(f"{_NS}url"):
            loc = node.findtext(f"{_NS}loc")
            if loc:
                urls.append({"url": loc.strip(), "lastmod": (node.findtext(f"{_NS}lastmod") or "").strip()})
    return urls, children


def collect_sitemap_urls(sitemap_url: str, timeout: int = 15, max_children: int = 50) -> list[dict]:
    seen: set[str] = set()
    queue = [sitemap_url]
    entries: list[dict] = []
    while queue and len(seen) < max_children:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        try:
            urls, children = parse_sitemap(fetch(current, timeout))
        except Exception as exc:
            print(f"SITEMAP_SKIP {current}: {exc}")
            continue
        entries.extend(urls)
        queue.extend(children)
    return entries
