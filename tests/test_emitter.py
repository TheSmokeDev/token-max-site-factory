import json

from tmsf.emitters.html import build_jsonld, extract_faq, markdown_body_to_html, parse_frontmatter

SAMPLE = """---
title: "Accident Claim Help in Fresno, California | Acme Claims Co"
description: "Fresno claim guide."
locale: "en"
---

# Accident Claim Help in Fresno, California | Acme Claims Co

An answer-first opening paragraph with **bold** and a [link](/resources).

## How the process works

Body paragraph one.
Continued on the next line.

> A standalone citable answer about Fresno claims.

- first item
- second item

## Frequently asked questions

### Do I need a police report in Fresno?

Yes, a report helps document the crash facts.

### How long do I have to file?

California deadlines vary by claim type.
"""


def test_frontmatter_and_body_split():
    meta, body = parse_frontmatter(SAMPLE)
    assert meta["title"].startswith("Accident Claim Help in Fresno")
    assert body.lstrip().startswith("# Accident Claim Help")


def test_markdown_rendering():
    _, body = parse_frontmatter(SAMPLE)
    html = markdown_body_to_html(body)
    assert "<h1>Accident Claim Help in Fresno" in html
    assert "<h2>How the process works</h2>" in html
    assert "<strong>bold</strong>" in html
    assert '<a href="/resources">link</a>' in html
    assert "<blockquote><p>A standalone citable answer" in html
    assert "<li>first item</li>" in html
    assert "<p>Body paragraph one. Continued on the next line.</p>" in html


def test_faq_extraction_and_jsonld():
    _, body = parse_frontmatter(SAMPLE)
    faqs = extract_faq(body)
    assert len(faqs) == 2
    assert faqs[0][0] == "Do I need a police report in Fresno?"
    cfg = {"canonical_host": "https://www.example.com"}
    jsonld = build_jsonld(cfg, "T", "D", "https://www.example.com/ca/fresno/x", faqs)
    payload = json.loads(jsonld)
    types = [node["@type"] for node in payload["@graph"]]
    assert "FAQPage" in types and "BreadcrumbList" in types and "WebPage" in types


def test_html_escaping_in_inline():
    html = markdown_body_to_html("a paragraph with <script> and & chars")
    assert "<script>" not in html
    assert "&amp;" in html
