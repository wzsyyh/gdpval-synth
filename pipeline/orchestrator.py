"""Production orchestrator — generate N candidates across the diversity grid.

Pipeline per cell:
  1. Pick a real seed appropriate to the cell (seeds.selector)
  2. Synthesize TaskCandidate (3 LLM stages)
  3. Run full quality funnel (5 stages, fail-fast)
  4. Save accepted to data/accepted/, rejected to data/rejected/

Parallelism: ThreadPoolExecutor with 8 workers. Our LLMClient is httpx-sync,
so threading suffices and avoids async/await refactor. The OpenRouter API
handles concurrency well; bottleneck is per-request latency, not contention.

Funnel results are appended to data/funnel_log.jsonl regardless of outcome,
which is what the writeup uses to plot the reject-rate funnel chart.
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
from pipeline.critic.funnel import FunnelResult, evaluate
from pipeline.diversity.grid import CellAssignment, build_grid, coverage_stats
from pipeline.scenario.synthesis import synthesize_task
from pipeline.scenario.task_candidate import TaskCandidate
from pipeline.seeds.base import Seed
from pipeline.seeds.selector import select as select_seed

logger = logging.getLogger(__name__)


@dataclass
class RunOutcome:
    cell_index: int
    occupation: str
    deliverable_id: str
    archetype: str
    difficulty: str
    seed_id: str | None
    candidate_id: str | None
    accepted: bool
    rejection_reason: str | None
    elapsed_s: float
    error: str | None = None


def _process_cell(
    idx: int,
    cell: CellAssignment,
    used_seeds: set[str],
    used_lock,
    *,
    skip_solve_rate: bool,
    skip_citations: bool,
) -> tuple[RunOutcome, FunnelResult | None]:
    t0 = time.time()
    rng = random.Random((idx * 17) + 99991)
    with used_lock:
        seed = select_seed(cell.occupation, cell.archetype, cell.difficulty, used=used_seeds, rng=rng)
        if seed:
            used_seeds.add(seed.seed_id)
    if seed is None:
        return RunOutcome(
            cell_index=idx,
            occupation=cell.occupation,
            deliverable_id=cell.deliverable_id,
            archetype=cell.archetype,
            difficulty=cell.difficulty.value,
            seed_id=None,
            candidate_id=None,
            accepted=False,
            rejection_reason="no available seed",
            elapsed_s=round(time.time() - t0, 1),
        ), None

    try:
        task = synthesize_task(seed, cell.deliverable_id, cell.archetype, cell.difficulty, rng=rng)
    except Exception as e:
        logger.exception("synthesis failed for cell %d", idx)
        return RunOutcome(
            cell_index=idx,
            occupation=cell.occupation,
            deliverable_id=cell.deliverable_id,
            archetype=cell.archetype,
            difficulty=cell.difficulty.value,
            seed_id=seed.seed_id,
            candidate_id=None,
            accepted=False,
            rejection_reason=None,
            elapsed_s=round(time.time() - t0, 1),
            error=f"synthesis: {type(e).__name__}: {e}",
        ), None

    # Save candidate first (we keep both accepted and rejected for the gallery).
    task.save(DATA_DIR / "candidates")

    # Run funnel.
    try:
        funnel = evaluate(task, skip_solve_rate=skip_solve_rate, skip_citations=skip_citations)
    except Exception as e:
        logger.exception("funnel crashed for cell %d", idx)
        return RunOutcome(
            cell_index=idx,
            occupation=cell.occupation,
            deliverable_id=cell.deliverable_id,
            archetype=cell.archetype,
            difficulty=cell.difficulty.value,
            seed_id=seed.seed_id,
            candidate_id=task.candidate_id,
            accepted=False,
            rejection_reason=None,
            elapsed_s=round(time.time() - t0, 1),
            error=f"funnel: {type(e).__name__}: {e}",
        ), None

    target_dir = DATA_DIR / ("accepted" if funnel.accepted else "rejected")
    target_dir.mkdir(parents=True, exist_ok=True)
    task.save(target_dir)

    # NEW: Render real deliverable file from blueprint (for accepted tasks)
    deliverable_meta = None
    if funnel.accepted and task.canonical.reference_answer:
        try:
            deliverable_meta = materialize_deliverable(task)
            task.gold_deliverable_path = deliverable_meta["file_path"]
            logger.info("  rendered deliverable: %s (%d bytes)", deliverable_meta["file_path"], deliverable_meta["file_size"])
        except Exception as e:
            logger.warning("deliverable rendering failed for %s: %s", task.candidate_id, e)

        # Render input attachments
        for att in (task.canonical.reference_answer.input_attachments or []):
            try:
                att_path = render_input_attachment(att, target_dir / task.candidate_id)
                task.input_attachment_paths.append(str(att_path))
                logger.info("  rendered attachment: %s", att_path)
            except Exception as e:
                logger.warning("attachment rendering failed for %s: %s", att.attachment_id, e)

        # Re-save with paths
        task.save(target_dir)

    return RunOutcome(
        cell_index=idx,
        occupation=cell.occupation,
        deliverable_id=cell.deliverable_id,
        archetype=cell.archetype,
        difficulty=cell.difficulty.value,
        seed_id=seed.seed_id,
        candidate_id=task.candidate_id,
        accepted=funnel.accepted,
        rejection_reason=funnel.rejection_reason,
        elapsed_s=round(time.time() - t0, 1),
    ), funnel


def run(
    n: int = 60,
    *,
    workers: int = 8,
    grid_seed: int = 42,
    skip_solve_rate: bool = True,
    skip_citations: bool = False,
) -> list[RunOutcome]:
    grid = build_grid(n, seed=grid_seed)
    logger.info("grid built: %s", json.dumps(coverage_stats(grid), indent=2))

    used_seeds: set[str] = set()
    used_lock = __import__("threading").Lock()

    outcomes: list[RunOutcome] = []
    funnel_pass = 0
    funnel_fail = 0
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _process_cell, i, cell, used_seeds, used_lock,
                skip_solve_rate=skip_solve_rate, skip_citations=skip_citations,
            ): i
            for i, cell in enumerate(grid)
        }
        for fut in as_completed(futures):
            outcome, _funnel = fut.result()
            outcomes.append(outcome)
            tag = "✓" if outcome.accepted else "✗"
            elapsed_total = time.time() - t_start
            if outcome.accepted:
                funnel_pass += 1
            else:
                funnel_fail += 1
            logger.info(
                "[%2d/%d] %s %s/%s/%s %ss   %s",
                len(outcomes), len(grid), tag,
                outcome.occupation, outcome.deliverable_id, outcome.difficulty,
                outcome.elapsed_s,
                outcome.rejection_reason or outcome.error or "ACCEPTED",
            )
            logger.info("  pass=%d fail=%d  total wall=%.1fs", funnel_pass, funnel_fail, elapsed_total)

    # Write run summary
    summary = {
        "ts": time.time(),
        "n": n,
        "workers": workers,
        "accepted": funnel_pass,
        "rejected": funnel_fail,
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
    p.add_argument("--skip-solve-rate", action="store_true", help="skip the 3-model probe (faster)")
    p.add_argument("--skip-citations", action="store_true", help="skip CourtListener API check")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Quiet down noisy libs.
    for noisy in ("httpx", "httpcore", "huggingface_hub", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    outcomes = run(
        n=args.n,
        workers=args.workers,
        grid_seed=args.grid_seed,
        skip_solve_rate=args.skip_solve_rate,
        skip_citations=args.skip_citations,
    )
    accepted = sum(1 for o in outcomes if o.accepted)
    print(f"\n{'=' * 80}\nDONE: {accepted}/{len(outcomes)} accepted ({accepted / len(outcomes):.0%})\n{'=' * 80}")
    # Per-occupation breakdown.
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
