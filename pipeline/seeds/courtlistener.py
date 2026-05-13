"""CourtListener harvester: real legal opinions, parties, citations.

We pull recent (~last 5 years) opinions from federal district courts plus a
sample of state supreme courts. From each we extract: case caption, parties,
court, date, citation, and a representative text excerpt. Scenarios then graft
these onto a hypothetical client situation, but the *citations* and *court rules*
stay real — pinned in CanonicalScenario.facts and validated downstream.

API: https://www.courtlistener.com/help/api/rest/v4/
Auth: Token in `Authorization: Token <key>` header
Rate limits: 5000 req/hour with token, plenty.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import time

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from pipeline.config import settings
from pipeline.seeds.base import Seed, save_seed, seed_exists

logger = logging.getLogger(__name__)

BASE = "https://www.courtlistener.com/api/rest/v4"

# Mix of federal (high-quality opinions) and state supreme courts.
TARGET_COURTS = [
    "scotus",      # Supreme Court of the United States
    "ca9", "ca2", "ca5", "cafc",  # circuit courts: 9th, 2nd, 5th, Federal
    "dcd", "nysd", "cand", "txnd",  # district courts: DC, S.D.N.Y., N.D. Cal., N.D. Tex.
    "cal",         # California Supreme Court
    "ny",          # New York Court of Appeals
]


class CourtListenerClient:
    def __init__(self) -> None:
        token = settings().courtlistener_api_token
        self.client = httpx.Client(
            base_url=BASE,
            headers={"Authorization": f"Token {token}"},
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=3, min=4, max=60),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    def search_opinions(
        self,
        court: str,
        cited_gt: int = 1,
        date_filed_after: str = "2020-01-01",
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        """Search opinion clusters with citations and recent date.

        cited_gt=1 filters to opinions cited at least once (excludes obscure
        unpublished orders). Returns 'cluster' objects with embedded opinions.
        """
        resp = self.client.get(
            "/search/",
            params={
                "type": "o",
                "court": court,
                "cited_gt": cited_gt,
                "filed_after": date_filed_after,
                "order_by": "score desc",
                "page_size": page_size,
            },
        )
        if resp.status_code == 429:
            wait = float(resp.headers.get("Retry-After", "10"))
            time.sleep(wait)
            resp.raise_for_status()
        resp.raise_for_status()
        time.sleep(1.0)  # be polite at search level
        return resp.json().get("results", [])

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=3, min=4, max=60),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    def get_opinion(self, opinion_id: int) -> dict[str, Any]:
        resp = self.client.get(f"/opinions/{opinion_id}/")
        if resp.status_code == 429:
            # Honor Retry-After if present, else backoff.
            wait = float(resp.headers.get("Retry-After", "5"))
            time.sleep(wait)
            resp.raise_for_status()
        resp.raise_for_status()
        time.sleep(0.4)  # courtesy throttle to stay under burst limit
        return resp.json()

    def close(self) -> None:
        self.client.close()


def _extract_excerpt(opinion_json: dict, max_chars: int = 2000) -> str:
    for key in ("plain_text", "html_with_citations", "html", "html_lawbox"):
        body = opinion_json.get(key) or ""
        if body and len(body) > 200:
            # Strip naive HTML tags if present.
            import re

            text = re.sub(r"<[^>]+>", " ", body)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:max_chars]
    return ""


def harvest(target_per_court: int = 5) -> list[Seed]:
    """Pull `target_per_court` opinions from each TARGET_COURTS, dedupe, save."""
    cl = CourtListenerClient()
    seeds: list[Seed] = []
    cutoff = (datetime.now() - timedelta(days=5 * 365)).strftime("%Y-%m-%d")

    try:
        for court in TARGET_COURTS:
            logger.info("Searching %s …", court)
            try:
                hits = cl.search_opinions(court=court, date_filed_after=cutoff)
            except httpx.HTTPError as e:
                logger.warning("  search failed for %s: %s", court, e)
                continue

            count_for_court = 0
            for hit in hits:
                if count_for_court >= target_per_court:
                    break

                cluster_id = hit.get("cluster_id") or hit.get("id")
                case_name = hit.get("caseName") or hit.get("case_name") or "Unknown"
                citation = (hit.get("citation") or [None])[0] if hit.get("citation") else None
                date_filed = hit.get("dateFiled") or hit.get("date_filed")
                opinion_ids = hit.get("opinions") or hit.get("opinion_ids") or []
                if not opinion_ids:
                    continue
                op_id = opinion_ids[0] if isinstance(opinion_ids[0], int) else opinion_ids[0].get("id")
                if not op_id:
                    continue

                identifier = f"cluster:{cluster_id}"
                if seed_exists("courtlistener", identifier, "lawyer"):
                    continue

                try:
                    op = cl.get_opinion(op_id)
                except httpx.HTTPError as e:
                    logger.warning("  opinion %s fetch failed: %s", op_id, e)
                    continue

                excerpt = _extract_excerpt(op)
                if not excerpt:
                    continue

                seed = Seed(
                    seed_id=Seed.make_id("courtlistener", identifier),
                    source="courtlistener",
                    occupation="lawyer",
                    identifier=identifier,
                    title=case_name[:200],
                    fetched_at=date.today(),
                    payload={
                        "cluster_id": cluster_id,
                        "court": court,
                        "case_name": case_name,
                        "citation": citation,
                        "date_filed": date_filed,
                        "opinion_id": op_id,
                        "judges": hit.get("judge") or hit.get("judges"),
                    },
                    text_excerpt=excerpt,
                )
                save_seed(seed)
                seeds.append(seed)
                count_for_court += 1

            logger.info("  → %d kept from %s", count_for_court, court)
    finally:
        cl.close()

    logger.info("CourtListener: harvested %d total seeds", len(seeds))
    return seeds


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out = harvest(target_per_court=5)
    print(f"\nHarvested {len(out)} legal seeds")
    for s in out[:3]:
        print(f"\n  [{s.seed_id}] {s.payload.get('court')} | {s.title}")
        print(f"     {s.payload.get('citation')} | filed {s.payload.get('date_filed')}")
        print(f"     {s.text_excerpt[:200]}…")
