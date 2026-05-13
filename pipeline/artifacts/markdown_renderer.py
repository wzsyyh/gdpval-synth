"""Markdown deliverable renderer.

Used for SWE design docs, code reviews, postmortems. Direct LLM output —
markdown is a text format, no structured planning needed.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pipeline.artifacts.base import PLANNER_MODEL, deliverable_dir
from pipeline.llm import default_client
from pipeline.scenario.task_candidate import TaskCandidate

logger = logging.getLogger(__name__)


_MD_SYS = """You are a senior {occupation_title} producing a high-quality professional deliverable. You will receive:
  1. The full task prompt
  2. The canonical scenario state (real entities, dates, citations)
  3. The grading rubric

Produce the deliverable as a single Markdown document. The rubric is your contract — every criterion that can be satisfied by your document MUST be satisfied. Be concrete, specific, and grounded in the canonical facts.

Hard rules:
- Reference canonical facts by their actual values (real names, real numbers, real PR/issue numbers).
- Match the EXACT format requirements: headings, sections, file structure described in the rubric.
- For code blocks, include realistic code (not pseudocode). Use the languages and frameworks that match the project.
- For benchmarks/numbers in technical docs, give plausible specific values with units.
- DO NOT include AI hedging ("I would recommend", "it might be useful to consider"). Write with authority.
- Length: this should be a substantial deliverable (1500-5000 words for design docs, postmortems, code reviews).

Output: a single markdown document. No preamble, no closing remarks. Start at the first heading.
"""


def render_markdown(task: TaskCandidate, model: str = PLANNER_MODEL) -> Path:
    client = default_client()
    occupation_title = {
        "lawyer": "lawyer",
        "financial_analyst": "investment banking analyst",
        "software_engineer": "senior software engineer",
    }[task.occupation]

    sys_prompt = _MD_SYS.format(occupation_title=occupation_title)
    rubric_text = "\n".join(
        f"  [+{r.score}] ({r.category}) {r.criterion}" for r in task.rubric
    )
    user = (
        f"## Task prompt\n{task.prompt}\n\n"
        f"## Canonical scenario state\n{task.canonical.context_for_agent()}\n\n"
        f"## Rubric (every criterion you can satisfy, you MUST satisfy)\n{rubric_text}\n\n"
        f"Produce the deliverable as a markdown document now."
    )
    logger.info("rendering markdown deliverable for %s with %s", task.candidate_id, model)
    content, _ = client.chat(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user},
        ],
        model=model,
        temperature=0.5,
        max_tokens=8000,
    )

    out_dir = deliverable_dir(task.candidate_id)
    fname = f"{task.deliverable.deliverable_id}.md"
    out_path = out_dir / fname
    out_path.write_text(content)
    logger.info("  wrote %d chars → %s", len(content), out_path)
    return out_path
