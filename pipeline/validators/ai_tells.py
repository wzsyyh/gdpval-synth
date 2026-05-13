"""Detect AI-generated phrasing leakage.

Real bosses, lawyers, and analysts do not write "As an AI", "Please ensure
that", "It is important to note that". When these patterns appear in a
generated prompt, the task feels synthetic to a domain reader.

We hard-reject any candidate whose prompt or rubric contains these tells.
The list is conservative — false positives are acceptable; false negatives
(letting AI tells through) are not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pipeline.scenario.task_candidate import TaskCandidate

_AI_TELL_PATTERNS = [
    re.compile(r"\bas an ai\b", re.I),
    re.compile(r"\bas a language model\b", re.I),
    re.compile(r"\bI am unable to\b", re.I),
    re.compile(r"\bI cannot provide\b", re.I),
    re.compile(r"\bplease ensure that you\b", re.I),
    re.compile(r"\bit is important to note that\b", re.I),
    re.compile(r"\bit is worth noting that\b", re.I),
    re.compile(r"\bplease note that\b", re.I),
    re.compile(r"\bI hope this helps\b", re.I),
    re.compile(r"\bfeel free to\b", re.I),
    # "Let me know if" removed — it's idiomatic in real boss emails.
    # Em-dash overuse is an LLM tell when used as a sentence connector.
    # Two or more in a row in a single sentence is suspicious.
    re.compile(r"—[^—.!?\n]{1,40}—[^—.!?\n]{1,40}—"),
    # "Delve into" / "intricate" / "robust framework" — common LLM tells.
    re.compile(r"\bdelve into\b", re.I),
    re.compile(r"\bin today's (fast-paced|rapidly-evolving|dynamic) world\b", re.I),
    re.compile(r"\bnavigate the complexities\b", re.I),
    # ChatGPT-style closings.
    re.compile(r"\bI hope this (helps|is helpful|provides)\b", re.I),
    re.compile(r"\bcertainly[!,.]\s+here", re.I),
]


@dataclass
class AiTellsReport:
    passed: bool
    hits: list[tuple[str, str]]  # (pattern_repr, matched_text)


def scan_text(text: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for pat in _AI_TELL_PATTERNS:
        m = pat.search(text)
        if m:
            hits.append((pat.pattern, m.group(0)))
    return hits


def validate(task: TaskCandidate) -> AiTellsReport:
    all_text_parts = [task.prompt]
    all_text_parts.extend(r.criterion for r in task.rubric)
    all_text = "\n".join(all_text_parts)
    hits = scan_text(all_text)
    return AiTellsReport(passed=not hits, hits=hits)
