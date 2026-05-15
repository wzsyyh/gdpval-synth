"""LLM-based consistency validator.

Two-stage design:
  Stage 1 (Planner): Given prompt + rubric + answer format → generates a verification checklist
  Stage 2 (Executor): Given checklist + seed + answer → executes verification and reports findings

Why two stages?
  - Stage 1 isolates "understanding what needs to be checked" from "actually checking"
  - Stage 2 gets a focused checklist and can't miss items by getting lost in long context
  - Works generically for any occupation / deliverable type
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from pipeline.llm import default_client
from pipeline.scenario.task_candidate import TaskCandidate
from pipeline.seeds.base import Seed

logger = logging.getLogger(__name__)


# ─────────────────────────── Stage 1 Output ───────────────────────────


class VerificationItem(BaseModel):
    """One item in the verification checklist."""

    item_id: str = Field(description="Unique identifier, e.g. V001")
    description: str = Field(description="What to verify (human-readable)")
    verification_type: Literal["fact_check", "calculation", "reference", "existence", "alignment"] = Field(
        description="Type of verification needed"
    )
    what_to_find_in_seed: str = Field(description="Specific instruction: what raw data to locate in the seed material")
    what_to_find_in_answer: str = Field(description="Specific instruction: what claim to locate in the answer")
    expected_formula: str | None = Field(default=None, description="If calculation, the formula to apply")


class VerificationPlan(BaseModel):
    """Output of Stage 1: the verification checklist."""

    deliverable_type: str = Field(description="Type of deliverable being verified")
    focus_areas: list[str] = Field(default_factory=list, description="Summary of key verification themes")
    items: list[VerificationItem] = Field(description="Ordered checklist of verification items")


# ─────────────────────────── Stage 2 Output ───────────────────────────


class ValidationResult(BaseModel):
    """Structured output from the LLM consistency check (Stage 2)."""

    seed_aligned: bool = Field(description="All key facts/numbers in the answer are grounded in the seed material")
    seed_issues: list[str] = Field(default_factory=list, description="Specific invented facts or mismatched numbers")

    calculations_correct: bool = Field(description="All computed values are mathematically correct based on seed data")
    calculation_issues: list[str] = Field(default_factory=list, description="Wrong calculations or incorrect formulas")

    rubric_aligned: bool = Field(description="Every rubric criterion can be verified against the answer content")
    rubric_issues: list[str] = Field(default_factory=list, description="Rubric items with no evidence in the answer")

    rubric_grounded: bool = Field(description="Every specific fact, number, or reference in rubric criteria exists in the seed material")
    rubric_grounding_issues: list[str] = Field(default_factory=list, description="Rubric criteria that reference facts not found in the seed")

    prompt_aligned: bool = Field(description="The answer fully addresses all requirements in the prompt")
    prompt_issues: list[str] = Field(default_factory=list, description="Prompt requirements not reflected in the answer")

    overall_passed: bool = Field(description="TRUE only if all four checks pass")


@dataclass
class LlmConsistencyReport:
    passed: bool
    seed_aligned: bool
    calculations_correct: bool
    rubric_aligned: bool
    rubric_grounded: bool
    prompt_aligned: bool
    issues: list[str] = field(default_factory=list)


# ─────────────────────────── Prompts ───────────────────────────

_PLANNER_SYS = """You are a Verification Planner. Your job is to read a task's prompt, rubric, and answer structure, then generate a detailed verification checklist.

This checklist will be handed to an auditor who will execute each item. The auditor is meticulous but needs very clear instructions.

## Rules

1. Read the rubric carefully. Every rubric item that checks a specific fact, number, citation, or calculation MUST become a verification item.
2. Group related items (e.g. all margin calculations) but do not merge them into one vague item.
3. For each verification item, write explicit instructions:
   - what_to_find_in_seed: tell the auditor exactly where to look in the seed material
   - what_to_find_in_answer: tell the auditor exactly what claim to check in the answer
   - expected_formula: if it's a calculation, write the exact formula (e.g. "Q4 = FY - Q3_YTD", "margin = gross_profit / revenue")
4. The checklist should be EXHAUSTIVE — the auditor will follow it item by item.
5. Do NOT skip items because they seem "obvious" or "minor". The auditor needs every item spelled out.

## Output

Return a single JSON object matching the VerificationPlan schema."""


_EXECUTOR_SYS = """You are a strict auditor executing a verification checklist. You are skeptical — you assume the answer MAY contain errors, and your job is to FIND them.

## Critical Instructions

1. Follow the checklist ITEM BY ITEM. Do not skip items. Do not merge items.
2. For each item:
   a) Locate the raw data in the seed material (use BOTH the narrative text AND the structured JSON)
   b) Locate the claim in the answer (use BOTH the narrative text AND the structured claims JSON)
   c) If it's a calculation: PERFORM THE CALCULATION YOURSELF. Do not trust the answer's numbers.
   d) Compare your finding with the answer's claim
   e) Record whether it matches
3. **Show your work**: For calculation items, briefly note the raw numbers you used and your result.
4. **Do not let the answer and rubric confirm each other.** They were generated together and may share the same error. The seed material is the ONLY ground truth.
5. If you find ANY material factual error or calculation error, set overall_passed = false.
6. For each rubric criterion that contains a specific fact, number, date, or citation, verify that this fact EXISTS in the seed material. Do not trust the answer to confirm the rubric — they were generated together and may share the same error. The seed is the only ground truth for rubric content. If a rubric criterion references a fact not in the seed, note it in rubric_grounding_issues.

## Output

Return a single JSON object matching the ValidationResult schema."""


# ─────────────────────────── Seed / Answer Builders ───────────────────────────


def _build_seed_text(seed: Seed) -> str:
    """Render seed material as text."""
    p = seed.payload
    lines = [f"# Seed Material: {seed.title}", f"Source: {seed.source}", f"Identifier: {seed.identifier}", ""]

    if seed.source == "courtlistener":
        lines.extend([
            f"Case Name: {p.get('case_name', 'N/A')}",
            f"Citation: {p.get('citation', 'N/A')}",
            f"Court: {p.get('court', 'N/A')}",
            f"Date Filed: {p.get('date_filed', 'N/A')}",
            f"Judges: {p.get('judges', 'N/A')}",
            "",
            "## Opinion Text",
            seed.text_excerpt or "(no excerpt)",
        ])

    elif seed.source == "sec_edgar_xbrl":
        lines.extend([
            f"Company: {p.get('entity_name', 'N/A')}",
            f"Ticker: {p.get('ticker', 'N/A')}",
            f"CIK: {p.get('cik', 'N/A')}",
            f"Sector: {p.get('sector', 'N/A')}",
            "",
            "## Financial Data (XBRL)",
        ])
        key_facts = p.get("key_facts", {})
        for concept, observations in key_facts.items():
            lines.append(f"\n### {concept}")
            for obs in observations:
                val = obs.get("val")
                if val is not None:
                    fp = obs.get("fp", "")
                    fy = obs.get("fy", "")
                    start = obs.get("start", "")
                    end = obs.get("end", "")
                    if start and end and start != end:
                        label = f"{fp} {fy} ({start} to {end})"
                    else:
                        label = f"{fp} {fy}"
                    if abs(val) < 1000 or val != int(val):
                        lines.append(f"  {label}: {val}")
                    else:
                        lines.append(f"  {label}: {val:,.0f}")
        lines.extend(["", "## Recent Filings"])
        for f in p.get("recent_filings", []):
            lines.append(f"  {f.get('form')} — {f.get('date')}")

    elif seed.source == "github_issue_pr":
        lines.extend([
            f"Repository: {p.get('repo', 'N/A')}",
            f"PR Number: #{p.get('pr_number', 'N/A')}",
            f"PR Title: {p.get('pr_title', 'N/A')}",
            f"Merged At: {p.get('merged_at', 'N/A')}",
            f"Changed Files: {p.get('changed_files', 'N/A')}",
            "",
            "## PR Description",
            p.get("pr_body", "(no description)"),
        ])
        if p.get("linked_issue"):
            lines.extend([
                "",
                f"## Linked Issue #{p.get('linked_issue')}",
                p.get("issue_body", "(no issue body)"),
            ])
        diff = p.get("diff", "")
        if diff:
            lines.extend(["", "## Diff", diff])

    return "\n".join(lines)


def _build_seed_structured(seed: Seed) -> str:
    """Return seed payload as structured JSON."""
    p = seed.payload
    if seed.source == "sec_edgar_xbrl":
        data: dict = {"entity_name": p.get("entity_name"), "ticker": p.get("ticker")}
        key_facts = p.get("key_facts", {})
        for concept, observations in key_facts.items():
            rows = []
            for obs in observations:
                val = obs.get("val")
                if val is None:
                    continue
                display_val = val
                unit = "raw"
                if abs(val) >= 1_000_000_000 and val == int(val):
                    display_val = val / 1_000_000
                    unit = "millions"
                rows.append(
                    {
                        "period": obs.get("fp"),
                        "year": obs.get("fy"),
                        "start": obs.get("start"),
                        "end": obs.get("end"),
                        "value": display_val,
                        "unit": unit,
                        "form": obs.get("form"),
                    }
                )
            data[concept] = rows
        return json.dumps(data, indent=2)

    if seed.source == "courtlistener":
        return json.dumps(
            {
                "case_name": p.get("case_name"),
                "citation": p.get("citation"),
                "court": p.get("court"),
                "date_filed": p.get("date_filed"),
                "judges": p.get("judges"),
            },
            indent=2,
        )

    if seed.source == "github_issue_pr":
        return json.dumps(
            {
                "repo": p.get("repo"),
                "pr_number": p.get("pr_number"),
                "pr_title": p.get("pr_title"),
                "changed_files": p.get("changed_files"),
                "additions": p.get("additions"),
                "deletions": p.get("deletions"),
            },
            indent=2,
        )

    return "{}"


def _blueprint_to_text(task: TaskCandidate) -> str:
    """Flatten the reference answer blueprint into readable text."""
    answer = task.canonical.reference_answer
    parts: list[str] = []

    if answer.title:
        parts.append(f"Title: {answer.title}")
    if answer.md_title:
        parts.append(f"Title: {answer.md_title}")

    if answer.doc_header:
        h = answer.doc_header
        for label, value in [("TO", h.to), ("FROM", h.from_), ("DATE", h.date), ("RE", h.re), ("CC", h.cc)]:
            if value:
                parts.append(f"{label}: {value}")

    if answer.sections:
        for sec in answer.sections:
            if sec.heading:
                parts.append(f"\n## {sec.heading}")
            for para in sec.paragraphs:
                parts.append(para)

    if answer.md_sections:
        for sec in answer.md_sections:
            if sec.heading:
                parts.append(f"\n## {sec.heading}")
            for para in sec.paragraphs:
                parts.append(para)

    if answer.sheets:
        for sheet in answer.sheets:
            parts.append(f"\n### Sheet: {sheet.name}")
            for cell in sheet.cells:
                if cell.value is not None:
                    parts.append(f"  {cell.ref}: {cell.value}")
                if cell.formula is not None:
                    parts.append(f"  {cell.ref}: {cell.formula}")

    if answer.signature_block:
        parts.append(f"\nSignature:\n{answer.signature_block}")

    return "\n".join(parts)


def _build_answer_structured(task: TaskCandidate) -> str:
    """Return answer claims as structured JSON."""
    answer = task.canonical.reference_answer
    claims: list[dict] = []
    for ev in answer.expected_values:
        claims.append(
            {
                "description": ev.description,
                "value": ev.value,
                "tolerance": ev.tolerance,
                "location": ev.location,
            }
        )

    rubric_claims: list[dict] = []
    for r in task.rubric:
        if r.category in ("data", "accuracy", "reference"):
            rubric_claims.append(
                {
                    "score": r.score,
                    "criterion": r.criterion,
                    "category": r.category,
                }
            )

    return json.dumps(
        {
            "expected_values": claims,
            "format": answer.format,
            "title": answer.title or answer.md_title,
            "doc_header": (
                {
                    "to": answer.doc_header.to,
                    "from": answer.doc_header.from_,
                    "date": answer.doc_header.date,
                    "re": answer.doc_header.re,
                }
                if answer.doc_header
                else None
            ),
            "rubric_data_claims": rubric_claims,
        },
        indent=2,
    )


# ─────────────────────────── Two-Stage Validation ───────────────────────────


def validate(task: TaskCandidate, seed: Seed) -> LlmConsistencyReport:
    """Run two-stage LLM-based consistency validation.

    Stage 1 (Planner): Generates a verification checklist from prompt + rubric + answer.
    Stage 2 (Executor): Executes the checklist against seed + answer.
    """
    client = default_client()

    seed_text = _build_seed_text(seed)
    seed_structured = _build_seed_structured(seed)
    answer_text = _blueprint_to_text(task)
    answer_structured = _build_answer_structured(task)
    rubric_text = "\n".join(
        f"  [+{r.score}] ({r.category}) {r.criterion}" for r in task.rubric
    )

    # ── Stage 1: Planner ──
    planner_prompt = (
        f"## Deliverable Type\n\n{task.archetype}\n\n"
        f"## Task Prompt\n\n{task.prompt}\n\n"
        f"## Reference Answer (Narrative)\n\n{answer_text}\n\n"
        f"## Reference Answer (Structured Claims)\n\n```json\n{answer_structured}\n```\n\n"
        f"## Rubric ({len(task.rubric)} items)\n\n{rubric_text}\n\n"
        "Generate a verification checklist. Return JSON matching the schema."
    )

    logger.info("stage 1: planning verification for %s", task.candidate_id)
    plan = client.chat_structured(
        [
            {"role": "system", "content": _PLANNER_SYS},
            {"role": "user", "content": planner_prompt},
        ],
        VerificationPlan,
        temperature=0.3,
        max_tokens=8000,
    )
    logger.info(
        "  plan generated: %d items, focus=%s",
        len(plan.items),
        plan.focus_areas,
    )

    # ── Stage 2: Executor ──
    checklist_text = "\n".join(
        f"  {item.item_id} [{item.verification_type}] {item.description}\n"
        f"    Seed: {item.what_to_find_in_seed}\n"
        f"    Answer: {item.what_to_find_in_answer}"
        + (f"\n    Formula: {item.expected_formula}" if item.expected_formula else "")
        for item in plan.items
    )

    executor_prompt = (
        f"## Seed Material (Narrative)\n\n{seed_text}\n\n"
        f"## Seed Material (Structured JSON)\n\n```json\n{seed_structured}\n```\n\n"
        f"## Task Prompt\n\n{task.prompt}\n\n"
        f"## Reference Answer (Narrative)\n\n{answer_text}\n\n"
        f"## Reference Answer (Structured Claims)\n\n```json\n{answer_structured}\n```\n\n"
        f"## Verification Checklist ({len(plan.items)} items)\n\n{checklist_text}\n\n"
        f"## Rubric ({len(task.rubric)} items)\n\n{rubric_text}\n\n"
        "Execute the checklist item by item. Return JSON matching the schema."
    )

    logger.info("stage 2: executing verification for %s", task.candidate_id)
    result = client.chat_structured(
        [
            {"role": "system", "content": _EXECUTOR_SYS},
            {"role": "user", "content": executor_prompt},
        ],
        ValidationResult,
        temperature=0.2,
        max_tokens=8000,
    )

    issues: list[str] = []
    issues.extend(result.seed_issues)
    issues.extend(result.calculation_issues)
    issues.extend(result.rubric_issues)
    issues.extend(result.rubric_grounding_issues)
    issues.extend(result.prompt_issues)

    # Rubric grounding failure should fail the overall check
    overall_passed = result.overall_passed and result.rubric_grounded

    logger.info(
        "  consistency result: seed=%s calc=%s rubric=%s rubric_grounded=%s prompt=%s → %s",
        result.seed_aligned,
        result.calculations_correct,
        result.rubric_aligned,
        result.rubric_grounded,
        result.prompt_aligned,
        "PASS" if overall_passed else "FAIL",
    )

    return LlmConsistencyReport(
        passed=overall_passed,
        seed_aligned=result.seed_aligned,
        calculations_correct=result.calculations_correct,
        rubric_aligned=result.rubric_aligned,
        rubric_grounded=result.rubric_grounded,
        prompt_aligned=result.prompt_aligned,
        issues=issues,
    )
