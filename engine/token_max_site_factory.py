#!/usr/bin/env python3
"""token-max-site-factory — universal point-and-shoot content factory CLI.

Generalized port of the SR22 token-max lane. Local-only by design: it never
deploys, submits URLs, changes DNS, or touches Google/Vercel account state.
Run in-workflow commands FROM the target repo root (the Archon worktree);
factory-side commands (new-site, install, scan) can run from anywhere.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tmsf import __version__, factory_path  # noqa: E402
from tmsf import batch as batch_mod  # noqa: E402
from tmsf.config import load_effective_config, load_site_config  # noqa: E402
from tmsf.emitters import emit as emit_mod  # noqa: E402
from tmsf.materialize import materialize  # noqa: E402
from tmsf.preflight import run_preflight  # noqa: E402
from tmsf.report import write_report  # noqa: E402
from tmsf.validators import validate_batch  # noqa: E402


def _cfg(args: argparse.Namespace) -> dict:
    return load_effective_config(args.site)


def _artifacts(cfg: dict) -> Path:
    return Path(cfg["artifacts_dir"])


def _default(value: str | None, fallback: Path) -> Path:
    return Path(value) if value else fallback


def cmd_bootstrap(args: argparse.Namespace) -> None:
    cfg = load_site_config(args.site)
    payload = batch_mod.parse_bootstrap_input(cfg, args.input or "")
    out = _default(args.output, _artifacts(cfg) / "state" / "input.json")
    batch_mod.write_json(out, payload)
    materialized = materialize(cfg)
    print(json.dumps({**payload, "materialized": materialized}, indent=2))


def cmd_preflight(args: argparse.Namespace) -> None:
    cfg = _cfg(args)
    run_preflight(cfg, require_marker=not args.no_marker)


def cmd_prepare(args: argparse.Namespace) -> None:
    cfg = _cfg(args)
    batch_mod.prepare_batch(
        cfg,
        products=args.products,
        limit=args.limit,
        cities=args.cities if args.cities is not None else ",".join(cfg["inventory"].get("pilot_entities") or []),
        phase=args.phase,
        dry_run=args.dry_run,
        output=_default(args.output, _artifacts(cfg) / "state" / "batch.json"),
        resume=args.resume,
        resume_existing_outputs=args.resume_existing_outputs,
        skip_existing_routes=args.skip_existing_routes,
    )


def cmd_prepare_from_input(args: argparse.Namespace) -> None:
    cfg = _cfg(args)
    payload = json.loads(_default(args.input, _artifacts(cfg) / "state" / "input.json").read_text(encoding="utf-8"))
    cities = payload["cities"] if "cities" in payload else ",".join(cfg["inventory"].get("pilot_entities") or [])
    batch_mod.prepare_batch(
        cfg,
        products=payload.get("products") or "",
        limit=int(payload.get("limit") or 45),
        cities=cities,
        phase=payload.get("phase") or "custom",
        dry_run=bool(payload.get("dry_run")),
        output=_default(args.output, _artifacts(cfg) / "state" / "batch.json"),
        resume=bool(args.resume),
        resume_existing_outputs=bool(args.resume_existing_outputs),
        skip_existing_routes=bool(args.skip_existing_routes),
    )


def cmd_next_page(args: argparse.Namespace) -> None:
    cfg = _cfg(args)
    batch_mod.next_page(
        cfg,
        _default(args.batch, _artifacts(cfg) / "state" / "batch.json"),
        args.statuses,
        args.max_retries,
        args.output,
    )


def cmd_packet(args: argparse.Namespace) -> None:
    cfg = _cfg(args)
    batch_mod.packet_by_id(
        cfg,
        _default(args.batch, _artifacts(cfg) / "state" / "batch.json"),
        args.page_id,
        args.output or "",
    )


def cmd_remaining(args: argparse.Namespace) -> None:
    cfg = _cfg(args)
    batch_mod.remaining(
        _default(args.batch, _artifacts(cfg) / "state" / "batch.json"),
        args.statuses,
        args.exit_zero_when_done,
    )


def cmd_pending_ids(args: argparse.Namespace) -> None:
    cfg = _cfg(args)
    batch_mod.pending_ids(
        _default(args.batch, _artifacts(cfg) / "state" / "batch.json"),
        args.statuses,
        args.max_retries,
    )


def cmd_mark_generated(args: argparse.Namespace) -> None:
    cfg = _cfg(args)
    batch_mod.mark_generated(
        _default(args.batch, _artifacts(cfg) / "state" / "batch.json"),
        args.page_id,
        args.status,
    )


def cmd_generate(args: argparse.Namespace) -> None:
    if not args.allow_draft_generator:
        raise SystemExit(
            "Deterministic draft generation is disabled. Use the Archon fresh-context writer loop, "
            "or pass --allow-draft-generator only for local debugging."
        )
    raise SystemExit("Draft generator intentionally not implemented for this lane.")


def cmd_validate(args: argparse.Namespace) -> None:
    cfg = _cfg(args)
    quality = cfg["quality"]

    def pick(cli_value, key):
        return cli_value if cli_value is not None else quality[key]

    validate_batch(
        cfg,
        _default(args.batch, _artifacts(cfg) / "state" / "batch.json"),
        _default(args.output, _artifacts(cfg) / "reports" / "validation.json"),
        min_words=pick(args.min_words, "hard_min_words"),
        min_h2=pick(args.min_h2, "min_h2"),
        min_quotes=pick(args.min_quotes, "min_ai_citable_passages"),
        min_faq_questions=pick(args.min_faq_questions, "min_faq_questions"),
        min_text_html_ratio=pick(args.min_text_html_ratio, "min_text_html_ratio"),
        max_pairwise_overlap=pick(args.max_pairwise_overlap, "max_pairwise_overlap"),
        max_cross_overlap=pick(args.max_cross_overlap, "max_cross_overlap"),
        cross_corpus_limit=args.cross_corpus_limit,
        shingle_size=pick(args.shingle_size, "shingle_size"),
        mark_held_back=args.mark_held_back,
        no_fail=args.no_fail,
    )


def cmd_validation_ok(args: argparse.Namespace) -> None:
    cfg = _cfg(args)
    path = _default(args.report, _artifacts(cfg) / "reports" / "validation.json")
    if not path.exists():
        print("VALIDATION_REPORT_MISSING")
        raise SystemExit(1)
    payload = json.loads(path.read_text(encoding="utf-8"))
    ok = bool(payload.get("ok"))
    print("VALIDATION_OK" if ok else "VALIDATION_NOT_OK")
    raise SystemExit(0 if ok else 1)


def cmd_emit(args: argparse.Namespace) -> None:
    cfg = _cfg(args)
    emit_mod(cfg, _default(args.batch, _artifacts(cfg) / "state" / "batch.json"))


def cmd_report(args: argparse.Namespace) -> None:
    cfg = _cfg(args)
    write_report(
        cfg,
        _default(args.batch, _artifacts(cfg) / "state" / "batch.json"),
        _default(args.validation, _artifacts(cfg) / "reports" / "validation.json"),
        _default(args.output, _artifacts(cfg) / "reports" / "batch-report.md"),
    )


def cmd_new_site(args: argparse.Namespace) -> None:
    from tmsf.install import scaffold_site

    scaffold_site(args.site, args.target_repo)


def cmd_install(args: argparse.Namespace) -> None:
    from tmsf.install import install_site

    install_site(args.site, workflow_name=args.workflow_name, allow_claude=args.allow_claude, run_input=args.run_input)


def cmd_scan(args: argparse.Namespace) -> None:
    from tmsf.scan import run_scan

    run_scan(args.site, allow_network=args.allow_network)


def cmd_scan_local_content(args: argparse.Namespace) -> None:
    from tmsf.scan import scan_local_only

    scan_local_only(args.site)


def cmd_diff_live_preview(args: argparse.Namespace) -> None:
    raise SystemExit("diff-live-preview is not implemented in v1 (needs rendered-DOM tooling).")


def main() -> None:
    parser = argparse.ArgumentParser(prog="token_max_site_factory", description=__doc__)
    parser.add_argument("--version", action="version", version=f"token-max-site-factory {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add(name, func, **kwargs):
        p = sub.add_parser(name, **kwargs)
        p.add_argument("--site", required=True, help="site id under sites/")
        p.set_defaults(func=func)
        return p

    p = add("bootstrap", cmd_bootstrap)
    p.add_argument("--input", default="")
    p.add_argument("--output", default="")

    p = add("preflight", cmd_preflight)
    p.add_argument("--no-live-mutation", action="store_true", help="(implied; kept for workflow readability)")
    p.add_argument("--no-marker", action="store_true", help="skip the .token-max/sites/<id>.json marker check")

    p = add("prepare", cmd_prepare)
    p.add_argument("--products", default=None)
    p.add_argument("--limit", type=int, default=45)
    p.add_argument("--cities", default=None)
    p.add_argument("--phase", default="custom")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--output", default="")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--resume-existing-outputs", action="store_true")
    p.add_argument("--skip-existing-routes", action="store_true")

    p = add("prepare-from-input", cmd_prepare_from_input)
    p.add_argument("--input", default="")
    p.add_argument("--output", default="")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--resume-existing-outputs", action="store_true")
    p.add_argument("--skip-existing-routes", action="store_true")

    p = add("next-page", cmd_next_page)
    p.add_argument("--batch", default="")
    p.add_argument("--statuses", default="pending_generation")
    p.add_argument("--max-retries", type=int, default=3)
    p.add_argument("--output", default="")

    p = add("packet", cmd_packet)
    p.add_argument("--batch", default="")
    p.add_argument("--page-id", required=True)
    p.add_argument("--output")

    p = add("remaining", cmd_remaining)
    p.add_argument("--batch", default="")
    p.add_argument("--statuses", default="pending_generation")
    p.add_argument("--exit-zero-when-done", action="store_true")

    p = add("pending-ids", cmd_pending_ids)
    p.add_argument("--batch", default="")
    p.add_argument("--statuses", default="pending_generation")
    p.add_argument("--max-retries", type=int, default=3)

    p = add("mark-generated", cmd_mark_generated)
    p.add_argument("--batch", default="")
    p.add_argument("--page-id", required=True)
    p.add_argument("--status", choices=["generated", "regenerated"], default="generated")

    p = add("generate", cmd_generate)
    p.add_argument("--batch", default="")
    p.add_argument("--allow-draft-generator", action="store_true")

    p = add("validate", cmd_validate)
    p.add_argument("--batch", default="")
    p.add_argument("--output", default="")
    p.add_argument("--min-words", type=int, default=None)
    p.add_argument("--min-h2", type=int, default=None)
    p.add_argument("--min-quotes", type=int, default=None)
    p.add_argument("--min-faq-questions", type=int, default=None)
    p.add_argument("--min-text-html-ratio", type=float, default=None)
    p.add_argument("--max-pairwise-overlap", type=float, default=None)
    p.add_argument("--max-cross-overlap", type=float, default=None)
    p.add_argument("--cross-corpus-limit", type=int, default=0)
    p.add_argument("--shingle-size", type=int, default=None)
    p.add_argument("--mark-held-back", action="store_true")
    p.add_argument("--no-fail", action="store_true")

    p = add("validation-ok", cmd_validation_ok)
    p.add_argument("--report", default="")

    p = add("emit", cmd_emit)
    p.add_argument("--batch", default="")

    p = add("report", cmd_report)
    p.add_argument("--batch", default="")
    p.add_argument("--validation", default="")
    p.add_argument("--output", default="")

    p = add("new-site", cmd_new_site)
    p.add_argument("--target-repo", required=True)

    p = add("install", cmd_install)
    p.add_argument("--workflow-name", default="")
    p.add_argument("--allow-claude", action="store_true")
    p.add_argument("--run-input", default="", help="baked workflow input (0.5.0 bash nodes do not receive USER_MESSAGE)")

    p = add("scan", cmd_scan)
    p.add_argument("--allow-network", action="store_true")

    add("scan-local-content", cmd_scan_local_content)
    add("diff-live-preview", cmd_diff_live_preview)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
