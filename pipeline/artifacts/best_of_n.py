"""Best-of-N gold deliverable generation + LLM-as-judge selection.

For each accepted task:
  1. Generate N candidate deliverables using N different generator models
     (cross-family for diversity).
  2. Score each candidate against the rubric using a separate LLM judge
     (also cross-family from the generators).
  3. Keep the highest-scoring one as the "gold" deliverable.

Output: data/gold/{candidate_id}.json containing
  {
    "candidate_id": ...,
    "gold_deliverable": "...markdown text...",
    "gold_score": float,
    "gold_model": str,
    "all_attempts": [{"model": str, "score": float, "deliverable": str}, ...]
  }

These (prompt, gold_deliverable) pairs are the SFT corpus.

Scope decision: we render all deliverables as markdown text (regardless of
the task's `primary_format`), because:
  - Markdown is universal — captures legal memos, design docs, financial
    analysis text, and structured spreadsheets-as-tables.
  - SFT training is text-in / text-out; binary file outputs would require
    decoding which adds complexity without benefit for the SFT signal.
  - The deliverable's role here is training data, not a downloadable artifact.
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from pathlib import Path

from pydantic import BaseModel, Field

from pipeline.config import DATA_DIR
from pipeline.llm import LLMClient, LLMError, default_client
from pipeline.scenario.task_candidate import TaskCandidate

logger = logging.getLogger(__name__)

GOLD_DIR = DATA_DIR / "gold"
GOLD_DIR.mkdir(parents=True, exist_ok=True)


# Three cross-family generators with diverse training corpora.
GENERATOR_MODELS = [
    "deepseek/deepseek-v4-pro",
    "moonshotai/kimi-k2.6",
    "xiaomi/mimo-v2.5-pro",
]

# Judge: a fourth model, ideally yet another family.
JUDGE_MODEL = "deepseek/deepseek-v4-pro"


_GEN_SYS = """You are a senior {occupation_title} producing a high-quality professional deliverable. You will receive:
  1. The full task prompt
  2. The canonical scenario state (real entities, dates, citations) — these are AUTHORITATIVE; do not invent alternatives
  3. The grading rubric — your output will be scored against it

Hard rules:
- Reference canonical facts by their actual values (real names, real numbers, real PR/issue numbers).
- The rubric is your contract — every criterion that can be satisfied by your document MUST be satisfied.
- For technical work (code, financial models): produce specific numbers, real method/file references, plausible benchmark figures.
- DO NOT include AI hedging ("I would recommend", "it might be useful to consider"). Write with authority.
- Length: substantial professional deliverable (2000-6000 words for design docs, postmortems, code reviews, briefs, memos).
- Output as a single Markdown document. For spreadsheet-style deliverables, use markdown tables.

Output: a single markdown document. No preamble, no closing remarks. Start at the first heading or the body text.
"""


class JudgeScore(BaseModel):
    rubric_satisfaction: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of total rubric points achieved (0.0–1.0). Score by going through each criterion and granting points if satisfied."
    )
    strengths: list[str] = Field(default_factory=list, description="≤3 specific things the deliverable does well.")
    weaknesses: list[str] = Field(default_factory=list, description="≤3 specific gaps or errors in this deliverable.")


_JUDGE_SYS = """You are an expert evaluator scoring a generated deliverable against its rubric. Be calibrated and ruthless.

For each rubric item, decide whether the deliverable satisfies it (or substantially does). Sum the points awarded, divide by total possible points, that is `rubric_satisfaction`.

Common evaluator failure modes to avoid:
- Don't grant credit for criteria the deliverable does not actually meet (look for the specific element).
- For "judgment" items (qualitative), grant credit only if the deliverable presents a clear, justified position — not a hedged equivocation.
- For "accuracy" items requiring specific values, grant credit only if the value appears (or substantively equivalent).
- A single deliverable rarely satisfies >85% of rubric points.

Output JSON JudgeScore.
"""


def _generate_one(
    task: TaskCandidate, model: str, client: LLMClient
) -> tuple[str, str, float] | tuple[str, None, float]:
    """Generate one deliverable. Returns (model, content, elapsed_s) or (model, None, elapsed_s)."""
    occupation_title = {
        "lawyer": "lawyer",
        "financial_analyst": "investment banking analyst",
        "software_engineer": "senior software engineer",
    }[task.occupation]
    sys_prompt = _GEN_SYS.format(occupation_title=occupation_title)
    rubric_text = "\n".join(
        f"  [+{r.score}] ({r.category}) {r.criterion}" for r in task.rubric
    )
    user = (
        f"## Task prompt\n{task.prompt}\n\n"
        f"## Canonical scenario state\n{task.canonical.context_for_agent()}\n\n"
        f"## Rubric\n{rubric_text}\n\n"
        f"Produce the deliverable now."
    )
    t0 = time.time()
    try:
        content, _ = client.chat(
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user},
            ],
            model=model,
            temperature=0.6,
            max_tokens=8000,
        )
        return model, content.strip(), round(time.time() - t0, 1)
    except LLMError as e:
        logger.warning("generation failed for %s on %s: %s", task.candidate_id, model, e)
        return model, None, round(time.time() - t0, 1)


def _judge_one(
    task: TaskCandidate, deliverable: str, client: LLMClient, model: str = JUDGE_MODEL
) -> JudgeScore | None:
    rubric_text = "\n".join(
        f"  [+{r.score}] ({r.category}) {r.criterion}" for r in task.rubric
    )
    user = (
        f"## Task prompt\n{task.prompt}\n\n"
        f"## Rubric ({len(task.rubric)} items, {task.total_rubric_points()} total points)\n{rubric_text}\n\n"
        f"## Submitted deliverable\n{deliverable}\n\n"
        "Score this deliverable. Return JSON JudgeScore."
    )
    try:
        return client.chat_structured(
            [
                {"role": "system", "content": _JUDGE_SYS},
                {"role": "user", "content": user},
            ],
            JudgeScore,
            model=model,
            temperature=0.2,
            max_tokens=4000,
        )
    except LLMError as e:
        logger.warning("judge failed for %s: %s", task.candidate_id, e)
        return None


def best_of_n(
    task: TaskCandidate,
    *,
    generators: list[str] = GENERATOR_MODELS,
    judge: str = JUDGE_MODEL,
    parallel_gen: bool = True,
) -> dict:
    client = default_client()

    # Generate N candidates in parallel.
    attempts: list[dict] = []
    if parallel_gen:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(generators)) as pool:
            futures = [pool.submit(_generate_one, task, m, client) for m in generators]
            for fut in concurrent.futures.as_completed(futures):
                model, content, elapsed = fut.result()
                attempts.append({"model": model, "deliverable": content, "gen_elapsed_s": elapsed})
    else:
        for m in generators:
            model, content, elapsed = _generate_one(task, m, client)
            attempts.append({"model": model, "deliverable": content, "gen_elapsed_s": elapsed})

    # Judge each (sequentially, judge is a single model).
    for a in attempts:
        if not a["deliverable"]:
            a["score"] = -1.0
            a["strengths"] = []
            a["weaknesses"] = ["generation failed"]
            continue
        js = _judge_one(task, a["deliverable"], client, model=judge)
        if js is None:
            a["score"] = 0.0
            a["strengths"] = []
            a["weaknesses"] = ["judge failed"]
        else:
            a["score"] = js.rubric_satisfaction
            a["strengths"] = js.strengths
            a["weaknesses"] = js.weaknesses

    # Pick the best.
    best = max(attempts, key=lambda a: a["score"])

    return {
        "candidate_id": task.candidate_id,
        "gold_model": best["model"],
        "gold_score": best["score"],
        "gold_deliverable": best["deliverable"],
        "gold_strengths": best.get("strengths", []),
        "gold_weaknesses": best.get("weaknesses", []),
        "all_attempts": [
            {
                "model": a["model"],
                "score": a["score"],
                "gen_elapsed_s": a["gen_elapsed_s"],
                "deliverable_chars": len(a["deliverable"]) if a["deliverable"] else 0,
                "strengths": a.get("strengths", []),
                "weaknesses": a.get("weaknesses", []),
            }
            for a in attempts
        ],
    }


def materialize_gold(task: TaskCandidate) -> dict:
    """Run best_of_n and persist the result to disk."""
    out_path = GOLD_DIR / f"{task.candidate_id}.json"
    if out_path.exists():
        import json
        return json.loads(out_path.read_text())
    result = best_of_n(task)
    import json
    out_path.write_text(json.dumps(result, indent=2))
    logger.info(
        "  gold for %s: %s @ %.2f (%d chars)",
        task.candidate_id, result["gold_model"], result["gold_score"],
        len(result["gold_deliverable"]) if result["gold_deliverable"] else 0,
    )
    return result
