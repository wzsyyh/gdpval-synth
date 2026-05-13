"""Download the 220 public real GDPval tasks for dedup + anchor calibration.

Used by:
  - diversity.embed_dedup: reject candidates within ε of any real task
  - report blind Turing study: mix real + synthetic for human evaluators
  - human anchor calibration during pipeline tuning
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pipeline.config import DATA_DIR

logger = logging.getLogger(__name__)

REFERENCE_DIR = DATA_DIR / "gdpval_reference"
HF_DATASET = "openai/gdpval"


def download_reference() -> Path:
    """Snapshot the public GDPval gold set locally."""
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REFERENCE_DIR / "tasks.jsonl"
    if out_path.exists() and out_path.stat().st_size > 0:
        logger.info("GDPval reference already cached at %s", out_path)
        return out_path

    from datasets import load_dataset

    logger.info("Downloading GDPval public tasks from HuggingFace…")
    ds = load_dataset(HF_DATASET, split="train")
    n = 0
    with out_path.open("w") as f:
        for row in ds:
            f.write(json.dumps(row, default=str) + "\n")
            n += 1
    logger.info("Wrote %d real GDPval tasks → %s", n, out_path)
    return out_path


def load_reference_tasks() -> list[dict]:
    path = REFERENCE_DIR / "tasks.jsonl"
    if not path.exists():
        path = download_reference()
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = download_reference()
    tasks = load_reference_tasks()
    print(f"\nLoaded {len(tasks)} reference tasks")
    if tasks:
        print(f"Sample task keys: {list(tasks[0].keys())}")
        sample = tasks[0]
        for k, v in sample.items():
            sv = str(v)
            print(f"  {k}: {sv[:120]}{'…' if len(sv) > 120 else ''}")
