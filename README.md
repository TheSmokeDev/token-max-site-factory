# token-max-site-factory

[![CI](https://github.com/TheSmokeDev/token-max-site-factory/actions/workflows/ci.yml/badge.svg)](https://github.com/TheSmokeDev/token-max-site-factory/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/TheSmokeDev/token-max-site-factory?include_prereleases&sort=semver)](https://github.com/TheSmokeDev/token-max-site-factory/releases/tag/v0.6.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-f06424.svg)](LICENSE)

Universal, point-and-shoot [Archon](https://archon.diy) content factory. Point
it at any website: **scan** the existing site, build an inventory, then
**expand** it into hundreds of token-max SEO/GEO pages — with quantified
quality gates extracted from a production insurance lane and preserved in a
deterministic public test suite.

> If these gates save you from shipping thin or fabricated programmatic pages,
> star the repo so other builders can find the factory.

> **Status: v0.6 beta.** The engine is usable and tested, but APIs may still
> move. This repository proves generation contracts and local validation. It
> does not publish private performance data or turn a local pass into a claim
> about deployment, indexation, rankings, conversions, or AI citations.

**The factory never deploys.** No DNS, no Search Console, no sitemap
submission, no indexing requests, no live account mutation. Generation ends at
a clean validation report; shipping is a separate, human-approved lane. A
preflight node greps the engine for live-mutation command patterns on every
run and refuses to proceed if any appear.

Companion skills in the [geo-skills pack](https://github.com/TheSmokeDev/geo-skills):

- `token-max-factory` operates one scan/generation/validation lane.
- `tokenmax-fleet-orchestrator` sequences many sites through consumer-owned
  build, deploy, live-proof, and indexing-queue adapters with resumable state
  and production freeze gates.

## Why this exists

Programmatic pages fail two ways: thin duplicate content Google ignores, or
hallucinated "local facts" that poison trust. The factory attacks both with a
hard quality contract and a packet system where **the packet is the only fact
source** — the writer never invents a price, office, or statistic.

## Starter to enterprise

The same engine supports three governance modes through `program.scale`:

| Scale | Intended use | Additional contract |
|---|---|---|
| `starter` | One operator, local business, focused product, first pilot | Owner intent, packet facts, bounded pilot, human review |
| `growth` | Agency/client program or repeatable multi-service lane | Audience, conversion goal, evidence owner, success metrics, primary query, route owner |
| `enterprise` | Multi-location, multi-brand, regulated, or multilingual program | All growth fields plus named reviewers and authority sources |

Read [Operating Modes: Starter to Enterprise](docs/OPERATING-MODES.md) for the
full evidence -> owner map -> gold page -> pilot -> gates -> reviewer -> canary ->
measurement stack. More pages are not the enterprise feature. Governance,
collision control, provenance, and proof are.

## Quality contract (per page, defaults)

| Gate | Default |
|---|---|
| Words | 2,800–3,400 target, hard fail < 2,700 |
| Uniqueness | pairwise + cross-corpus shingle/Jaccard ≤ 0.10 (90%+ unique) |
| Structure | ≥ 8 H2 sections, ≥ 4 AI-citable blockquotes, ≥ 5 FAQ questions |
| Text-to-HTML | ≥ 0.15 |
| Titles/meta | present and unique per page; H1 must match title |
| Facts | packet = the only fact source; prohibited-claim regexes per vertical |
| Ownership | growth/enterprise require primary query + canonical route owner |
| Governance | enterprise requires evidence owner, reviewers, metrics, sources, and a named source link per page |
| Receipts | SHA-256 config/prompt/batch/validation/page manifest; public states default false |

## Prerequisites

- [Archon CLI](https://archon.diy/getting-started/installation/) **>= 0.5.0**
  (free, MIT) — `curl -fsSL https://archon.diy/install | bash` or
  `irm https://archon.diy/install.ps1 | iex`
- A coding agent Archon can drive. Default writer is **codex** at `xhigh`
  reasoning (ChatGPT subscription); **claude** works via explicit
  `install --allow-claude` (Claude subscription). The provider is a per-site
  config knob — no SEO APIs, no paid data vendors, nothing else to buy.
- Python 3.10+ with PyYAML.

## Point-and-shoot: onboarding a site

Install the verified release wheel:

```bash
pip install https://github.com/TheSmokeDev/token-max-site-factory/releases/download/v0.6.0/token_max_site_factory-0.6.0-py3-none-any.whl
tokenmax doctor --json
```

For development from a clone:

```bash
git clone https://github.com/TheSmokeDev/token-max-site-factory
cd token-max-site-factory
python -m pip install -e ".[dev]"

# Verify the command surface and configured sites
tokenmax doctor --json
tokenmax list-sites --json

# Validate the GEO research handoff before generation
tokenmax owner-map --input owner-intent-map.json --json

# 1. Scaffold a config
tokenmax new-site --site mysite --target-repo /path/to/site-repo

# 2. Scan the live site (sitemap + polite crawl) and the local repo — the ONLY
#    network step, always manual:
tokenmax scan --site mysite --allow-network

# 3. Edit sites/mysite/site.yaml: topics (the page matrix), entities source
#    (CSV/JSON/TS), output/route templates, prompt profile, claim rules,
#    cross-corpus roots, phases. Start from sites/example/site.yaml.

# 4. Install the workflow shim into the target repo
tokenmax install --site mysite --run-input "pilot-10"

# 5. Run — always FROM the target repo (worktree isolation keys off it)
cd /path/to/site-repo
archon workflow run token-max-site-factory-mysite --no-worktree

# 6. Review the worktree diff + the report at <artifacts>/reports/batch-report.md
#    Merge, then deploy through YOUR normal lane. The factory is done.
```

The legacy `python engine/token_max_site_factory.py ...` form remains supported for
existing workflows.

The packaged command surface follows the agent-native principles demonstrated by
[CLI-Anything](https://github.com/HKUDS/CLI-Anything): self-describing help,
machine-readable diagnostics, installed-command tests, and authentic backend
integration. TokenMax keeps its own fail-closed state and approval contracts.

Pilot before tranche, always: prove 10–25 pages pass every gate before
scaling. Keep tranches ≤ 300 pages (pairwise overlap is O(n²)).

A starter entity dataset ships in the example site: 472 California cities
(name/slug/county/region/population/zip/area-code) at
`sites/example/facts/ca-cities.csv`.

## Architecture

- `engine/token_max_site_factory.py` — CLI (see `--help`); state on disk;
  every run resumable (`--resume --resume-existing-outputs`).
- `engine/tmsf/` — config (per-site YAML → resolved snapshot at bootstrap),
  adapters (ts_array, static_list, sitemap, crawler, local_content),
  validators (word/H2/quotes/FAQ/ratio/prohibited/overlap), emitters
  (markdown passthrough, deterministic HTML, Next.js content), preflight
  (live-mutation guard + site marker), install (workflow shim renderer).
- `prompts/base-writer.md` + `prompts/profiles/*` — the writer contract;
  bootstrap materializes base + profile + site claim rules into the run's
  artifacts dir (no cross-repo reads mid-run).
- `workflow-templates/token-max-site-factory.yaml.tmpl` — the proven DAG:
  bootstrap → no-live-mutation preflight → prepare (resume-safe ledger) →
  fresh-context generate loop (one page per iteration, `until_bash` ledger
  check) → validate/regenerate loop → hard gate → emit → report.
- `sites/<site_id>/site.yaml` — one config per target site; `inventory.json`
  is the cached scan; `facts/` holds entity CSVs.
- `.token-max/sites/<site_id>.json` — per-site target marker, allowing one
  monorepo to host multiple factory lanes without marker collisions. Legacy
  `.token-max/site.json` markers remain readable.
- `marketplace/` — the Archon marketplace package
  (`archon workflow install token-max-site-factory`).

Shipped prompt profiles: `local-service-seo`, `multi-location-enterprise`,
`saas-b2b`, `ecommerce-category`, and `regulated-insurance`. New verticals need
their own profile and prohibited-claim policy.

The report step writes a human report and a machine receipt. The receipt hashes the
resolved config, materialized prompt, batch, validation, page sources, and emitted
outputs, and explicitly records deployment/indexing/ranking/citation as false until a
separate release or measurement lane proves them.

### HTML sites

Set `page_format: html`, a `staging_template` (writer produces markdown
there), and an `html_template` (a hand-authored page shell in the TARGET repo
with `{{TITLE}} {{META_DESCRIPTION}} {{CANONICAL}} {{JSONLD}} {{BODY_HTML}}
{{LANG}}` slots). Validation runs on the staging markdown; the `emit` step
deterministically renders final HTML with FAQPage/WebPage/Breadcrumb JSON-LD.
Emitted heads carry `rel=canonical`, so canonical-skipping head-bakers leave
factory pages alone.

## Running on Archon 0.5.0 — gotchas worth knowing

1. **Run input is baked at install time** (`install --run-input "..."`).
   0.5.0 bash nodes do not receive `USER_MESSAGE` (regression; fixed on the
   Archon dev branch). To change what a run does, re-run `install` with a new
   `--run-input`. Grammar: `pilot-10`, `<phase>`, `<phase>-tranche-300`,
   `--topics a,b --entities x,y --limit 20`, `--dry-run`.
2. **Never put dollar-sign shell variables in workflow YAML** — 0.5.0 blanks
   every one in inline node scripts. On-disk scripts (`engine/tmsf.sh`) are
   safe. The template is already dollar-free; keep it that way.
3. **Archon's bash may be WSL bash** — the template's if/else picks the
   Windows vs `/mnt/c/...` path form automatically.
4. **Prefer `--detach` for long runs** — survives the launching shell; track
   progress via the batch ledger, not the console.
5. **Stale "running" rows block relaunch** ("Workflow already active on this
   path"): `archon workflow status` → `archon workflow abandon <run-id>`
   (DB-only; safe when the process is dead).
6. **`until_bash` exit-1 "error" log lines during loops are normal** — that's
   the "not done yet" signal; the loop is fine.

## Troubleshooting

- **Resume after interruption:** just re-run the workflow with the same
  input; `prepare --resume --resume-existing-outputs` folds in everything on
  disk. Never delete `<artifacts>/state/batch.json`.
- **Held-back pages loop forever:** each page has a retry budget
  (`quality.max_retries`, default 3); the hard `enforce-validation-gate`
  fails the run if quality can't be met — read
  `<artifacts>/reports/validation.json` `held_back[].failures`.
- **`PREFLIGHT_FAIL: missing marker`:** run `install --site <id>` in the
  target repo first (or the run is in the wrong repo for that config).

## Provenance

Extracted and generalized from a production insurance programmatic-content lane.
The public repository carries the reusable engine, tests, policies, and receipts;
it intentionally does not publish stale or private traffic/citation claims. The port
was parity-tested against the original bootstrap, prepare, packet, resume, and
validator contracts before the current portable layers were added.

## License

MIT — built by [SmokeDev](https://github.com/TheSmokeDev).
If the factory supports published work, use GitHub's **Cite this repository** control
backed by [CITATION.cff](CITATION.cff).
