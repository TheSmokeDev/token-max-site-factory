"""Validation orchestrator — port of sr22_token_max.py validate() L711-870
and validation_hint() L684-694, with config-driven thresholds/patterns and the
new FAQ gate (disabled with min_faq_questions=0 for legacy parity runs)."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from .. import target_root
from ..emitters.html import parse_frontmatter
from .overlap import corpus_text, cross_corpus_files, jaccard, shingles, strip_utility_sections
from .prohibited import compile_patterns
from .rendered_ratio import text_html_ratio
from .text_quality import faq_question_count, visible_text, word_count


def now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validation_hint(failures: list[dict], prohibited_names: set[str]) -> str:
    kinds = {str(item.get("algo") or "") for item in failures}
    if "normalized_overlap" in kinds or "cross_corpus_overlap" in kinds:
        return "rewrite_sentence_skeletons_structure_examples_and_faqs"
    if "word_count" in kinds:
        return "expand_to_3000_words_with_city_product_specific_sections"
    if "text_html_ratio" in kinds:
        return "reduce_markup_and_lists_expand_plain_text_paragraphs"
    if "faq_questions" in kinds:
        return "add_city_product_specific_faq_questions_40_90_words_each"
    if kinds & {
        "missing_title",
        "missing_description",
        "missing_h1",
        "h1_title_mismatch",
        "duplicate_title",
        "duplicate_description",
    }:
        return "rewrite_unique_title_description_and_matching_h1"
    if "source_links" in kinds:
        return "add_named_packet_authority_source_links_or_remove_unsupported_claims"
    if kinds & prohibited_names:
        return "remove_prohibited_claims_and_replace_with_current_ca_guidance"
    return "fresh_context_full_rewrite_against_packet"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def validate_batch(
    cfg: dict,
    batch_path: Path,
    output_path: Path,
    *,
    min_words: int,
    min_h2: int,
    min_quotes: int,
    min_faq_questions: int,
    min_text_html_ratio: float,
    max_pairwise_overlap: float,
    max_cross_overlap: float,
    cross_corpus_limit: int,
    shingle_size: int,
    mark_held_back: bool,
    no_fail: bool,
) -> None:
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    if batch.get("dry_run"):
        report = {
            "ok": True,
            "dry_run": True,
            "page_count": len(batch.get("pages", [])),
            "failure_count": 0,
            "held_back": [],
            "status_counts": dict(Counter(p.get("status") for p in batch.get("pages", []))),
        }
        write_json(output_path, report)
        print(json.dumps(report, indent=2))
        return

    utility_patterns = list(cfg.get("utility_section_patterns") or [])
    prohibited = compile_patterns(cfg.get("prohibited_patterns") or {})
    prohibited_names = set(prohibited)

    page_failures: dict[str, list[dict]] = {}
    generated_texts: dict[str, str] = {}
    generated_paths: dict[str, Path] = {}
    metadata_records: dict[str, tuple[str, str]] = {}
    page_by_id = {str(page["id"]): page for page in batch.get("pages", [])}

    for page in batch.get("pages", []):
        pid = str(page["id"])
        source_rel = str(page.get("staging") or page["output"])
        path = target_root() / source_rel
        generated_paths[pid] = path
        if not path.exists():
            page_failures.setdefault(pid, []).append({"algo": "missing_file", "message": f"missing {source_rel}"})
            continue
        raw = path.read_text(encoding="utf-8")
        generated_texts[pid] = strip_utility_sections(raw, utility_patterns)
        meta, body = parse_frontmatter(raw)
        title = str(meta.get("title") or "").strip()
        description = str(meta.get("description") or "").strip()
        h1_match = re.search(r"^#\s+(.+?)\s*$", body, re.M)
        h1 = h1_match.group(1).strip() if h1_match else ""
        metadata_records[pid] = (title, description)
        if not title:
            page_failures.setdefault(pid, []).append(
                {"algo": "missing_title", "message": "frontmatter title is missing"}
            )
        if not description:
            page_failures.setdefault(pid, []).append(
                {"algo": "missing_description", "message": "frontmatter description is missing"}
            )
        if not h1:
            page_failures.setdefault(pid, []).append({"algo": "missing_h1", "message": "H1 is missing"})
        elif title and h1.casefold() != title.casefold():
            page_failures.setdefault(pid, []).append(
                {"algo": "h1_title_mismatch", "message": f"H1 {h1!r} does not match title {title!r}"}
            )
        words = word_count(raw)
        if words < min_words:
            page_failures.setdefault(pid, []).append(
                {"algo": "word_count", "message": f"word_count {words} < {min_words}", "word_count": words}
            )
        h2_count = len(re.findall(r"^##\s+", raw, re.M))
        if h2_count < min_h2:
            page_failures.setdefault(pid, []).append(
                {"algo": "section_count", "message": f"H2 count {h2_count} < {min_h2}", "h2_count": h2_count}
            )
        quote_count = len(re.findall(r"^>\s+", raw, re.M))
        if quote_count < min_quotes:
            page_failures.setdefault(pid, []).append(
                {"algo": "ai_citable_passages", "message": f"blockquote count {quote_count} < {min_quotes}"}
            )
        ratio = text_html_ratio(raw)
        if ratio < min_text_html_ratio:
            page_failures.setdefault(pid, []).append(
                {"algo": "text_html_ratio", "message": f"text_to_html_ratio {ratio:.3f} < {min_text_html_ratio}"}
            )
        if min_faq_questions > 0:
            faq_count = faq_question_count(raw)
            if faq_count < min_faq_questions:
                page_failures.setdefault(pid, []).append(
                    {"algo": "faq_questions", "message": f"FAQ question count {faq_count} < {min_faq_questions}"}
                )
        for name, pattern in prohibited.items():
            if pattern.search(raw):
                page_failures.setdefault(pid, []).append({"algo": name, "message": f"{name} pattern matched"})

        min_source_links = int(cfg.get("quality", {}).get("min_source_links") or 0)
        if str((cfg.get("program") or {}).get("scale") or "starter") == "enterprise":
            min_source_links = max(1, min_source_links)
        authority_urls = [
            str(source.get("url") or "")
            for source in cfg.get("authority_sources") or []
            if isinstance(source, dict) and source.get("url")
        ]
        source_link_count = sum(1 for url in authority_urls if url in raw)
        if source_link_count < min_source_links:
            page_failures.setdefault(pid, []).append(
                {
                    "algo": "source_links",
                    "message": f"named authority source links {source_link_count} < {min_source_links}",
                }
            )

    for field_index, algo in ((0, "duplicate_title"), (1, "duplicate_description")):
        groups: dict[str, list[str]] = {}
        for pid, values in metadata_records.items():
            value = values[field_index].casefold().strip()
            if value:
                groups.setdefault(value, []).append(pid)
        for duplicate_ids in groups.values():
            if len(duplicate_ids) < 2:
                continue
            for pid in duplicate_ids:
                others = [other for other in duplicate_ids if other != pid]
                page_failures.setdefault(pid, []).append(
                    {
                        "algo": algo,
                        "message": f"{algo} shared with {', '.join(others)}",
                        "other_pages": others,
                    }
                )

    overlaps: list[dict] = []
    ids = list(generated_texts)
    generated_shingles = {pid: shingles(visible_text(text), shingle_size) for pid, text in generated_texts.items()}
    for i, left in enumerate(ids):
        for right in ids[i + 1 :]:
            score = jaccard(generated_shingles[left], generated_shingles[right])
            if score > max_pairwise_overlap:
                overlaps.append({"left": left, "right": right, "jaccard": round(score, 4)})
                page_failures.setdefault(left, []).append(
                    {
                        "algo": "normalized_overlap",
                        "message": f"overlap {score:.4f} > {max_pairwise_overlap} against {right}",
                        "other_page": right,
                    }
                )
                page_failures.setdefault(right, []).append(
                    {
                        "algo": "normalized_overlap",
                        "message": f"overlap {score:.4f} > {max_pairwise_overlap} against {left}",
                        "other_page": left,
                    }
                )

    cross_overlaps: list[dict] = []
    generated_output_paths = {path.resolve() for path in generated_paths.values()}
    corpus_files = [
        path
        for path in cross_corpus_files(cfg.get("cross_corpus_roots") or [], cfg.get("cross_corpus_glob") or "**/*.md", cross_corpus_limit)
        if path.resolve() not in generated_output_paths
    ]
    for corpus_file in corpus_files:
        try:
            corpus_raw = corpus_text(corpus_file, utility_patterns)
        except UnicodeDecodeError:
            continue
        corpus_set = shingles(visible_text(corpus_raw), shingle_size)
        if not corpus_set:
            continue
        for pid, page_set in generated_shingles.items():
            score = jaccard(page_set, corpus_set)
            if score > max_cross_overlap:
                try:
                    rel = str(corpus_file.relative_to(target_root()))
                except ValueError:
                    rel = str(corpus_file)
                cross_overlaps.append({"page": pid, "other": rel, "jaccard": round(score, 4)})
                page_failures.setdefault(pid, []).append(
                    {
                        "algo": "cross_corpus_overlap",
                        "message": f"overlap {score:.4f} > {max_cross_overlap} against {rel}",
                        "other_page": rel,
                    }
                )

    held_back = []
    for pid, failures in sorted(page_failures.items()):
        page = page_by_id.get(pid, {})
        held_back.append(
            {
                "page": pid,
                "output": page.get("output"),
                "route": page.get("route"),
                "retry_count": int(page.get("retry_count") or 0),
                "failures": failures,
                "regenerate_with": validation_hint(failures, prohibited_names),
            }
        )

    if mark_held_back:
        failed_ids = set(page_failures)
        for page in batch.get("pages", []):
            pid = str(page["id"])
            if pid in failed_ids:
                page["status"] = "held_back"
                page["validation_failures"] = page_failures[pid]
                page["regenerate_with"] = validation_hint(page_failures[pid], prohibited_names)
                page["validation_checked_at"] = now_iso()
            elif page.get("status") in {"generated", "regenerated", "held_back"}:
                if page.get("status") == "held_back":
                    page["status"] = "regenerated" if int(page.get("retry_count") or 0) else "generated"
                page["validation_failures"] = []
                page["regenerate_with"] = ""
                page["validation_passed_at"] = now_iso()
        batch_path.write_text(json.dumps(batch, indent=2) + "\n", encoding="utf-8")

    report = {
        "ok": not held_back,
        "page_count": len(batch.get("pages", [])),
        "failure_count": sum(len(items) for items in page_failures.values()),
        "held_back_count": len(held_back),
        "held_back": held_back[:500],
        "overlap_count": len(overlaps),
        "overlaps": overlaps[:500],
        "cross_corpus_file_count": len(corpus_files),
        "cross_overlap_count": len(cross_overlaps),
        "cross_overlaps": cross_overlaps[:500],
        "status_counts": dict(Counter(page.get("status") for page in batch.get("pages", []))),
    }
    write_json(output_path, report)
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "page_count": report["page_count"],
                "held_back_count": report["held_back_count"],
                "failure_count": report["failure_count"],
                "overlap_count": report["overlap_count"],
                "cross_overlap_count": report["cross_overlap_count"],
                "status_counts": report["status_counts"],
            },
            indent=2,
        )
    )
    if held_back and not no_fail:
        raise SystemExit(1)
