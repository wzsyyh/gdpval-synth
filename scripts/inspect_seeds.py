"""List all harvested seeds across the 3 occupations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.seeds.base import load_seeds  # noqa: E402

for occ in ("lawyer", "financial_analyst", "software_engineer"):
    seeds = load_seeds(occ)
    print(f"\n{'=' * 80}\n{occ.upper()}: {len(seeds)} seeds\n{'=' * 80}")
    for i, s in enumerate(seeds, 1):
        print(f"  {i:2d}. [{s.seed_id}] {s.title[:90]}")
