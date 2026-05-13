"""GDPval alignment verification script.

Run after each batch to measure how closely generated tasks match real GDPval style.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np


def analyze_batch(candidate_dir: Path) -> dict:
    """Analyze a batch of TaskCandidate JSON files."""
    tasks = []
    for p in sorted(candidate_dir.glob("sc_*.json")):
        try:
            tasks.append(json.loads(p.read_text()))
        except Exception:
            continue

    if not tasks:
        return {"error": f"No tasks found in {candidate_dir}"}

    n = len(tasks)

    # Prompt metrics
    prompt_lengths = [len(t["prompt"]) for t in tasks]
    you_are_count = sum(1 for t in tasks if t["prompt"].lower().startswith("you are"))
    deadline_count = sum(
        1 for t in tasks
        if any(w in t["prompt"].lower() for w in ["deadline", "due by", "due date", "close of business", "end of day", "eod", "by friday", "by monday", "by wednesday", "by thursday"])
    )
    numbered_list_count = sum(
        1 for t in tasks
        if any(line.strip().startswith((str(i) + ".")) for i in range(1, 20) for line in t["prompt"].split("\n")[:30])
    )
    bullet_count = sum(
        1 for t in tasks
        if any(line.strip().startswith(("- ", "* ")) for line in t["prompt"].split("\n")[:30])
    )
    attachment_count = sum(
        1 for t in tasks
        if any(w in t["prompt"].lower() for w in ["attached", "attachment", "provided", "see the", "below", "excerpt"])
    )

    # Rubric metrics
    rubric_item_counts = [len(t["rubric"]) for t in tasks]
    total_points = [sum(r["score"] for r in t["rubric"]) for t in tasks]

    all_scores = []
    all_categories = []
    penalty_count = 0
    exact_match_count = 0
    for t in tasks:
        for r in t["rubric"]:
            all_scores.append(r["score"])
            all_categories.append(r.get("category", "content"))
            if r.get("is_penalty") or r["score"] < 0:
                penalty_count += 1
            # Heuristic: exact-match items mention specific names/numbers in quotes or with "identifies"
            crit = r["criterion"].lower()
            if any(w in crit for w in ["identifies", "lists", "names", "cites", "correctly"]) and any(c in crit for c in ['"', "$", "%", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
                exact_match_count += 1

    score_counter = Counter(all_scores)
    cat_counter = Counter(all_categories)

    # Format metrics
    formats = [t["deliverable"]["primary_format"] for t in tasks]
    format_counter = Counter(formats)

    # Input attachments
    has_input = sum(1 for t in tasks if t.get("input_attachment_specs"))
    has_gold = sum(1 for t in tasks if t.get("gold_deliverable_path"))

    def _stats(arr):
        a = np.array(arr)
        return {
            "min": int(np.min(a)),
            "max": int(np.max(a)),
            "mean": round(float(np.mean(a)), 1),
            "median": round(float(np.median(a)), 1),
            "p25": round(float(np.percentile(a, 25)), 1),
            "p75": round(float(np.percentile(a, 75)), 1),
        }

    return {
        "n": n,
        "prompt": {
            "length": _stats(prompt_lengths),
            "starts_with_you_are": {"count": you_are_count, "pct": round(you_are_count / n * 100, 1)},
            "has_deadline": {"count": deadline_count, "pct": round(deadline_count / n * 100, 1)},
            "has_numbered_list": {"count": numbered_list_count, "pct": round(numbered_list_count / n * 100, 1)},
            "has_bullets": {"count": bullet_count, "pct": round(bullet_count / n * 100, 1)},
            "mentions_attachment": {"count": attachment_count, "pct": round(attachment_count / n * 100, 1)},
        },
        "rubric": {
            "item_count": _stats(rubric_item_counts),
            "total_points": _stats(total_points),
            "score_distribution": dict(sorted(score_counter.items())),
            "category_distribution": dict(cat_counter),
            "penalty_items": {"count": penalty_count, "pct": round(penalty_count / len(all_scores) * 100, 2) if all_scores else 0},
            "exact_match_items": {"count": exact_match_count, "pct": round(exact_match_count / len(all_scores) * 100, 1) if all_scores else 0},
        },
        "formats": dict(format_counter),
        "attachments": {
            "has_input": {"count": has_input, "pct": round(has_input / n * 100, 1)},
            "has_gold_deliverable": {"count": has_gold, "pct": round(has_gold / n * 100, 1)},
        },
    }


def print_comparison(report: dict) -> None:
    """Print report with GDPval target comparison."""
    print("=" * 70)
    print("GDPval ALIGNMENT REPORT")
    print("=" * 70)
    print(f"Tasks analyzed: {report['n']}")
    print()

    print("--- PROMPT ---")
    p = report["prompt"]
    l = p["length"]
    print(f"Length (chars):  min={l['min']}, median={l['median']}, mean={l['mean']}, max={l['max']}")
    print(f"  TARGET: median ~2,024  |  ACTUAL: median {l['median']}")
    print()
    print(f"Starts with 'You are a...': {p['starts_with_you_are']['pct']}% ({p['starts_with_you_are']['count']}/{report['n']})")
    print(f"  TARGET: ~78%  |  ACTUAL: {p['starts_with_you_are']['pct']}%")
    print()
    print(f"Has explicit deadline:      {p['has_deadline']['pct']}%")
    print(f"  TARGET: ~3%  |  ACTUAL: {p['has_deadline']['pct']}%")
    print()
    print(f"Has numbered lists:         {p['has_numbered_list']['pct']}%")
    print(f"  TARGET: ~17%  |  ACTUAL: {p['has_numbered_list']['pct']}%")
    print()
    print(f"Has bullet points:          {p['has_bullets']['pct']}%")
    print(f"  TARGET: ~36%  |  ACTUAL: {p['has_bullets']['pct']}%")
    print()
    print(f"Mentions attachments:       {p['mentions_attachment']['pct']}%")
    print(f"  TARGET: ~44%  |  ACTUAL: {p['mentions_attachment']['pct']}%")
    print()

    print("--- RUBRIC ---")
    r = report["rubric"]
    ic = r["item_count"]
    print(f"Item count:      min={ic['min']}, median={ic['median']}, mean={ic['mean']}, max={ic['max']}")
    print(f"  TARGET: median ~47  |  ACTUAL: median {ic['median']}")
    print()
    tp = r["total_points"]
    print(f"Total points:    min={tp['min']}, median={tp['median']}, mean={tp['mean']}, max={tp['max']}")
    print(f"  TARGET: median ~70  |  ACTUAL: median {tp['median']}")
    print()
    print("Score distribution:")
    for score, count in sorted(r["score_distribution"].items()):
        pct = round(count / sum(r["score_distribution"].values()) * 100, 1)
        print(f"  {score:>+3d}: {count:>3d} ({pct:>5.1f}%)")
    print(f"  TARGET: ~52% +1, ~42% +2, ~6% +3+  |  Penalty: {r['penalty_items']['pct']}% (target ~0.9%)")
    print()
    print("Category distribution:")
    for cat, count in sorted(r["category_distribution"].items(), key=lambda x: -x[1]):
        pct = round(count / sum(r["category_distribution"].values()) * 100, 1)
        print(f"  {cat:15s}: {count:>3d} ({pct:>5.1f}%)")
    print()
    print(f"Exact-match items: {r['exact_match_items']['pct']}% of all rubric items")
    print(f"  TARGET: ~73% of tasks have some  |  ACTUAL: {r['exact_match_items']['pct']}%")
    print()

    print("--- FORMATS ---")
    for fmt, count in sorted(report["formats"].items(), key=lambda x: -x[1]):
        pct = round(count / report["n"] * 100, 1)
        print(f"  {fmt:15s}: {count:>3d} ({pct:>5.1f}%)")
    print(f"  TARGET: PDF~39%, XLSX~30%, DOCX~29%, PPTX~8%")
    print()

    print("--- ATTACHMENTS ---")
    a = report["attachments"]
    print(f"Has input attachments:   {a['has_input']['pct']}%")
    print(f"  TARGET: ~57%  |  ACTUAL: {a['has_input']['pct']}%")
    print()
    print(f"Has gold deliverable:    {a['has_gold_deliverable']['pct']}%")
    print(f"  TARGET: ~84%  |  ACTUAL: {a['has_gold_deliverable']['pct']}%")
    print()
    print("=" * 70)


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("dir", type=Path, default=Path("data/accepted"), nargs="?")
    args = p.parse_args()

    report = analyze_batch(args.dir)
    if "error" in report:
        print(report["error"], file=sys.stderr)
        sys.exit(1)

    print_comparison(report)

    # Also write JSON
    out_path = args.dir / "_alignment_report.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to: {out_path}")


if __name__ == "__main__":
    main()
