"""Central config — env vars, paths, model routing."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SEEDS_STORE = PROJECT_ROOT / "pipeline" / "seeds" / "store"
TAXONOMY_PATH = PROJECT_ROOT / "pipeline" / "taxonomy" / "occupations.yaml"


class Settings(BaseModel):
    openrouter_api_key: str | None = None
    courtlistener_api_token: str
    github_token: str
    sec_edgar_user_agent: str
    fred_api_key: str | None = None

    # Mimo API (primary LLM provider for this run)
    mimo_api_key: str | None = None
    mimo_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1/chat/completions"
    mimo_model: str = "mimo-v2.5-pro"

    # Model routing: if mimo is configured, use it; else fall back to openrouter
    generator_model: str = "mimo-v2.5-pro"
    critic_model: str = "mimo-v2.5-pro"
    solve_rate_models: list[str] = [
        "mimo-v2.5-pro",
    ]
    embed_model: str = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    required = {
        "courtlistener_api_token": "COURTLISTENER_API_TOKEN",
        "github_token": "GITHUB_TOKEN",
        "sec_edgar_user_agent": "SEC_EDGAR_USER_AGENT",
    }
    optional = {
        "openrouter_api_key": "OPENROUTER_API_KEY",
    }
    kwargs: dict[str, str | None | list[str]] = {}
    missing: list[str] = []
    for field, env_var in required.items():
        val = os.environ.get(env_var)
        if not val:
            missing.append(env_var)
        kwargs[field] = val
    for field, env_var in optional.items():
        kwargs[field] = os.environ.get(env_var)
    if missing:
        raise RuntimeError(
            f"Missing required env vars: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill in."
        )
    if fred := os.environ.get("FRED_API_KEY"):
        kwargs["fred_api_key"] = fred
    # Mimo API config
    if mimo_key := os.environ.get("MIMO_API_KEY"):
        kwargs["mimo_api_key"] = mimo_key
    if mimo_url := os.environ.get("MIMO_BASE_URL"):
        kwargs["mimo_base_url"] = mimo_url
    if mimo_model := os.environ.get("MIMO_MODEL"):
        kwargs["mimo_model"] = mimo_model
    # Override model routing from env if explicitly set
    if gen := os.environ.get("GENERATOR_MODEL"):
        kwargs["generator_model"] = gen
    if crit := os.environ.get("CRITIC_MODEL"):
        kwargs["critic_model"] = crit
    for opt in ("generator_model", "critic_model", "embed_model"):
        if v := os.environ.get(opt.upper()):
            kwargs[opt] = v
    return Settings(**kwargs)  # type: ignore[arg-type]
