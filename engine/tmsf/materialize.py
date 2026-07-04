"""Bootstrap materialization — snapshot the resolved config and render the
writer prompt (base + profile + site claim rules) into the run's artifacts
dir. After bootstrap, no node or writer iteration reads the factory repo."""

from __future__ import annotations

from pathlib import Path

from . import factory_path
from .config import write_resolved_snapshot


def prompt_tokens(cfg: dict) -> dict[str, str]:
    quality = cfg["quality"]
    return {
        "{{SITE_ID}}": str(cfg["site_id"]),
        "{{DOMAIN}}": str(cfg["domain"]),
        "{{TARGET_WORDS_MIN}}": f"{quality['target_words_min']:,}",
        "{{TARGET_WORDS_MAX}}": f"{quality['target_words_max']:,}",
        "{{HARD_MIN_WORDS}}": f"{quality['hard_min_words']:,}",
        "{{RATIO_PCT}}": str(int(round(quality["min_text_html_ratio"] * 100))),
        "{{MIN_H2}}": str(quality["min_h2"]),
        "{{MIN_QUOTES}}": str(quality["min_ai_citable_passages"]),
        "{{MIN_FAQ}}": str(quality["min_faq_questions"]),
    }


def materialize_writer_prompt(cfg: dict) -> Path:
    base = factory_path("prompts/base-writer.md").read_text(encoding="utf-8")
    for token, value in prompt_tokens(cfg).items():
        base = base.replace(token, value)

    parts = [base.rstrip()]
    profile_name = str(cfg.get("prompt_profile") or "")
    if profile_name:
        profile_path = factory_path(f"prompts/profiles/{profile_name}.md")
        if not profile_path.exists():
            raise SystemExit(f"prompt profile not found: {profile_path}")
        parts.append(profile_path.read_text(encoding="utf-8").rstrip())
    claim_rules = str(cfg.get("claim_rules_md") or "").strip()
    if claim_rules:
        parts.append("# Site-Specific Claim Rules\n\n" + claim_rules)

    out = Path(cfg["artifacts_dir"]) / "context" / "writer-prompt.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    return out


def materialize(cfg: dict) -> dict[str, str]:
    snapshot = write_resolved_snapshot(cfg)
    prompt = materialize_writer_prompt(cfg)
    return {"resolved_config": str(snapshot), "writer_prompt": str(prompt)}
