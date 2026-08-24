"""Site config loading, validation, defaults, and resolved snapshots.

One YAML per target site at sites/<site_id>/site.yaml in the factory repo.
`bootstrap` materializes a resolved snapshot into the run's artifacts dir so
in-flight runs are immune to config edits and never cross-read the factory
repo mid-run.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from . import FACTORY_ROOT, factory_path

# Quality defaults = the proven SR22 values (North Star spec).
DEFAULT_QUALITY = {
    "target_words_min": 2800,
    "target_words_max": 3400,
    "hard_min_words": 2700,
    "min_h2": 8,
    "min_faq_questions": 5,
    "min_ai_citable_passages": 4,
    "min_source_links": 0,
    "min_text_html_ratio": 0.15,
    "max_pairwise_overlap": 0.10,
    "max_cross_overlap": 0.10,
    "shingle_size": 9,
    "max_retries": 3,
}

DEFAULT_CRAWL = {
    "max_pages": 200,
    "delay_seconds": 1.0,
    "timeout_seconds": 15,
}

DEFAULT_LIVE_MUTATION = {
    "allow_deploy": False,
    "allow_dns": False,
    "allow_gsc": False,
    "allow_indexing": False,
}

DEFAULT_PROGRAM = {
    "scale": "starter",
    "business_model": "local-service",
    "audience": "",
    "conversion_goal": "",
    "evidence_owner": "",
    "reviewers": [],
    "success_metrics": [],
}

PROGRAM_SCALES = {"starter", "growth", "enterprise"}
PROGRAM_KEYS = set(DEFAULT_PROGRAM)

ALLOWED_TOP_KEYS = {
    "site_id",
    "domain",
    "canonical_host",
    "target_repo_root",
    "page_format",
    "output_template",
    "route_template",
    "staging_template",
    "html_template",
    "build_verify_command",
    "locales",
    "provider",
    "model_reasoning_effort",
    "artifacts_dir",
    "batch_kind",
    "inventory",
    "phases",
    "default_phase",
    "frontmatter",
    "prompt_profile",
    "claim_rules_md",
    "authority_sources",
    "quality",
    "prohibited_patterns",
    "utility_section_patterns",
    "cross_corpus_roots",
    "cross_corpus_glob",
    "live_mutation",
    "writer_contract",
    "comparison_corpus",
    "intent_contract",
    "program",
}

REQUIRED_TOP_KEYS = {
    "site_id",
    "domain",
    "canonical_host",
    "target_repo_root",
    "output_template",
    "route_template",
    "artifacts_dir",
    "inventory",
}

TOPIC_REQUIRED = {"key", "file_key", "route_segment", "label", "title_label"}

# Packet-visible topic fields, in the legacy PRODUCT_CONFIG order.
TOPIC_PACKET_FIELDS = [
    "file_key",
    "route_segment",
    "label",
    "title_label",
    "intent",
    "primary_decision",
    "must_answer",
]


class ConfigError(SystemExit):
    def __init__(self, message: str) -> None:
        super().__init__(f"site-config error: {message}")


def sites_dir() -> Path:
    return factory_path("sites")


def site_config_path(site_id: str) -> Path:
    return sites_dir() / site_id / "site.yaml"


def _validate(cfg: dict, source: str) -> None:
    unknown = set(cfg) - ALLOWED_TOP_KEYS
    if unknown:
        raise ConfigError(f"unknown top-level key(s) in {source}: {', '.join(sorted(unknown))}")
    missing = REQUIRED_TOP_KEYS - set(cfg)
    if missing:
        raise ConfigError(f"missing required key(s) in {source}: {', '.join(sorted(missing))}")
    if cfg.get("page_format") not in (None, "markdown", "html", "nextjs_content"):
        raise ConfigError(f"page_format must be 'markdown', 'html', or 'nextjs_content' in {source}")
    topics = (cfg.get("inventory") or {}).get("topics") or []
    if not topics:
        raise ConfigError(f"inventory.topics must list at least one topic in {source}")
    for topic in topics:
        missing_fields = TOPIC_REQUIRED - set(topic)
        if missing_fields:
            raise ConfigError(
                f"topic {topic.get('key', '?')!r} missing field(s) {', '.join(sorted(missing_fields))} in {source}"
            )
    for name, value in (cfg.get("prohibited_patterns") or {}).items():
        try:
            re.compile(str(value))
        except re.error as exc:
            raise ConfigError(f"prohibited_patterns.{name} is not a valid regex in {source}: {exc}")
    if cfg.get("intent_contract") is not None and not isinstance(cfg["intent_contract"], dict):
        raise ConfigError(f"intent_contract must be a mapping in {source}")
    if cfg.get("authority_sources") is not None and not isinstance(cfg["authority_sources"], list):
        raise ConfigError(f"authority_sources must be a list in {source}")
    program = cfg.get("program")
    scale = "starter"
    if program is not None:
        if not isinstance(program, dict):
            raise ConfigError(f"program must be a mapping in {source}")
        unknown_program = set(program) - PROGRAM_KEYS
        if unknown_program:
            raise ConfigError(
                f"unknown program key(s) in {source}: {', '.join(sorted(unknown_program))}"
            )
        scale = str(program.get("scale") or "starter")
        if scale not in PROGRAM_SCALES:
            raise ConfigError(
                f"program.scale must be one of {', '.join(sorted(PROGRAM_SCALES))} in {source}"
            )
        for key in ("reviewers", "success_metrics"):
            if key in program and not isinstance(program[key], list):
                raise ConfigError(f"program.{key} must be a list in {source}")
        if scale in {"growth", "enterprise"}:
            intent = cfg.get("intent_contract") or {}
            required_program = ("business_model", "audience", "conversion_goal", "evidence_owner")
            missing_program = [key for key in required_program if not str(program.get(key) or "").strip()]
            if missing_program:
                raise ConfigError(
                    f"program.scale {scale} requires program fields "
                    f"{', '.join(missing_program)} in {source}"
                )
            missing_intent = [key for key in ("primary_query", "route_owner") if not str(intent.get(key) or "").strip()]
            if missing_intent:
                raise ConfigError(
                    f"program.scale {scale} requires intent_contract fields "
                    f"{', '.join(missing_intent)} in {source}"
                )
            if not program.get("success_metrics"):
                raise ConfigError(f"program.scale {scale} requires program.success_metrics in {source}")
            if any(not str(metric or "").strip() for metric in program.get("success_metrics") or []):
                raise ConfigError(f"program.success_metrics cannot contain blank values in {source}")
        if scale == "enterprise":
            if not program.get("reviewers"):
                raise ConfigError(f"program.scale enterprise requires program.reviewers in {source}")
            authority_sources = cfg.get("authority_sources") or []
            if not authority_sources:
                raise ConfigError(f"program.scale enterprise requires authority_sources in {source}")
            if any(
                not isinstance(item, dict)
                or not str(item.get("label") or "").strip()
                or not str(item.get("url") or "").strip()
                for item in authority_sources
            ):
                raise ConfigError(
                    f"enterprise authority_sources require nonblank label and url fields in {source}"
                )
    if cfg.get("prompt_profile") == "multi-location-enterprise" and scale != "enterprise":
        raise ConfigError(
            f"prompt_profile multi-location-enterprise requires program.scale enterprise in {source}"
        )
    if cfg.get("page_format") == "html" and not cfg.get("html_template"):
        raise ConfigError(f"page_format html requires html_template in {source}")
    if cfg.get("page_format") == "nextjs_content" and not cfg.get("staging_template"):
        raise ConfigError(f"page_format nextjs_content requires staging_template in {source}")


def _apply_defaults(cfg: dict) -> dict:
    cfg.setdefault("page_format", "markdown")
    cfg.setdefault("locales", ["en"])
    cfg.setdefault("provider", "codex")
    cfg.setdefault("model_reasoning_effort", "xhigh")
    cfg.setdefault("batch_kind", f"{cfg['site_id']}-token-max")
    cfg.setdefault("phases", {})
    cfg.setdefault("default_phase", "pilot")
    cfg.setdefault("frontmatter", {})
    cfg.setdefault("prompt_profile", "local-service-seo")
    cfg.setdefault("claim_rules_md", "")
    cfg.setdefault("authority_sources", [])
    cfg.setdefault("prohibited_patterns", {})
    cfg.setdefault("utility_section_patterns", [])
    cfg.setdefault("cross_corpus_roots", [])
    cfg.setdefault("cross_corpus_glob", "**/*.md")
    cfg.setdefault("writer_contract", {})
    cfg.setdefault("comparison_corpus", {})
    cfg.setdefault("intent_contract", {})
    cfg.setdefault("staging_template", "")
    cfg.setdefault("html_template", "")
    cfg.setdefault("build_verify_command", "")

    program = dict(DEFAULT_PROGRAM)
    program.update(cfg.get("program") or {})
    program["reviewers"] = list(program.get("reviewers") or [])
    program["success_metrics"] = list(program.get("success_metrics") or [])
    cfg["program"] = program

    quality = dict(DEFAULT_QUALITY)
    quality.update(cfg.get("quality") or {})
    cfg["quality"] = quality

    live = dict(DEFAULT_LIVE_MUTATION)
    live.update(cfg.get("live_mutation") or {})
    cfg["live_mutation"] = live

    inventory = cfg["inventory"]
    inventory.setdefault("pilot_entities", [])
    inventory.setdefault("sitemap_url", "")
    inventory.setdefault("facts_files", [])
    crawl = dict(DEFAULT_CRAWL)
    crawl.update(inventory.get("crawl") or {})
    inventory["crawl"] = crawl

    fm = cfg["frontmatter"]
    fm.setdefault("title_template", "{topic_title_label} in {entity_name}")
    fm.setdefault("description_template", "{entity_name} {topic_label} guide.")
    fm.setdefault("published", "")
    fm.setdefault("updated", "")
    return cfg


def load_site_config(site_id: str) -> dict:
    path = site_config_path(site_id)
    if not path.exists():
        raise ConfigError(f"no site config at {path}")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if cfg.get("site_id") != site_id:
        raise ConfigError(f"site_id mismatch: {path} declares {cfg.get('site_id')!r}, expected {site_id!r}")
    _validate(cfg, str(path))
    return _apply_defaults(cfg)


def resolved_snapshot_path(artifacts_dir: str | Path) -> Path:
    return Path(artifacts_dir) / "state" / "site-config.resolved.json"


def write_resolved_snapshot(cfg: dict) -> Path:
    path = resolved_snapshot_path(cfg["artifacts_dir"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def load_effective_config(site_id: str) -> dict:
    """Prefer the run's resolved snapshot (written by bootstrap) so in-flight
    runs are immune to factory-side config edits; fall back to the factory
    config for pre-bootstrap commands (scan, install, new-site, parity)."""
    try:
        factory_cfg = load_site_config(site_id)
    except ConfigError:
        factory_cfg = None
    if factory_cfg is not None:
        snapshot = resolved_snapshot_path(factory_cfg["artifacts_dir"])
        if snapshot.exists():
            return json.loads(snapshot.read_text(encoding="utf-8"))
        return factory_cfg
    raise ConfigError(f"unknown site {site_id!r}")


def topics_by_key(cfg: dict) -> dict[str, dict]:
    return {str(t["key"]): t for t in cfg["inventory"]["topics"]}


def topic_aliases(cfg: dict) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for topic in cfg["inventory"]["topics"]:
        key = str(topic["key"])
        for alias in topic.get("aliases") or []:
            aliases[str(alias).strip().lower()] = key
    return aliases


def topic_packet_config(topic: dict) -> dict:
    return {name: topic[name] for name in TOPIC_PACKET_FIELDS if name in topic}
