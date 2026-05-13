"""Financial fact consistency validator.

For Financial Analyst tasks, the canonical pinned facts come from real EDGAR
XBRL data, so accounting identities (assets = liabilities + equity within
~2%) should hold by construction. This validator catches:
  - Pinned facts that violate the balance sheet equation (indicates a bug
    in the canonical builder, NOT in LLM output).
  - Numbers in the prompt body that don't match canonical pinned values
    (LLM tried to "round" or "approximate" canonical facts).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pipeline.scenario.task_candidate import TaskCandidate


@dataclass
class FinancialReport:
    passed: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _fact_value(task: TaskCandidate, prefix: str) -> float | None:
    for f in task.canonical.facts:
        if f.id.startswith(prefix) and isinstance(f.value, int | float):
            return float(f.value)
    return None


# Patterns like "$22,217.0 million", "$22.2 billion", "$164,787 million"
_DOLLAR_RE = re.compile(
    r"\$\s?([\d,]+(?:\.\d+)?)\s*(million|billion|thousand|M|B|K|mn|bn)?",
    re.I,
)


def _to_dollars(num_str: str, unit: str | None) -> float:
    n = float(num_str.replace(",", ""))
    if not unit:
        return n
    unit_lo = unit.lower()
    if unit_lo in ("million", "m", "mn"):
        return n * 1e6
    if unit_lo in ("billion", "b", "bn"):
        return n * 1e9
    if unit_lo in ("thousand", "k"):
        return n * 1e3
    return n


def validate(task: TaskCandidate, tolerance: float = 0.05) -> FinancialReport:
    if task.occupation != "financial_analyst":
        return FinancialReport(passed=True)

    issues: list[str] = []
    warnings: list[str] = []

    assets = _fact_value(task, "fact_Assets")
    liabilities = _fact_value(task, "fact_Liabilities")
    equity = _fact_value(task, "fact_StockholdersEquity")

    # Balance sheet identity within tolerance.
    if assets is not None and liabilities is not None and equity is not None:
        derived = liabilities + equity
        if abs(derived - assets) / max(assets, 1) > tolerance:
            issues.append(
                f"balance sheet identity violated: assets={assets:,.0f} vs L+E={derived:,.0f} "
                f"(diff {(derived - assets) / assets:.2%})"
            )

    # Sanity-check large numbers in prompt against pinned facts.
    # If a billion-scale number in the prompt has no matching canonical fact within 5%,
    # warn (it might be an LLM-invented number).
    pinned_values = [
        f.value for f in task.canonical.facts
        if isinstance(f.value, int | float) and abs(f.value) > 1e6
    ]
    matches_in_prompt = []
    suspicious = []
    for m in _DOLLAR_RE.finditer(task.prompt):
        val = _to_dollars(m.group(1), m.group(2))
        if val < 1e6:
            continue  # only check large figures
        matched = any(
            abs(val - pv) / max(abs(pv), 1) <= tolerance for pv in pinned_values
        )
        if matched:
            matches_in_prompt.append(val)
        else:
            suspicious.append((m.group(0), val))
    if len(suspicious) > 2:
        warnings.append(
            f"{len(suspicious)} large $ figures in prompt not matching any pinned fact "
            f"(first 3: {[s[0] for s in suspicious[:3]]})"
        )

    return FinancialReport(passed=not issues, issues=issues, warnings=warnings)
