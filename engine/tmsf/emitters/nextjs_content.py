"""Deterministic staging-markdown -> Next.js spoke-content emitter.

The writer produces validated staging markdown (same contract as the html
emitter's staging step); this emitter reshapes it into the exact frontmatter
a Next.js content pipeline expects (gray-matter YAML + markdown body), so
the existing [vertical]/[slug] route renders it with zero new Next.js code.
No model involvement in this transform -- reuses the html emitter's
staging-markdown parsing (frontmatter/FAQ) plus new blockquote/sources
extraction that follows the same deterministic-regex approach."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .. import target_root
from ..adapters import load_entities
from ..config import topics_by_key
from .html import extract_faq, parse_frontmatter

_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


def _split_quote_source(text: str) -> dict:
    match = _LINK_RE.search(text)
    if not match:
        return {"text": text.strip()}
    clean = (text[: match.start()] + text[match.end():]).strip()
    clean = re.sub(r"\s+([.,;:])", r"\1", clean).strip()
    return {"text": clean, "sourceLabel": match.group(1), "sourceUrl": match.group(2)}


def extract_blockquotes(markdown: str) -> list[str]:
    """One entry per contiguous blockquote block (lines merged, '> ' stripped)."""
    quotes: list[str] = []
    current: list[str] = []
    for raw in markdown.splitlines():
        stripped = raw.strip()
        if stripped.startswith(">"):
            current.append(stripped[1:].lstrip())
        else:
            if current:
                quotes.append(" ".join(current))
                current = []
    if current:
        quotes.append(" ".join(current))
    return quotes


def extract_sources(markdown: str) -> list[dict]:
    match = re.search(r"^##\s+Sources\s*$", markdown, re.I | re.M)
    if not match:
        return []
    section = markdown[match.end():]
    next_h2 = re.search(r"^##\s+", section, re.M)
    if next_h2:
        section = section[: next_h2.start()]
    sources: list[dict] = []
    for line in section.splitlines():
        m = _LINK_RE.search(line)
        if m:
            sources.append({"label": m.group(1), "url": m.group(2)})
    return sources


def extract_h1(markdown: str) -> str:
    match = re.search(r"^#\s+(.+)$", markdown, re.M)
    return match.group(1).strip() if match else ""


_BLOCK_BOUNDARY_RE = re.compile(r"^(#|>|[-*]\s)")


def extract_bluf_and_intro(markdown: str) -> tuple[str, str]:
    """First two paragraphs after the H1 (skips other headings/quotes/lists).

    Uses a list-item regex requiring a space after '-'/'*' so bold-emphasis
    paragraphs (which start with a bare '**') aren't mistaken for list items."""
    h1 = re.search(r"^#\s+.+$", markdown, re.M)
    body = markdown[h1.end():] if h1 else markdown
    paragraphs: list[str] = []
    current: list[str] = []
    for raw in body.splitlines():
        stripped = raw.strip()
        if not stripped or _BLOCK_BOUNDARY_RE.match(stripped):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            if len(paragraphs) >= 2:
                break
            continue
        current.append(stripped)
    if current and len(paragraphs) < 2:
        paragraphs.append(" ".join(current))
    bluf = paragraphs[0].strip("*").strip() if paragraphs else ""
    intro = paragraphs[1] if len(paragraphs) > 1 else ""
    return bluf, intro


def strip_faq_and_sources(markdown: str) -> str:
    """Body minus the FAQ + Sources sections (they move into frontmatter arrays)."""
    for pattern in (r"^##\s+.*(frequently asked|faq).*$", r"^##\s+Sources\s*$"):
        match = re.search(pattern, markdown, re.I | re.M)
        if not match:
            continue
        next_h2 = re.search(r"^##\s+", markdown[match.end():], re.M)
        end = match.end() + next_h2.start() if next_h2 else len(markdown)
        markdown = markdown[: match.start()] + markdown[end:]
    return markdown.strip() + "\n"


def build_frontmatter(cfg: dict, meta: dict, body_md: str) -> dict:
    entities = load_entities(cfg)
    topic = topics_by_key(cfg)[str(meta.get("product") or "")]
    entity = entities.get(str(meta.get("city") or ""), {})
    faqs = extract_faq(body_md)
    quotes = [_split_quote_source(q) for q in extract_blockquotes(body_md)]
    sources = extract_sources(body_md)
    h1 = extract_h1(body_md) or meta.get("title") or ""
    bluf, intro = extract_bluf_and_intro(body_md)

    return {
        "vertical": topic["file_key"],
        "verticalLabel": topic.get("title_label") or topic.get("label") or topic["file_key"],
        "type": "city",
        "city": entity.get("name") or meta.get("city") or "",
        "state": entity.get("state") or "",
        "title": meta.get("title") or "",
        "description": meta.get("description") or "",
        "h1": h1,
        "bluf": bluf,
        "intro": intro,
        "keyTakeaways": quotes,
        "faq": [{"q": q, "a": a} for q, a in faqs],
        "sources": sources,
        "serviceKeywords": topic.get("label") or "",
        "datePublished": meta.get("published") or "",
        "dateModified": meta.get("updated") or meta.get("published") or "",
        "draft": False,
    }


def emit_page(cfg: dict, page: dict) -> Path:
    staging = target_root() / str(page["staging"])
    markdown = staging.read_text(encoding="utf-8")
    meta, body_md = parse_frontmatter(markdown)
    fm = build_frontmatter(cfg, meta, body_md)
    body = strip_faq_and_sources(body_md)
    frontmatter_yaml = yaml.safe_dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    rendered = f"---\n{frontmatter_yaml}---\n\n{body}"
    out = target_root() / str(page["output"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    return out


def emit_nextjs_content_batch(cfg: dict, batch: dict) -> None:
    emitted = 0
    for page in batch.get("pages", []):
        if page.get("status") not in {"generated", "regenerated"} or not page.get("staging"):
            continue
        out = emit_page(cfg, page)
        emitted += 1
        print(f"EMITTED={out}")
    print(f"EMIT_COUNT={emitted}")
