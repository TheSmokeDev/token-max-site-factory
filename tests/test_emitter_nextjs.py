import yaml

from tmsf.emitters.nextjs_content import (
    emit_page,
    extract_blockquotes,
    extract_bluf_and_intro,
    extract_h1,
    extract_sources,
    strip_faq_and_sources,
)

STAGING = """---
title: "Local SEO Services in Btown, Bcounty | AcmeCo"
description: "Btown local SEO guide."
city: btown
product: alpha
locale: en
published: 2026-07-03
updated: 2026-07-03
---

# Stop losing customers to page two.

**Local SEO services for a Btown small business typically run $300 to $1,500 a month** and cover Google Business Profile management, citations, and review response.

Most owners never see the difference between "SEO" and "GBP management" spelled out until it costs them a lead.

## What local SEO services actually include

Btown body paragraph.

> [BLS, 43-6013](https://www.bls.gov/oes/current/oes436013.htm) A standalone citable answer about Btown local SEO scope.

## Frequently asked questions

### How much do local SEO services cost in Btown?

Typically $300 to $1,500 a month depending on competition and scope.

### Do you guarantee rankings?

No reputable vendor can guarantee a specific ranking position.

## Sources

- [BLS, 43-6013](https://www.bls.gov/oes/current/oes436013.htm)
"""


def test_extract_h1():
    assert extract_h1(STAGING) == "Stop losing customers to page two."


def test_extract_bluf_and_intro():
    bluf, intro = extract_bluf_and_intro(STAGING)
    assert bluf.startswith("Local SEO services for a Btown small business")
    assert intro.startswith('Most owners never see the difference')


def test_extract_blockquotes_splits_source():
    quotes = extract_blockquotes(STAGING)
    assert len(quotes) == 1
    assert "A standalone citable answer about Btown" in quotes[0]


def test_extract_sources():
    sources = extract_sources(STAGING)
    assert sources == [{"label": "BLS, 43-6013", "url": "https://www.bls.gov/oes/current/oes436013.htm"}]


def test_strip_faq_and_sources_removes_both_sections():
    body = strip_faq_and_sources(STAGING)
    assert "Frequently asked questions" not in body
    assert "## Sources" not in body
    assert "What local SEO services actually include" in body


def test_emit_page_produces_spoke_compatible_frontmatter(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    staging_path = tmp_path / "staging.md"
    staging_path.write_text(STAGING, encoding="utf-8")
    page = {
        "staging": "staging.md",
        "output": "content/ai-receptionist/alpha/btown.md",
        "status": "generated",
    }

    out = emit_page(site_cfg, page)
    rendered = out.read_text(encoding="utf-8")

    assert rendered.startswith("---\n")
    fm_text, body = rendered.split("---\n", 2)[1:]
    fm = yaml.safe_load(fm_text)

    # Matches site/lib/spoke.ts SpokeMeta's required shape.
    for key in (
        "vertical", "verticalLabel", "type", "city", "state", "title", "description",
        "h1", "bluf", "intro", "keyTakeaways", "faq", "sources", "serviceKeywords",
        "datePublished", "dateModified", "draft",
    ):
        assert key in fm, f"missing spoke.ts field: {key}"

    assert fm["vertical"] == "alpha"
    assert fm["type"] == "city"
    assert fm["city"] == "Btown"
    assert fm["state"] == ""  # fixture entities.csv has no state column (uses county)
    assert fm["draft"] is False
    assert len(fm["faq"]) == 2
    assert fm["faq"][0]["q"].startswith("How much do local SEO services cost")
    assert len(fm["keyTakeaways"]) == 1
    assert fm["keyTakeaways"][0]["sourceUrl"] == "https://www.bls.gov/oes/current/oes436013.htm"
    assert len(fm["sources"]) == 1
    assert "Frequently asked questions" not in body
    assert "What local SEO services actually include" in body
