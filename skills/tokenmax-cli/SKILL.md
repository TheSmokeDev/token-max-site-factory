---
name: tokenmax-cli
description: Agent-native command surface for the TokenMax programmatic SEO/GEO page factory. Use when an operator or coding agent needs to run tokenmax doctor, list configured sites, validate a GEO owner-intent handoff, scaffold or scan a site, prepare and resume a bounded batch, enforce deterministic quality gates, emit supported formats, or create provenance receipts without deploying or mutating provider state.
---

# TokenMax CLI

Use the installed `tokenmax` command instead of invoking `engine/token_max_site_factory.py` directly.

## Inspect First

```bash
tokenmax doctor --json
tokenmax list-sites --json
tokenmax owner-map --input owner-intent-map.json --json
```

An invalid owner map blocks generation. Resolve ambiguous ownership or missing
evidence instead of bypassing the gate.

## Local Workflow

```bash
tokenmax new-site --site <id> --target-repo <path>
tokenmax scan --site <id> --allow-network
tokenmax install --site <id> --run-input pilot-10
```

Run generation commands from the target repository/worktree. Start with one gold
page and a representative pilot. Review validation and receipt artifacts before a
separate release lane.

## Rules

- Treat the packet as the only page-specific fact source.
- Keep generation, deployment, indexing, rankings, and citations as separate states.
- Do not enable deploy, DNS, Search Console, or indexing flags in this factory.
- Do not expand a failed pilot or invalid owner map.
- Use JSON diagnostic commands for agent decisions and preserve nonzero exits.
- Never treat a local validation receipt as public or provider proof.
