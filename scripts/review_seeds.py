"""Systematic quality review of harvested seeds.

For each occupation, applies heuristic quality checks and reports a
breakdown of pass/fail with example failures so we know what to fix.
"""

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.seeds.base import load_seeds  # noqa: E402


def review_lawyer() -> None:
    seeds = load_seeds("lawyer")
    print(f"\n{'=' * 80}\nLAWYER ({len(seeds)} seeds)\n{'=' * 80}")
    courts = Counter()
    has_citation = 0
    sufficient_text = 0
    procedural_only = []  # likely procedural orders, less useful
    for s in seeds:
        courts[s.payload.get("court", "?")] += 1
        if s.payload.get("citation"):
            has_citation += 1
        if len(s.text_excerpt) > 1500:
            sufficient_text += 1
        # Detect "procedural only" by very short or order-style title
        title_low = s.title.lower()
        if any(
            k in title_low
            for k in ("order ", "petition for", "denied", "granted certiorari")
        ):
            procedural_only.append(s.title[:80])

    print(f"  has citation: {has_citation}/{len(seeds)}")
    print(f"  ≥1500 char excerpt: {sufficient_text}/{len(seeds)}")
    print(f"  court spread: {dict(courts)}")
    if procedural_only:
        print(f"  potentially procedural ({len(procedural_only)}):")
        for t in procedural_only[:3]:
            print(f"    - {t}")
    # Sample one mid-quality and one top-quality
    print("\n  Sample (top): ", seeds[0].title[:90])
    print(f"    court={seeds[0].payload.get('court')}, cite={seeds[0].payload.get('citation')}")
    print(f"    excerpt[:200]={seeds[0].text_excerpt[:200]}")


def review_financial() -> None:
    seeds = load_seeds("financial_analyst")
    print(f"\n{'=' * 80}\nFINANCIAL ANALYST ({len(seeds)} seeds)\n{'=' * 80}")
    sectors = Counter()
    concept_count = []
    has_recent_10k = 0
    has_recent_10q = 0
    for s in seeds:
        sectors[s.payload.get("sector", "?")] += 1
        n = len(s.payload.get("key_facts", {}))
        concept_count.append(n)
        forms = [f["form"] for f in s.payload.get("recent_filings", [])]
        if "10-K" in forms:
            has_recent_10k += 1
        if "10-Q" in forms:
            has_recent_10q += 1
    print(f"  sector spread ({len(sectors)} sectors): {dict(sectors)}")
    print(
        f"  concept richness: min={min(concept_count)}, "
        f"median={sorted(concept_count)[len(concept_count) // 2]}, max={max(concept_count)}"
    )
    print(f"  has recent 10-K filing: {has_recent_10k}/{len(seeds)}")
    print(f"  has recent 10-Q filing: {has_recent_10q}/{len(seeds)}")
    # Show fact ranges
    print("\n  Sample:")
    s = seeds[0]
    print(f"    {s.title} — {s.payload['sector']}")
    for k, obs in list(s.payload["key_facts"].items())[:4]:
        if obs:
            v = obs[0].get("val")
            end = obs[0].get("end")
            print(f"      {k} @ {end}: {v:,}" if isinstance(v, int | float) else f"      {k}: {v}")


_BAD_TITLE_PATTERNS = re.compile(
    r"\b("
    r"code[_ ]of[_ ]conduct|coc|"
    r"contributing|"
    r"readme|"
    r"docs?(\s|$|:)|documentation|"
    r"changelog|"
    r"typo|"
    r"linter|formatting|prettier|black|isort|"
    r"copyright|license|"
    r"test only|testing only|"
    r"version bump|bump version|"
    r"pin (deps|dependencies)|update deps|update dependencies|"
    r"add example|add tutorial|"
    r"sponsor|funding|"
    r"emoji"
    r")\b",
    re.I,
)

_GOOD_HINT_PATTERNS = re.compile(
    r"\b(fix|bug|crash|leak|race|deadlock|regression|cve|security|"
    r"performance|perf|memory|panic|segfault|"
    r"refactor|implement|optimize|migrate)\b",
    re.I,
)


def review_swe() -> None:
    seeds = load_seeds("software_engineer")
    print(f"\n{'=' * 80}\nSOFTWARE ENGINEER ({len(seeds)} seeds)\n{'=' * 80}")
    repos = Counter()
    bad_titles = []
    good_titles = []
    has_linked_issue = 0
    has_diff = 0
    big_enough_diff = 0
    tiny_diff = []
    massive_pr = []
    for s in seeds:
        repos[s.payload.get("repo", "?")] += 1
        title = s.payload.get("pr_title", "") or ""
        if _BAD_TITLE_PATTERNS.search(title):
            bad_titles.append(title)
        if _GOOD_HINT_PATTERNS.search(title):
            good_titles.append(title)
        if s.payload.get("linked_issue"):
            has_linked_issue += 1
        diff = s.payload.get("diff", "")
        if diff:
            has_diff += 1
        # heuristic: meaty PR has linked issue OR meaningful body OR meaningful diff
        adds = s.payload.get("additions", 0)
        dels = s.payload.get("deletions", 0)
        if 20 <= adds + dels <= 1500:
            big_enough_diff += 1
        if adds + dels < 10:
            tiny_diff.append((title[:60], adds, dels))
        if adds + dels > 1500:
            massive_pr.append((title[:60], adds, dels))

    print(f"  repo spread ({len(repos)} repos): top 5 by count: {dict(repos.most_common(5))}")
    print(f"  has linked issue: {has_linked_issue}/{len(seeds)}")
    print(f"  has any diff: {has_diff}/{len(seeds)}")
    print(f"  diff size in [20, 1500] LOC: {big_enough_diff}/{len(seeds)}")
    print(f"\n  ❌ likely-low-quality titles (docs/conduct/etc): {len(bad_titles)}/{len(seeds)}")
    for t in bad_titles[:8]:
        print(f"    - {t}")
    print(f"\n  ✅ promising titles (fix/perf/refactor/security): {len(good_titles)}/{len(seeds)}")
    for t in good_titles[:8]:
        print(f"    - {t}")
    if tiny_diff:
        print(f"\n  ⚠️  tiny PRs (<10 LOC total): {len(tiny_diff)}")
        for t, a, d in tiny_diff[:3]:
            print(f"    - +{a}/-{d}: {t}")


if __name__ == "__main__":
    review_lawyer()
    review_financial()
    review_swe()
