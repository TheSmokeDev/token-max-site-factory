"""Batch report — port of sr22_token_max.py report() L910-937 with the
site id in the title and an explicit live-mutation status line."""

from __future__ import annotations

import json
from pathlib import Path


def write_report(cfg: dict, batch_path: Path, validation_path: Path, output_path: Path) -> None:
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8")) if validation_path.exists() else {}
    lines = [
        f"# {cfg['site_id']} Token-Max Batch Report",
        "",
        f"- Phase: `{batch.get('phase', 'custom')}`",
        f"- Products: `{', '.join(batch.get('products', []))}`",
        f"- Pages: `{len(batch.get('pages', []))}`",
        f"- Resumed existing output files: `{batch.get('resumed_existing_output_count', 0)}`",
        f"- Validation OK: `{validation.get('ok')}`",
        f"- Held back: `{validation.get('held_back_count')}`",
        f"- Cross-corpus files checked: `{validation.get('cross_corpus_file_count')}`",
        f"- Page format: `{cfg.get('page_format')}`",
        f"- Live mutations: `none`",
        "",
        "## Pages",
        "",
    ]
    for page in batch.get("pages", []):
        lines.append(
            f"- `{page['route']}` -> `{page['output']}` ({page.get('word_count', 'n/a')} words, {page.get('status')})"
        )
    if validation.get("held_back"):
        lines.extend(["", "## Held Back", ""])
        for item in validation["held_back"]:
            lines.append(f"- `{item['page']}`: `{item['regenerate_with']}`")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"REPORT={output_path}")
