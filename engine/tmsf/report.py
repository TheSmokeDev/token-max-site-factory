"""Human batch report plus machine-readable provenance receipts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import __version__, target_root


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _target_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else target_root() / path


def _page_receipt(page: dict) -> dict:
    source_rel = str(page.get("staging") or page.get("output") or "")
    output_rel = str(page.get("output") or "")
    source_path = _target_path(source_rel)
    output_path = _target_path(output_rel)
    return {
        "page_id": page.get("id"),
        "route": page.get("route"),
        "locale": page.get("locale"),
        "status": page.get("status"),
        "source_path": source_rel,
        "source_sha256": _sha256(source_path),
        "output_path": output_rel,
        "output_sha256": _sha256(output_path),
        "validation_passed_at": page.get("validation_passed_at"),
    }


def _receipt_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}.receipts.json")


def write_report(cfg: dict, batch_path: Path, validation_path: Path, output_path: Path) -> None:
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8")) if validation_path.exists() else {}
    artifact_root = _target_path(str(cfg["artifacts_dir"]))
    resolved_config = artifact_root / "state" / "site-config.resolved.json"
    writer_prompt = artifact_root / "context" / "writer-prompt.md"
    program = cfg.get("program") or {}
    intent = cfg.get("intent_contract") or {}
    receipt_path = _receipt_path(output_path)

    receipt = {
        "schema_version": 1,
        "factory_version": __version__,
        "site_id": cfg["site_id"],
        "domain": cfg["domain"],
        "program": program,
        "intent_contract": intent,
        "batch": {
            "phase": batch.get("phase", "custom"),
            "generated_at": batch.get("generated_at"),
            "page_count": len(batch.get("pages", [])),
            "validation_ok": validation.get("ok"),
        },
        "artifact_hashes": {
            "resolved_config_sha256": _sha256(resolved_config),
            "writer_prompt_sha256": _sha256(writer_prompt),
            "batch_sha256": _sha256(batch_path),
            "validation_sha256": _sha256(validation_path),
        },
        "pages": [_page_receipt(page) for page in batch.get("pages", [])],
        "review": {
            "required_reviewers": list(program.get("reviewers") or []),
            "reviewer_receipts": [],
            "approved": False,
        },
        "external_state": {
            "production_deployed": False,
            "live_verified": False,
            "indexing_verified": False,
            "ranking_verified": False,
            "citation_verified": False,
        },
    }

    lines = [
        f"# {cfg['site_id']} Token-Max Batch Report",
        "",
        f"- Factory version: `{__version__}`",
        f"- Program scale: `{program.get('scale', 'starter')}`",
        f"- Business model: `{program.get('business_model', 'not specified')}`",
        f"- Route owner: `{intent.get('route_owner') or 'not specified'}`",
        f"- Evidence owner: `{program.get('evidence_owner') or 'not specified'}`",
        f"- Phase: `{batch.get('phase', 'custom')}`",
        f"- Products: `{', '.join(batch.get('products', []))}`",
        f"- Pages: `{len(batch.get('pages', []))}`",
        f"- Resumed existing output files: `{batch.get('resumed_existing_output_count', 0)}`",
        f"- Validation OK: `{validation.get('ok')}`",
        f"- Held back: `{validation.get('held_back_count')}`",
        f"- Cross-corpus files checked: `{validation.get('cross_corpus_file_count')}`",
        f"- Page format: `{cfg.get('page_format')}`",
        "- Live mutations: `none`",
        "- Production deployed: `false`",
        "- Indexing/ranking/citation verified: `false`",
        f"- Machine receipt: `{receipt_path}`",
        "",
        "## Pages",
        "",
    ]
    for page in batch.get("pages", []):
        page_receipt = _page_receipt(page)
        lines.append(
            f"- `{page['route']}` -> `{page['output']}` "
            f"({page.get('word_count', 'n/a')} words, {page.get('status')}, "
            f"sha256 `{page_receipt['output_sha256'] or 'missing'}`)"
        )
    if validation.get("held_back"):
        lines.extend(["", "## Held Back", ""])
        for item in validation["held_back"]:
            lines.append(f"- `{item['page']}`: `{item['regenerate_with']}`")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"REPORT={output_path}")
    print(f"RECEIPTS={receipt_path}")
