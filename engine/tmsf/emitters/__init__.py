"""Output emitters. markdown = passthrough (the writer writes final files);
html = deterministic staging-markdown -> full HTML render (M6);
nextjs_content = deterministic staging-markdown -> Next.js spoke-content
frontmatter (matches an existing site's content contract, e.g. a Next.js
site/lib/spoke.ts)."""

from __future__ import annotations

import json
from pathlib import Path


def emit(cfg: dict, batch_path: Path) -> None:
    fmt = str(cfg.get("page_format") or "markdown")
    if fmt == "markdown":
        print("EMIT=noop")
        return
    if fmt == "html":
        from .html import emit_html_batch

        batch = json.loads(batch_path.read_text(encoding="utf-8"))
        emit_html_batch(cfg, batch)
        return
    if fmt == "nextjs_content":
        from .nextjs_content import emit_nextjs_content_batch

        batch = json.loads(batch_path.read_text(encoding="utf-8"))
        emit_nextjs_content_batch(cfg, batch)
        return
    raise SystemExit(f"Unknown page_format: {fmt}")
