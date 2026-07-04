"""Bounded, polite HTTP page crawler — stdlib only (urllib + html.parser).

Extracts title / first H1 / meta description / canonical / robots meta /
lang / visible word count / same-host links from each page. Honors
robots.txt, a page budget, and a fixed inter-request delay. GET-only."""

from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser

from .sitemap import USER_AGENT

SKIP_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".css", ".js",
    ".pdf", ".zip", ".mp3", ".mp4", ".woff", ".woff2", ".xml", ".json", ".txt",
)


class PageExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.h1 = ""
        self.meta_description = ""
        self.canonical = ""
        self.robots = ""
        self.lang = ""
        self.links: list[str] = []
        self._stack: list[str] = []
        self._text_parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "html":
            self.lang = attrs_dict.get("lang") or ""
        elif tag == "meta":
            name = (attrs_dict.get("name") or "").lower()
            if name == "description":
                self.meta_description = attrs_dict.get("content") or ""
            elif name == "robots":
                self.robots = attrs_dict.get("content") or ""
        elif tag == "link" and (attrs_dict.get("rel") or "").lower() == "canonical":
            self.canonical = attrs_dict.get("href") or ""
        elif tag == "a" and attrs_dict.get("href"):
            self.links.append(attrs_dict["href"])
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        self._stack.append(tag)

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        while self._stack and self._stack.pop() != tag:
            pass

    def handle_data(self, data):
        if self._skip_depth:
            return
        if "title" in self._stack and not self.title:
            self.title = data.strip()
        elif "h1" in self._stack and not self.h1:
            self.h1 = data.strip()
        self._text_parts.append(data)

    @property
    def word_count(self) -> int:
        return len(" ".join(self._text_parts).split())


def fetch_page(url: str, timeout: int = 15) -> tuple[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        raw = response.read()
    charset = "utf-8"
    if "charset=" in content_type:
        charset = content_type.split("charset=")[-1].split(";")[0].strip() or "utf-8"
    return raw.decode(charset, errors="replace"), content_type


def extract(url: str, html: str) -> dict:
    parser = PageExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    return {
        "url": url,
        "title": parser.title,
        "h1": parser.h1,
        "meta_description": parser.meta_description,
        "canonical": parser.canonical,
        "robots": parser.robots,
        "word_count": parser.word_count,
        "lang": parser.lang,
    }


def _same_host(url: str, host: str) -> bool:
    return urllib.parse.urlparse(url).netloc in ("", host)


def _normalize(base: str, href: str) -> str | None:
    href = href.split("#", 1)[0].strip()
    if not href or href.startswith(("mailto:", "tel:", "javascript:")):
        return None
    absolute = urllib.parse.urljoin(base, href)
    if absolute.lower().endswith(SKIP_EXTENSIONS):
        return None
    return absolute


def crawl(
    seeds: list[str],
    canonical_host: str,
    *,
    max_pages: int = 200,
    delay_seconds: float = 1.0,
    timeout_seconds: int = 15,
    follow_links: bool = True,
) -> list[dict]:
    host = urllib.parse.urlparse(canonical_host).netloc
    robots = urllib.robotparser.RobotFileParser()
    try:
        robots.set_url(urllib.parse.urljoin(canonical_host, "/robots.txt"))
        robots.read()
    except Exception:
        robots = None

    seen: set[str] = set()
    queue = list(dict.fromkeys(seeds))
    results: list[dict] = []
    while queue and len(results) < max_pages:
        url = queue.pop(0)
        if url in seen or not _same_host(url, host):
            continue
        seen.add(url)
        if robots is not None and not robots.can_fetch(USER_AGENT, url):
            print(f"CRAWL_ROBOTS_SKIP {url}")
            continue
        try:
            html, content_type = fetch_page(url, timeout_seconds)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            print(f"CRAWL_ERROR {url}: {exc}")
            continue
        if "html" not in content_type:
            continue
        parser = PageExtractor()
        try:
            parser.feed(html)
        except Exception:
            pass
        page = extract(url, html)
        page["source"] = "crawl"
        results.append(page)
        print(f"CRAWLED {len(results)}/{max_pages} {url}")
        if follow_links:
            for href in parser.links:
                normalized = _normalize(url, href)
                if normalized and normalized not in seen and _same_host(normalized, host):
                    queue.append(normalized)
        time.sleep(delay_seconds)
    return results
