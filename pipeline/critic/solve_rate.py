"""Solve-rate probe: is the task too easy for frontier models?

For each candidate, ask three cross-family frontier models to predict their
expected score on the task's rubric — without actually producing the
deliverable. Models that confidently predict >7/10 indicate the task is
too easy / too prescribed and should be rejected.

This is the central GDPval-difficulty filter. Real GDPval tasks see frontier
models lose to humans 50%+ of the time; if our synthetic tasks are easily
solvable, we've drifted off-distribution.

Three-model probe matters: a single model rating a task low could be that
model's blind spot; if all three say >7/10, the task really is easy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field

from pipeline.config import settings
from pipeline.llm import LLMError, default_client
from pipeline.scenario.task_candidate import TaskCandidate

logger = logging.getLogger(__name__)


class SolveRateEstimate(BaseModel):
    expected_score: int = Field(
        ge=1, le=10,
        description="Your predicted self-score on this task's rubric, 1-10. Be calibrated, not optimistic.",
    )
    most_at_risk_criteria: list[str] = Field(
        default_factory=list,
        description="≤4 specific rubric items you'd be most likely to miss or fail.",
    )
    confidence: int = Field(
        ge=1, le=10,
        description="How confident are you in your self-assessment? 10 = high confidence.",
    )


_PROBE_SYS = """You are predicting how well YOU specifically would do on this professional task. Be calibrated and self-aware.

You will see the task prompt and rubric. WITHOUT actually producing the deliverable, estimate your expected total score (as a self-rating 1-10).

Real GDPval tasks are hard: frontier models like you score around 4-7/10 on average against human experts. If you predict 9 or 10, you're being overconfident. If you predict 1-3, you're being false-modest.

Hard rules:
- Do NOT produce any part of the deliverable.
- Do NOT explain step-by-step how you would solve it.
- Output ONLY the JSON SolveRateEstimate.
- Be honest about what you'd miss: format requirements, specific citations, exact-value rubric items.
"""


@dataclass
class SolveRateReport:
    candidate_id: str
    estimates: list[tuple[str, SolveRateEstimate]]  # (model, estimate)
    max_score: int
    mean_score: float
    rejected: bool
    rejection_reason: str | None


def probe(
    task: TaskCandidate,
    *,
    models: list[str] | None = None,
    reject_threshold: int = 7,
) -> SolveRateReport:
    """Run the probe across N cross-family models. Reject if max ≥ threshold."""
    client = default_client()
    models = models or settings().solve_rate_models

    rubric_text = "\n".join(
        f"  [+{r.score}] {r.criterion}" for r in task.rubric
    )
    user = (
        f"## Task prompt\n{task.prompt}\n\n"
        f"## Rubric ({len(task.rubric)} items, {task.total_rubric_points()} total points)\n{rubric_text}\n\n"
        "Predict your expected score and return JSON SolveRateEstimate."
    )

    estimates: list[tuple[str, SolveRateEstimate]] = []
    for model in models:
        try:
            est = client.chat_structured(
                [
                    {"role": "system", "content": _PROBE_SYS},
                    {"role": "user", "content": user},
                ],
                SolveRateEstimate,
                model=model,
                temperature=0.4,
                max_tokens=800,
            )
            estimates.append((model, est))
            logger.info("  %s: %d/10 (conf %d)", model, est.expected_score, est.confidence)
        except LLMError as e:
            logger.warning("solve-rate probe failed for %s: %s", model, e)
            continue

    if not estimates:
        return SolveRateReport(
            candidate_id=task.candidate_id,
            estimates=[],
            max_score=0,
            mean_score=0.0,
            rejected=False,
            rejection_reason="all probes failed; not rejecting",
        )

    scores = [e.expected_score for _, e in estimates]
    max_s = max(scores)
    mean_s = sum(scores) / len(scores)

    rejected = max_s >= reject_threshold
    reason = None
    if rejected:
        worst_model = max(estimates, key=lambda x: x[1].expected_score)
        reason = f"{worst_model[0]} predicted {worst_model[1].expected_score}/10 (≥{reject_threshold})"

    return SolveRateReport(
        candidate_id=task.candidate_id,
        estimates=estimates,
        max_score=max_s,
        mean_score=mean_s,
        rejected=rejected,
        rejection_reason=reason,
    )
