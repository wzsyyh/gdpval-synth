"""Re-judge gold files that have score=0.00 (judge failed due to token limits).

Reads existing deliverables from data/gold/*.json, re-runs judge with
max_tokens=8000 on each generation attempt, and updates the file if
a non-zero score is obtained.

Usage: uv run python scripts/rejudge_zeros.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.artifacts.best_of_n import _JUDGE_SYS, JudgeScore  # noqa: E402
from pipeline.config import DATA_DIR  # noqa: E402
from pipeline.llm import LLMClient, LLMError  # noqa: E402
from pipeline.scenario.task_candidate import TaskCandidate  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

GOLD_DIR = DATA_DIR / "gold"
ACCEPTED_DIR = DATA_DIR / "accepted"
JUDGE_MODEL = "deepseek/deepseek-v4-pro"
# Use more tokens so reasoning models can finish before outputting JSON.
JUDGE_MAX_TOKENS = 8000


def rejudge(gold_path: Path) -> bool:
    """Re-judge all_attempts in a score=0 gold file. Returns True if updated."""
    data = json.loads(gold_path.read_text())
    if data.get("gold_score", 0) > 0.0:
        return False  # Already has a real score.

    cand_id = data["candidate_id"]
    cand_path = ACCEPTED_DIR / f"{cand_id}.json"
    if not cand_path.exists():
        logger.warning("Candidate file missing: %s", cand_path)
        return False

    task = TaskCandidate.load(cand_path)
    rubric_text = "\n".join(
        f"  [+{r.score}] ({r.category}) {r.criterion}" for r in task.rubric
    )
    client = LLMClient()
    attempts = data.get("all_attempts", [])

    best_score = -1.0
    best_idx = 0
    any_scored = False

    for i, attempt in enumerate(attempts):
        deliverable = attempt.get("deliverable") or data.get("gold_deliverable") or ""
        if not deliverable:
            continue
        user = (
            f"## Task prompt\n{task.prompt}\n\n"
            f"## Rubric ({len(task.rubric)} items, {task.total_rubric_points()} total points)\n{rubric_text}\n\n"
            f"## Submitted deliverable\n{deliverable[:20000]}\n\n"
            "Score this deliverable. Return JSON JudgeScore."
        )
        try:
            js: JudgeScore = client.chat_structured(
                [
                    {"role": "system", "content": _JUDGE_SYS},
                    {"role": "user", "content": user},
                ],
                JudgeScore,
                model=JUDGE_MODEL,
                temperature=0.2,
                max_tokens=JUDGE_MAX_TOKENS,
            )
            score = js.rubric_satisfaction
            logger.info("  attempt %d (%s): %.2f", i, attempt.get("model", "?"), score)
            if score > best_score:
                best_score = score
                best_idx = i
            any_scored = True
        except LLMError as e:
            logger.warning("  attempt %d judge failed: %s", i, e)

    if not any_scored or best_score <= 0.0:
        logger.info("%s: still no score after rejudge", cand_id)
        return False

    # Update the gold file.
    best_attempt = attempts[best_idx]
    data["gold_score"] = best_score
    data["gold_model"] = best_attempt.get("model", "?")
    data["gold_deliverable"] = best_attempt.get("deliverable", data.get("gold_deliverable", ""))
    gold_path.write_text(json.dumps(data, indent=2))
    logger.info("%s: updated score=%.2f model=%s", cand_id, best_score, data["gold_model"])
    return True


def main() -> None:
    zero_files = [
        f for f in GOLD_DIR.glob("*.json")
        if json.loads(f.read_text()).get("gold_score", 0) == 0.0
    ]
    logger.info("Found %d gold files with score=0.00", len(zero_files))
    updated = 0
    for f in zero_files:
        logger.info("Rejudging %s ...", f.name)
        if rejudge(f):
            updated += 1
    logger.info("Done: %d/%d updated", updated, len(zero_files))


if __name__ == "__main__":
    main()
