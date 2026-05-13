"""Auto-curate the final 24 from the accepted pool.

Strategy:
  - Target 8 per occupation
  - Within occupation: rank accepted candidates by composite score
    (realism * 0.4 + solvability * 0.3 + (10 - solve_rate_max) * 0.3)
  - Greedily pick to maximize diversity (deliverable, archetype coverage)
  - Output: data/final/ + a sample gallery for the report

Run after orchestrator finishes.
"""

import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.config import DATA_DIR  # noqa: E402
from pipeline.scenario.task_candidate import TaskCandidate  # noqa: E402

ACCEPTED = DATA_DIR / "accepted"
FINAL = DATA_DIR / "final"
TARGET_PER_OCC = 8


def composite_score(funnel: dict) -> float:
    realism = funnel.get("realism_overall") or 0
    solvability = funnel.get("solvability_overall") or 0
    sr_max = funnel.get("solve_rate_max") or 0
    sr_signal = max(0, 10 - sr_max)  # lower solve_rate_max is better (harder task)
    return realism * 0.4 + solvability * 0.3 + sr_signal * 0.3


def load_funnel_lookup() -> dict[str, dict]:
    log = DATA_DIR / "funnel_log.jsonl"
    by_id = {}
    if not log.exists():
        return {}
    for line in log.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("accepted"):
            by_id[r["candidate_id"]] = r
    return by_id


def main() -> None:
    pool = sorted(ACCEPTED.glob("*.json"))
    if not pool:
        print("No accepted candidates. Run pipeline.orchestrator first.")
        return

    funnel_by_id = load_funnel_lookup()
    by_occ: dict[str, list[tuple[TaskCandidate, float]]] = defaultdict(list)
    for p in pool:
        tc = TaskCandidate.load(p)
        funnel = funnel_by_id.get(tc.candidate_id, {})
        score = composite_score(funnel)
        by_occ[tc.occupation].append((tc, score))

    # Greedy diversity-aware pick within each occupation.
    picks: list[TaskCandidate] = []
    for occ, items in by_occ.items():
        items.sort(key=lambda x: x[1], reverse=True)
        chosen: list[TaskCandidate] = []
        seen_cells: set[tuple[str, str]] = set()
        # First pass: prioritize new (deliverable, archetype) cells.
        for tc, _ in items:
            if len(chosen) >= TARGET_PER_OCC:
                break
            cell = (tc.deliverable.deliverable_id, tc.archetype)
            if cell not in seen_cells:
                seen_cells.add(cell)
                chosen.append(tc)
        # Second pass: fill remaining slots with highest-score regardless.
        if len(chosen) < TARGET_PER_OCC:
            for tc, _ in items:
                if tc in chosen:
                    continue
                if len(chosen) >= TARGET_PER_OCC:
                    break
                chosen.append(tc)
        picks.extend(chosen)
        print(f"  {occ}: picked {len(chosen)} of {len(items)} accepted ({len(seen_cells)} unique cells)")

    FINAL.mkdir(parents=True, exist_ok=True)
    # Clean previous finals.
    for old in FINAL.glob("*.json"):
        old.unlink()
    for tc in picks:
        shutil.copy(ACCEPTED / f"{tc.candidate_id}.json", FINAL / f"{tc.candidate_id}.json")
    print(f"\n  total final: {len(picks)} → {FINAL}")

    # Sanity print
    print("\nFinal task distribution:")
    by_occ_count: dict = defaultdict(lambda: defaultdict(int))
    for tc in picks:
        by_occ_count[tc.occupation][tc.deliverable.deliverable_id] += 1
    for occ, deliv_map in sorted(by_occ_count.items()):
        print(f"  {occ}:")
        for d, c in sorted(deliv_map.items()):
            print(f"    {d}: {c}")


if __name__ == "__main__":
    main()
