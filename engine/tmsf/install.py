"""Site scaffolding + target-repo installation.

`new-site` writes an annotated sites/<id>/site.yaml starter.
`install` stamps the thin workflow shim into the TARGET repo's
.archon/workflows/, writes the .token-max/site.json marker, and gitignores
the artifacts dir — after which `archon workflow run` from the target repo is
the whole point-and-shoot story."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import FACTORY_ROOT, factory_path
from .config import load_site_config

SITE_TEMPLATE = """\
site_id: {site_id}
domain: {site_id}.example.com
canonical_host: https://{site_id}.example.com
target_repo_root: {target_repo}

page_format: markdown              # markdown | html (html needs html_template)
output_template: "content/{{entity}}/{{topic_file_key}}.md"   # target-repo-relative
route_template: "/{{entity}}/{{topic_route_segment}}"
artifacts_dir: .token-max-artifacts/{site_id}/pilot

inventory:
  entities:
    adapter: static_list           # static_list (csv/json) | ts_array
    path: sites/{site_id}/facts/entities.csv
  topics:
    - key: example-topic
      file_key: example-topic
      route_segment: example-topic
      label: example topic
      title_label: Example Topic
      intent: what visitor need this page answers
      primary_decision: the single decision the page should enable
      must_answer:
        - first question the page must answer
  pilot_entities: []
  sitemap_url: ""                  # for `scan --allow-network`

phases:
  pilot: {{ topics: "example-topic", entities: pilot, limit: 10 }}

frontmatter:
  title_template: "{{topic_title_label}} in {{entity_name}}"
  description_template: "{{entity_name}} {{topic_label}} guide."
  published: ""
  updated: ""

prompt_profile: local-service-seo
authority_sources: []
prohibited_patterns: {{}}
utility_section_patterns: []
cross_corpus_roots: []
comparison_corpus: {{}}
writer_contract:
  must_include: []
  must_not_include: []
live_mutation:
  allow_deploy: false
  allow_dns: false
  allow_gsc: false
  allow_indexing: false
"""


def scaffold_site(site_id: str, target_repo: str) -> None:
    site_dir = factory_path(f"sites/{site_id}")
    config_path = site_dir / "site.yaml"
    if config_path.exists():
        raise SystemExit(f"site config already exists: {config_path}")
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "facts").mkdir(exist_ok=True)
    config_path.write_text(
        SITE_TEMPLATE.format(site_id=site_id, target_repo=str(Path(target_repo).resolve()).replace("\\", "/")),
        encoding="utf-8",
    )
    print(f"SCAFFOLDED={config_path}")
    print("Next: edit the config, run `scan --site ... --allow-network` (optional), then `install --site ...`.")


def install_site(site_id: str, *, workflow_name: str = "", allow_claude: bool = False, run_input: str = "") -> None:
    cfg = load_site_config(site_id)
    if str(cfg.get("provider")) == "claude" and not allow_claude:
        raise SystemExit(
            "site config sets provider: claude — Codex xhigh is the factory default; "
            "re-run install with --allow-claude to explicitly approve the Claude provider"
        )
    target = Path(str(cfg["target_repo_root"]))
    if not (target / ".git").exists():
        raise SystemExit(f"target_repo_root is not a git repo: {target}")

    name = workflow_name or f"token-max-site-factory-{site_id}"
    template = factory_path("workflow-templates/token-max-site-factory.yaml.tmpl").read_text(encoding="utf-8")
    factory_root = str(FACTORY_ROOT).replace("\\", "/")
    factory_root_wsl = _wsl_path(factory_root)
    max_iterations = _max_iterations(cfg)
    baked_input = run_input or str(cfg.get("default_phase") or "pilot")
    if '"' in baked_input:
        raise SystemExit("--run-input must not contain double quotes")
    rendered = (
        template.replace("{{WORKFLOW_NAME}}", name)
        .replace("{{RUN_INPUT}}", baked_input)
        .replace("{{FACTORY_ROOT_WSL}}", factory_root_wsl)
        .replace("{{SITE_ID}}", str(cfg["site_id"]))
        .replace("{{FACTORY_ROOT}}", factory_root)
        .replace("{{ARTIFACTS_DIR}}", str(cfg["artifacts_dir"]).replace("\\", "/"))
        .replace("{{PROVIDER}}", str(cfg["provider"]))
        .replace("{{REASONING}}", str(cfg["model_reasoning_effort"]))
        .replace("{{MAX_ITERATIONS}}", str(max_iterations))
        .replace("{{DOMAIN}}", str(cfg["domain"]))
        .replace("{{HARD_MIN_WORDS}}", str(cfg["quality"]["hard_min_words"]))
        .replace("{{BUILD_VERIFY_COMMAND}}", str(cfg.get("build_verify_command") or "true"))
    )

    workflows_dir = target / ".archon" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    workflow_path = workflows_dir / f"{name}.yaml"
    workflow_path.write_text(rendered, encoding="utf-8")

    marker_dir = target / ".token-max"
    marker_dir.mkdir(exist_ok=True)
    marker = {
        "site_id": site_id,
        "factory_root": factory_root,
        "workflow": name,
        "installed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    (marker_dir / "site.json").write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")

    _ensure_gitignore(target, ".token-max-artifacts/")
    print(f"INSTALLED_WORKFLOW={workflow_path}")
    print(f"MARKER={marker_dir / 'site.json'}")
    print(f"BAKED_RUN_INPUT={baked_input}")
    print(f"RUN: cd {target} && archon workflow run {name}")


def _wsl_path(windows_path: str) -> str:
    """C:/Users/x -> /mnt/c/Users/x (Archon's bash node may resolve WSL bash,
    where Windows-style absolute paths do not exist)."""
    if len(windows_path) > 2 and windows_path[1] == ":":
        return f"/mnt/{windows_path[0].lower()}{windows_path[2:]}"
    return windows_path


def _max_iterations(cfg: dict) -> int:
    limits = [int(p.get("limit") or 0) for p in (cfg.get("phases") or {}).values()]
    biggest = max(limits or [100])
    return max(200, biggest + 200)


def _ensure_gitignore(target: Path, entry: str) -> None:
    gitignore = target / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if entry not in existing.splitlines():
        gitignore.write_text(existing.rstrip("\n") + ("\n" if existing else "") + entry + "\n", encoding="utf-8")
