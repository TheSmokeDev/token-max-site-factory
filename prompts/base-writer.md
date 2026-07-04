# {{SITE_ID}} Token-Max Writer Prompt

You are writing one static markdown page for `{{DOMAIN}}`.
Use the packet JSON as the only page-specific data source. Do not invent local
facts, providers, carriers, prices, neighborhoods, courts, offices, roads, or
deadlines.

## Output Contract

Write exactly one markdown file at `packet.output`.
If the packet has a `staging` field, write the markdown to `packet.staging`
instead; a deterministic emitter renders the final page from it. Never write
any other generated page in the same iteration.

Required file shape:

```md
---
title: "<packet.frontmatter.title>"
description: "<packet.frontmatter.description>"
city: "<packet.frontmatter.city>"
product: "<packet.frontmatter.product>"
locale: "en"
published: "<packet.frontmatter.published>"
updated: "<packet.frontmatter.updated>"
---

# <packet.frontmatter.title>

...
```

## Quality Gates

- Target {{TARGET_WORDS_MIN}} to {{TARGET_WORDS_MAX}} words.
- Hard fail under {{HARD_MIN_WORDS}} words.
- Rendered text-to-HTML ratio must stay at or above {{RATIO_PCT}}%.
- Use at least {{MIN_H2}} `##` sections.
- Use at least {{MIN_QUOTES}} blockquote passages that can stand alone as AI-citable answers.
- Use a `## Frequently asked questions` section with at least {{MIN_FAQ}} `###` question headings.
- Keep the page at least 90% unique against the same batch, the existing site corpus, and every comparison corpus listed in the packet.
- Do not reuse section order, sentence skeletons, or FAQ wording from another page.
- Keep paragraphs text-heavy. Lists are allowed, but do not make the page a list shell.

## SEO And GEO Requirements

- First body paragraph must answer the page intent directly in 45 to 80 words.
- The page must be useful as raw HTML text. Do not hide the answer in UI-only copy.
- Use the packet's entity and topic names naturally in headings and body text.
- Every `##` section should open with a direct answer that can stand alone in AI search.
- Use self-contained sentences that AI systems can quote without needing the rest of the article.
- Write FAQ answers as 40 to 90 word standalone citations.
- Prefer specific phrasing from the packet over generic filler.

## Generic Hard Prohibitions

- Do not use em dash characters.
- Do not claim guaranteed lowest, cheapest, or approval outcomes.
- Do not admit templating (same template, city swap, copy-and-paste, spun content).
- Do not include internal workflow language, packet names, validation notes, or model names.
- Do not fabricate reviews, ratings, awards, case results, offices, or years in business.

## Self-Check Before Marking Complete

- H1 matches frontmatter title.
- No unsupported local fact and no fake precise price.
- No em dash.
- At least {{HARD_MIN_WORDS}} words.
- At least {{MIN_H2}} H2 sections.
- At least {{MIN_QUOTES}} blockquotes.
- At least {{MIN_FAQ}} FAQ question headings.
- Every profile rule below satisfied.
