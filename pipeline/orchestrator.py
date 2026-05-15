"""Production orchestrator — generate N candidates from seeds.

Pipeline per task:
  1. Pick a real seed (seeds.selector)
  2. Unified generate: LLM reads full seed → produces TaskCandidate in one call
  3. Render deliverable from blueprint (deterministic code)
  4. Save accepted to data/accepted/

Parallelism: ThreadPoolExecutor with 8 workers.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass

from pipeline.artifacts.input_renderer import render_input_attachment
from pipeline.artifacts.renderer import materialize_deliverable
from pipeline.config import DATA_DIR
from pipeline.diversity.grid import CellAssignment, build_grid, coverage_stats
from pipeline.scenario.synthesis import synthesize_task
from pipeline.scenario.task_candidate import TaskCandidate
from pipeline.seeds.base import Seed
from pipeline.seeds.selector import select as select_seed
from pipeline.validators.hard_quality import validate as hard_quality_validate
from pipeline.validators.llm_consistency import validate as consistency_validate

logger = logging.getLogger(__name__)


@dataclass
class RunOutcome:
    cell_index: int
    occupation: str
    difficulty: str
    seed_id: str | None
    candidate_id: str | None
    accepted: bool
    elapsed_s: float
    error: str | None = None


def _process_cell(
    idx: int,
    cell: CellAssignment,
    used_seeds: set[str],
    used_lock,
    skip_validation: bool = False,
) -> RunOutcome:
    t0 = time.time()
    rng = random.Random((idx * 17) + 99991)
    with used_lock:
        seed = select_seed(cell.occupation, cell.difficulty, used=used_seeds, rng=rng)
        if seed:
            used_seeds.add(seed.seed_id)
    if seed is None:
        return RunOutcome(
            cell_index=idx,
            occupation=cell.occupation,
            difficulty=cell.difficulty.value,
            seed_id=None,
            candidate_id=None,
            accepted=False,
            elapsed_s=round(time.time() - t0, 1),
            error="no available seed",
        )

    try:
        task = synthesize_task(seed, cell.occupation, cell.difficulty.value)
    except Exception as e:
        logger.exception("synthesis failed for cell %d", idx)
        return RunOutcome(
            cell_index=idx,
            occupation=cell.occupation,
            difficulty=cell.difficulty.value,
            seed_id=seed.seed_id,
            candidate_id=None,
            accepted=False,
            elapsed_s=round(time.time() - t0, 1),
            error=f"synthesis: {type(e).__name__}: {e}",
        )

    # Hard quality check: fast deterministic filter (cheap)
    try:
        hq = hard_quality_validate(task, seed)
        if not hq.passed:
            task.save(DATA_DIR / "rejected")
            issue_summary = "; ".join(hq.issues[:3])
            logger.info("  hard quality reject: %s", issue_summary)
            return RunOutcome(
                cell_index=idx,
                occupation=cell.occupation,
                difficulty=cell.difficulty.value,
                seed_id=seed.seed_id,
                candidate_id=task.candidate_id,
                accepted=False,
                elapsed_s=round(time.time() - t0, 1),
                error=f"hard_quality: {issue_summary}",
            )
    except Exception as e:
        logger.warning("hard quality validation crashed for %s: %s", task.candidate_id, e)

    # Consistency validation: hard gate (LLM-based) — can be skipped for manual review
    if not skip_validation:
        try:
            crep = consistency_validate(task, seed)
            if not crep.passed:
                task.save(DATA_DIR / "rejected")
                issue_summary = "; ".join(crep.issues[:3]) if crep.issues else "alignment issues"
                return RunOutcome(
                    cell_index=idx,
                    occupation=cell.occupation,
                    difficulty=cell.difficulty.value,
                    seed_id=seed.seed_id,
                    candidate_id=task.candidate_id,
                    accepted=False,
                    elapsed_s=round(time.time() - t0, 1),
                    error=f"consistency: {issue_summary}",
                )
        except Exception as e:
            logger.warning("consistency validation crashed for %s: %s", task.candidate_id, e)

    # Save candidate
    task.save(DATA_DIR / "candidates")

    # Render deliverable
    target_dir = DATA_DIR / "accepted"
    target_dir.mkdir(parents=True, exist_ok=True)
    deliverable_meta = None
    if task.canonical.reference_answer:
        try:
            deliverable_meta = materialize_deliverable(task)
            task.gold_deliverable_path = deliverable_meta["file_path"]
            logger.info("  rendered deliverable: %s (%d bytes)", deliverable_meta["file_path"], deliverable_meta["file_size"])
        except Exception as e:
            logger.warning("deliverable rendering failed for %s: %s", task.candidate_id, e)

        # Render input attachments (skip duplicates with identical body)
        seen_bodies: set[str] = set()
        for att in (task.canonical.reference_answer.input_attachments or []):
            body = (att.content_blueprint or {}).get("body", "")
            body_hash = hash(body)
            if body_hash in seen_bodies:
                logger.info("  skipping duplicate attachment: %s", att.attachment_id)
                continue
            seen_bodies.add(body_hash)
            try:
                att_path = render_input_attachment(att, target_dir / task.candidate_id)
                task.input_attachment_paths.append(str(att_path))
                logger.info("  rendered attachment: %s", att_path)
            except Exception as e:
                logger.warning("attachment rendering failed for %s: %s", att.attachment_id, e)

        task.save(target_dir)

    return RunOutcome(
        cell_index=idx,
        occupation=cell.occupation,
        difficulty=cell.difficulty.value,
        seed_id=seed.seed_id,
        candidate_id=task.candidate_id,
        accepted=True,
        elapsed_s=round(time.time() - t0, 1),
    )


def run(
    n: int = 60,
    *,
    workers: int = 8,
    grid_seed: int = 42,
    skip_validation: bool = False,
) -> list[RunOutcome]:
    grid = build_grid(n, seed=grid_seed)
    logger.info("grid built: %s", json.dumps(coverage_stats(grid), indent=2))

    used_seeds: set[str] = set()
    used_lock = __import__("threading").Lock()

    outcomes: list[RunOutcome] = []
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_process_cell, i, cell, used_seeds, used_lock, skip_validation): i
            for i, cell in enumerate(grid)
        }
        for fut in as_completed(futures):
            outcome = fut.result()
            outcomes.append(outcome)
            tag = "✓" if outcome.accepted else "✗"
            elapsed_total = time.time() - t_start
            logger.info(
                "[%2d/%d] %s %s/%s %ss   %s",
                len(outcomes), len(grid), tag,
                outcome.occupation, outcome.difficulty,
                outcome.elapsed_s,
                outcome.error or "ACCEPTED",
            )
            accepted_so_far = sum(1 for o in outcomes if o.accepted)
            logger.info("  accepted=%d/%d  wall=%.1fs", accepted_so_far, len(outcomes), elapsed_total)

    # Write run summary
    summary = {
        "ts": time.time(),
        "n": n,
        "workers": workers,
        "accepted": sum(1 for o in outcomes if o.accepted),
        "rejected": sum(1 for o in outcomes if not o.accepted),
        "wall_s": round(time.time() - t_start, 1),
        "grid_stats": coverage_stats(grid),
    }
    (DATA_DIR / "run_summary.json").write_text(json.dumps(summary, indent=2))
    return outcomes


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("-n", type=int, default=60)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--grid-seed", type=int, default=42)
    p.add_argument("--skip-validation", action="store_true", help="Skip LLM consistency validation (for manual review)")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for noisy in ("httpx", "httpcore", "huggingface_hub", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    outcomes = run(
        n=args.n,
        workers=args.workers,
        grid_seed=args.grid_seed,
        skip_validation=args.skip_validation,
    )
    accepted = sum(1 for o in outcomes if o.accepted)
    print(f"\n{'=' * 80}\nDONE: {accepted}/{len(outcomes)} accepted ({accepted / len(outcomes):.0%})\n{'=' * 80}")
    from collections import Counter
    by_occ = Counter()
    by_occ_ok = Counter()
    for o in outcomes:
        by_occ[o.occupation] += 1
        if o.accepted:
            by_occ_ok[o.occupation] += 1
    for occ in sorted(by_occ):
        print(f"  {occ:25s} {by_occ_ok[occ]:3d}/{by_occ[occ]:3d}  ({by_occ_ok[occ] / by_occ[occ]:.0%})")


if __name__ == "__main__":
    main()
