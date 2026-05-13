"""Live monitor for the orchestrator batch run.

Usage: uv run python scripts/monitor.py
Reads /tmp/gdpval_run.log and prints accept/reject counts + ETA + per-bucket
rejection breakdown so we can see whether the funnel is healthy mid-run.
"""

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

LOG_PATHS = [Path("/tmp/gdpval_run.log"), Path("/tmp/gdpval_run2.log")]
FUNNEL_LOG = Path("data/funnel_log.jsonl")


def main() -> None:
    log = next((p for p in LOG_PATHS if p.exists()), None)
    if log is None:
        print("no log found")
        return

    text = log.read_text()
    completed = re.findall(r"\[\s*(\d+)/(\d+)\]\s*([✓✗])\s*(\S+)\s+([\d.]+)s\s+(.*)", text)
    if not completed:
        print("(no completions yet — orchestrator still warming up)")
        # Show the tail
        for line in text.splitlines()[-5:]:
            print(f"  | {line}")
        return

    total = int(completed[-1][1])
    done = len(completed)
    accepted = sum(1 for c in completed if c[2] == "✓")
    rejected = done - accepted
    elapsed_total = sum(float(c[4]) for c in completed)
    avg_per = elapsed_total / done if done else 0
    eta_min = avg_per * (total - done) / 60

    print(f"Progress: {done}/{total}  accepted={accepted} ({accepted / done:.0%})")
    print(f"Avg per task: {avg_per:.0f}s    ETA: {eta_min:.0f} min remaining")
    print()

    # Bucket rejections
    reasons = Counter()
    for c in completed:
        if c[2] == "✓":
            continue
        msg = c[5]
        if "hard validators" in msg:
            reasons["hard_validators"] += 1
        elif "too close to real GDPval" in msg:
            reasons["dedup_overlap"] += 1
        elif "realism overall" in msg:
            reasons["realism_low"] += 1
        elif "solvability overall" in msg:
            reasons["solvability_low"] += 1
        elif "predicted" in msg and "≥" in msg:
            reasons["solve_rate_too_easy"] += 1
        elif "crashed" in msg or "Structured output failed" in msg:
            reasons["critic_crashed"] += 1
        else:
            reasons["other"] += 1

    print("Rejection reasons:")
    for k, v in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  {v:3d}  {k}")
    print()

    # Per-occupation breakdown
    occ = Counter()
    occ_ok = Counter()
    for c in completed:
        # Parse "lawyer/motion_to_dismiss/medium" from c[3]
        path = c[3]
        if "/" in path:
            o = path.split("/")[0]
            occ[o] += 1
            if c[2] == "✓":
                occ_ok[o] += 1
    print("Per occupation:")
    for o in sorted(occ):
        print(f"  {o:25s} {occ_ok[o]:3d}/{occ[o]:3d}  ({occ_ok[o] / occ[o]:.0%})")


if __name__ == "__main__":
    main()
