"""XLSX deliverable renderer.

Two-stage:
  1. Planner LLM produces a structured WorkbookPlan with sheets, cells,
     formulas, and data ranges. NUMBERS that must reconcile (totals, balance
     sheet identity) are EXPRESSED AS FORMULAS, not as values — so Excel
     enforces consistency at recompute time.
  2. openpyxl writes the workbook with live formulas. Excel/LibreOffice
     evaluates them when opened.

The "formulas not values" rule is what prevents the LLM-invented-financials
failure mode: even if the LLM picks a wrong assumption, the downstream
totals will still balance because Excel computes them from the assumption
cells.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from pydantic import BaseModel, Field

from pipeline.artifacts.base import PLANNER_MODEL, deliverable_dir
from pipeline.llm import default_client
from pipeline.scenario.task_candidate import TaskCandidate

logger = logging.getLogger(__name__)


class CellSpec(BaseModel):
    ref: str = Field(description="Cell reference like A1, B5, etc.")
    value: str | float | int | None = Field(
        default=None,
        description="Literal value. EITHER value OR formula must be set, not both.",
    )
    formula: str | None = Field(
        default=None,
        description="Excel formula starting with '='. Use this for any computed value.",
    )
    bold: bool = False
    italic: bool = False
    fill: Literal["none", "header", "input", "subtotal", "total"] = "none"
    number_format: str | None = Field(
        default=None,
        description="Excel format string like '#,##0', '0.00%', '_($* #,##0_)'. None = default.",
    )
    alignment: Literal["left", "center", "right"] | None = None


class SheetPlan(BaseModel):
    name: str = Field(description="Sheet tab name. ≤ 31 chars, no special chars.")
    cells: list[CellSpec]
    column_widths: dict[str, float] = Field(
        default_factory=dict,
        description="Map column letter → width in Excel character units.",
    )


class WorkbookPlan(BaseModel):
    sheets: list[SheetPlan]
    cover_memo: str | None = Field(
        default=None,
        description="Optional cover memo placed at top of first sheet as merged text.",
    )


# Color palette for fills (kept minimal for clean look).
_FILL_COLORS = {
    "header": "1F4E78",     # dark blue
    "input": "FFF2CC",      # light yellow (analyst convention: inputs are yellow)
    "subtotal": "D9E1F2",   # light blue
    "total": "BDD7EE",      # medium blue
}


_XLSX_SYS = """You are a senior {occupation_title} producing a high-quality Excel workbook deliverable. Output a structured WorkbookPlan that will be rendered by openpyxl.

CRITICAL RULES:
1. Numbers that must RECONCILE must be FORMULAS, not literal values:
   - Totals, subtotals: =SUM(B2:B10) NOT 12345
   - Computed margins: =B5/B4 NOT 0.32
   - Balance sheet identity: assets = liabilities + equity must follow from formulas
   - Sensitivity tables: each cell is a formula tied to inputs
2. Inputs/assumptions are LITERAL values placed in cells with fill="input".
   These are the only places where the analyst makes a judgment call.
3. Reference canonical facts by their EXACT values (real revenue, real assets, etc.).
4. Use proper Excel format strings: '#,##0' for whole millions, '0.00%' for percents,
   '$#,##0' or '_($* #,##0_)' for currency.
5. Sheet names ≤ 31 chars, no slashes/asterisks.

DCF/Valuation models specifically:
  - Build forecasts as formulas off a "growth rate" assumption cell
  - WACC components in a dedicated "Inputs" sheet, then referenced
  - Sensitivity table is a 2-D grid of formulas referencing two assumption cells
  - Per-share value computed as =EQUITY_VALUE / SHARES_OUT (not hardcoded)

Variance analysis:
  - Variance columns are formulas: =Actual - Budget
  - % variance: =(Actual - Budget) / Budget

The rubric is your contract — every criterion you can satisfy MUST be satisfied.
Output ONLY the JSON WorkbookPlan.
"""


def plan_workbook(task: TaskCandidate, model: str = PLANNER_MODEL) -> WorkbookPlan:
    client = default_client()
    occupation_title = {
        "lawyer": "lawyer",
        "financial_analyst": "investment banking analyst",
        "software_engineer": "senior software engineer",
    }[task.occupation]
    sys_prompt = _XLSX_SYS.format(occupation_title=occupation_title)
    rubric_text = "\n".join(
        f"  [+{r.score}] ({r.category}) {r.criterion}" for r in task.rubric
    )
    user = (
        f"## Task prompt\n{task.prompt}\n\n"
        f"## Canonical scenario state\n{task.canonical.context_for_agent()}\n\n"
        f"## Rubric\n{rubric_text}\n\n"
        f"Plan the workbook now. Aim for 3-6 sheets, 50-300 cells per sheet, "
        f"with formulas wherever values must reconcile."
    )
    logger.info("planning xlsx for %s with %s", task.candidate_id, model)
    plan = client.chat_structured(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user},
        ],
        WorkbookPlan,
        model=model,
        temperature=0.4,
        max_tokens=12000,
    )
    logger.info(
        "  plan: %d sheets, %d total cells",
        len(plan.sheets),
        sum(len(s.cells) for s in plan.sheets),
    )
    return plan


def _apply_cell_style(cell, spec: CellSpec) -> None:
    if spec.bold or spec.italic:
        cell.font = Font(
            name="Calibri",
            size=11,
            bold=spec.bold,
            italic=spec.italic,
            color="FFFFFF" if spec.fill == "header" else "000000",
        )
    if spec.fill != "none":
        color = _FILL_COLORS.get(spec.fill)
        if color:
            cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
    if spec.number_format:
        cell.number_format = spec.number_format
    if spec.alignment:
        cell.alignment = Alignment(horizontal=spec.alignment, vertical="center")


def render_plan_to_xlsx(plan: WorkbookPlan, out_path: Path) -> Path:
    wb = Workbook()
    # Remove default sheet; we'll add our own.
    wb.remove(wb.active)

    for sheet_plan in plan.sheets:
        # Sanitize sheet name.
        name = sheet_plan.name.replace("/", "-").replace("\\", "-")[:31]
        ws = wb.create_sheet(title=name)

        for spec in sheet_plan.cells:
            try:
                cell = ws[spec.ref]
            except (ValueError, AttributeError):
                logger.warning("invalid cell ref %s; skipping", spec.ref)
                continue
            if spec.formula is not None:
                cell.value = spec.formula if spec.formula.startswith("=") else f"={spec.formula}"
            elif spec.value is not None:
                cell.value = spec.value
            _apply_cell_style(cell, spec)

        # Column widths
        for col_letter, width in sheet_plan.column_widths.items():
            try:
                ws.column_dimensions[col_letter.upper()].width = max(8.0, min(60.0, width))
            except (ValueError, KeyError):
                pass

        # Default reasonable column widths if none supplied
        if not sheet_plan.column_widths:
            ws.column_dimensions["A"].width = 40
            for c in range(2, 10):
                ws.column_dimensions[get_column_letter(c)].width = 16

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path


def render_xlsx(task: TaskCandidate, model: str = PLANNER_MODEL) -> Path:
    plan = plan_workbook(task, model=model)
    out_dir = deliverable_dir(task.candidate_id)
    out_path = out_dir / f"{task.deliverable.deliverable_id}.xlsx"
    render_plan_to_xlsx(plan, out_path)
    logger.info("  wrote .xlsx → %s", out_path)
    return out_path
