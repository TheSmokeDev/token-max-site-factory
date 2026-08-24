import json
from pathlib import Path

import pytest

from conftest import make_page
from tmsf.validators import validate_batch
from tmsf.validators.text_quality import faq_question_count


GATES = dict(
    min_words=50,
    min_h2=8,
    min_quotes=4,
    min_faq_questions=5,
    min_text_html_ratio=0.15,
    max_pairwise_overlap=0.10,
    max_cross_overlap=0.10,
    cross_corpus_limit=0,
    shingle_size=9,
    mark_held_back=False,
    no_fail=True,
)


def run_validate(site_cfg, tmp_path, pages: dict[str, str], gates=None):
    batch = {
        "kind": "test",
        "dry_run": False,
        "pages": [
            {"id": pid, "status": "generated", "output": f"content/{pid}.md", "route": f"/{pid}"}
            for pid in pages
        ],
    }
    for pid, text in pages.items():
        out = tmp_path / "content" / f"{pid}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps(batch), encoding="utf-8")
    report_path = tmp_path / "validation.json"
    validate_batch(site_cfg, batch_path, report_path, **{**GATES, **(gates or {})})
    return json.loads(report_path.read_text(encoding="utf-8"))


def failures_for(report, pid):
    for item in report["held_back"]:
        if item["page"] == pid:
            return {f["algo"] for f in item["failures"]}
    return set()


def test_clean_page_passes(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report = run_validate(site_cfg, tmp_path, {"good": make_page(words=80)})
    assert report["ok"] is True and report["held_back_count"] == 0


def test_each_gate_fails_independently(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report = run_validate(
        site_cfg,
        tmp_path,
        {
            "short": make_page(words=10, seed="short"),
            "fewh2": make_page(words=300, h2=3, seed="fewh2"),
            "noquotes": make_page(words=300, quotes=1, seed="noquotes"),
            "nofaq": make_page(words=300, faqs=2, seed="nofaq"),
            "banned": make_page(words=300, seed="banned", extra="the xyzzy word appears here\n"),
            "emdash": make_page(words=300, seed="emdash", extra="an em—dash sneaks in\n"),
        },
        gates={"min_words": 200},
    )
    assert "word_count" in failures_for(report, "short")
    assert "section_count" in failures_for(report, "fewh2")
    assert "ai_citable_passages" in failures_for(report, "noquotes")
    assert "faq_questions" in failures_for(report, "nofaq")
    assert "forbidden_word" in failures_for(report, "banned")
    assert "em_dash" in failures_for(report, "emdash")


def test_faq_gate_disabled_with_zero(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report = run_validate(site_cfg, tmp_path, {"nofaq": make_page(words=80, faqs=0, seed="nofaq")},
                          gates={"min_faq_questions": 0})
    assert "faq_questions" not in failures_for(report, "nofaq")


def test_metadata_and_h1_gates(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    page = make_page(words=80, seed="metadata")
    page = page.replace('description: "Description metadata"\n', "")
    page = page.replace("# T metadata", "# A different H1")
    report = run_validate(site_cfg, tmp_path, {"metadata": page})
    assert "missing_description" in failures_for(report, "metadata")
    assert "h1_title_mismatch" in failures_for(report, "metadata")


def test_duplicate_title_and_description_gates(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = make_page(words=80, seed="first")
    second = make_page(words=80, seed="second")
    second = second.replace('title: "T second"', 'title: "T first"')
    second = second.replace('description: "Description second"', 'description: "Description first"')
    second = second.replace("# T second", "# T first")
    report = run_validate(site_cfg, tmp_path, {"first": first, "second": second})
    assert "duplicate_title" in failures_for(report, "first")
    assert "duplicate_description" in failures_for(report, "second")


def test_enterprise_pages_require_named_authority_source_link(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source_url = "https://example.com/research"
    site_cfg["program"]["scale"] = "enterprise"
    site_cfg["authority_sources"] = [{"label": "Research", "url": source_url}]

    missing = run_validate(site_cfg, tmp_path, {"missing": make_page(words=80, seed="missing-source")})
    assert "source_links" in failures_for(missing, "missing")

    present = run_validate(
        site_cfg,
        tmp_path,
        {"present": make_page(words=80, seed="present-source", extra=f"[Research]({source_url})\n")},
    )
    assert "source_links" not in failures_for(present, "present")


def test_pairwise_overlap_flags_near_duplicates(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    same = make_page(words=120, seed="same")
    report = run_validate(site_cfg, tmp_path, {"copy1": same, "copy2": same + "\nextra line.\n"})
    assert report["overlap_count"] >= 1
    assert "normalized_overlap" in failures_for(report, "copy1")


def test_cross_corpus_overlap_including_html(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    page = make_page(words=120, seed="corpus")
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    body_html = "<html><body>" + "".join(
        f"<p>{line}</p>" for line in page.splitlines() if line and not line.startswith(("#", "-", ">"))
    ) + "</body></html>"
    (corpus_dir / "existing.html").write_text(body_html, encoding="utf-8")
    report = run_validate(site_cfg, tmp_path, {"newpage": page})
    assert report["cross_overlap_count"] >= 1
    assert "cross_corpus_overlap" in failures_for(report, "newpage")


def test_missing_file_and_mark_held_back(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    batch = {
        "kind": "test",
        "dry_run": False,
        "pages": [{"id": "ghost", "status": "generated", "output": "content/ghost.md", "route": "/ghost"}],
    }
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps(batch), encoding="utf-8")
    validate_batch(site_cfg, batch_path, tmp_path / "v.json", **{**GATES, "mark_held_back": True})
    updated = json.loads(batch_path.read_text(encoding="utf-8"))
    assert updated["pages"][0]["status"] == "held_back"
    assert updated["pages"][0]["validation_failures"][0]["algo"] == "missing_file"


def test_mark_held_back_restores_a_stale_status_after_the_page_passes(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "content/page.md"
    output.parent.mkdir(parents=True)
    output.write_text(make_page(words=80), encoding="utf-8")
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(
        json.dumps(
            {
                "kind": "test",
                "dry_run": False,
                "pages": [
                    {
                        "id": "page",
                        "status": "held_back",
                        "output": "content/page.md",
                        "route": "/page",
                        "retry_count": 0,
                        "validation_failures": [{"algo": "old_failure"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    validate_batch(site_cfg, batch_path, tmp_path / "v.json", **{**GATES, "mark_held_back": True})

    updated = json.loads(batch_path.read_text(encoding="utf-8"))
    assert updated["pages"][0]["status"] == "generated"
    assert updated["pages"][0]["validation_failures"] == []


def test_faq_count_fallback_without_faq_h2():
    doc = "# T\n\n## A\n\n### Is this a question?\n\ntext\n\n### Not a question\n"
    assert faq_question_count(doc) == 1
    doc_with_h2 = "# T\n\n## Frequently asked questions\n\n### Q1?\n\n### Q2?\n\n## Next\n\n### Q3?\n"
    assert faq_question_count(doc_with_h2) == 2
