#!/usr/bin/env python3
"""One-shot: export the 472-city TS dataset to a domain-neutral CSV usable by
the static_list adapter for any site (county/population/zip are not
insurance-specific).

Usage: python tools/export_cities_csv.py <california-cities.ts> <out.csv>
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))

from tmsf.adapters.ts_array import _blocks, number_field, string_field  # noqa: E402


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src = Path(sys.argv[1]).read_text(encoding="utf-8")
    out = Path(sys.argv[2])
    rows = []
    for block in _blocks(src, "californiaTopCities"):
        name = string_field(block, "name")
        slug = string_field(block, "slug")
        if not (name and slug):
            continue
        rows.append(
            {
                "name": name,
                "slug": slug,
                "county": string_field(block, "county") or "",
                "region": string_field(block, "region") or "",
                "population": number_field(block, "population") or "",
                "zip_code": string_field(block, "zipCode") or "",
                "area_code": string_field(block, "areaCode") or "",
            }
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"EXPORTED={out} rows={len(rows)}")


if __name__ == "__main__":
    main()
