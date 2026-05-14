"""Simple seed sampler.

No taxonomy, no grid balancing. Just pick N seeds across occupations
with a difficulty bias, and let the LLM decide what deliverable type
makes sense for each seed.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from pipeline.scenario.canonical import DifficultyBand
from pipeline.seeds.base import Seed, load_seeds

logger = logging.getLogger(__name__)

_OCCUPATIONS = ["lawyer", "financial_analyst", "software_engineer"]

# Difficulty distribution calibrated to real GDPval (~60% medium).
_DIFF_DIST: dict[str, float] = {
    "light": 0.20,
    "medium": 0.55,
    "hard": 0.25,
}


@dataclass(frozen=True)
class CellAssignment:
    occupation: str
    difficulty: DifficultyBand


def build_grid(total_n: int, *, seed: int = 0) -> list[CellAssignment]:
    """Build a flat list of `total_n` assignments."""
    rng = random.Random(seed)
    per_occ = total_n // len(_OCCUPATIONS)
    remainder = total_n - per_occ * len(_OCCUPATIONS)

    assignments: list[CellAssignment] = []
    for occ in _OCCUPATIONS:
        n_for_this = per_occ + (1 if remainder > 0 else 0)
        if remainder > 0:
            remainder -= 1
        for _ in range(n_for_this):
            difficulty = _pick_difficulty(_DIFF_DIST, rng)
            assignments.append(CellAssignment(occupation=occ, difficulty=difficulty))

    rng.shuffle(assignments)
    return assignments


def _pick_difficulty(dist: dict[str, float], rng: random.Random) -> DifficultyBand:
    keys = list(dist.keys())
    weights = [dist[k] for k in keys]
    pick = rng.choices(keys, weights=weights, k=1)[0]
    return DifficultyBand(pick)


def coverage_stats(assignments: list[CellAssignment]) -> dict:
    """Quick stats for sanity-checking uniformity."""
    from collections import Counter

    occ_count = Counter(a.occupation for a in assignments)
    diff_count = Counter(a.difficulty.value for a in assignments)
    return {
        "total": len(assignments),
        "by_occupation": dict(occ_count),
        "by_difficulty": dict(diff_count),
    }


if __name__ == "__main__":
    import json

    grid = build_grid(60, seed=42)
    print(json.dumps(coverage_stats(grid), indent=2))
    print("\nFirst 10 cells:")
    for a in grid[:10]:
        print(f"  {a.occupation:20s} {a.difficulty.value}")
