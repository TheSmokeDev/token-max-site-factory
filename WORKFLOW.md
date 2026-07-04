# token-max-site-factory

**Category:** content generation / programmatic SEO+GEO
**Providers:** codex (default, `modelReasoningEffort: xhigh`); claude by explicit opt-in
**Isolation:** run from the target repo; worktree-friendly; fully resumable from disk state
**Live mutation:** none — generation and validation only

## What it does

Points at any website and expands it into a validated set of token-max
SEO/GEO pages (city × service, product × topic — any entity × topic matrix):

1. **Scan** (manual, GET-only): sitemap + polite crawl + local content →
   cached inventory.
2. **Prepare**: deterministic batch ledger from the entity/topic matrix
   (resume-safe; dedupes against routes the site already has).
3. **Generate**: fresh-context loop, exactly one page per iteration, packet
   JSON as the only fact source.
4. **Validate & regenerate**: word count, structure, FAQ, text-to-HTML,
   prohibited-claim regexes, pairwise + cross-corpus uniqueness (shingle/
   Jaccard ≤ 0.10); held-back pages get targeted rewrite hints until clean or
   retry budget exhausted; a hard gate enforces the result.
5. **Emit**: markdown passthrough, or deterministic HTML render into the
   site's own template (FAQPage/WebPage/Breadcrumb JSON-LD included).
6. **Report**: page-by-page markdown report; explicit "Live mutations: none".

## Install

```bash
python engine/token_max_site_factory.py new-site --site <id> --target-repo <path>
python engine/token_max_site_factory.py scan --site <id> --allow-network
# edit sites/<id>/site.yaml
python engine/token_max_site_factory.py install --site <id>
cd <target-repo> && archon workflow run token-max-site-factory-<id> "pilot-10"
```

## Inputs

`"pilot-10"` · `"pilot-10 --dry-run"` · `"<phase>"` · `"<phase>-tranche-300"` ·
`"--topics a,b --entities x,y --limit 20"` — phases are named presets in the
site config.

## Safety

Default-deny mutation: a preflight node greps the engine for live-mutation
command patterns and asserts the config's `live_mutation.*` flags are all
false; a `.token-max/site.json` marker prevents pointing the wrong config at
the wrong repo. Deploy/DNS/GSC stay separate human-approved lanes.
