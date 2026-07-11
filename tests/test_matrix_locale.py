import pytest

from tmsf.matrix import build_pages


def config(locales):
    return {
        "locales": locales,
        "inventory": {
            "topics": [
                {
                    "key": "sr22",
                    "file_key": "sr22",
                    "route_segment": "seguro-sr22",
                }
            ]
        },
        "output_template": "content/{entity}/{topic_file_key}.md",
        "route_template": "/es/{entity}/{topic_route_segment}",
    }


def test_matrix_uses_configured_locale():
    pages = build_pages(
        config(["es"]),
        {"los-angeles": {"slug": "los-angeles", "name": "Los Angeles"}},
        ["los-angeles"],
        ["sr22"],
        1,
    )

    assert pages[0]["id"] == "los-angeles-sr22-es"
    assert pages[0]["locale"] == "es"


def test_matrix_rejects_ambiguous_multi_locale_contract():
    with pytest.raises(SystemExit, match="exactly one configured locale"):
        build_pages(
            config(["en", "es"]),
            {"los-angeles": {"slug": "los-angeles", "name": "Los Angeles"}},
            ["los-angeles"],
            ["sr22"],
            1,
        )
