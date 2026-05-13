"""Markdown deliverable validator.

Checks that the rendered markdown document matches the blueprint:
- All required sections exist (by heading)
- Required content keywords present
"""

from __future__ import annotations

import logging
from pathlib import Path

from pipeline.scenario.reference_answer import ReferenceAnswer

logger = logging.getLogger(__name__)


def validate_md(file_path: Path, blueprint: ReferenceAnswer) -> tuple[bool, list[str]]:
    """Validate a markdown file against its blueprint.

    Returns (passed, list of failure reasons).
    """
    failures: list[str] = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"Cannot read markdown: {e}"]

    content_lower = content.lower()

    # Check required sections exist
    for section in (blueprint.md_sections or []):
        heading_found = False
        heading_lower = section.heading.lower()
        for line in content.split("\n"):
            if heading_lower in line.lower() and line.strip().startswith("#"):
                heading_found = True
                break
        if not heading_found:
            failures.append(f"Missing section heading: {section.heading}")

    # Check expected_values
    for ev in blueprint.expected_values:
        if str(ev.value).lower() not in content_lower:
            failures.append(f"Expected value not found: '{ev.description}' = '{ev.value}'")

    passed = len(failures) == 0
    return passed, failures
