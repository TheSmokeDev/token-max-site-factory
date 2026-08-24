import json
from pathlib import Path

import yaml

from tmsf import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_tokenmax_agent_skill_metadata_is_valid():
    skill = (ROOT / "skills" / "tokenmax-cli" / "SKILL.md").read_text(encoding="utf-8")
    _, frontmatter, body = skill.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert set(metadata) == {"name", "description"}
    assert metadata["name"] == "tokenmax-cli"
    assert body.strip()

    agent = yaml.safe_load((ROOT / "skills" / "tokenmax-cli" / "agents" / "openai.yaml").read_text(encoding="utf-8"))
    interface = agent["interface"]
    assert "$tokenmax-cli" in interface["default_prompt"]
    assert 25 <= len(interface["short_description"]) <= 64


def test_citation_and_schema_are_machine_readable():
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    assert citation["version"] == __version__
    assert citation["repository-code"].endswith("/token-max-site-factory")

    schema = json.loads((ROOT / "schemas" / "owner-intent-map.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == 1
