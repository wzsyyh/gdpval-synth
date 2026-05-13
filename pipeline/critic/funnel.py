"""End-to-end quality funnel for a TaskCandidate.

Stages, in order (each gates the next — fail-fast on cheap stages):

  1. Hard validators       (no LLM)         — citations, dates, AI-tells, financials
  2. Embedding dedup       (local model)    — reject if too close to real GDPval
  3. Realism critic        (1 LLM call)     — Moonshot Kimi
  4. Solvability critic    (1 LLM call)     — Moonshot Kimi
  5. Solve-rate probe      (3 LLM calls)    — DeepSeek Pro / Xiaomi MiMo / Moonshot Kimi

Output: FunnelResult with pass/fail and per-stage scores. Final dataset
exports include only candidates that pass ALL stages.

For Day-5 production runs we'll process candidates in parallel batches.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pipeline.config import DATA_DIR
from pipeline.critic import realism, solvability, solve_rate
from pipeline.diversity import embed_dedup
from pipeline.scenario.task_candidate import TaskCandidate
from pipeline.validators.runner import run_all as run_hard_validators

logger = logging.getLogger(__name__)


_FUNNEL_LOG = DATA_DIR / "funnel_log.jsonl"


@dataclass
class FunnelResult:
    candidate_id: str
    stage_passed: str   # name of the last stage passed
    accepted: bool
    rejection_reason: str | None
    timings: dict[str, float] = field(default_factory=dict)

    # Per-stage details (None if not run)
    hard_validator_failures: dict | None = None
    dedup_max_similarity: float | None = None
    dedup_matched_real_id: str | None = None
    realism_overall: int | None = None
    realism_breakdown: dict | None = None
    solvability_overall: int | None = None
    solvability_breakdown: dict | None = None
    solve_rate_max: int | None = None
    solve_rate_mean: float | None = None
    solve_rate_estimates: list[dict] = field(default_factory=list)


# Thresholds — calibrated empirically; documented in the writeup.
# 0.85 catches near-paraphrases without rejecting same-domain novelty:
# we observed legitimate same-occupation tasks landing at ~0.79; pure paraphrases >0.90.
DEDUP_THRESHOLD = 0.85
REALISM_MIN = 5  # overall realism ≥ 5 (single-critic scale; 5 = "borderline ok")
SOLVABILITY_MIN = 5
SOLVE_RATE_MAX = 7  # if any model predicts ≥7, task is too easy → reject


def _log(result: FunnelResult) -> None:
    _FUNNEL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _FUNNEL_LOG.open("a") as f:
        f.write(json.dumps({**asdict(result), "ts": time.time()}, default=str) + "\n")


def evaluate(
    task: TaskCandidate,
    *,
    skip_solve_rate: bool = False,
    skip_citations: bool = False,
) -> FunnelResult:
    """Run the full funnel on one candidate. Returns FunnelResult."""
    res = FunnelResult(
        candidate_id=task.candidate_id,
        stage_passed="none",
        accepted=False,
        rejection_reason=None,
    )

    # Stage 1 — Hard validators
    t0 = time.time()
    hv = run_hard_validators(task, run_citations=not skip_citations)
    res.timings["hard_validators"] = round(time.time() - t0, 2)
    if not hv.passed:
        res.rejection_reason = f"hard validators failed: {hv.reasons()}"
        res.hard_validator_failures = hv.failures
        _log(res)
        return res
    res.stage_passed = "hard_validators"
    res.hard_validator_failures = hv.failures  # may have warnings but no failures

    # Stage 2 — Dedup against real GDPval
    t0 = time.time()
    is_close, max_sim, matched_id = embed_dedup.too_close_to_reference(
        task.prompt, threshold=DEDUP_THRESHOLD
    )
    res.timings["dedup"] = round(time.time() - t0, 2)
    res.dedup_max_similarity = max_sim
    res.dedup_matched_real_id = matched_id
    if is_close:
        res.rejection_reason = f"too close to real GDPval task {matched_id} (sim={max_sim:.3f})"
        _log(res)
        return res
    res.stage_passed = "dedup"

    # Stage 3 — Realism critic
    t0 = time.time()
    try:
        rscore = realism.critique(task)
    except Exception as e:
        res.rejection_reason = f"realism critic crashed at stage=realism: {e}"
        res.timings["realism"] = round(time.time() - t0, 2)
        _log(res)
        return res
    res.timings["realism"] = round(time.time() - t0, 2)
    res.realism_overall = rscore.overall
    res.realism_breakdown = {
        "workplace_voice": rscore.workplace_voice,
        "domain_specificity": rscore.domain_specificity,
        "rubric_quality": rscore.rubric_quality,
        "fact_grounding": rscore.fact_grounding,
        "issues": rscore.issues,
        "suggestions": rscore.suggestions,
    }
    if rscore.overall < REALISM_MIN:
        res.rejection_reason = f"realism overall={rscore.overall} < {REALISM_MIN}"
        _log(res)
        return res
    res.stage_passed = "realism"

    # Stage 4 — Solvability critic
    t0 = time.time()
    try:
        sscore = solvability.critique(task)
    except Exception as e:
        res.rejection_reason = f"solvability critic crashed: {e}"
        _log(res)
        return res
    res.timings["solvability"] = round(time.time() - t0, 2)
    res.solvability_overall = sscore.overall
    res.solvability_breakdown = {
        "info_sufficient": sscore.info_sufficient,
        "rubric_satisfiable": sscore.rubric_satisfiable,
        "ambiguity_appropriate": sscore.ambiguity_appropriate,
        "missing_information": sscore.missing_information,
        "unsatisfiable_rubric_items": sscore.unsatisfiable_rubric_items,
    }
    if sscore.overall < SOLVABILITY_MIN:
        res.rejection_reason = f"solvability overall={sscore.overall} < {SOLVABILITY_MIN}"
        _log(res)
        return res
    res.stage_passed = "solvability"

    # Stage 5 — Solve-rate probe (3 cross-family models)
    if not skip_solve_rate:
        t0 = time.time()
        try:
            srep = solve_rate.probe(task, reject_threshold=SOLVE_RATE_MAX)
        except Exception as e:
            res.rejection_reason = f"solve-rate probe crashed: {e}"
            _log(res)
            return res
        res.timings["solve_rate"] = round(time.time() - t0, 2)
        res.solve_rate_max = srep.max_score
        res.solve_rate_mean = round(srep.mean_score, 2)
        res.solve_rate_estimates = [
            {"model": m, "score": e.expected_score, "confidence": e.confidence}
            for m, e in srep.estimates
        ]
        if srep.rejected:
            res.rejection_reason = srep.rejection_reason
            _log(res)
            return res
        res.stage_passed = "solve_rate"

    res.accepted = True
    _log(res)
    return res
