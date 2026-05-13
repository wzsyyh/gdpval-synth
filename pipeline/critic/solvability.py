"""Solvability critic: is there enough information in the task to actually do it?

A common synthesis failure: the prompt is realistic-sounding but missing
critical inputs (e.g. "use last quarter's revenue" without giving it). The
task becomes unsolvable in the GDPval sense — the deliverable can't be
fully scored against the rubric because key facts aren't available.

This is run by the SAME critic model as realism (Moonshot Kimi) but with a
different system prompt focused on completeness rather than aesthetics.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from pipeline.config import settings
from pipeline.llm import default_client
from pipeline.scenario.task_candidate import TaskCandidate

logger = logging.getLogger(__name__)


class SolvabilityScore(BaseModel):
    info_sufficient: int = Field(
        ge=1, le=10,
        description="Is enough info present in prompt + canonical facts to produce a passing deliverable? 10 = comprehensive. ≤5 = key info missing.",
    )
    rubric_satisfiable: int = Field(
        ge=1, le=10,
        description="What fraction of rubric items can be satisfied by a careful executor working only from prompt + canonical facts? 10 = all. ≤5 = rubric expects info that's not provided.",
    )
    ambiguity_appropriate: int = Field(
        ge=1, le=10,
        description="Real workplace tasks have *some* ambiguity. 10 = right amount of leftover ambiguity (1-2 minor judgment calls). ≤4 = either over-specified or under-specified.",
    )
    overall: int = Field(ge=1, le=10)
    missing_information: list[str] = Field(
        default_factory=list,
        description="Specific facts/values/conventions that the task implicitly assumes but does not provide. Empty if none.",
    )
    unsatisfiable_rubric_items: list[str] = Field(
        default_factory=list,
        description="Rubric items that cannot be satisfied with the given prompt + canonical facts. Empty if none.",
    )


_SOLVABILITY_SYS = """You are evaluating whether a generated task is *solvable* by a frontier LLM that has been given the task prompt + the canonical pinned facts AND can draw on its general training-time knowledge of the domain.

CRUCIAL — match GDPval's actual framing: real GDPval tasks routinely instruct "use publicly available data on the open web" or "based on your knowledge of [domain]" without providing all referenced data. The model is expected to fill from its training. So:

  - A task asking the model to discuss a real Ninth Circuit case is solvable if the case excerpt is in canonical facts OR the case is well-known enough that the model has read it during training.
  - A task asking for Q4 2025 financials of a public company is solvable if the prompt grounds it (gives a ticker / EDGAR pointer) — the model can recall public filings.
  - A task referencing pandas API behavior is solvable if the executor is a strong code model who has seen the pandas codebase.

What ACTUALLY makes a task unsolvable:
  - Required facts are PRIVATE and not derivable (e.g., "use the client's internal margin guidance" with no number given).
  - Rubric items require exact strings that aren't in the prompt or canonical facts ("include the exact paragraph 7 of the Defense's brief" when no brief is provided).
  - Logical contradictions in the prompt (asks for X using Y where Y excludes X).
  - Required input attachment that doesn't exist (prompt says "see attached spreadsheet" but no attachment exists).

What is FINE (do NOT count as unsolvable):
  - Public knowledge the model is expected to know (real cases, public companies, well-documented APIs, government regulations).
  - Reasoning the model needs to do (computing margins, drafting legal arguments, reviewing code).
  - Format expectations the model can satisfy by following instructions.

Output JSON SolvabilityScore. Calibration target: most well-formed GDPval-style tasks should score 7-8 here; only genuinely under-specified tasks should score ≤4.
"""


def critique(
    task: TaskCandidate,
    model: str | None = None,
) -> SolvabilityScore:
    client = default_client()
    model = model or settings().critic_model

    rubric_text = "\n".join(
        f"  [+{r.score}] {r.criterion}" for r in task.rubric
    )
    facts_text = "\n".join(
        f"  [{f.id}] {f.kind}: {str(f.value)[:300]}{(' ' + f.unit) if f.unit else ''}"
        for f in task.canonical.facts
    )

    user = (
        f"## Task prompt\n{task.prompt}\n\n"
        f"## Canonical pinned facts ({len(task.canonical.facts)})\n{facts_text}\n\n"
        f"## Rubric\n{rubric_text}\n\n"
        "Evaluate solvability and return JSON SolvabilityScore."
    )
    logger.info("solvability critique on %s using %s", task.candidate_id, model)
    return client.chat_structured(
        [
            {"role": "system", "content": _SOLVABILITY_SYS},
            {"role": "user", "content": user},
        ],
        SolvabilityScore,
        model=model,
        temperature=0.3,
        max_tokens=4096,
    )
