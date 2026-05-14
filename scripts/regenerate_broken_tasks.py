"""Regenerate 11 financial tasks with empty sections.

Usage:
    uv run python scripts/regenerate_broken_tasks.py

This script:
1. Identifies 11 financial tasks whose reference_answer.sections is None
2. Re-runs synthesis for each seed with the fixed financial system prompt
3. Validates with the updated hard_quality checker (now catches empty sections)
4. If passed: replaces old accepted + deliverables files
5. If failed: moves to rejected
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from pipeline.artifacts.renderer import render_deliverable
from pipeline.scenario.synthesis import unified_generate
from pipeline.scenario.task_candidate import TaskCandidate
from pipeline.seeds.base import load_seeds
from pipeline.validators.hard_quality import validate as hard_validate

logger = logging.getLogger(__name__)


def _find_broken_tasks() -> list[tuple[str, str, str, str]]:
    """Find tasks with empty content sections. Returns list of (task_id, seed_id, occ, arch)."""
    broken = []
    for f in Path("data/accepted").glob("*.json"):
        with open(f) as fh:
            d = json.load(fh)
        ra = d.get("canonical", {}).get("reference_answer", {})
        has_content = ra.get("sections") or ra.get("md_sections") or ra.get("sheets")
        if not has_content:
            broken.append((
                d.get("candidate_id", ""),
                d.get("seed_id", ""),
                d.get("occupation", ""),
                d.get("archetype", ""),
            ))
    return broken


def _load_seed(seed_id: str, occupation: str):
    """Load a seed by ID from the store."""
    for s in load_seeds(occupation):
        if s.seed_id == seed_id:
            return s
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    broken = _find_broken_tasks()
    if not broken:
        print("No broken tasks found!")
        return

    print(f"Found {len(broken)} broken tasks to regenerate:\n")
    for tid, sid, occ, arch in broken:
        print(f"  {tid}: {occ} / {arch} (seed={sid})")
    print()

    accepted_dir = Path("data/accepted")
    rejected_dir = Path("data/rejected")
    deliverables_dir = Path("data/deliverables")
    rejected_dir.mkdir(parents=True, exist_ok=True)

    for tid, sid, occ, arch in broken:
        print(f"\n{'='*60}")
        print(f"Regenerating {tid} ({occ} / {arch})")
        print(f"{'='*60}")

        seed = _load_seed(sid, occ)
        if not seed:
            print(f"  ❌ Seed {sid} not found, skipping")
            continue

        # Generate new task
        try:
            task = unified_generate(seed, occupation=occ, difficulty="medium")
        except Exception as e:
            print(f"  ❌ Generation failed: {e}")
            continue

        # Validate
        report = hard_validate(task, seed)
        print(f"  Hard quality: {'PASS' if report.passed else 'FAIL'} ({len(report.issues)} issues)")
        if report.issues:
            for issue in report.issues:
                print(f"    - {issue}")

        # Remove old files
        old_json = accepted_dir / f"{tid}.json"
        old_deliv = deliverables_dir / tid
        if old_json.exists():
            old_json.unlink()
        if old_deliv.exists():
            shutil.rmtree(old_deliv)

        if report.passed:
            # Save new accepted
            new_json = accepted_dir / f"{task.candidate_id}.json"
            with open(new_json, "w") as fh:
                json.dump(task.model_dump(mode="json"), fh, indent=2, ensure_ascii=False)

            # Render deliverable
            try:
                path = render_deliverable(task)
                print(f"  ✅ ACCEPTED → {task.candidate_id}, deliverable: {path.name}")
            except Exception as e:
                print(f"  ⚠️  Accepted but render failed: {e}")
        else:
            # Save to rejected
            rej_json = rejected_dir / f"{task.candidate_id}.json"
            with open(rej_json, "w") as fh:
                data = task.model_dump(mode="json")
                data["_rejection_reasons"] = report.issues
                json.dump(data, fh, indent=2, ensure_ascii=False)
            print(f"  ❌ REJECTED → {task.candidate_id}")

    print(f"\n{'='*60}")
    print("Regeneration complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
