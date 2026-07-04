import pytest

from tmsf.adapters import load_entities
from tmsf.matrix import build_pages, entity_order, resolve_topics


def test_entity_order_pilot_first_then_population(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entities = load_entities(site_cfg)
    order = entity_order(site_cfg, entities, [])
    assert order == ["btown", "ctown", "atown"]  # pilot first, then population desc


def test_entity_order_requested_and_unknown(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entities = load_entities(site_cfg)
    assert entity_order(site_cfg, entities, ["ctown"]) == ["ctown"]
    with pytest.raises(SystemExit, match="Unknown entity"):
        entity_order(site_cfg, entities, ["nope"])


def test_resolve_topics_aliases_and_unknown(site_cfg):
    assert resolve_topics(site_cfg, "alfa/beta") == ["alpha", "beta"]
    assert resolve_topics(site_cfg, None) == ["alpha", "beta"]
    assert resolve_topics(site_cfg, "all") == ["alpha", "beta"]
    with pytest.raises(SystemExit, match="Unknown topic"):
        resolve_topics(site_cfg, "gamma")


def test_build_pages_limit_and_skip_routes(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entities = load_entities(site_cfg)
    pages = build_pages(site_cfg, entities, ["atown", "btown"], ["alpha", "beta"], limit=3)
    assert len(pages) == 3
    assert pages[0]["id"] == "atown-alpha-en"
    assert pages[0]["output"] == "content/atown/alpha.md"
    assert pages[0]["route"] == "/atown/alpha-service"
    skipped = build_pages(site_cfg, entities, ["atown"], ["alpha", "beta"], limit=10,
                          skip_routes={"/atown/alpha-service"})
    assert [p["id"] for p in skipped] == ["atown-beta-en"]
