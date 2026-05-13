"""Generate gold deliverables for the 3 sample TaskCandidates from Day 2."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.artifacts.base import materialize  # noqa: E402
from pipeline.config import DATA_DIR  # noqa: E402
from pipeline.scenario.task_candidate import TaskCandidate  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    candidates_dir = DATA_DIR / "candidates"
    paths = sorted(candidates_dir.glob("*.json"))
    if not paths:
        print("No candidates found in data/candidates/. Run scripts/test_synthesis.py first.")
        return

    for p in paths:
        tc = TaskCandidate.load(p)
        if only and only not in tc.occupation:
            continue
        print(f"\n{'#' * 90}")
        print(f"# {tc.occupation} | {tc.deliverable.deliverable_id} ({tc.deliverable.primary_format})")
        print(f"# candidate {tc.candidate_id}")
        print(f"{'#' * 90}")
        try:
            out = materialize(tc)
            size_kb = out.stat().st_size / 1024
            print(f"  ✓ wrote {out} ({size_kb:.1f} KB)")
        except Exception as e:
            print(f"  ✗ failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
