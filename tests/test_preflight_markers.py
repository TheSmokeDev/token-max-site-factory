import json

from tmsf.preflight import check_marker


def write_marker(path, site_id):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"site_id": site_id}), encoding="utf-8")


def test_per_site_markers_coexist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_marker(tmp_path / ".token-max/sites/alpha.json", "alpha")
    write_marker(tmp_path / ".token-max/sites/beta.json", "beta")

    assert check_marker("alpha") == []
    assert check_marker("beta") == []


def test_legacy_marker_remains_supported(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_marker(tmp_path / ".token-max/site.json", "alpha")

    assert check_marker("alpha") == []


def test_per_site_marker_wins_over_legacy_marker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_marker(tmp_path / ".token-max/site.json", "alpha")
    write_marker(tmp_path / ".token-max/sites/beta.json", "wrong-site")

    errors = check_marker("beta")
    assert len(errors) == 1
    assert "wrong-site" in errors[0]
