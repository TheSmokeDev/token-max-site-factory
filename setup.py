from pathlib import Path

from setuptools import setup


ROOT = Path(__file__).resolve().parent
RESOURCE_DIRS = ("docs", "marketplace", "prompts", "schemas", "sites/example", "skills", "workflow-templates")
ROOT_FILES = ("CITATION.cff", "LICENSE", "README.md", "WORKFLOW.md")
ENGINE_FILES = ("engine/python_shim.sh", "engine/tmsf.sh", "engine/token_max_site_factory.py")


def bundled_data_files() -> list[tuple[str, list[str]]]:
    grouped: dict[str, list[str]] = {}
    for directory in RESOURCE_DIRS:
        base = ROOT / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            relative = path.relative_to(ROOT)
            destination = str(Path("share/token-max-site-factory") / relative.parent)
            grouped.setdefault(destination, []).append(relative.as_posix())
    grouped.setdefault("share/token-max-site-factory", []).extend(
        name for name in ROOT_FILES if (ROOT / name).exists()
    )
    grouped.setdefault("share/token-max-site-factory/engine", []).extend(
        name for name in ENGINE_FILES if (ROOT / name).exists()
    )
    return sorted(grouped.items())


setup(data_files=bundled_data_files())
