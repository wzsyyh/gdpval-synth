"""Diversity grid sampler.

The taxonomy defines the (occupation × deliverable × difficulty × archetype)
configuration space. This sampler turns it into a flat list of `CellAssignment`s
respecting:
  - per-occupation balance (roughly equal across the 3 occupations)
  - difficulty distribution from taxonomy.diversity_grid.difficulty_distribution
  - archetype rotation (each archetype sampled at least once before any repeats)
  - deliverable coverage (each occupation hits all its deliverable types)

Why not let the LLM choose: free generation collapses to "write an analysis
report" and "do a DCF". An explicit grid forces the long tail.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass

import yaml

from pipeline.config import TAXONOMY_PATH
from pipeline.scenario.canonical import DifficultyBand

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CellAssignment:
    occupation: str           # "lawyer" | "financial_analyst" | "software_engineer"
    deliverable_id: str
    archetype: str
    difficulty: DifficultyBand


def load_taxonomy() -> dict:
    return yaml.safe_load(TAXONOMY_PATH.read_text())


def build_grid(total_n: int, *, seed: int = 0) -> list[CellAssignment]:
    """Build a flat list of `total_n` assignments balanced across the grid."""
    tax = load_taxonomy()
    occs = list(tax["occupations"].keys())
    rng = random.Random(seed)
    diff_dist: dict[str, float] = tax["diversity_grid"]["difficulty_distribution"]

    # Build per-occupation pools of (deliverable, archetype) pairs.
    occ_pairs: dict[str, list[tuple[str, str]]] = {}
    for occ in occs:
        meta = tax["occupations"][occ]
        pairs = []
        for d in meta["deliverables"]:
            for arche in d["archetypes"]:
                pairs.append((d["id"], arche))
        rng.shuffle(pairs)
        occ_pairs[occ] = pairs

    # Per-occupation target count
    per_occ_target = total_n // len(occs)
    remainder = total_n - per_occ_target * len(occs)

    assignments: list[CellAssignment] = []
    for occ in occs:
        n_for_this = per_occ_target + (1 if remainder > 0 else 0)
        if remainder > 0:
            remainder -= 1

        pairs = occ_pairs[occ]
        # Round-robin through pairs so we hit every deliverable/archetype combo
        # before repeating any.
        for i in range(n_for_this):
            deliverable_id, archetype = pairs[i % len(pairs)]
            difficulty = _pick_difficulty(diff_dist, rng)
            assignments.append(CellAssignment(
                occupation=occ,
                deliverable_id=deliverable_id,
                archetype=archetype,
                difficulty=difficulty,
            ))

    rng.shuffle(assignments)
    return assignments


def _pick_difficulty(dist: dict[str, float], rng: random.Random) -> DifficultyBand:
    keys = list(dist.keys())
    weights = [dist[k] for k in keys]
    pick = rng.choices(keys, weights=weights, k=1)[0]
    return DifficultyBand(pick)


def coverage_stats(assignments: list[CellAssignment]) -> dict:
    """Quick stats for sanity-checking grid uniformity."""
    from collections import Counter

    occ_count = Counter(a.occupation for a in assignments)
    deliv_count = Counter((a.occupation, a.deliverable_id) for a in assignments)
    diff_count = Counter(a.difficulty.value for a in assignments)
    arche_count = Counter((a.occupation, a.archetype) for a in assignments)
    return {
        "total": len(assignments),
        "by_occupation": dict(occ_count),
        "by_deliverable": {f"{k[0]}/{k[1]}": v for k, v in deliv_count.items()},
        "by_difficulty": dict(diff_count),
        "by_archetype_count": len(arche_count),
        "unique_cells": len({(a.occupation, a.deliverable_id, a.archetype, a.difficulty.value) for a in assignments}),
    }


if __name__ == "__main__":
    import json
    grid = build_grid(60, seed=42)
    print(json.dumps(coverage_stats(grid), indent=2))
    print("\nFirst 10 cells:")
    for a in grid[:10]:
        print(f"  {a.occupation:20s} {a.deliverable_id:30s} {a.archetype:25s} {a.difficulty.value}")
