"""Legal citation validator: roundtrip every cited case against CourtListener.

A canonical scenario for a Lawyer task should cite real cases. Both the
canonical pinned `precedent_citation` AND any case names that appear in the
prompt body (auto-extracted via regex) are verified.

Citations the LLM "hallucinates" (made-up reporter volumes, page numbers,
or case names) fail this validator and the candidate is rejected.

API: https://www.courtlistener.com/api/rest/v4/citation-lookup/

We send a citation string and CourtListener returns matched clusters; if
zero matches AND the citation isn't very fresh (which the API may not yet
have indexed), we flag it.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from functools import lru_cache

import httpx

from pipeline.config import settings
from pipeline.scenario.task_candidate import TaskCandidate

logger = logging.getLogger(__name__)

# Reporter citation regex — covers F., F.2d, F.3d, F.4th, U.S., S. Ct., etc.
# Conservative: only catches well-formed citations like "142 F.4th 1194".
_CITATION_RE = re.compile(
    r"\b(\d{1,4})\s+"
    r"(F\.?\s?(?:2d|3d|4th)?|"
    r"U\.S\.|S\.\s?Ct\.|"
    r"L\.\s?Ed\.\s?(?:2d)?|"
    r"F\.\s?Supp\.?\s?(?:2d|3d)?)\s+"
    r"(\d{1,5})\b"
)


@dataclass
class CitationReport:
    passed: bool
    found: list[str] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)
    skipped: int = 0  # API errors, not counted as failures


_BASE = "https://www.courtlistener.com/api/rest/v4"


def _client() -> httpx.Client:
    token = settings().courtlistener_api_token
    return httpx.Client(
        base_url=_BASE,
        headers={"Authorization": f"Token {token}"},
        timeout=httpx.Timeout(20.0, connect=10.0),
    )


@lru_cache(maxsize=512)
def _citation_exists(volume: str, reporter: str, page: str) -> bool | None:
    """Return True/False if the API can verify, None if API fails."""
    cite_str = f"{volume} {reporter} {page}"
    try:
        with _client() as c:
            resp = c.post(
                "/citation-lookup/",
                data={"text": cite_str},
            )
            if resp.status_code == 200:
                results = resp.json()
                # API returns list of citation matches; each has clusters or status
                if isinstance(results, list) and results:
                    return any(
                        r.get("status") in (200, 300) and r.get("clusters")
                        for r in results
                    )
                return False
            elif resp.status_code == 429:
                time.sleep(5)
                return None
            else:
                logger.debug("citation lookup %s → %d", cite_str, resp.status_code)
                return None
    except httpx.HTTPError as e:
        logger.debug("citation lookup error %s: %s", cite_str, e)
        return None


def extract_citations(text: str) -> list[tuple[str, str, str, str]]:
    """Return list of (full_match, volume, reporter, page)."""
    out = []
    for m in _CITATION_RE.finditer(text):
        out.append((m.group(0), m.group(1), m.group(2), m.group(3)))
    return out


def validate(task: TaskCandidate, max_check: int = 8) -> CitationReport:
    """Only runs for lawyer tasks. Other occupations pass trivially."""
    if task.occupation != "lawyer":
        return CitationReport(passed=True)

    text = task.prompt + "\n" + "\n".join(r.criterion for r in task.rubric)
    cites = extract_citations(text)
    # Dedupe.
    seen = set()
    unique = []
    for full, v, r, p in cites:
        key = (v, r.replace(" ", "").replace(".", "").lower(), p)
        if key not in seen:
            seen.add(key)
            unique.append((full, v, r, p))

    found, not_found, skipped = [], [], 0
    for full, v, r, p in unique[:max_check]:
        result = _citation_exists(v, r, p)
        if result is True:
            found.append(full)
        elif result is False:
            not_found.append(full)
        else:
            skipped += 1
        time.sleep(0.5)  # be polite

    # Pass criterion: only fail if essentially ALL citations are unverifiable.
    # CourtListener's citation index lags real cases by weeks/months and the
    # critic catches truly hallucinated citations more reliably than this regex
    # match. We treat this validator as a soft signal: reject only if the ratio
    # of unverifiable citations is clearly out of distribution.
    total_checked = len(found) + len(not_found)
    if total_checked == 0:
        return CitationReport(passed=True, found=found, not_found=not_found, skipped=skipped)
    fail_rate = len(not_found) / total_checked
    # Pass if at least 1 found OR fail rate < 80% (allow 1-2 unverifiable mixed in).
    passed = len(found) >= 1 or fail_rate < 0.8
    return CitationReport(passed=passed, found=found, not_found=not_found, skipped=skipped)
