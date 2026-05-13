"""DOCX deliverable renderer.

Two-stage:
  1. Planner LLM produces a structured DocPlan (sections, paragraphs, signature).
  2. python-docx assembles a real .docx with proper styling.

The structured plan keeps the LLM from emitting raw XML or trying to mimic
DOCX formatting in markdown. Citations, headers, footers, signature blocks
are handled by code, not the LLM.

Optional PDF rendering via LibreOffice headless if installed.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from pydantic import BaseModel, Field

from pipeline.artifacts.base import PLANNER_MODEL, deliverable_dir
from pipeline.llm import default_client
from pipeline.scenario.task_candidate import TaskCandidate

logger = logging.getLogger(__name__)


class DocSection(BaseModel):
    heading: str = Field(description="Section heading text. Use empty string for body-only blocks.")
    heading_level: int = Field(default=1, ge=1, le=4, description="1=top-level, 2=sub, 3=sub-sub")
    paragraphs: list[str] = Field(description="Body paragraphs, in order. Markdown-lite OK (bold via **, italic via *).")


class DocHeader(BaseModel):
    """Optional memorandum-style TO/FROM/DATE/RE block at top."""
    to: str | None = None
    from_: str | None = Field(default=None, alias="from")
    date: str | None = None
    re: str | None = None
    cc: str | None = None


class DocPlan(BaseModel):
    document_kind: Literal[
        "legal_memo", "motion", "brief", "contract", "letter", "general"
    ] = "general"
    title: str | None = None
    header: DocHeader | None = None
    sections: list[DocSection]
    signature_block: str | None = None
    page_settings: Literal["double_spaced", "single_spaced"] = "single_spaced"


_DOCX_SYS = """You are a senior {occupation_title} producing a high-quality professional document. Output a structured plan that will be rendered as a real .docx file.

Hard rules:
- Reference canonical facts by their actual values (real names, real citations, real dollar amounts).
- The rubric is your contract. Every rubric criterion that can be satisfied by your document MUST be satisfied.
- For legal documents: use proper Bluebook citations, formal headings, professional tone.
- For business documents: use clear section structure, executive summary if applicable.
- DO NOT use AI hedging ("It is important to note", "Please be advised that"). Write with authority.
- Each paragraph should be 2-5 sentences typically. Don't write one-sentence paragraphs unless needed for emphasis.
- For multi-page documents, distribute content across sections appropriately (don't dump everything into one section).

Length expectation: this is a substantial professional deliverable. For an 8-page legal memo expect 8-15 sections, for a 5-page memo expect 5-10 sections.

Output: a JSON DocPlan. The plan will be rendered into a .docx by code.
"""


def plan_doc(task: TaskCandidate, model: str = PLANNER_MODEL) -> DocPlan:
    client = default_client()
    occupation_title = {
        "lawyer": "lawyer",
        "financial_analyst": "investment banking analyst",
        "software_engineer": "senior software engineer",
    }[task.occupation]
    sys_prompt = _DOCX_SYS.format(occupation_title=occupation_title)
    rubric_text = "\n".join(
        f"  [+{r.score}] ({r.category}) {r.criterion}" for r in task.rubric
    )
    user = (
        f"## Task prompt\n{task.prompt}\n\n"
        f"## Canonical scenario state\n{task.canonical.context_for_agent()}\n\n"
        f"## Rubric\n{rubric_text}\n\n"
        f"Produce the DocPlan now. Make sure heading_level is in range [1, 4]."
    )
    logger.info("planning docx for %s with %s", task.candidate_id, model)
    plan = client.chat_structured(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user},
        ],
        DocPlan,
        model=model,
        temperature=0.5,
        max_tokens=8000,
    )
    logger.info("  plan: %d sections", len(plan.sections))
    return plan


def _add_paragraph_with_bold(doc, text: str, *, alignment=None):
    """Render simple **bold** spans inside a paragraph."""
    p = doc.add_paragraph()
    if alignment is not None:
        p.alignment = alignment
    parts = text.split("**")
    bold = False
    for part in parts:
        if part:
            run = p.add_run(part)
            run.bold = bold
        bold = not bold
    return p


def render_plan_to_docx(plan: DocPlan, out_path: Path) -> Path:
    doc = Document()

    # Document-wide formatting baseline.
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)

    if plan.page_settings == "double_spaced":
        for sect in doc.sections:
            sect.top_margin = sect.bottom_margin = sect.left_margin = sect.right_margin = (
                Pt(72)  # 1 inch
            )
        doc.styles["Normal"].paragraph_format.line_spacing = 2.0

    # Title
    if plan.title:
        h = doc.add_heading(plan.title, level=0)
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Memorandum header (TO/FROM/DATE/RE)
    if plan.header:
        for label, value in [
            ("TO", plan.header.to),
            ("FROM", plan.header.from_),
            ("DATE", plan.header.date),
            ("RE", plan.header.re),
            ("CC", plan.header.cc),
        ]:
            if value:
                p = doc.add_paragraph()
                run = p.add_run(f"{label}:\t")
                run.bold = True
                p.add_run(value)
        # Visual separator
        doc.add_paragraph("_" * 80)

    # Sections
    for section in plan.sections:
        if section.heading:
            doc.add_heading(section.heading, level=section.heading_level)
        for para in section.paragraphs:
            _add_paragraph_with_bold(doc, para)

    # Signature
    if plan.signature_block:
        doc.add_paragraph()  # spacer
        for line in plan.signature_block.split("\n"):
            doc.add_paragraph(line)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    return out_path


def maybe_render_pdf(docx_path: Path) -> Path | None:
    """Use LibreOffice headless to convert .docx → .pdf if available."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        logger.info("LibreOffice not found; skipping PDF rendering")
        return None
    try:
        subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(docx_path.parent),
                str(docx_path),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        pdf_path = docx_path.with_suffix(".pdf")
        if pdf_path.exists():
            logger.info("  PDF rendered → %s", pdf_path)
            return pdf_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.warning("PDF rendering failed: %s", e)
    return None


def render_docx(task: TaskCandidate, model: str = PLANNER_MODEL) -> Path:
    plan = plan_doc(task, model=model)
    out_dir = deliverable_dir(task.candidate_id)
    out_path = out_dir / f"{task.deliverable.deliverable_id}.docx"
    render_plan_to_docx(plan, out_path)
    logger.info("  wrote .docx → %s", out_path)
    if "pdf" in task.deliverable.primary_format:
        maybe_render_pdf(out_path)
    return out_path
