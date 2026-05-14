"""Input attachment renderers.

Deterministic code rendering of input files provided alongside the task prompt.
These are source documents, data files, contract drafts, etc. that the candidate
must work from.
"""

from __future__ import annotations

import logging
from pathlib import Path

from openpyxl import Workbook

from pipeline.config import DATA_DIR
from pipeline.scenario.reference_answer import InputAttachment

logger = logging.getLogger(__name__)


def render_input_attachment(attachment: InputAttachment, task_dir: Path) -> Path:
    """Render an input attachment to a file. Returns the path."""
    renderers = {
        "xlsx": _render_input_xlsx,
        "docx": _render_input_docx,
        "md": _render_input_md,
        "txt": _render_input_txt,
        "csv": _render_input_csv,
        "pdf": _render_input_pdf,
    }
    renderer = renderers.get(attachment.format)
    if not renderer:
        raise ValueError(f"No renderer for input attachment format: {attachment.format}")
    return renderer(attachment, task_dir)


def _render_input_xlsx(attachment: InputAttachment, task_dir: Path) -> Path:
    """Render a simple data table as Excel."""
    bp = attachment.content_blueprint
    wb = Workbook()
    ws = wb.active
    ws.title = bp.get("sheet_name", "Data")

    # Write header row
    from openpyxl.styles import Font
    columns = bp.get("columns", [])
    for col_idx, col_name in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = Font(bold=True)

    # Write data rows
    rows = bp.get("rows", [])
    for row_idx, row_data in enumerate(rows, 2):
        for col_idx, value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Auto-adjust column widths
    for col_idx in range(1, len(columns) + 1):
        ws.column_dimensions[chr(64 + col_idx)].width = 20

    out_path = task_dir / attachment.filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path


def _render_input_docx(attachment: InputAttachment, task_dir: Path) -> Path:
    """Render a simple document (contract draft, memo, etc.)."""
    from docx import Document
    from docx.shared import Pt

    bp = attachment.content_blueprint
    doc = Document()

    title = bp.get("title", "Document")
    doc.add_heading(title, level=1)

    parties = bp.get("parties", [])
    if parties:
        doc.add_paragraph(f"Between: {parties[0]} and {parties[1]}")
        doc.add_paragraph()

    for clause in bp.get("clauses", []):
        doc.add_heading(clause.get("name", ""), level=2)
        doc.add_paragraph(clause.get("text", ""))

    out_path = task_dir / attachment.filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    return out_path


def _render_input_md(attachment: InputAttachment, task_dir: Path) -> Path:
    """Render a markdown file (PR diff, API spec, bug report)."""
    bp = attachment.content_blueprint
    lines = []

    if "title" in bp:
        lines.append(f"# {bp['title']}\n")

    if "repo" in bp:
        lines.append(f"**Repository:** {bp['repo']}\n")
    if "pr_num" in bp:
        lines.append(f"**PR:** #{bp['pr_num']}\n")

    if "diff_excerpt" in bp:
        lines.append("## Diff Excerpt\n")
        lines.append("```diff")
        lines.append(bp["diff_excerpt"])
        lines.append("```\n")

    if "requirements" in bp:
        lines.append("## Requirements\n")
        for req in bp["requirements"]:
            lines.append(f"- {req}")
        lines.append("")

    if "repro_steps" in bp:
        lines.append("## Reproduction Steps\n")
        for step in bp["repro_steps"]:
            lines.append(f"- {step}")
        lines.append("")

    if "expected_behavior" in bp:
        lines.append(f"**Expected:** {bp['expected_behavior']}\n")
    if "actual_behavior" in bp:
        lines.append(f"**Actual:** {bp['actual_behavior']}\n")

    if "body" in bp:
        if lines:
            lines.append("")
        lines.append(bp["body"])

    out_path = task_dir / attachment.filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _render_input_txt(attachment: InputAttachment, task_dir: Path) -> Path:
    """Render a plain text file."""
    bp = attachment.content_blueprint
    text = bp.get("content", "")
    out_path = task_dir / attachment.filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return out_path


def _render_input_csv(attachment: InputAttachment, task_dir: Path) -> Path:
    """Render a CSV file."""
    bp = attachment.content_blueprint
    import csv

    out_path = task_dir / attachment.filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        for row in bp.get("rows", []):
            writer.writerow(row)
    return out_path


def _render_input_pdf(attachment: InputAttachment, task_dir: Path) -> Path:
    """Render PDF by first creating docx then converting."""
    # For MVP: render as docx, then convert if LibreOffice is available
    docx_path = _render_input_docx(
        InputAttachment(
            attachment_id=attachment.attachment_id,
            filename=attachment.filename.replace(".pdf", "_temp.docx"),
            format="docx",
            description=attachment.description,
            content_blueprint=attachment.content_blueprint,
        ),
        task_dir,
    )

    pdf_path = task_dir / attachment.filename
    try:
        from pipeline.artifacts.renderer import maybe_render_pdf
        converted = maybe_render_pdf(docx_path)
        if converted:
            docx_path.unlink(missing_ok=True)
            return converted
    except Exception as e:
        logger.warning("PDF conversion failed for input attachment %s: %s", attachment.attachment_id, e)

    # Fallback: rename temp docx to original filename with .docx extension
    fallback_path = task_dir / attachment.filename.replace(".pdf", ".docx")
    docx_path.rename(fallback_path)
    return fallback_path
