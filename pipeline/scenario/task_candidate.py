"""TaskCandidate: the output object of scenario synthesis.

A TaskCandidate has everything needed to ship as a GDPval-style task except
the materialized deliverable artifacts (those are produced by pipeline.artifacts
in Day 3 and attached when packaged for final delivery).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from pipeline.config import DATA_DIR
from pipeline.scenario.canonical import CanonicalScenario


class RubricItem(BaseModel):
    """A single atomic scoring criterion. Mirrors GDPval's rubric_json items.

    Calibrated to real GDPval distribution:
      - 52% of items are +1, 42% are +2, ~6% are +3 or higher
      - 0.9% are penalty items (negative scores)
      - Median ~47 items per rubric, median total points ~70
    """

    score: int = Field(ge=-5, le=5, description="Points awarded if criterion is met. Positive for credit, negative for penalties. GDPval: 52% +1, 42% +2, 0.9% penalty. Cap at 5 to prevent over-weighting.")
    criterion: str = Field(description="Plainly stated criterion. Format/accuracy items should be machine-checkable; judgment items can use relative phrasing.")
    category: str = Field(
        default="content",
        description="One of: format, reference, data, style, accuracy, content, judgment, completeness, structure",
    )
    is_penalty: bool = Field(default=False, description="True if this is a penalty/deduction item (score < 0).")


class DeliverableSpec(BaseModel):
    deliverable_id: str
    primary_format: str  # e.g. "docx", "pdf", "xlsx", "pptx", "repo_tarball", "markdown"
    expected_size: str | None = None  # e.g. "8-12 pages", "4 sheets", "10-18 slides"


class TaskCandidate(BaseModel):
    candidate_id: str
    occupation: str
    archetype: str
    difficulty: str
    seed_id: str

    prompt: str
    deliverable: DeliverableSpec
    rubric: list[RubricItem]

    canonical: CanonicalScenario

    # Optional input attachments (real GDPval: ~57% have them)
    input_attachment_specs: list[dict] = Field(default_factory=list)

    # Paths to rendered artifacts (set by orchestrator after rendering)
    gold_deliverable_path: str | None = Field(default=None, description="Path to rendered gold deliverable file")
    input_attachment_paths: list[str] = Field(default_factory=list, description="Paths to rendered input attachment files")

    # Generation provenance
    generator_model: str
    rubric_model: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def total_rubric_points(self) -> int:
        return sum(r.score for r in self.rubric)

    def save(self, dir_path: Path | None = None) -> Path:
        out_dir = dir_path or (DATA_DIR / "candidates")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{self.candidate_id}.json"
        path.write_text(self.model_dump_json(indent=2))
        return path

    @classmethod
    def load(cls, path: Path) -> TaskCandidate:
        return cls.model_validate_json(path.read_text())


def render_for_inspection(tc: TaskCandidate) -> str:
    """Pretty render for human review."""
    lines = [
        f"=== TaskCandidate {tc.candidate_id} ===",
        f"occupation:    {tc.occupation}",
        f"deliverable:   {tc.deliverable.deliverable_id} ({tc.deliverable.primary_format})",
        f"archetype:     {tc.archetype}",
        f"difficulty:    {tc.difficulty}",
        f"rubric items:  {len(tc.rubric)} criteria, {tc.total_rubric_points()} total points",
        f"seed:          {tc.canonical.seed.source}:{tc.canonical.seed.identifier}",
        "",
        "─── PROMPT ───",
        tc.prompt,
        "",
        "─── RUBRIC (first 12 items) ───",
    ]
    for r in tc.rubric[:12]:
        lines.append(f"  [+{r.score}] ({r.category}) {r.criterion}")
    if len(tc.rubric) > 12:
        lines.append(f"  … {len(tc.rubric) - 12} more")
    lines.append("")
    lines.append("─── CANONICAL ENTITIES ───")
    for e in tc.canonical.entities:
        lines.append(f"  [{e.id}] {e.kind}: {e.name}")
    lines.append("")
    lines.append("─── PINNED FACTS ───")
    for f in tc.canonical.facts[:10]:
        v = f"{f.value:,}" if isinstance(f.value, int | float) and abs(f.value) > 1000 else f.value
        lines.append(f"  [{f.id}] {f.kind}: {v}{' ' + f.unit if f.unit else ''}")
    if len(tc.canonical.facts) > 10:
        lines.append(f"  … {len(tc.canonical.facts) - 10} more")
    return "\n".join(lines)


__all__ = ["TaskCandidate", "RubricItem", "DeliverableSpec", "render_for_inspection"]
