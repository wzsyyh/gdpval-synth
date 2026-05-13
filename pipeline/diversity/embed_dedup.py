"""Embedding-based dedup against real GDPval reference + intra-pipeline dedup.

Two purposes:
  1. **Contamination guard**: any candidate task whose embedding is within ε of
     a real GDPval task is rejected — defends against accidentally regenerating
     the public benchmark.
  2. **Intra-pipeline diversity**: pairwise distance among candidates surfaces
     mode collapse before it affects the final 24.

Uses a small local sentence-transformers model (no API dependency, ~30 MB).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from pipeline.config import DATA_DIR, settings
from pipeline.seeds.gdpval_reference import REFERENCE_DIR, load_reference_tasks

logger = logging.getLogger(__name__)

EMBED_CACHE = DATA_DIR / "embeddings"
EMBED_CACHE.mkdir(parents=True, exist_ok=True)


_model: SentenceTransformer | None = None


def model() -> SentenceTransformer:
    global _model
    if _model is None:
        name = settings().embed_model
        logger.info("loading embedder %s", name)
        _model = SentenceTransformer(name)
    return _model


def embed(texts: list[str]) -> np.ndarray:
    """Return L2-normalized embeddings for cosine similarity."""
    arr = model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(arr, dtype=np.float32)


def build_reference_index() -> tuple[np.ndarray, list[dict]]:
    """Embed all 220 real GDPval prompts; cache to disk."""
    cache_vec = EMBED_CACHE / "gdpval_reference.npy"
    cache_meta = EMBED_CACHE / "gdpval_reference_meta.jsonl"
    if cache_vec.exists() and cache_meta.exists():
        vecs = np.load(cache_vec)
        meta = [json.loads(l) for l in cache_meta.read_text().splitlines() if l.strip()]
        logger.info("loaded cached reference index: %d vectors dim=%d", len(meta), vecs.shape[1])
        return vecs, meta

    tasks = load_reference_tasks()
    texts = [t["prompt"] for t in tasks]
    logger.info("embedding %d real GDPval prompts…", len(texts))
    vecs = embed(texts)
    np.save(cache_vec, vecs)
    with cache_meta.open("w") as f:
        for t in tasks:
            f.write(
                json.dumps(
                    {"task_id": t["task_id"], "occupation": t["occupation"], "sector": t["sector"]}
                )
                + "\n"
            )
    return vecs, [
        {"task_id": t["task_id"], "occupation": t["occupation"], "sector": t["sector"]}
        for t in tasks
    ]


def too_close_to_reference(text: str, threshold: float = 0.78) -> tuple[bool, float, str | None]:
    """Return (is_too_close, max_cosine, matching_real_task_id).

    Threshold 0.78 chosen empirically — pure paraphrases land >0.85,
    same-domain different-task lands ~0.6-0.75, so 0.78 catches near-duplicates
    without rejecting legitimate same-occupation novelty.
    """
    ref_vecs, ref_meta = build_reference_index()
    qv = embed([text])  # (1, d)
    sims = (qv @ ref_vecs.T).flatten()
    idx = int(sims.argmax())
    max_sim = float(sims[idx])
    if max_sim >= threshold:
        return True, max_sim, ref_meta[idx]["task_id"]
    return False, max_sim, None


def pairwise_min_distance(texts: list[str]) -> np.ndarray:
    """Min cosine distance from each text to the rest (NaN if only 1)."""
    vecs = embed(texts)
    sims = vecs @ vecs.T
    np.fill_diagonal(sims, -np.inf)
    nearest = sims.max(axis=1)
    return 1.0 - nearest  # convert similarity → distance


def diversity_stats(texts: list[str]) -> dict[str, Any]:
    if len(texts) < 2:
        return {"n": len(texts), "note": "need ≥2 for diversity stats"}
    vecs = embed(texts)
    sims = vecs @ vecs.T
    np.fill_diagonal(sims, np.nan)
    upper = sims[np.triu_indices_from(sims, k=1)]
    return {
        "n": len(texts),
        "mean_pairwise_similarity": float(np.nanmean(upper)),
        "min_pairwise_similarity": float(np.nanmin(upper)),
        "max_pairwise_similarity": float(np.nanmax(upper)),
        "mean_pairwise_distance": float(1.0 - np.nanmean(upper)),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    vecs, meta = build_reference_index()
    print(f"\nReference index: {vecs.shape[0]} vectors × {vecs.shape[1]} dims")

    # Smoke-test: a real prompt should self-match at ~1.0; a totally unrelated string should be ~<0.2.
    real_prompt = load_reference_tasks()[0]["prompt"]
    is_close, sim, task_id = too_close_to_reference(real_prompt, threshold=0.99)
    print(f"\nSelf-match test: sim={sim:.4f}, matched={task_id}, is_close={is_close}")

    novel = "Build me a cake from scratch and explain how to frost it like a professional baker."
    is_close, sim, task_id = too_close_to_reference(novel)
    print(f"Novel-text test: sim={sim:.4f}, is_close={is_close}")
