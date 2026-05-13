"""Common seed record schema and disk cache.

A Seed is the bridge between real-world public artifacts and the canonical
scenario state. After harvest, scenario.synthesis lifts entities/dates/numbers
from a Seed into a CanonicalScenario without inventing facts.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from pipeline.config import SEEDS_STORE

logger = logging.getLogger(__name__)


class Seed(BaseModel):
    """A real public artifact used as scenario grounding."""

    seed_id: str  # deterministic hash of (source, identifier)
    source: Literal["courtlistener", "sec_edgar_xbrl", "github_issue_pr"]
    occupation: Literal["lawyer", "financial_analyst", "software_engineer"]
    identifier: str  # source-native id (CL cluster id, EDGAR accession, GH PR url)
    title: str
    fetched_at: date

    # Free-form structured payload — contents differ per source. Always JSON-able.
    payload: dict = Field(default_factory=dict)

    # Plain-text rendering used for embedding / dedup / quick LLM context.
    text_excerpt: str

    @classmethod
    def make_id(cls, source: str, identifier: str) -> str:
        return hashlib.sha256(f"{source}:{identifier}".encode()).hexdigest()[:16]


def seed_dir(occupation: str) -> Path:
    p = SEEDS_STORE / occupation
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_seed(seed: Seed) -> Path:
    out = seed_dir(seed.occupation) / f"{seed.seed_id}.json"
    out.write_text(seed.model_dump_json(indent=2))
    return out


def load_seeds(occupation: str) -> list[Seed]:
    out: list[Seed] = []
    for p in sorted(seed_dir(occupation).glob("*.json")):
        try:
            out.append(Seed.model_validate_json(p.read_text()))
        except Exception as e:  # noqa: BLE001
            logger.warning("failed to load seed %s: %s", p, e)
    return out


def seed_exists(source: str, identifier: str, occupation: str) -> bool:
    sid = Seed.make_id(source, identifier)
    return (seed_dir(occupation) / f"{sid}.json").exists()
