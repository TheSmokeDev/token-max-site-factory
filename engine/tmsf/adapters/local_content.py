"""Local content scanner — inventories pages already present in the target
repo (markdown or HTML) so the matrix builder can dedupe against them."""

from __future__ import annotations

import re
from pathlib import Path


def _title_of(path: Path, raw: str) -> str:
    if path.suffix.lower() in {".html", ".htm"}:
        match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S | re.I)
        return (match.group(1).strip() if match else "")
    match = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", raw, re.M)
    if match:
        return match.group(1)
    match = re.search(r"^#\s+(.+)$", raw, re.M)
    return match.group(1).strip() if match else ""


def _word_count(path: Path, raw: str) -> int:
    text = raw
    if path.suffix.lower() in {".html", ".htm"}:
        text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
    return len(text.split())


def scan_local(root: Path, globs: tuple[str, ...] = ("**/*.md", "**/*.html")) -> list[dict]:
    results: list[dict] = []
    if not root.exists():
        return results
    for pattern in globs:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            try:
                raw = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            results.append(
                {
                    "url": str(path.relative_to(root)).replace("\\", "/"),
                    "title": _title_of(path, raw),
                    "h1": "",
                    "meta_description": "",
                    "canonical": "",
                    "robots": "",
                    "word_count": _word_count(path, raw),
                    "lang": "es" if "/es/" in str(path).replace("\\", "/") + "/" else "en",
                    "source": "local",
                }
            )
    return results
