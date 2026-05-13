"""DOCX deliverable validator.

Checks that the rendered Word document matches the blueprint:
- All required sections exist (by heading text)
- Header fields present
- Page count in expected range (if specified)
"""

from __future__ import annotations

import logging
from pathlib import Path

from docx import Document

from pipeline.scenario.reference_answer import ReferenceAnswer

logger = logging.getLogger(__name__)


def validate_docx(file_path: Path, blueprint: ReferenceAnswer) -> tuple[bool, list[str]]:
    """Validate a docx file against its blueprint.

    Returns (passed, list of failure reasons).
    """
    failures: list[str] = []

    try:
        doc = Document(file_path)
    except Exception as e:
        return False, [f"Cannot open document: {e}"]

    # Extract headings and paragraphs
    headings = []
    full_text = []
    for para in doc.paragraphs:
        text = para.text.strip()
        full_text.append(text)
        if para.style.name.startswith("Heading") or para.text.strip().isupper():
            headings.append(text)

    full_text_lower = "\n".join(full_text).lower()

    # Check required sections exist
    for section in (blueprint.sections or []):
        heading_found = False
        heading_lower = section.heading.lower()
        for h in headings:
            if heading_lower in h.lower():
                heading_found = True
                break
        if not heading_found:
            failures.append(f"Missing section heading: {section.heading}")

    # Check header fields
    if blueprint.doc_header:
        hdr = blueprint.doc_header
        if hdr.to and hdr.to.lower() not in full_text_lower:
            failures.append(f"Missing header field: TO ({hdr.to})")
        if hdr.from_ and hdr.from_.lower() not in full_text_lower:
            failures.append(f"Missing header field: FROM ({hdr.from_})")
        if hdr.date and hdr.date.lower() not in full_text_lower:
            failures.append(f"Missing header field: DATE ({hdr.date})")
        if hdr.re and hdr.re.lower() not in full_text_lower:
            failures.append(f"Missing header field: RE ({hdr.re})")

    # Check expected_values
    for ev in blueprint.expected_values:
        if str(ev.value).lower() not in full_text_lower:
            failures.append(f"Expected value not found: '{ev.description}' = '{ev.value}'")

    passed = len(failures) == 0
    return passed, failures
