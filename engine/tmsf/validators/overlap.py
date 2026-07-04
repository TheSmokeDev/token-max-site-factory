"""Uniqueness engine — verbatim port of sr22_token_max.py L666-708 with two
generalizations: utility-section patterns and cross-corpus roots come from
site config, and corpus files may be HTML (tag-stripped before shingling)."""

from __future__ import annotations

import re
from pathlib import Path

from .. import target_root


def strip_utility_sections(markdown: str, patterns: list[str]) -> str:
    text = markdown
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.S | re.I)
    return text


def shingles(text: str, k: int = 9) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(tokens[i : i + k]) for i in range(max(0, len(tokens) - k + 1))}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def html_to_text(raw: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", raw, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def cross_corpus_files(roots: list[str], glob: str, limit: int = 0) -> list[Path]:
    files: list[Path] = []
    for raw in roots:
        root = Path(raw)
        if not root.is_absolute():
            root = target_root() / root
        if root.exists():
            files.extend(sorted(root.glob(glob)))
    if limit and len(files) > limit:
        return files[:limit]
    return files


def corpus_text(path: Path, utility_patterns: list[str]) -> str:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".html", ".htm"}:
        return html_to_text(raw)
    return strip_utility_sections(raw, utility_patterns)
