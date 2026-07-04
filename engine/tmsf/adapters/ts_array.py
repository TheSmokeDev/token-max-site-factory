"""TypeScript array entity adapter — verbatim port of the SR22 lane's
city_blocks()/load_cities()/city_public_context() regex parser
(sr22_token_max.py L158-217, L258-270).

Parses ``export const <export> = [ ... ];`` blocks out of a TS data file in
the TARGET repo (path is repo-relative, resolved against cwd) and returns the
packet-visible public context per entity.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .. import target_root


def string_field(block: str, key: str) -> str | None:
    match = re.search(rf"\b{re.escape(key)}:\s*'([^']*)'", block)
    return match.group(1) if match else None


def number_field(block: str, key: str) -> str | None:
    match = re.search(rf"\b{re.escape(key)}:\s*(-?[0-9]+(?:\.[0-9]+)?)", block)
    return match.group(1) if match else None


def _blocks(src: str, export: str) -> Iterable[str]:
    array_match = re.search(rf"export const {re.escape(export)}[^=]*=\s*\[(?P<body>.+?)\]\s*;", src, re.S)
    if not array_match:
        raise SystemExit(f"Could not find {export} array")
    for chunk in re.split(r"\n  \},?\n", array_match.group("body")):
        chunk = chunk.strip()
        if chunk:
            yield chunk


def load_entities(spec: dict) -> dict[str, dict]:
    path = Path(str(spec.get("path") or ""))
    if not path.is_absolute():
        path = target_root() / path
    export = str(spec.get("export") or "californiaTopCities")
    src = path.read_text(encoding="utf-8")

    entities: dict[str, dict] = {}
    for block in _blocks(src, export):
        name = string_field(block, "name")
        slug = string_field(block, "slug")
        county = string_field(block, "county")
        population = number_field(block, "population")
        zip_code = string_field(block, "zipCode")
        area_code = string_field(block, "areaCode")
        if not (name and slug and county and population and zip_code and area_code):
            continue
        dmv_block = re.search(r"dmvOffice:\s*\{(?P<body>.*?)\n    \}", block, re.S)
        demo_block = re.search(r"demographics:\s*\{(?P<body>.*?)\n    \}", block, re.S)
        entities[slug] = {
            "name": name,
            "slug": slug,
            "county": county,
            "region": string_field(block, "region"),
            "population": int(float(population)),
            "zip_code": zip_code,
            "area_code": area_code,
            "geo": {"lat": number_field(block, "lat"), "lng": number_field(block, "lng")},
            "dmv_office": {
                "name": string_field(dmv_block.group("body"), "name") or "",
                "address": string_field(dmv_block.group("body"), "address") or "",
                "distance": string_field(dmv_block.group("body"), "distance") or "",
            }
            if dmv_block
            else {},
            "demographics": {
                "medianIncome": number_field(demo_block.group("body"), "medianIncome") or "",
                "medianAge": number_field(demo_block.group("body"), "medianAge") or "",
                "avgVehiclesPerHousehold": number_field(demo_block.group("body"), "avgVehiclesPerHousehold") or "",
            }
            if demo_block
            else {},
        }
    return entities
