"""Deterministic staging-markdown -> full HTML emitter.

The writer produces validated markdown at page.staging; this emitter renders
it into the site's hand-authored template (page.output). No model involvement,
no external markdown lib — a bounded subset: h1-h3, paragraphs, blockquotes,
unordered lists, links, bold/italic. The emitted head carries rel=canonical,
which makes the site's own head-baking tooling (canonical-skipping head bakers)
skip these pages — coexistence by idempotency."""

from __future__ import annotations

import html as html_lib
import json
import re
from pathlib import Path

from .. import target_root


def parse_frontmatter(markdown: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n?", markdown, re.S)
    if not match:
        return {}, markdown
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        kv = re.match(r"^(\w+):\s*[\"']?(.*?)[\"']?\s*$", line)
        if kv:
            meta[kv.group(1)] = kv.group(2)
    return meta, markdown[match.end():]


def _inline(text: str) -> str:
    text = html_lib.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def markdown_body_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    quote_lines: list[str] = []

    def flush_paragraph():
        if paragraph:
            out.append(f"      <p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list():
        if list_items:
            out.append("      <ul>")
            out.extend(f"        <li>{_inline(item)}</li>" for item in list_items)
            out.append("      </ul>")
            list_items.clear()

    def flush_quote():
        if quote_lines:
            out.append(f"      <blockquote><p>{_inline(' '.join(quote_lines))}</p></blockquote>")
            quote_lines.clear()

    def flush_all():
        flush_paragraph()
        flush_list()
        flush_quote()

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_all()
        elif stripped.startswith("### "):
            flush_all()
            out.append(f"      <h3>{_inline(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            flush_all()
            out.append(f"      <h2>{_inline(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            flush_all()
            out.append(f"      <h1>{_inline(stripped[2:])}</h1>")
        elif stripped.startswith("> "):
            flush_paragraph()
            flush_list()
            quote_lines.append(stripped[2:])
        elif re.match(r"^[-*]\s+", stripped):
            flush_paragraph()
            flush_quote()
            list_items.append(re.sub(r"^[-*]\s+", "", stripped))
        else:
            flush_list()
            flush_quote()
            paragraph.append(stripped)
    flush_all()
    return "\n".join(out)


def extract_faq(markdown: str) -> list[tuple[str, str]]:
    match = re.search(r"^##\s+.*(frequently asked|faq).*$", markdown, re.I | re.M)
    if not match:
        return []
    section = markdown[match.end():]
    next_h2 = re.search(r"^##\s+", section, re.M)
    if next_h2:
        section = section[: next_h2.start()]
    faqs: list[tuple[str, str]] = []
    parts = re.split(r"^###\s+", section, flags=re.M)
    for part in parts[1:]:
        lines = part.splitlines()
        question = lines[0].strip()
        answer = " ".join(l.strip() for l in lines[1:] if l.strip() and not l.strip().startswith(("#", ">", "-")))
        if question and answer:
            faqs.append((question, answer))
    return faqs


def build_jsonld(cfg: dict, title: str, description: str, canonical: str, faqs: list[tuple[str, str]]) -> str:
    host = str(cfg["canonical_host"]).rstrip("/")
    graph: list[dict] = [
        {
            "@type": "WebPage",
            "@id": f"{canonical}#webpage",
            "url": canonical,
            "name": title,
            "description": description,
            "inLanguage": "en-US",
            "isPartOf": {"@id": f"{host}/#website"},
        },
        {
            "@type": "BreadcrumbList",
            "@id": f"{canonical}#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{host}/"},
                {"@type": "ListItem", "position": 2, "name": title, "item": canonical},
            ],
        },
    ]
    if faqs:
        graph.append(
            {
                "@type": "FAQPage",
                "@id": f"{canonical}#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a},
                    }
                    for q, a in faqs
                ],
            }
        )
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


def emit_page(cfg: dict, page: dict, template: str) -> Path:
    staging = target_root() / str(page["staging"])
    markdown = staging.read_text(encoding="utf-8")
    meta, body_md = parse_frontmatter(markdown)
    title = meta.get("title") or str(page.get("id"))
    description = meta.get("description") or ""
    canonical = str(cfg["canonical_host"]).rstrip("/") + str(page["route"])
    faqs = extract_faq(body_md)
    rendered = (
        template.replace("{{LANG}}", meta.get("locale") or "en")
        .replace("{{TITLE}}", html_lib.escape(title))
        .replace("{{META_DESCRIPTION}}", html_lib.escape(description))
        .replace("{{CANONICAL}}", canonical)
        .replace("{{JSONLD}}", build_jsonld(cfg, title, description, canonical, faqs))
        .replace("{{BODY_HTML}}", markdown_body_to_html(body_md))
    )
    out = target_root() / str(page["output"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    return out


def emit_html_batch(cfg: dict, batch: dict) -> None:
    template_path = target_root() / str(cfg["html_template"])
    if not template_path.exists():
        raise SystemExit(f"html_template not found in target repo: {template_path}")
    template = template_path.read_text(encoding="utf-8")
    emitted = 0
    for page in batch.get("pages", []):
        if page.get("status") not in {"generated", "regenerated"} or not page.get("staging"):
            continue
        out = emit_page(cfg, page, template)
        emitted += 1
        print(f"EMITTED={out}")
    print(f"EMIT_COUNT={emitted}")
