"""Static text-to-HTML ratio heuristic — verbatim port of sr22_token_max.py
L638-663. Synthesizes rough HTML from markdown; it does NOT fetch a rendered
DOM (a real rendered check is a later milestone — see
fleet-seo-geo-rendered-evidence.yaml prior art)."""

from __future__ import annotations

import re

from .text_quality import markdown_to_text, visible_text


def rough_html(markdown: str) -> str:
    html_parts: list[str] = []
    for raw in markdown_to_text(markdown).splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# "):
            html_parts.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_parts.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html_parts.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("> "):
            html_parts.append(f"<blockquote>{line[2:]}</blockquote>")
        elif re.match(r"^[-*]\s+", line):
            # NOTE: the double-backslash pattern is a preserved quirk of the
            # source lane (its f-string used r'^[-*]\\s+', which matches a
            # literal backslash and so never strips the bullet). Byte-parity
            # of ratio values requires keeping it.
            item_text = re.sub(r"^[-*]\\s+", "", line)
            html_parts.append(f"<li>{item_text}</li>")
        else:
            html_parts.append(f"<p>{line}</p>")
    return "\n".join(html_parts)


def text_html_ratio(markdown: str) -> float:
    html = rough_html(markdown)
    if not html:
        return 0.0
    return len(visible_text(markdown)) / len(html)
