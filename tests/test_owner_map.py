import json
from pathlib import Path

from tmsf.owner_map import validate_owner_map


FIXTURE = Path(__file__).parent / "fixtures" / "owner-map.valid.json"


def test_owner_map_contract_accepts_geo_handoff():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert validate_owner_map(payload) == []


def test_owner_map_contract_rejects_empty_evidence_and_oversized_pilot():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["owners"][0]["evidence_sources"] = []
    payload["pilot"] *= 11
    payload["evidence_collected_at"] = "not-a-date"
    payload["surprise"] = True
    errors = validate_owner_map(payload)
    assert any("evidence_sources cannot be empty" in error for error in errors)
    assert "pilot cannot contain more than 10 routes" in errors
    assert any("ISO-8601" in error for error in errors)
    assert any("unknown top-level" in error for error in errors)
