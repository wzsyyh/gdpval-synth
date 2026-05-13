"""Seed selector — pick a seed appropriate for a (occupation, archetype, difficulty) cell.

Logic:
  - SWE: rank by quality scorer; sample top decile to keep variety
  - Lawyer: prefer SCOTUS/circuit cases for hard, district for light
  - Financial: large-cap (revenues >$50B) for hard, mid/small for light/medium
  - Avoid reusing seeds within a run (passing in `used` set)
"""

from __future__ import annotations

import logging
import random

from pipeline.scenario.canonical import DifficultyBand
from pipeline.seeds.base import Seed, load_seeds
from pipeline.seeds.swe_quality import rank as swe_rank

logger = logging.getLogger(__name__)


def _financial_revenue(seed: Seed) -> float:
    """Return latest revenue from a financial seed, or 0 if unknown."""
    facts = seed.payload.get("key_facts", {})
    for k in ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"):
        obs = facts.get(k)
        if obs and isinstance(obs[0].get("val"), int | float):
            return float(obs[0]["val"])
    return 0.0


def _lawyer_court_tier(seed: Seed) -> int:
    """SCOTUS=3, circuit=2, district=1, other=0."""
    code = seed.payload.get("court", "")
    if code == "scotus":
        return 3
    if code.startswith("ca"):
        return 2
    if code in {"dcd", "nysd", "cand", "txnd"}:
        return 1
    return 0


def select(
    occupation: str,
    archetype: str,
    difficulty: DifficultyBand,
    *,
    used: set[str] | None = None,
    rng: random.Random | None = None,
) -> Seed | None:
    used = used or set()
    rng = rng or random.Random()
    pool = [s for s in load_seeds(occupation) if s.seed_id not in used]
    if not pool:
        # All seeds have been used at least once; allow reuse rather than failing.
        pool = load_seeds(occupation)
    if not pool:
        return None

    if occupation == "software_engineer":
        from datetime import date, datetime, timedelta
        # Prefer PRs merged in the last 3 years (avoid stale 2020-era PRs).
        cutoff = date.today() - timedelta(days=3 * 365)

        def _is_recent(seed: Seed) -> bool:
            merged_at = seed.payload.get("merged_at") or ""
            if not merged_at:
                return False
            try:
                d = datetime.fromisoformat(merged_at.replace("Z", "+00:00")).date()
                return d >= cutoff
            except (ValueError, TypeError):
                return False

        recent_pool = [s for s in pool if _is_recent(s)]
        working = recent_pool or pool
        ranked = swe_rank(working, min_score=3.0)
        if not ranked:
            return rng.choice(working)
        if difficulty == DifficultyBand.HARD:
            cut = max(1, len(ranked) // 4)
        elif difficulty == DifficultyBand.MEDIUM:
            cut = max(1, len(ranked) // 2)
        else:
            cut = len(ranked)
        return rng.choice([s for s, _sc in ranked[:cut]])

    if occupation == "lawyer":
        if difficulty == DifficultyBand.HARD:
            preferred = [s for s in pool if _lawyer_court_tier(s) >= 2]
        elif difficulty == DifficultyBand.MEDIUM:
            preferred = [s for s in pool if _lawyer_court_tier(s) >= 1]
        else:
            preferred = pool
        return rng.choice(preferred or pool)

    if occupation == "financial_analyst":
        revenues = [(s, _financial_revenue(s)) for s in pool]
        if difficulty == DifficultyBand.HARD:
            preferred = [s for s, r in revenues if r > 50e9]
        elif difficulty == DifficultyBand.LIGHT:
            preferred = [s for s, r in revenues if r < 100e9]
        else:
            preferred = pool
        return rng.choice(preferred or pool)

    return rng.choice(pool)
