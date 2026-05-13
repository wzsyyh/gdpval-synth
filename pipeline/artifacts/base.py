"""Gold deliverable materialization — turn TaskCandidate into a real answer file.

Architecture:
  Stage A — Deliverable Planner (LLM, structured output)
    Given the task prompt + canonical state + rubric, the planner produces a
    structured representation of the answer (sections, cells, code blocks)
    rather than free-form text. This keeps the LLM focused on content and
    pushes file-format mechanics into code.
  Stage B — Renderer (code, no LLM)
    Format-specific code converts the plan into the actual file. python-docx
    for .docx, openpyxl for .xlsx, plain text writer for markdown.

Why structured plans, not direct file output:
  - LLMs producing .xlsx XML directly are unreliable.
  - Plans are inspectable and editable before rendering.
  - We can validate plans (e.g., balance sheet identity) before writing files.
  - Same plan can be rendered in multiple formats if needed.

The planner uses the higher-tier `deepseek-v4-pro` model since deliverable
quality matters here — the gold answer is what frontier models will be
compared against during solve-rate probing on Day 4.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pipeline.config import DATA_DIR

if TYPE_CHECKING:
    from pipeline.scenario.task_candidate import TaskCandidate

logger = logging.getLogger(__name__)

DELIVERABLES_DIR = DATA_DIR / "deliverables"
DELIVERABLES_DIR.mkdir(parents=True, exist_ok=True)


PLANNER_MODEL = "deepseek/deepseek-v4-pro"


def deliverable_dir(candidate_id: str) -> Path:
    p = DELIVERABLES_DIR / candidate_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def materialize(task: TaskCandidate) -> Path:
    """Dispatch to format-specific renderer. Returns the primary deliverable path."""
    fmt = task.deliverable.primary_format
    if fmt in ("markdown", "md"):
        from pipeline.artifacts.markdown_renderer import render_markdown
        return render_markdown(task)
    if fmt in ("docx", "docx+pdf", "pdf"):
        from pipeline.artifacts.docx_renderer import render_docx
        return render_docx(task)
    if fmt in ("xlsx", "xlsx+pptx"):
        from pipeline.artifacts.xlsx_renderer import render_xlsx
        return render_xlsx(task)
    if fmt == "repo_tarball":
        from pipeline.artifacts.markdown_renderer import render_markdown
        # Many SWE design-doc / postmortem deliverables use markdown rather than
        # a full repo tarball; we default to markdown unless the task explicitly
        # demands a repo.
        return render_markdown(task)
    if fmt == "pptx":
        from pipeline.artifacts.markdown_renderer import render_markdown
        # Defer pptx rendering — generate a slide-outline markdown instead.
        return render_markdown(task)
    raise NotImplementedError(f"no renderer for format: {fmt}")
