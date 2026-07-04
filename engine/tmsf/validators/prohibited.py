"""Prohibited-claim patterns.

The domain-neutral base set is always on (ported verbatim from
sr22_token_max.py PROHIBITED_PATTERNS); each site adds its own vertical
patterns via config (compiled re.I | re.S)."""

from __future__ import annotations

import re

BASE_PATTERNS: dict[str, re.Pattern] = {
    "em_dash": re.compile(r"—"),
    "guarantee_claim": re.compile(r"guaranteed\s+(lowest|cheap|cheapest|rate|approval)", re.I),
    "template_admission": re.compile(r"(same template|city swap|copy[- ]and[- ]paste|spun content)", re.I),
}


def compile_patterns(site_patterns: dict[str, str]) -> dict[str, re.Pattern]:
    combined = dict(BASE_PATTERNS)
    for name, raw in (site_patterns or {}).items():
        combined[name] = re.compile(str(raw), re.I | re.S)
    return combined
