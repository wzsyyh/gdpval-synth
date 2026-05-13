"""Print one seed's full content. Usage:

    uv run python scripts/show_seed.py lawyer
    uv run python scripts/show_seed.py financial_analyst 5
    uv run python scripts/show_seed.py software_engineer 12
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.seeds.base import load_seeds  # noqa: E402


def main() -> None:
    occ = sys.argv[1] if len(sys.argv) > 1 else "lawyer"
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    seeds = load_seeds(occ)
    if not seeds:
        print(f"No seeds for {occ}")
        return
    s = seeds[idx]
    print(f"=== {occ} seed {idx} ===")
    print(f"seed_id:    {s.seed_id}")
    print(f"source:     {s.source}")
    print(f"identifier: {s.identifier}")
    print(f"title:      {s.title}")
    print(f"fetched_at: {s.fetched_at}")
    print()
    print("--- PAYLOAD ---")
    import json
    print(json.dumps(s.payload, indent=2, default=str)[:3000])
    print()
    print("--- TEXT EXCERPT ---")
    print(s.text_excerpt)


if __name__ == "__main__":
    main()
