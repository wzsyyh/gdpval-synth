"""Coverage / diversity statistics across a set of TaskCandidates.

Used for the writeup: heatmap of (occupation × difficulty), histogram of rubric
sizes, embedding pairwise distance distribution, n-gram repetition rate.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.config import DATA_DIR
from pipeline.scenario.task_candidate import TaskCandidate


def load_pool(directory: Path) -> list[TaskCandidate]:
    return [TaskCandidate.load(p) for p in sorted(directory.glob("*.json"))]


def coverage_grid(tasks: list[TaskCandidate]) -> dict[str, Any]:
    occ_diff = Counter((t.occupation, t.difficulty) for t in tasks)
    occ_deliv = Counter((t.occupation, t.deliverable.deliverable_id) for t in tasks)
    occ_arche = Counter((t.occupation, t.archetype) for t in tasks)
    return {
        "n": len(tasks),
        "occupation_x_difficulty": {f"{k[0]}/{k[1]}": v for k, v in occ_diff.items()},
        "occupation_x_deliverable": {f"{k[0]}/{k[1]}": v for k, v in occ_deliv.items()},
        "occupation_x_archetype_unique": len(occ_arche),
    }


def rubric_stats(tasks: list[TaskCandidate]) -> dict[str, Any]:
    sizes = [len(t.rubric) for t in tasks]
    points = [t.total_rubric_points() for t in tasks]
    if not sizes:
        return {"n": 0}
    return {
        "n": len(tasks),
        "rubric_items": {
            "min": min(sizes), "median": sorted(sizes)[len(sizes) // 2],
            "max": max(sizes), "mean": round(sum(sizes) / len(sizes), 1),
        },
        "rubric_points": {
            "min": min(points), "median": sorted(points)[len(points) // 2],
            "max": max(points), "mean": round(sum(points) / len(points), 1),
        },
    }


def pairwise_diversity(tasks: list[TaskCandidate]) -> dict[str, Any]:
    if len(tasks) < 2:
        return {"n": len(tasks), "note": "need ≥2"}
    from pipeline.diversity.embed_dedup import embed
    vecs = embed([t.prompt for t in tasks])
    sims = vecs @ vecs.T
    np.fill_diagonal(sims, np.nan)
    upper = sims[np.triu_indices_from(sims, k=1)]
    return {
        "n": len(tasks),
        "mean_pairwise_sim": round(float(np.nanmean(upper)), 3),
        "min_pairwise_sim": round(float(np.nanmin(upper)), 3),
        "max_pairwise_sim": round(float(np.nanmax(upper)), 3),
        "mean_pairwise_dist": round(1.0 - float(np.nanmean(upper)), 3),
    }


def funnel_summary(funnel_log_path: Path) -> dict[str, Any]:
    if not funnel_log_path.exists():
        return {"note": "no funnel log"}
    rows = [json.loads(line) for line in funnel_log_path.read_text().splitlines() if line.strip()]
    rejection_reasons = Counter()
    stage_passed = Counter()
    accepted = 0
    for r in rows:
        if r.get("accepted"):
            accepted += 1
        else:
            reason = r.get("rejection_reason") or "unknown"
            # Bucket by stage
            if "hard validators failed" in reason:
                bucket = "hard_validators"
            elif "too close to real GDPval" in reason:
                bucket = "dedup_too_similar"
            elif "realism overall" in reason:
                bucket = "realism_low"
            elif "solvability overall" in reason:
                bucket = "solvability_low"
            elif "predicted" in reason and "≥" in reason:
                bucket = "solve_rate_too_easy"
            elif "crashed" in reason:
                bucket = "critic_crashed"
            else:
                bucket = "other"
            rejection_reasons[bucket] += 1
        stage_passed[r.get("stage_passed", "none")] += 1
    return {
        "total_processed": len(rows),
        "accepted": accepted,
        "rejected": len(rows) - accepted,
        "accept_rate": round(accepted / max(len(rows), 1), 3),
        "rejection_by_stage": dict(rejection_reasons),
        "max_stage_reached": dict(stage_passed),
    }


def all_stats() -> dict[str, Any]:
    return {
        "candidates": coverage_grid(load_pool(DATA_DIR / "candidates")),
        "accepted": coverage_grid(load_pool(DATA_DIR / "accepted")),
        "rejected": coverage_grid(load_pool(DATA_DIR / "rejected")),
        "rubric_accepted": rubric_stats(load_pool(DATA_DIR / "accepted")),
        "rubric_all": rubric_stats(load_pool(DATA_DIR / "candidates")),
        "diversity_accepted": pairwise_diversity(load_pool(DATA_DIR / "accepted")),
        "diversity_all": pairwise_diversity(load_pool(DATA_DIR / "candidates")),
        "funnel": funnel_summary(DATA_DIR / "funnel_log.jsonl"),
    }


if __name__ == "__main__":
    print(json.dumps(all_stats(), indent=2))
