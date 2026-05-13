"""SEC EDGAR XBRL harvester: real, structured corporate financial facts.

XBRL data is structured by construction — accounting identities (assets =
liabilities + equity, etc.) are guaranteed to balance, which lets us avoid the
"LLM-invented financials" trap. We pull `companyfacts` for a curated set of
public tickers across sectors and stash a recent snapshot per ticker.

API: https://www.sec.gov/edgar/sec-api-documentation
Required header: User-Agent identifying contact.
Rate limit: 10 req/s soft cap; we throttle to 5/s.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from pipeline.config import settings
from pipeline.seeds.base import Seed, save_seed, seed_exists

logger = logging.getLogger(__name__)

# CIK lookups — diversified across sectors for scenario variety.
# CIK is left-padded to 10 digits in the API URL.
TARGET_TICKERS: list[tuple[str, str, str]] = [
    # (ticker, CIK, sector)
    ("AAPL", "0000320193", "tech_hardware"),
    ("MSFT", "0000789019", "tech_software"),
    ("NVDA", "0001045810", "tech_semis"),
    ("GOOGL", "0001652044", "tech_internet"),
    ("META", "0001326801", "tech_internet"),
    ("AMZN", "0001018724", "retail_ecom"),
    ("TSLA", "0001318605", "auto"),
    ("WMT", "0000104169", "retail"),
    ("KO", "0000021344", "consumer_staples"),
    ("JNJ", "0000200406", "healthcare"),
    ("PFE", "0000078003", "pharma"),
    ("UNH", "0000731766", "healthcare_insurance"),
    ("JPM", "0000019617", "banking"),
    ("BAC", "0000070858", "banking"),
    ("GS", "0000886982", "investment_banking"),
    ("XOM", "0000034088", "energy"),
    ("CVX", "0000093410", "energy"),
    ("BA", "0000012927", "aerospace"),
    ("CAT", "0000018230", "industrials"),
    ("DE", "0000315189", "industrials"),
    ("HD", "0000354950", "retail"),
    ("PG", "0000080424", "consumer_staples"),
    ("DIS", "0001744489", "media"),
    ("NKE", "0000320187", "apparel"),
    ("UBER", "0001543151", "tech_services"),
]


class EdgarClient:
    def __init__(self) -> None:
        ua = settings().sec_edgar_user_agent
        self.client = httpx.Client(
            headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"},
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=20),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def company_facts(self, cik: str) -> dict[str, Any]:
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        resp = self.client.get(url)
        resp.raise_for_status()
        time.sleep(0.2)  # 5 req/s
        return resp.json()

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=20),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def submissions(self, cik: str) -> dict[str, Any]:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = self.client.get(url)
        resp.raise_for_status()
        time.sleep(0.2)
        return resp.json()

    def close(self) -> None:
        self.client.close()


# Concept tags used in financial scenarios. Limited list keeps payloads small.
KEY_CONCEPTS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "CostOfGoodsAndServicesSold",
    "GrossProfit",
    "OperatingIncomeLoss",
    "NetIncomeLoss",
    "Assets",
    "Liabilities",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "EarningsPerShareDiluted",
    "ResearchAndDevelopmentExpense",
    "SellingGeneralAndAdministrativeExpense",
]


def _extract_recent_facts(cf: dict, n_periods: int = 8) -> dict[str, list[dict]]:
    """Pull most recent N annual + quarterly observations per concept."""
    out: dict[str, list[dict]] = {}
    facts = cf.get("facts", {}).get("us-gaap", {})
    for concept in KEY_CONCEPTS:
        entry = facts.get(concept)
        if not entry:
            continue
        usd = entry.get("units", {}).get("USD") or entry.get("units", {}).get("USD/shares")
        if not usd:
            continue
        # Take most recent observations, sorted by end date.
        sorted_obs = sorted(usd, key=lambda x: x.get("end", ""), reverse=True)
        out[concept] = sorted_obs[:n_periods]
    return out


def harvest() -> list[Seed]:
    cl = EdgarClient()
    seeds: list[Seed] = []
    try:
        for ticker, cik, sector in TARGET_TICKERS:
            identifier = f"ticker:{ticker}"
            if seed_exists("sec_edgar_xbrl", identifier, "financial_analyst"):
                logger.info("  skip cached %s", ticker)
                continue
            logger.info("Fetching %s (%s) …", ticker, cik)
            try:
                cf = cl.company_facts(cik)
                sub = cl.submissions(cik)
            except httpx.HTTPError as e:
                logger.warning("  failed: %s", e)
                continue

            recent = _extract_recent_facts(cf)
            if not recent:
                logger.warning("  %s: no key concepts found", ticker)
                continue

            entity_name = cf.get("entityName") or sub.get("name", ticker)
            recent_filings = sub.get("filings", {}).get("recent", {})
            filing_dates = recent_filings.get("filingDate", [])[:10]
            forms = recent_filings.get("form", [])[:10]
            accessions = recent_filings.get("accessionNumber", [])[:10]

            # Render an excerpt summarizing key financials for embedding/dedup.
            excerpt_lines = [f"{entity_name} ({ticker}) — {sector}"]
            for concept, obs in list(recent.items())[:5]:
                if obs:
                    latest = obs[0]
                    val = latest.get("val")
                    end = latest.get("end")
                    excerpt_lines.append(f"  {concept} @ {end}: {val:,}" if isinstance(val, int | float) else f"  {concept}: {val}")
            excerpt = "\n".join(excerpt_lines)

            seed = Seed(
                seed_id=Seed.make_id("sec_edgar_xbrl", identifier),
                source="sec_edgar_xbrl",
                occupation="financial_analyst",
                identifier=identifier,
                title=f"{entity_name} ({ticker})",
                fetched_at=date.today(),
                payload={
                    "ticker": ticker,
                    "cik": cik,
                    "sector": sector,
                    "entity_name": entity_name,
                    "key_facts": recent,
                    "recent_filings": [
                        {"form": f, "date": d, "accession": a}
                        for f, d, a in zip(forms, filing_dates, accessions, strict=False)
                    ],
                },
                text_excerpt=excerpt,
            )
            save_seed(seed)
            seeds.append(seed)
    finally:
        cl.close()
    logger.info("EDGAR: harvested %d total seeds", len(seeds))
    return seeds


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out = harvest()
    print(f"\nHarvested {len(out)} financial seeds")
    for s in out[:3]:
        print(f"\n  [{s.seed_id}] {s.title}")
        print(f"     sector: {s.payload['sector']}")
        print(f"     concepts: {list(s.payload['key_facts'].keys())[:5]}")
        print(f"     recent filings: {[f['form'] for f in s.payload['recent_filings'][:5]]}")
