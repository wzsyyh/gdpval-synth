#!/usr/bin/env python3
"""
Comprehensive statistics script for the GDPval 220-task dataset.
Run: python analyze_gdpval.py
"""

import json
import re
import statistics
from collections import Counter


def percentile(arr, p):
    """Linear interpolation percentile."""
    k = (len(arr) - 1) * p
    f = int(k)
    c = min(f + 1, len(arr) - 1)
    return arr[f] * (c - k) + arr[c] * (k - f)


def main():
    path = "data/gdpval_reference/tasks.jsonl"
    tasks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            tasks.append(json.loads(line))

    n = len(tasks)
    print(f"Loaded {n} tasks from {path}")

    # ------------------------------------------------------------------
    # 1. Prompt length distribution
    # ------------------------------------------------------------------
    pl = [len(t["prompt"]) for t in tasks]
    pl_s = sorted(pl)
    print("\n" + "=" * 60)
    print("1. PROMPT LENGTH DISTRIBUTION (characters)")
    print("=" * 60)
    print(f"  Count: {n}")
    print(f"  Min:   {min(pl_s)}")
    print(f"  Max:   {max(pl_s)}")
    print(f"  Mean:  {statistics.mean(pl_s):.1f}")
    print(f"  Med:   {percentile(pl_s, 0.5):.1f}")
    print(f"  P25:   {percentile(pl_s, 0.25):.1f}")
    print(f"  P75:   {percentile(pl_s, 0.75):.1f}")
    print(f"  P90:   {percentile(pl_s, 0.90):.1f}")

    # ------------------------------------------------------------------
    # 2. Rubric density
    # ------------------------------------------------------------------
    rc = []
    rt = []
    pos_scores = []
    neg_scores = []
    for t in tasks:
        rubric = json.loads(t["rubric_json"])
        rc.append(len(rubric))
        rt.append(sum(item.get("score", 0) for item in rubric))
        for item in rubric:
            s = item.get("score", 0)
            (pos_scores if s > 0 else neg_scores).append(s)

    rc_s = sorted(rc)
    rt_s = sorted(rt)
    print("\n" + "=" * 60)
    print("2. RUBRIC DENSITY")
    print("=" * 60)
    print(f"  Items per task:")
    print(f"    Min: {min(rc_s)}, Max: {max(rc_s)}, Mean: {statistics.mean(rc_s):.1f}, Median: {percentile(rc_s, 0.5):.1f}")
    print(f"  Total points per task:")
    print(f"    Min: {min(rt_s)}, Max: {max(rt_s)}, Mean: {statistics.mean(rt_s):.1f}, Median: {percentile(rt_s, 0.5):.1f}")
    total_items = len(pos_scores) + len(neg_scores)
    print(f"  Positive-score items: {len(pos_scores)} ({100*len(pos_scores)/total_items:.1f}%)")
    print(f"  Negative-score items (penalties): {len(neg_scores)} ({100*len(neg_scores)/total_items:.1f}%)")
    ps = Counter(pos_scores)
    print("  Positive score value distribution:")
    for sc in sorted(ps.keys()):
        print(f"    +{sc}: {ps[sc]} items ({100*ps[sc]/len(pos_scores):.1f}%)")

    # ------------------------------------------------------------------
    # 3. Occupation distribution
    # ------------------------------------------------------------------
    occ = Counter(t["occupation"] for t in tasks)
    print("\n" + "=" * 60)
    print("3. OCCUPATION DISTRIBUTION")
    print("=" * 60)
    print(f"  Unique occupations: {len(occ)}")
    for o, c in occ.most_common():
        print(f"  {c:3d}  {o}")

    # ------------------------------------------------------------------
    # 4. Deliverable format distribution
    # ------------------------------------------------------------------
    ext = Counter()
    for t in tasks:
        for df in t.get("deliverable_files", []):
            e = df.split(".")[-1].lower() if "." in df else "none"
            ext[e] += 1
    print("\n" + "=" * 60)
    print("4. DELIVERABLE FORMAT DISTRIBUTION")
    print("=" * 60)
    for e, c in ext.most_common():
        print(f"  {c:3d}  .{e}")

    # ------------------------------------------------------------------
    # 5. Has reference files?
    # ------------------------------------------------------------------
    has_ref = sum(1 for t in tasks if t.get("reference_file_urls") and len(t["reference_file_urls"]) > 0)
    ref_counts = [len(t.get("reference_file_urls", []) or []) for t in tasks]
    print("\n" + "=" * 60)
    print("5. HAS REFERENCE FILES?")
    print("=" * 60)
    print(f"  Tasks with references: {has_ref}/{n} ({100*has_ref/n:.1f}%)")
    print(f"  Reference files per task: min={min(ref_counts)}, max={max(ref_counts)}, mean={statistics.mean(ref_counts):.1f}")

    # ------------------------------------------------------------------
    # 6. Has deliverable files?
    # ------------------------------------------------------------------
    has_del = sum(1 for t in tasks if t.get("deliverable_file_urls") and len(t["deliverable_file_urls"]) > 0)
    print("\n" + "=" * 60)
    print("6. HAS DELIVERABLE FILES?")
    print("=" * 60)
    print(f"  Tasks with deliverables: {has_del}/{n} ({100*has_del/n:.1f}%)")

    # ------------------------------------------------------------------
    # 7. Prompt structure patterns
    # ------------------------------------------------------------------
    you_are = sum(1 for t in tasks if t["prompt"].strip().startswith("You are"))
    has_deadline = sum(1 for t in tasks if re.search(r"\b(due date|deadline|due by)\b", t["prompt"], re.I))
    has_dollar = sum(1 for t in tasks if re.search(r"\$[\d,]+(?:\.\d{2})?", t["prompt"]))
    has_numbered = sum(1 for t in tasks if re.search(r"\n\s*\d+[\.\)]\s+\w", t["prompt"]))
    has_bullet = sum(1 for t in tasks if re.search(r"\n\s*[-\*•]\s+\w", t["prompt"]))
    has_date_ctx = sum(
        1
        for t in tasks
        if re.search(
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
            t["prompt"],
        )
    )
    has_attached = sum(1 for t in tasks if "attached" in t["prompt"].lower() or "attachment" in t["prompt"].lower())
    has_create = sum(1 for t in tasks if "create" in t["prompt"].lower())
    has_review = sum(1 for t in tasks if "review" in t["prompt"].lower())

    print("\n" + "=" * 60)
    print("7. PROMPT STRUCTURE PATTERNS")
    print("=" * 60)
    print(f"  Starts with 'You are...':           {you_are}/{n} ({100*you_are/n:.1f}%)")
    print(f"  Mentions attached/attachment:       {has_attached}/{n} ({100*has_attached/n:.1f}%)")
    print(f"  Has numbered requirements (1. 2.):  {has_numbered}/{n} ({100*has_numbered/n:.1f}%)")
    print(f"  Has bullet-point requirements:      {has_bullet}/{n} ({100*has_bullet/n:.1f}%)")
    print(f"  Explicit deadline/due date:         {has_deadline}/{n} ({100*has_deadline/n:.1f}%)")
    print(f"  Mentions specific dollar amounts:   {has_dollar}/{n} ({100*has_dollar/n:.1f}%)")
    print(f"  Sets temporal context (month year): {has_date_ctx}/{n} ({100*has_date_ctx/n:.1f}%)")
    print(f"  Contains 'create':                  {has_create}/{n} ({100*has_create/n:.1f}%)")
    print(f"  Contains 'review':                  {has_review}/{n} ({100*has_review/n:.1f}%)")

    # ------------------------------------------------------------------
    # 8. Rubric patterns
    # ------------------------------------------------------------------
    keywords = [
        "format", "reference", "data", "style", "content", "presentation",
        "structure", "calculation", "citation", "organization", "accuracy",
        "correctness", "clarity", "grammar", "spelling", "completeness",
    ]
    kw_counts = Counter()
    for t in tasks:
        rubric = json.loads(t["rubric_json"])
        for item in rubric:
            crit = item.get("criterion", "").lower()
            for kw in keywords:
                if kw in crit:
                    kw_counts[kw] += 1

    tasks_with_named = 0
    named_items = 0
    for t in tasks:
        rubric = json.loads(t["rubric_json"])
        has_one = False
        for item in rubric:
            crit = item.get("criterion", "").lower()
            if any(w in crit for w in ["accuracy", "accurate", "correct", "exactly", "matches", "named", "titled"]):
                if re.search(
                    r"\b[A-Z][a-zA-Z\s]{2,}\b|\$[\d,]+|\b\d{4}\b|\b\d+\.\d+\b",
                    item.get("criterion", ""),
                ):
                    has_one = True
                    named_items += 1
        if has_one:
            tasks_with_named += 1

    print("\n" + "=" * 60)
    print("8. RUBRIC PATTERNS")
    print("=" * 60)
    print("  Top keywords in rubric criteria:")
    for kw, c in kw_counts.most_common():
        print(f"    {c:4d}  {kw}")
    print(f"\n  Tasks with at least one specific named-entity/number requirement: {tasks_with_named}/{n} ({100*tasks_with_named/n:.1f}%)")
    print(f"  Total such rubric items: {named_items}")

    # ------------------------------------------------------------------
    # Bonus: Sector distribution
    # ------------------------------------------------------------------
    sec = Counter(t["sector"] for t in tasks)
    print("\n" + "=" * 60)
    print("BONUS: SECTOR DISTRIBUTION")
    print("=" * 60)
    for s, c in sec.most_common():
        print(f"  {c:3d}  {s}")


if __name__ == "__main__":
    main()
