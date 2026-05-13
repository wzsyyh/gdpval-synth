"""End-to-end critic funnel on the 3 Day-2 candidates."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.config import DATA_DIR  # noqa: E402
from pipeline.critic.funnel import evaluate  # noqa: E402
from pipeline.scenario.task_candidate import TaskCandidate  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    paths = sorted((DATA_DIR / "candidates").glob("*.json"))
    if not paths:
        print("No candidates. Run scripts/test_synthesis.py first.")
        return

    for p in paths:
        tc = TaskCandidate.load(p)
        if only and only not in tc.occupation:
            continue
        print(f"\n{'#' * 80}")
        print(f"# {tc.occupation} | {tc.candidate_id}")
        print(f"{'#' * 80}")
        result = evaluate(tc)
        status = "✓ ACCEPTED" if result.accepted else "✗ REJECTED"
        print(f"  {status}  (last stage: {result.stage_passed})")
        if result.rejection_reason:
            print(f"  reason: {result.rejection_reason}")
        if result.dedup_max_similarity is not None:
            print(f"  dedup max sim: {result.dedup_max_similarity:.3f}")
        if result.realism_overall is not None:
            rb = result.realism_breakdown or {}
            print(
                f"  realism: overall={result.realism_overall} "
                f"(voice={rb.get('workplace_voice')}, "
                f"domain={rb.get('domain_specificity')}, "
                f"rubric={rb.get('rubric_quality')}, "
                f"facts={rb.get('fact_grounding')})"
            )
            if rb.get("issues"):
                print(f"    issues: {rb['issues'][:3]}")
        if result.solvability_overall is not None:
            sb = result.solvability_breakdown or {}
            print(
                f"  solvability: overall={result.solvability_overall} "
                f"(info={sb.get('info_sufficient')}, rubric_sat={sb.get('rubric_satisfiable')})"
            )
        if result.solve_rate_estimates:
            print(f"  solve-rate (mean={result.solve_rate_mean}, max={result.solve_rate_max}):")
            for e in result.solve_rate_estimates:
                print(f"    {e['model']}: {e['score']}/10 (conf {e['confidence']})")
        print(f"  timings: {result.timings}")


if __name__ == "__main__":
    main()
