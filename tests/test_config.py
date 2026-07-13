import pytest

from tmsf.config import ConfigError, _apply_defaults, _validate, load_site_config, topic_aliases


def test_example_reference_config_loads():
    cfg = load_site_config("example")
    assert cfg["batch_kind"] == "example-token-max"
    assert cfg["quality"]["hard_min_words"] == 2700
    assert len(cfg["inventory"]["topics"]) == 1
    assert cfg["live_mutation"]["allow_deploy"] is False


def test_unknown_top_level_key_rejected(site_cfg):
    bad = dict(site_cfg)
    bad["deploy_target"] = "vercel"
    with pytest.raises(SystemExit, match="unknown top-level key"):
        _validate(bad, "test")


def test_intent_contract_accepted(site_cfg):
    cfg = dict(site_cfg)
    cfg["intent_contract"] = {
        "primary_query": "military car insurance california",
        "route_owner": "/en/military-auto-insurance",
    }
    _validate(cfg, "test")


def test_intent_contract_must_be_mapping(site_cfg):
    bad = dict(site_cfg)
    bad["intent_contract"] = "military car insurance california"
    with pytest.raises(SystemExit, match="intent_contract must be a mapping"):
        _validate(bad, "test")


def test_missing_topic_field_rejected(site_cfg):
    bad = dict(site_cfg)
    bad["inventory"] = {"topics": [{"key": "x"}]}
    with pytest.raises(SystemExit, match="missing field"):
        _validate(bad, "test")


def test_html_requires_template(site_cfg):
    bad = dict(site_cfg)
    bad["page_format"] = "html"
    bad["html_template"] = ""
    with pytest.raises(SystemExit, match="html_template"):
        _validate(bad, "test")


def test_nextjs_content_requires_staging_template(site_cfg):
    bad = dict(site_cfg)
    bad["page_format"] = "nextjs_content"
    with pytest.raises(SystemExit, match="staging_template"):
        _validate(bad, "test")


def test_nextjs_content_accepted_page_format(site_cfg):
    ok = dict(site_cfg)
    ok["page_format"] = "nextjs_content"
    ok["staging_template"] = "content-factory/pages/{topic_file_key}-{entity}.md"
    _validate(ok, "test")  # must not raise


def test_bad_regex_rejected(site_cfg):
    bad = dict(site_cfg)
    bad["prohibited_patterns"] = {"broken": "([unclosed"}
    with pytest.raises(SystemExit, match="not a valid regex"):
        _validate(bad, "test")


def test_quality_defaults_applied():
    cfg = _apply_defaults(
        {
            "site_id": "d",
            "domain": "d",
            "canonical_host": "https://d",
            "target_repo_root": ".",
            "output_template": "o",
            "route_template": "r",
            "artifacts_dir": "a",
            "inventory": {"topics": [{"key": "k", "file_key": "k", "route_segment": "k", "label": "k", "title_label": "K"}]},
        }
    )
    assert cfg["quality"]["target_words_min"] == 2800
    assert cfg["quality"]["max_pairwise_overlap"] == 0.10
    assert cfg["provider"] == "codex"


def test_topic_aliases(site_cfg):
    assert topic_aliases(site_cfg) == {"alfa": "alpha"}
