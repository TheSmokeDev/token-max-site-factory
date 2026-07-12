import subprocess
import sys
from pathlib import Path


def test_exported_csv_uses_lf_line_endings(tmp_path):
    source = tmp_path / "california-cities.ts"
    output = tmp_path / "ca-cities.csv"
    source.write_text(
        """export const californiaTopCities = [
  {
    name: 'Los Angeles',
    slug: 'los-angeles',
    county: 'Los Angeles',
    region: 'Southern California',
    population: 3898747,
    zipCode: '90012',
    areaCode: '213',
  },
];
""",
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[1] / "tools" / "export_cities_csv.py"
    subprocess.run([sys.executable, str(script), str(source), str(output)], check=True)

    payload = output.read_bytes()
    assert b"\r\n" not in payload
    assert payload.count(b"\n") == 2
