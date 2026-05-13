"""Date / timeline consistency validator.

Catches scenarios where:
  - The deadline is before the assignment date (impossible).
  - A precedent / reference event is dated AFTER the scenario "now".
  - Timeline events have stale dates (>2 years before today, suggesting the
    scenario was generated against an old seed and now reads as outdated).

Soft-fail: "stale" warnings don't reject; only hard impossibilities do.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from pipeline.scenario.task_candidate import TaskCandidate


@dataclass
class DateReport:
    passed: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate(task: TaskCandidate) -> DateReport:
    issues: list[str] = []
    warnings: list[str] = []
    timeline = {ev.id: ev for ev in task.canonical.timeline}

    assignment = timeline.get("assignment")
    deadline = timeline.get("deadline")
    if assignment and deadline:
        if deadline.date < assignment.date:
            issues.append(
                f"deadline ({deadline.date}) is before assignment ({assignment.date})"
            )

    # The "scenario now" is approximated by the assignment date.
    scenario_now = assignment.date if assignment else date.today()

    # Reference / precedent events must not be in the future relative to scenario_now.
    for ev in task.canonical.timeline:
        if ev.id in ("assignment", "deadline"):
            continue
        if ev.date > scenario_now:
            issues.append(
                f"reference event {ev.id} ({ev.date}) is after scenario now ({scenario_now})"
            )

    # Stale-seed warning: any reference event >5 years older than today.
    five_years_ago = date.today() - timedelta(days=5 * 365)
    for ev in task.canonical.timeline:
        if ev.id in ("assignment", "deadline"):
            continue
        if ev.date < five_years_ago:
            warnings.append(
                f"reference event {ev.id} is >5 years old ({ev.date}); may feel stale"
            )

    return DateReport(passed=not issues, issues=issues, warnings=warnings)
