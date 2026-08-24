# Operating Modes: Starter to Enterprise

TokenMax is one generation and validation engine with three governance levels. Scale
does not weaken the gates. It adds stronger ownership, evidence, review, and receipt
requirements.

## The full stack

```text
market and source evidence
  -> owner-intent map
  -> one gold-standard owner page
  -> repository scan and site.yaml contract
  -> representative pilot
  -> source + language + originality gates
  -> exact build and rendered-page proof
  -> reviewer receipts
  -> separately approved canary/deployment
  -> live, indexing, search, conversion, and AI-citation measurement
```

The factory owns the middle of that chain. It does not deploy, submit URLs, post to
communities, or convert a successful local build into a claim about public state.

## `program.scale`

| Scale | Best fit | Required control |
|---|---|---|
| `starter` | One operator, local business, focused product, or first pilot | Packet-only facts, one owner per intent, 10-page-or-smaller pilot, human review |
| `growth` | Agency/client program, multi-service site, or repeatable content lane | Audience, conversion goal, evidence owner, success metrics, primary query, route owner |
| `enterprise` | Multi-location, multi-brand, regulated, multilingual, or large editorial program | All growth controls plus named reviewers and authority sources; fleet-level collision and release policy outside this repo |

`starter` is the default for backward compatibility. Selecting `growth` or
`enterprise` without the required contracts makes config loading fail.

Example:

```yaml
program:
  scale: enterprise
  business_model: multi-location-service
  audience: procurement and operations leaders evaluating a regional provider
  conversion_goal: request a location-qualified consultation
  evidence_owner: revenue-operations
  reviewers: [brand, compliance, local-operations]
  success_metrics:
    - qualified organic consultation requests
    - non-branded impressions on approved owner routes
    - citation share on the frozen buyer prompt panel

intent_contract:
  primary_query: regional facilities maintenance provider
  route_owner: /services/facilities-maintenance
```

## Choose the content profile

| Profile | Use it for | Do not use it for |
|---|---|---|
| `local-service-seo` | Real service-area pages with operator expertise and packet-backed local facts | Fake offices or city-swap pages |
| `multi-location-enterprise` | Institutionally reviewed location/service programs | Unowned intents or unverified branch claims |
| `saas-b2b` | Use cases, integrations, comparisons, and solution pages with product evidence | Invented features, ROI, security, or customers |
| `ecommerce-category` | Category and buying decisions with current product evidence | Fake testing, stock, price, ratings, or urgency |
| `regulated-insurance` | California insurance comparison-prep pages under the shipped claim policy | Other jurisdictions or unsupported legal/price claims |

New verticals still need a dedicated prompt profile and prohibited-claim policy. A
generic profile is not a license to improvise domain facts.

## Owner intent before generation

Every candidate cluster receives one action:

- `upgrade`: an existing owner can satisfy it;
- `create`: no owner exists and the page has distinct evidence-backed utility;
- `consolidate`: multiple pages compete for the same decision;
- `hold`: evidence, differentiation, service truth, or review capacity is missing.

The [geo-skills owner-intent prompt](https://github.com/TheSmokeDev/geo-skills/tree/main/prompt-packs/dataforseo-intelligence)
can produce this handoff. Store the approved primary query and canonical route owner
in `intent_contract`.

## Community and Reddit boundary

Community pages are research inputs, not a scalable content loophole. TokenMax may
consume a reviewed brief that summarizes recurring questions and then create one
standalone useful page for a validated intent. It must not mass-produce
`reddit + keyword` pages, copy threads, manufacture quotes, impersonate customers,
post, vote, or treat anecdotes as factual authority.

## Rollout gates by scale

### Starter

1. Prove one owner page.
2. Run no more than a representative 10-page pilot.
3. Validate facts, originality, build, and rendered HTML.
4. Stop at a local handoff.

### Growth

1. Freeze audience, conversion, primary query, and route owner.
2. Prove one gold page and pilot across high-, medium-, and low-data entities.
3. Compare against the existing and sibling corpus.
4. Ship bounded tranches through the target repository's release lane.

### Enterprise

1. Establish a portfolio intent/collision map before any site batch.
2. Version evidence, claims, locale, owners, reviewers, and success metrics.
3. Test edge cases: regulated claims, sparse entities, locale rendering, canonical and
   hreflang behavior, client-only content, and rollback.
4. Require reviewer receipts and a separately approved canary.
5. Use the companion fleet orchestrator for multi-site stage state and freeze policy.

## Receipts

`report` writes both `batch-report.md` and `batch-report.receipts.json`. The JSON
receipt includes:

- factory version, program, and intent contract;
- SHA-256 for resolved config, materialized writer prompt, batch state, validation,
  page source, and emitted output;
- required reviewers with an empty approval ledger for the release lane to fill;
- explicit false values for deployed, live-verified, indexed, ranking, and cited.

Those false values are deliberate. Generation evidence must never be mistaken for
provider or public proof.

## Measurement

Define the measurement plan before writing. Keep sources separate:

- rendered/build quality;
- live deployment and discovery;
- Search Console impressions/clicks/queries;
- analytics conversions;
- AI prompt-panel mentions and citations.

Use 48-hour, 7-day, and 28-day checkpoints only after a verified deployment. A page
that passes TokenMax is locally ready, not automatically public, indexed, ranking, or
cited.
