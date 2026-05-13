"""ReferenceAnswer — the answer blueprint designed synchronously with the task.

The blueprint is a structured, machine-renderable description of what the correct
deliverable looks like. It is NOT the final file — it is the recipe that code
uses to produce the final file. Narrative text (paragraphs for docx/md) is
generated during synthesis and stored here, so rendering is deterministic code.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExpectedValue(BaseModel):
    """A value that the rendered deliverable must contain at a specific location."""

    description: str = Field(description="Human-readable description of what this value represents")
    value: str | float | int = Field(description="The expected value")
    tolerance: float | None = Field(
        default=None,
        description="For floats: acceptable absolute difference. None means exact match.",
    )
    location: str = Field(
        description="Where to find this value in the deliverable, e.g. 'Sheet Outputs cell B15'"
    )


# ─────────────────────────── XLSX Blueprint ───────────────────────────


class CellBlueprint(BaseModel):
    """A single cell in an Excel sheet."""

    ref: str = Field(description="Cell reference like A1, B5, etc.")
    value: str | float | int | None = Field(
        default=None,
        description="Literal value. EITHER value OR formula must be set, not both.",
    )
    formula: str | None = Field(
        default=None,
        description="Excel formula starting with '='. Use for computed values.",
    )
    bold: bool = False
    italic: bool = False
    fill: Literal["none", "header", "input", "subtotal", "total"] = "none"
    number_format: str | None = Field(
        default=None,
        description="Excel format string like '#,##0', '0.00%', '_($* #,##0_)'",
    )
    alignment: Literal["left", "center", "right"] | None = None


class SheetBlueprint(BaseModel):
    """A single sheet/tab in an Excel workbook."""

    name: str = Field(description="Sheet tab name. ≤ 31 chars, no special chars.")
    cells: list[CellBlueprint] = Field(default_factory=list)
    column_widths: dict[str, float] = Field(
        default_factory=dict,
        description="Map column letter → width in Excel character units.",
    )


# ─────────────────────────── DOCX Blueprint ───────────────────────────


class SectionBlueprint(BaseModel):
    """A section in a Word document."""

    heading: str = Field(description="Section heading text")
    heading_level: int = Field(default=1, ge=1, le=4, description="1=top-level, 2=sub, etc.")
    required_content: list[str] = Field(
        default_factory=list,
        description="Bullet points of what this section must cover (for validation).",
    )
    paragraphs: list[str] = Field(
        default_factory=list,
        description="Pre-written paragraph text. Generated during synthesis, not at render time.",
    )


class DocHeaderBlueprint(BaseModel):
    """Optional memorandum-style header."""

    to: str | None = None
    from_: str | None = Field(default=None, alias="from")
    date: str | None = None
    re: str | None = None
    cc: str | None = None


# ─────────────────────────── Markdown Blueprint ───────────────────────────


class MdSectionBlueprint(BaseModel):
    """A section in a markdown document."""

    heading: str = Field(description="Markdown heading text")
    heading_level: int = Field(default=2, ge=1, le=4)
    required_content: list[str] = Field(
        default_factory=list,
        description="What this section must cover.",
    )
    paragraphs: list[str] = Field(
        default_factory=list,
        description="Pre-written paragraph text.",
    )


# ─────────────────────────── Input Attachment ───────────────────────────


class InputAttachment(BaseModel):
    """An input file provided to the candidate alongside the prompt."""

    attachment_id: str = Field(description="Unique identifier for this attachment")
    filename: str = Field(description="Filename with extension")
    format: Literal["xlsx", "docx", "pdf", "csv", "txt", "md"] = Field(description="File format")
    description: str = Field(description="What this file contains, for the prompt writer to reference")
    content_blueprint: dict = Field(default_factory=dict, description="Structured content description for deterministic rendering")


# ─────────────────────────── ReferenceAnswer ───────────────────────────


class ReferenceAnswer(BaseModel):
    """The complete answer blueprint for a task."""

    format: Literal["xlsx", "docx", "markdown", "pdf", "repo_tarball"] = Field(
        description="Primary deliverable format"
    )

    # XLSX-specific
    sheets: list[SheetBlueprint] | None = None

    # DOCX-specific
    sections: list[SectionBlueprint] | None = None
    doc_header: DocHeaderBlueprint | None = None
    title: str | None = None
    signature_block: str | None = None
    page_settings: Literal["double_spaced", "single_spaced"] = "single_spaced"

    # Markdown-specific
    md_sections: list[MdSectionBlueprint] | None = None
    md_title: str | None = None

    # Input attachments (source docs, data files, drafts) provided alongside the task
    input_attachments: list[InputAttachment] = Field(default_factory=list)

    # Universal: values that validators will check
    expected_values: list[ExpectedValue] = Field(default_factory=list)

    # Narrative generation prompt (used during synthesis to fill paragraphs)
    narrative_prompt: str | None = Field(
        default=None,
        description="System prompt for LLM to generate narrative text for this blueprint.",
    )

    # Generation provenance
    generator_model: str | None = None
    generated_at: str | None = None
