"""Run all hard validators on a TaskCandidate. Returns a unified report."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from pipeline.scenario.task_candidate import TaskCandidate
from pipeline.validators import ai_tells, citations, dates, financials

logger = logging.getLogger(__name__)


@dataclass
class ValidatorReport:
    candidate_id: str
    passed: bool
    failures: dict[str, list[str]] = field(default_factory=dict)
    warnings: dict[str, list[str]] = field(default_factory=dict)

    def reasons(self) -> str:
        out = []
        for k, v in self.failures.items():
            out.append(f"FAIL[{k}]: {'; '.join(v)}")
        return " | ".join(out)


def run_all(task: TaskCandidate, *, run_citations: bool = True) -> ValidatorReport:
    failures: dict[str, list[str]] = {}
    warnings: dict[str, list[str]] = {}

    ait = ai_tells.validate(task)
    if not ait.passed:
        failures["ai_tells"] = [f"{p}: '{txt}'" for p, txt in ait.hits]

    drep = dates.validate(task)
    if not drep.passed:
        failures["dates"] = drep.issues
    if drep.warnings:
        warnings["dates"] = drep.warnings

    frep = financials.validate(task)
    if not frep.passed:
        failures["financials"] = frep.issues
    if frep.warnings:
        warnings["financials"] = frep.warnings

    if run_citations and task.occupation == "lawyer":
        crep = citations.validate(task)
        if not crep.passed:
            failures["citations"] = [
                f"verified={crep.found}",
                f"not_found={crep.not_found}",
                f"skipped={crep.skipped}",
            ]
        elif crep.found or crep.not_found:
            warnings["citations"] = [
                f"verified={len(crep.found)}/{len(crep.found) + len(crep.not_found)}"
            ]

    return ValidatorReport(
        candidate_id=task.candidate_id,
        passed=not failures,
        failures=failures,
        warnings=warnings,
    )
