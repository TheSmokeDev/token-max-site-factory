import sys
from pathlib import Path

import pytest

FACTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FACTORY / "engine"))

from tmsf.config import _apply_defaults  # noqa: E402


@pytest.fixture
def site_cfg(tmp_path):
    """Minimal valid config dict (defaults applied) for a synthetic site,
    with artifacts under tmp_path."""
    cfg = {
        "site_id": "testsite",
        "domain": "testsite.example.com",
        "canonical_host": "https://testsite.example.com",
        "target_repo_root": str(tmp_path),
        "output_template": "content/{entity}/{topic_file_key}.md",
        "route_template": "/{entity}/{topic_route_segment}",
        "artifacts_dir": str(tmp_path / "artifacts"),
        "inventory": {
            "entities": {"adapter": "static_list", "path": str(tmp_path / "entities.csv")},
            "topics": [
                {
                    "key": "alpha",
                    "aliases": ["alfa"],
                    "file_key": "alpha",
                    "route_segment": "alpha-service",
                    "label": "alpha service",
                    "title_label": "Alpha Service",
                    "intent": "test intent",
                    "primary_decision": "test decision",
                    "must_answer": ["q1"],
                },
                {
                    "key": "beta",
                    "file_key": "beta",
                    "route_segment": "beta-service",
                    "label": "beta service",
                    "title_label": "Beta Service",
                },
            ],
            "pilot_entities": ["btown"],
        },
        "prohibited_patterns": {"forbidden_word": r"\bxyzzy\b"},
        "utility_section_patterns": [r"##\s+Sources[\s\S]*?(?=\n## |\Z)"],
        "cross_corpus_roots": [str(tmp_path / "corpus")],
        "cross_corpus_glob": "**/*.*",
    }
    (tmp_path / "entities.csv").write_text(
        "name,slug,county,population\n"
        "Atown,atown,Acounty,50000\n"
        "Btown,btown,Bcounty,1000\n"
        "Ctown,ctown,Ccounty,90000\n",
        encoding="utf-8",
    )
    return _apply_defaults(cfg)


def make_page(words: int = 60, h2: int = 8, quotes: int = 4, faqs: int = 5, extra: str = "", seed: str = "unique") -> str:
    """Build a markdown page that passes gates at the given knobs (word target
    is scaled: tests use min_words=50 for speed)."""
    body = []
    body.append(f'---\ntitle: "T {seed}"\ndescription: "Description {seed}"\n---\n')
    body.append(f"# T {seed}\n")
    per_section = max(1, words // max(1, h2))
    for i in range(h2):
        body.append(f"## Section {seed} {i}\n")
        body.append(" ".join(f"{seed}{i}word{j}" for j in range(per_section)) + ".\n")
    for i in range(quotes):
        body.append(f"> Standalone {seed} citable answer number {i}.\n")
    if faqs:
        body.append("## Frequently asked questions\n")
        for i in range(faqs):
            body.append(f"### Question {seed} {i}?\n")
            body.append(f"Answer {seed} {i} text.\n")
    body.append(extra)
    return "\n".join(body)
