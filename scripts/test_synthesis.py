"""End-to-end smoke test of scenario synthesis.

Picks one seed per occupation, runs through the full 3-stage pipeline, and
prints the resulting TaskCandidate for inspection.
"""

import logging
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.scenario.canonical import DifficultyBand  # noqa: E402
from pipeline.scenario.synthesis import synthesize_task  # noqa: E402
from pipeline.scenario.task_candidate import render_for_inspection  # noqa: E402
from pipeline.seeds.base import load_seeds  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


CONFIGS = [
    # (occupation, seed_idx, deliverable_id, archetype, difficulty)
    ("financial_analyst", 0, "dcf_model", "equity_research", DifficultyBand.MEDIUM),
    ("lawyer", 0, "legal_memo", "regulatory_analysis", DifficultyBand.MEDIUM),
    ("software_engineer", 0, "design_doc", "perf_refactor", DifficultyBand.MEDIUM),
]


def main() -> None:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for occ, idx, deliv, arche, diff in CONFIGS:
        if only and only not in occ:
            continue
        seeds = load_seeds(occ)
        if not seeds:
            print(f"skip {occ}: no seeds")
            continue
        # For SWE pick the highest-quality seed by our scorer instead of [0].
        if occ == "software_engineer":
            from pipeline.seeds.swe_quality import rank
            ranked = rank(seeds)
            seed = ranked[idx][0] if ranked else seeds[idx]
        else:
            seed = seeds[idx]

        print(f"\n{'#' * 90}")
        print(f"# {occ.upper()} | seed={seed.title[:80]} | {deliv}/{arche}/{diff.value}")
        print(f"{'#' * 90}")
        rng = random.Random(int(seed.seed_id, 16))
        task = synthesize_task(seed, deliv, arche, diff, rng=rng)
        path = task.save()
        print(render_for_inspection(task))
        print(f"\n  saved: {path}")


if __name__ == "__main__":
    main()
