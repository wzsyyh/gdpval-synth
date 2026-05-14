"""Hard quality validators — cheap, deterministic checks that filter out low-quality tasks.

These are NOT LLM-based. They check structural properties that every GDPval-quality task
must satisfy. Tasks failing these checks are rejected immediately without expensive validation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from pipeline.scenario.task_candidate import TaskCandidate
from pipeline.seeds.base import Seed

logger = logging.getLogger(__name__)


@dataclass
class HardQualityReport:
    passed: bool
    issues: list[str] = field(default_factory=list)
    metrics: dict[str, int | float | bool] = field(default_factory=dict)


# ─────────────────────────── Checks ───────────────────────────


def _check_prompt_length(task: TaskCandidate, min_chars: int = 1300) -> str | None:
    length = len(task.prompt)
    if length < min_chars:
        return f"prompt too short: {length} chars (min {min_chars})"
    return None


def _check_rubric_count(task: TaskCandidate, min_items: int = 35, max_items: int = 80) -> str | None:
    n = len(task.rubric)
    if n < min_items:
        return f"rubric too small: {n} items (min {min_items})"
    if n > max_items:
        return f"rubric too large: {n} items (max {max_items})"
    return None


def _check_expected_values(task: TaskCandidate, min_items: int = 3) -> str | None:
    ref = task.canonical.reference_answer
    evs = ref.expected_values if ref else []
    n = len(evs)
    if n < min_items:
        return f"expected_values too few: {n} (min {min_items})"
    return None


def _check_score_distribution(task: TaskCandidate) -> str | None:
    """Ensure rubric score distribution is reasonable (no single score dominates >80%)."""
    from collections import Counter

    if not task.rubric:
        return "empty rubric"
    scores = Counter(r.score for r in task.rubric)
    total = len(task.rubric)
    for score, count in scores.items():
        if count / total > 0.85:
            return f"score distribution skewed: +{score} accounts for {count}/{total} ({count/total:.0%})"
    return None


def _check_rubric_style(task: TaskCandidate) -> str | None:
    """Ensure rubric items are specific and verifiable (not vague)."""
    vague_patterns = [
        r"is (good|well|appropriately|correctly)",
        r"demonstrates (understanding|knowledge|competence)",
        r"quality (is|of)",
        r"professional (tone|manner)",
    ]
    vague_count = 0
    for r in task.rubric:
        crit = r.criterion.lower()
        for pat in vague_patterns:
            if re.search(pat, crit):
                vague_count += 1
                break
    if vague_count > len(task.rubric) * 0.3:
        return f"rubric too vague: {vague_count}/{len(task.rubric)} items use subjective language"
    return None


def _check_attachment_quality(task: TaskCandidate) -> str | None:
    """Ensure input attachments have actual content."""
    ref = task.canonical.reference_answer
    if not ref:
        return None
    atts = ref.input_attachments or []
    for att in atts:
        blueprint = att.content_blueprint or {}
        body = blueprint.get("body", "")
        if len(body) < 100:
            return f"attachment {att.attachment_id} body too short: {len(body)} chars"
    return None


def _check_answer_has_content(task: TaskCandidate) -> str | None:
    """Ensure the reference answer has actual body content, not just a header."""
    ref = task.canonical.reference_answer
    if not ref:
        return "no reference_answer"

    fmt = ref.format
    if fmt in ("docx", "pdf"):
        sections = ref.sections
        if not sections:
            return f"format={fmt} but sections is empty (only header/title generated)"
        total_paras = sum(len(s.paragraphs) for s in sections)
        if total_paras < 3:
            return f"format={fmt} but only {total_paras} paragraphs across {len(sections)} sections"
    elif fmt == "markdown":
        md_sections = ref.md_sections
        if not md_sections:
            return "format=markdown but md_sections is empty"
        total_paras = sum(len(s.paragraphs) for s in md_sections)
        if total_paras < 3:
            return f"format=markdown but only {total_paras} paragraphs"
    elif fmt == "xlsx":
        sheets = ref.sheets
        if not sheets:
            return "format=xlsx but sheets is empty"
    return None


# ─────────────────────────── Public API ───────────────────────────


def validate(task: TaskCandidate, _seed: Seed) -> HardQualityReport:
    """Run all hard quality checks."""
    issues: list[str] = []
    metrics: dict[str, int | float | bool] = {}

    ref = task.canonical.reference_answer
    evs = ref.expected_values if ref else []

    metrics["prompt_length"] = len(task.prompt)
    metrics["rubric_count"] = len(task.rubric)
    metrics["expected_values_count"] = len(evs)
    metrics["has_attachments"] = bool(evs and ref and ref.input_attachments)

    checks = [
        _check_prompt_length(task),
        _check_rubric_count(task),
        _check_expected_values(task),
        _check_score_distribution(task),
        _check_rubric_style(task),
        _check_attachment_quality(task),
        _check_answer_has_content(task),
    ]

    for issue in checks:
        if issue:
            issues.append(issue)
            logger.warning("hard quality fail: %s", issue)

    passed = len(issues) == 0
    metrics["passed"] = passed

    logger.info(
        "hard quality: prompt=%d rubric=%d ev=%d → %s",
        metrics["prompt_length"],
        metrics["rubric_count"],
        metrics["expected_values_count"],
        "PASS" if passed else f"FAIL ({len(issues)} issues)",
    )

    return HardQualityReport(passed=passed, issues=issues, metrics=metrics)
