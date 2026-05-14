"""Consistency validator — check that prompt, answer, and rubric all agree.

Three checks:
  1. Seed alignment: expected values in the answer must come from the seed material.
  2. Rubric-answer alignment: rubric criteria must be verifiable against the answer.
  3. Prompt-answer alignment: the deliverable should cover what the prompt asks for.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from pipeline.scenario.reference_answer import ReferenceAnswer
from pipeline.scenario.task_candidate import TaskCandidate
from pipeline.seeds.base import Seed

logger = logging.getLogger(__name__)


@dataclass
class ConsistencyReport:
    passed: bool
    seed_aligned: list[tuple[str, bool]]  # (value_repr, found_in_seed)
    rubric_aligned: list[tuple[str, bool]]  # (criterion, verifiable)
    prompt_aligned: list[tuple[str, bool]]  # (requirement, covered)
    failures: list[str] = field(default_factory=list)


def _blueprint_to_text(answer: ReferenceAnswer) -> str:
    """Flatten a ReferenceAnswer blueprint into a single searchable string."""
    parts: list[str] = []

    if answer.title:
        parts.append(answer.title)
    if answer.md_title:
        parts.append(answer.md_title)

    if answer.doc_header:
        h = answer.doc_header
        for v in (h.to, h.from_, h.date, h.re, h.cc):
            if v:
                parts.append(str(v))

    if answer.sections:
        for sec in answer.sections:
            if sec.heading:
                parts.append(sec.heading)
            for para in sec.paragraphs:
                parts.append(para)

    if answer.md_sections:
        for sec in answer.md_sections:
            if sec.heading:
                parts.append(sec.heading)
            for para in sec.paragraphs:
                parts.append(para)

    if answer.sheets:
        for sheet in answer.sheets:
            parts.append(sheet.name)
            for cell in sheet.cells:
                if cell.value is not None:
                    parts.append(str(cell.value))
                if cell.formula is not None:
                    parts.append(cell.formula)

    if answer.signature_block:
        parts.append(answer.signature_block)

    return "\n".join(parts)


def _seed_to_text(seed: Seed) -> str:
    """Flatten a Seed into a single searchable string."""
    parts: list[str] = [seed.title, seed.source, seed.identifier]
    if seed.text_excerpt:
        parts.append(seed.text_excerpt)
    p = seed.payload
    for k, v in p.items():
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, int | float):
            parts.append(str(v))
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            for item in v[:5]:
                for ik, iv in item.items():
                    parts.append(str(iv))
    return "\n".join(parts)


def _normalize_value(v) -> str:
    """Strip formatting for fuzzy comparison."""
    s = str(v)
    s = s.replace("$", "").replace(",", "").replace("%", "").replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s).strip()
    # Remove trailing units for numbers
    s = re.sub(r"\s*(M|B|K|x|X)\b", "", s)
    return s


def _value_in_text(value, text: str) -> bool:
    """Check if a value appears in text (flexible matching)."""
    if value is None:
        return False

    s = str(value)
    if s in text:
        return True

    # Normalized containment
    norm_text = _normalize_value(text)
    norm_val = _normalize_value(s)
    if norm_val and norm_val in norm_text:
        return True

    # Case-insensitive for longer text
    if len(s) > 3 and s.lower() in text.lower():
        return True

    # Numeric matching
    try:
        num_val = float(norm_val)
        # Search for the number (with or without decimal) in text
        int_part = str(int(num_val))
        if int_part in text or int_part in norm_text:
            return True
        # Also try with 1 decimal
        dec = f"{num_val:.1f}"
        if dec in text or dec in norm_text:
            return True
    except (ValueError, TypeError):
        pass

    return False


def _extract_requirements(prompt: str) -> list[str]:
    """Naively extract requirement sentences from a prompt."""
    sentences = re.split(r"[.!?\n]", prompt)
    reqs: list[str] = []
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 10:
            continue
        # Look for directive language
        if re.search(r"\b(must|should|needs? to|required? to|prepare|draft|write|create|produce|include|contain)\b", sent, re.I):
            reqs.append(sent)
    return reqs[:8]  # Cap at 8 to avoid noise


def _criterion_verifiable(criterion: str, answer_text: str) -> bool:
    """Heuristic: a rubric criterion is verifiable if some of its key content words appear in the answer."""
    # Extract quoted strings (exact match targets)
    quoted = re.findall(r'"([^"]{3,50})"', criterion)
    for q in quoted:
        if q.lower() in answer_text.lower():
            return True

    # Extract capitalized noun phrases and longer words
    words = re.findall(r"[A-Za-z]{5,}", criterion)
    # Filter out generic evaluator words
    stop = {
        "deliverable", "document", "should", "correct", "appropriate", "professional",
        "consistent", "complete", "accurate", "clear", "proper", "relevant", "specific",
        "detailed", "sufficient", "includes", "contains", "mentions", "references",
        "criterion", "rubric", "answer", "response",
    }
    content_words = [w for w in words if w.lower() not in stop]
    if not content_words:
        return True  # No content words to check; assume OK

    hits = sum(1 for w in content_words if w.lower() in answer_text.lower())
    return hits >= max(1, len(content_words) // 3)


def _requirement_covered(requirement: str, answer_text: str) -> bool:
    """Heuristic: a prompt requirement is covered if some of its content words appear in the answer."""
    words = re.findall(r"[A-Za-z]{5,}", requirement)
    stop = {
        "deliverable", "document", "should", "must", "needs", "prepare", "draft",
        "write", "create", "produce", "include", "contain", "using", "based", "provided",
    }
    content_words = [w for w in words if w.lower() not in stop]
    if not content_words:
        return True
    hits = sum(1 for w in content_words if w.lower() in answer_text.lower())
    return hits >= max(1, len(content_words) // 3)


def validate(task: TaskCandidate, seed: Seed) -> ConsistencyReport:
    """Run all consistency checks."""
    answer_text = _blueprint_to_text(task.canonical.reference_answer)
    seed_text = _seed_to_text(seed)

    # ── Check 1: Seed alignment ──
    seed_aligned: list[tuple[str, bool]] = []
    for ev in task.canonical.reference_answer.expected_values:
        found = _value_in_text(ev.value, seed_text)
        seed_aligned.append((f"{ev.description}={ev.value}", found))

    # ── Check 2: Rubric-answer alignment ──
    rubric_aligned: list[tuple[str, bool]] = []
    for item in task.rubric:
        ok = _criterion_verifiable(item.criterion, answer_text)
        rubric_aligned.append((item.criterion, ok))

    # ── Check 3: Prompt-answer alignment ──
    prompt_aligned: list[tuple[str, bool]] = []
    requirements = _extract_requirements(task.prompt)
    for req in requirements:
        ok = _requirement_covered(req, answer_text)
        prompt_aligned.append((req, ok))

    # Collect failures
    failures: list[str] = []

    seed_mismatch = [v for v, ok in seed_aligned if not ok]
    if seed_mismatch:
        failures.append(f"seed_alignment: {len(seed_mismatch)}/{len(seed_aligned)} expected values not found in seed")

    rubric_mismatch = [c for c, ok in rubric_aligned if not ok]
    if rubric_mismatch:
        failures.append(f"rubric_alignment: {len(rubric_mismatch)}/{len(rubric_aligned)} criteria not verifiable")

    prompt_mismatch = [r for r, ok in prompt_aligned if not ok]
    if prompt_mismatch:
        failures.append(f"prompt_alignment: {len(prompt_mismatch)}/{len(prompt_aligned)} requirements not covered")

    # Thresholds: allow some fuzziness
    seed_ok_rate = sum(1 for _, ok in seed_aligned if ok) / max(len(seed_aligned), 1)
    rubric_ok_rate = sum(1 for _, ok in rubric_aligned if ok) / max(len(rubric_aligned), 1)
    prompt_ok_rate = sum(1 for _, ok in prompt_aligned if ok) / max(len(prompt_aligned), 1)

    passed = seed_ok_rate >= 0.5 and rubric_ok_rate >= 0.7 and prompt_ok_rate >= 0.5

    return ConsistencyReport(
        passed=passed,
        seed_aligned=seed_aligned,
        rubric_aligned=rubric_aligned,
        prompt_aligned=prompt_aligned,
        failures=failures,
    )
