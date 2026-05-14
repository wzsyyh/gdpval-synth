"""Gold deliverable materialization utilities."""

from __future__ import annotations

import logging
from pathlib import Path

from pipeline.config import DATA_DIR

logger = logging.getLogger(__name__)

DELIVERABLES_DIR = DATA_DIR / "deliverables"
DELIVERABLES_DIR.mkdir(parents=True, exist_ok=True)


def deliverable_dir(candidate_id: str) -> Path:
    p = DELIVERABLES_DIR / candidate_id
    p.mkdir(parents=True, exist_ok=True)
    return p
