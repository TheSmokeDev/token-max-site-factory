"""Text metrics — verbatim port of sr22_token_max.py L615-635, plus the FAQ
gate the SR22 lane specified in its writer contract but never enforced."""

from __future__ import annotations

import re


def markdown_to_text(markdown: str) -> str:
    return (
        re.sub(r"^---[\s\S]*?---", " ", markdown)
        .replace("—", " ")
        .replace(" ", " ")
    )


def visible_text(markdown: str) -> str:
    text = markdown_to_text(markdown)
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^#+\s*", " ", text, flags=re.M)
    text = re.sub(r"^[>*-]\s*", " ", text, flags=re.M)
    return re.sub(r"\s+", " ", text).strip()


def word_count(markdown: str) -> int:
    return len(re.findall(r"\b[\w,'/-]+\b", visible_text(markdown)))


FAQ_H2 = re.compile(r"^##\s+.*(frequently asked|faq)", re.I | re.M)


def faq_question_count(markdown: str) -> int:
    """Count question headings inside the FAQ section (### under the FAQ H2,
    up to the next H2). Fallback when no FAQ H2 exists: question-style ###
    headings anywhere in the document."""
    match = FAQ_H2.search(markdown)
    if match:
        section = markdown[match.end():]
        next_h2 = re.search(r"^##\s+", section, re.M)
        if next_h2:
            section = section[: next_h2.start()]
        return len(re.findall(r"^###\s+", section, re.M))
    return len(re.findall(r"^###\s+.*\?\s*$", markdown, re.M))
