"""SWE seed quality scorer.

GitHub PR seeds harvested by reactions skew toward visible-but-trivial
community PRs (CODE_OF_CONDUCT.md, docs additions). This scorer surfaces the
genuinely engineering-meaty seeds for use in scenario synthesis.

Scoring is heuristic — not a perfect classifier — but reliable enough that
the top decile contains real bug fixes, refactors, perf improvements.
"""

from __future__ import annotations

import re

from pipeline.seeds.base import Seed

_LOW_QUALITY_PATTERNS = re.compile(
    r"\b("
    r"code[_ ]of[_ ]conduct|coc|"
    r"contributing(\.md)?|"
    r"readme|"
    r"docs?(\s|$|:|\.)|documentation|"
    r"changelog|"
    r"typo|"
    r"linter|formatting|prettier|black|isort|"
    r"copyright|license|"
    r"version bump|bump version|"
    r"pin (deps|dependencies)|update deps|update dependencies|"
    r"add example|add tutorial|"
    r"sponsor|funding|"
    r"emoji"
    r")\b",
    re.I,
)

_ENGINEERING_PATTERNS = re.compile(
    r"\b("
    r"fix|bug|crash|leak|race|deadlock|regression|"
    r"cve|security|vulnerability|"
    r"performance|perf|memory|panic|segfault|stack overflow|"
    r"refactor|implement|optimize|migrate|"
    r"thread|async|await|concurren|"
    r"timeout|hang|stuck|"
    r"cache|invalidat|"
    r"correctness|correct"
    r")\b",
    re.I,
)


def score(seed: Seed) -> float:
    """Score a SWE seed in [0, 10]; higher = better engineering substance.

    Components:
      diff size sanity    [0..2]   prefer 20–1500 LOC
      title engineering   [0..3]   matches fix/perf/refactor/security keywords
      title cleanliness   [-3..0]  penalty for docs/CoC/changelog patterns
      linked issue        [0..2]   substantive task usually links a real issue
      body richness       [0..2]   PR body > 200 chars suggests real explanation
      diff present        [0..1]
    """
    p = seed.payload
    title = (p.get("pr_title") or "").strip()
    body = p.get("pr_body") or ""
    adds = p.get("additions", 0) or 0
    dels = p.get("deletions", 0) or 0
    total_loc = adds + dels

    # Diff size sanity
    if total_loc == 0:
        loc_score = 0.0
    elif 20 <= total_loc <= 1500:
        loc_score = 2.0
    elif 5 <= total_loc < 20:
        loc_score = 1.0
    elif 1500 < total_loc <= 3000:
        loc_score = 1.0
    else:
        loc_score = 0.5

    # Title cleanliness: hard penalty for docs/community PRs
    if _LOW_QUALITY_PATTERNS.search(title):
        cleanliness = -3.0
    else:
        cleanliness = 0.0

    # Title engineering signal
    eng_matches = len(_ENGINEERING_PATTERNS.findall(title))
    eng_score = min(eng_matches * 1.5, 3.0)

    # Linked issue
    linked = 2.0 if p.get("linked_issue") else 0.0

    # Body richness
    if len(body) >= 1000:
        body_score = 2.0
    elif len(body) >= 200:
        body_score = 1.0
    else:
        body_score = 0.0

    # Diff present
    diff_score = 1.0 if p.get("diff") else 0.0

    return loc_score + eng_score + cleanliness + linked + body_score + diff_score


def rank(seeds: list[Seed], min_score: float = 3.0) -> list[tuple[Seed, float]]:
    """Return seeds ranked by score, filtered to those at or above min_score."""
    scored = [(s, score(s)) for s in seeds]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [(s, sc) for s, sc in scored if sc >= min_score]


if __name__ == "__main__":
    from pipeline.seeds.base import load_seeds

    seeds = load_seeds("software_engineer")
    ranked = sorted([(s, score(s)) for s in seeds], key=lambda x: x[1], reverse=True)

    print(f"Total SWE seeds: {len(seeds)}")
    above = [(s, sc) for s, sc in ranked if sc >= 3.0]
    print(f"Above threshold 3.0: {len(above)}")
    print(f"\nTop 15:")
    for s, sc in ranked[:15]:
        print(f"  {sc:5.1f}  {s.payload['repo']}#{s.payload['pr_number']}: {s.payload['pr_title'][:80]}")
    print(f"\nBottom 5:")
    for s, sc in ranked[-5:]:
        print(f"  {sc:5.1f}  {s.payload['repo']}#{s.payload['pr_number']}: {s.payload['pr_title'][:80]}")
