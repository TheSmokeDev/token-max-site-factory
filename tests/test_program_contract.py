import json

import pytest

from tmsf.config import _validate
from tmsf.materialize import materialize_writer_prompt
from tmsf.packet import page_prompt_packet
from tmsf.report import write_report


def test_growth_program_requires_owner_and_evidence_contract(site_cfg):
    cfg = dict(site_cfg)
    cfg["program"] = {
        "scale": "growth",
        "business_model": "saas",
        "audience": "operations leaders",
        "conversion_goal": "request a demo",
        "evidence_owner": "product-marketing",
        "reviewers": [],
        "success_metrics": ["qualified demos"],
    }
    cfg["intent_contract"] = {}
    with pytest.raises(SystemExit, match="intent_contract fields"):
        _validate(cfg, "test")


def test_growth_program_with_owner_contract_is_valid(site_cfg):
    cfg = dict(site_cfg)
    cfg["program"] = {
        "scale": "growth",
        "business_model": "saas",
        "audience": "operations leaders",
        "conversion_goal": "request a demo",
        "evidence_owner": "product-marketing",
        "reviewers": [],
        "success_metrics": ["qualified demos"],
    }
    cfg["intent_contract"] = {"primary_query": "workflow automation", "route_owner": "/platform"}
    _validate(cfg, "test")


def test_enterprise_requires_reviewers_and_sources(site_cfg):
    cfg = dict(site_cfg)
    cfg["program"] = {
        "scale": "enterprise",
        "business_model": "multi-location-service",
        "audience": "procurement leaders",
        "conversion_goal": "request a consultation",
        "evidence_owner": "revenue-operations",
        "reviewers": [],
        "success_metrics": ["qualified consultations"],
    }
    cfg["intent_contract"] = {"primary_query": "regional provider", "route_owner": "/services"}
    with pytest.raises(SystemExit, match="program.reviewers"):
        _validate(cfg, "test")

    cfg["program"]["reviewers"] = ["brand", "compliance"]
    with pytest.raises(SystemExit, match="authority_sources"):
        _validate(cfg, "test")

    cfg["authority_sources"] = [{}]
    with pytest.raises(SystemExit, match="nonblank label and url"):
        _validate(cfg, "test")

    cfg["authority_sources"] = [{"label": "Product catalog", "url": "https://example.com/catalog"}]
    _validate(cfg, "test")


def test_enterprise_profile_requires_enterprise_scale(site_cfg):
    cfg = dict(site_cfg)
    cfg["prompt_profile"] = "multi-location-enterprise"
    with pytest.raises(SystemExit, match="requires program.scale enterprise"):
        _validate(cfg, "test")

    cfg.pop("program")
    with pytest.raises(SystemExit, match="requires program.scale enterprise"):
        _validate(cfg, "test")


def test_packet_carries_program_owner_and_page_locale(site_cfg):
    site_cfg["program"]["audience"] = "Spanish-speaking buyers"
    site_cfg["intent_contract"] = {"primary_query": "servicio alfa", "route_owner": "/es/alfa"}
    page = {
        "id": "btown-alpha-es",
        "status": "pending_generation",
        "output": "content/btown/alpha.es.md",
        "route": "/es/btown/alpha",
        "city": "btown",
        "product": "alpha",
        "locale": "es",
    }
    packet = page_prompt_packet(site_cfg, page, {"kind": "test"}, {"btown": {"name": "Btown", "slug": "btown"}})

    assert packet["frontmatter"]["locale"] == "es"
    assert packet["program"]["audience"] == "Spanish-speaking buyers"
    assert packet["intent_contract"]["route_owner"] == "/es/alfa"


@pytest.mark.parametrize(
    "profile",
    ["local-service-seo", "multi-location-enterprise", "saas-b2b", "ecommerce-category", "regulated-insurance"],
)
def test_shipped_profiles_materialize(profile, site_cfg):
    site_cfg["prompt_profile"] = profile
    path = materialize_writer_prompt(site_cfg)
    raw = path.read_text(encoding="utf-8")
    assert f"# Profile:" in raw
    assert 'locale: "<packet.frontmatter.locale>"' in raw


def test_report_writes_machine_receipt_with_false_external_state(site_cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    artifacts = tmp_path / "artifacts"
    (artifacts / "state").mkdir(parents=True)
    (artifacts / "context").mkdir(parents=True)
    (artifacts / "state" / "site-config.resolved.json").write_text("{}\n", encoding="utf-8")
    (artifacts / "context" / "writer-prompt.md").write_text("prompt\n", encoding="utf-8")
    site_cfg["artifacts_dir"] = str(artifacts)
    site_cfg["program"]["reviewers"] = ["owner"]
    site_cfg["intent_contract"] = {"primary_query": "alpha service", "route_owner": "/alpha"}

    page_path = tmp_path / "content" / "alpha.md"
    page_path.parent.mkdir()
    page_path.write_text("# Alpha\n\nVerified page.\n", encoding="utf-8")
    batch_path = artifacts / "state" / "batch.json"
    batch_path.write_text(
        json.dumps(
            {
                "phase": "pilot",
                "products": ["alpha"],
                "pages": [
                    {
                        "id": "alpha",
                        "route": "/alpha",
                        "output": "content/alpha.md",
                        "status": "generated",
                        "locale": "en",
                        "word_count": 2,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    validation_path = artifacts / "reports" / "validation.json"
    validation_path.parent.mkdir()
    validation_path.write_text(json.dumps({"ok": True, "held_back_count": 0}), encoding="utf-8")
    output_path = artifacts / "reports" / "batch-report.md"

    write_report(site_cfg, batch_path, validation_path, output_path)

    receipt = json.loads((artifacts / "reports" / "batch-report.receipts.json").read_text(encoding="utf-8"))
    assert receipt["factory_version"] == "0.6.0"
    assert receipt["pages"][0]["output_sha256"]
    assert receipt["artifact_hashes"]["writer_prompt_sha256"]
    assert receipt["review"]["required_reviewers"] == ["owner"]
    assert receipt["review"]["approved"] is False
    assert receipt["external_state"] == {
        "production_deployed": False,
        "live_verified": False,
        "indexing_verified": False,
        "ranking_verified": False,
        "citation_verified": False,
    }
