"""LLM client with support for multiple API backends (OpenRouter, Mimo).

All LLM calls in the pipeline route through here so we have a single place to
swap models, log token usage, and enforce retry logic.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from pipeline.config import PROJECT_ROOT, settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

USAGE_LOG = PROJECT_ROOT / "data" / "llm_usage.jsonl"

# Backend URLs
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        default_model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.s = settings()
        self.default_model = default_model or self.s.generator_model

        # Determine backend: Mimo if configured, else OpenRouter
        if api_key:
            self.api_key = api_key
            self.base_url = base_url or self.s.mimo_base_url
            self.backend = "mimo"
        elif self.s.mimo_api_key:
            self.api_key = self.s.mimo_api_key
            self.base_url = self.s.mimo_base_url
            self.backend = "mimo"
        elif self.s.openrouter_api_key:
            self.api_key = self.s.openrouter_api_key
            self.base_url = OPENROUTER_URL
            self.backend = "openrouter"
        else:
            raise RuntimeError("No LLM API key configured. Set MIMO_API_KEY or OPENROUTER_API_KEY in .env")

        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
        }
        if self.backend == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/local/gdpval-data"
            headers["X-Title"] = "gdpval-data-pipeline"

        self._client = httpx.Client(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers=headers,
        )
        logger.info("LLMClient initialized: backend=%s model=%s", self.backend, self.default_model)

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, LLMError)),
        reraise=True,
    )
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Returns (content, raw_response_dict). Caller does parsing."""
        model = model or self.default_model
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        t0 = time.time()
        resp = self._client.post(self.base_url, json=payload)
        if resp.status_code >= 400:
            raise LLMError(f"{self.backend} {resp.status_code}: {resp.text[:500]}")
        try:
            data = resp.json()
        except Exception as e:
            raise LLMError(f"{self.backend} returned non-JSON body: {resp.text[:300]}") from e
        elapsed = time.time() - t0

        if "choices" not in data or not data["choices"]:
            raise LLMError(f"No choices in response: {data}")
        message = data["choices"][0]["message"]
        content = message.get("content")
        if content is None:
            # Some models put their answer into reasoning_details; fall back.
            rd = message.get("reasoning") or ""
            if rd:
                content = rd
            else:
                raise LLMError(
                    f"empty content from {model}; finish_reason={data['choices'][0].get('finish_reason')}"
                )

        usage = data.get("usage", {})
        self._log_usage(model, usage, elapsed)
        return content, data

    def chat_structured(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        *,
        model: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 4096,
    ) -> T:
        """Force JSON output and validate against pydantic schema.

        Uses response_format json_object plus a retry loop on
        parse failure (some models ignore the constraint).
        """
        sys_addendum = (
            "\n\nReturn a single JSON object matching this schema:\n"
            f"{json.dumps(schema.model_json_schema(), indent=2)}"
        )
        msgs = [
            {**messages[0], "content": messages[0]["content"] + sys_addendum}
            if messages[0]["role"] == "system"
            else {"role": "system", "content": "Return JSON." + sys_addendum},
            *([m for m in messages if m["role"] != "system"]),
        ]
        last_err: Exception | None = None
        for _attempt in range(3):
            content, _ = self.chat(
                msgs,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            try:
                # Robust extraction: strip code fences AND find first { ... } object.
                stripped = content.strip()
                if stripped.startswith("```"):
                    stripped = stripped.strip("`")
                    if stripped.startswith("json\n"):
                        stripped = stripped[5:]
                # If preamble before JSON, locate first balanced { ... }.
                if not stripped.startswith("{") and not stripped.startswith("["):
                    start = stripped.find("{")
                    if start == -1:
                        raise ValueError(f"no JSON object found in: {stripped[:200]!r}")
                    # Walk to find matching close brace, respecting strings.
                    depth = 0
                    end = -1
                    in_str = False
                    escape = False
                    for i in range(start, len(stripped)):
                        ch = stripped[i]
                        if escape:
                            escape = False
                            continue
                        if ch == "\\" and in_str:
                            escape = True
                            continue
                        if ch == '"':
                            in_str = not in_str
                            continue
                        if in_str:
                            continue
                        if ch == "{":
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                            if depth == 0:
                                end = i + 1
                                break
                    if end == -1:
                        raise ValueError(f"unbalanced JSON in: {stripped[start:start+200]!r}")
                    stripped = stripped[start:end]
                return schema.model_validate_json(stripped)
            except Exception as e:
                last_err = e
                msgs.append({"role": "assistant", "content": content})
                msgs.append(
                    {
                        "role": "user",
                        "content": f"Your response failed validation: {e}. Return only valid JSON matching the schema.",
                    }
                )
        raise LLMError(f"Structured output failed after retries: {last_err}")

    def _log_usage(self, model: str, usage: dict, elapsed: float) -> None:
        USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with USAGE_LOG.open("a") as f:
            f.write(
                json.dumps(
                    {
                        "ts": time.time(),
                        "backend": self.backend,
                        "model": model,
                        "elapsed_s": round(elapsed, 2),
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "total_tokens": usage.get("total_tokens"),
                    }
                )
                + "\n"
            )

    def close(self) -> None:
        self._client.close()


_default: LLMClient | None = None


def default_client() -> LLMClient:
    global _default
    if _default is None:
        _default = LLMClient()
    return _default
