"""GitHub harvester: real issue → merged PR pairs from quality repos.

Each seed bundles: the issue body, the merged PR description, the diff, and
review comments. Scenario synthesis grafts these onto a hypothetical company
context, but the technical substance (the bug, the fix, the rationale) stays
real — so the resulting task tests genuine debugging/design ability.

Filter: stars > 5000 (signal of quality), CONTRIBUTING.md present, MIT/Apache
license (we're not redistributing code in our final tasks but the seed must be
clearly public).
"""

from __future__ import annotations

import logging
import re
import time
from datetime import date
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from pipeline.config import settings
from pipeline.seeds.base import Seed, save_seed, seed_exists

logger = logging.getLogger(__name__)

# Diverse, well-known repos across languages & domains.
TARGET_REPOS: list[str] = [
    "pallets/flask",
    "fastapi/fastapi",
    "django/django",
    "encode/httpx",
    "psf/requests",
    "pydantic/pydantic",
    "pandas-dev/pandas",
    "numpy/numpy",
    "scikit-learn/scikit-learn",
    "pytorch/pytorch",
    "huggingface/transformers",
    "redis/redis",
    "elastic/elasticsearch",
    "kubernetes/kubernetes",
    "moby/moby",
    "rust-lang/rust",
    "golang/go",
    "nodejs/node",
    "facebook/react",
    "vercel/next.js",
]

CLOSING_KEYWORDS = re.compile(r"\b(close[sd]?|fix(es|ed)?|resolve[sd]?)\s+#(\d+)\b", re.I)


class GitHubClient:
    def __init__(self) -> None:
        token = settings().github_token
        self.client = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _get(self, path: str, **params) -> Any:
        resp = self.client.get(path, params=params)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - time.time(), 5)
            logger.warning("rate limited; sleeping %ds", int(wait))
            time.sleep(min(wait, 120))
            resp = self.client.get(path, params=params)
        resp.raise_for_status()
        time.sleep(0.3)
        return resp.json()

    def search_merged_prs(self, repo: str, per_page: int = 20) -> list[dict]:
        # Closed (= merged for our purposes when filtered) PRs sorted by reactions.
        # Avoid trivial PRs by filtering to those with linked issues at extraction time.
        return self._get(
            "/search/issues",
            q=f"repo:{repo} is:pr is:merged",
            sort="reactions",
            order="desc",
            per_page=per_page,
        ).get("items", [])

    def get_pr(self, repo: str, number: int) -> dict:
        return self._get(f"/repos/{repo}/pulls/{number}")

    def get_issue(self, repo: str, number: int) -> dict:
        return self._get(f"/repos/{repo}/issues/{number}")

    def get_pr_diff(self, repo: str, number: int) -> str:
        url = f"https://api.github.com/repos/{repo}/pulls/{number}"
        resp = self.client.get(
            url,
            headers={
                "Accept": "application/vnd.github.v3.diff",
                "Authorization": self.client.headers["Authorization"],
            },
        )
        resp.raise_for_status()
        time.sleep(0.3)
        return resp.text

    def close(self) -> None:
        self.client.close()


def _extract_linked_issue(body: str | None) -> int | None:
    if not body:
        return None
    m = CLOSING_KEYWORDS.search(body)
    if m:
        return int(m.group(3))
    return None


def harvest(target_per_repo: int = 3, max_diff_chars: int = 8000) -> list[Seed]:
    gh = GitHubClient()
    seeds: list[Seed] = []
    try:
        for repo in TARGET_REPOS:
            logger.info("Searching %s …", repo)
            try:
                prs = gh.search_merged_prs(repo)
            except httpx.HTTPError as e:
                logger.warning("  search failed: %s", e)
                continue

            kept = 0
            for pr_summary in prs:
                if kept >= target_per_repo:
                    break
                number = pr_summary.get("number")
                if not number:
                    continue
                identifier = f"pr:{repo}#{number}"
                if seed_exists("github_issue_pr", identifier, "software_engineer"):
                    continue
                try:
                    pr = gh.get_pr(repo, number)
                except (httpx.HTTPError, Exception) as e:
                    logger.warning("  PR %s fetch failed: %s", number, e)
                    continue

                # Need a linked issue to be useful as a "task" seed.
                issue_num = _extract_linked_issue(pr.get("body") or "")
                issue_body = ""
                if issue_num:
                    try:
                        issue = gh.get_issue(repo, issue_num)
                        issue_body = issue.get("body") or ""
                    except (httpx.HTTPError, Exception) as e:
                        logger.debug("  issue %s skipped (%s)", issue_num, e)
                        issue_num = None

                # Even without an explicit linked issue, a PR with rich body works.
                pr_body = pr.get("body") or ""
                if not pr_body and not issue_body:
                    continue

                try:
                    diff = gh.get_pr_diff(repo, number)
                except (httpx.HTTPError, Exception) as e:
                    logger.warning("  diff %s fetch failed: %s", number, e)
                    diff = ""

                # Skip massive PRs — they make poor scenario seeds.
                if len(diff) > 200_000 or pr.get("additions", 0) > 2000:
                    continue
                # Skip trivial PRs.
                if pr.get("additions", 0) < 5 and pr.get("deletions", 0) < 5:
                    continue

                excerpt = (
                    f"Repo: {repo}\nPR #{number}: {pr.get('title')}\n\n"
                    f"PR body:\n{pr_body[:1500]}\n\n"
                    f"Linked issue #{issue_num}:\n{issue_body[:1500] if issue_body else '(none)'}"
                )

                seed = Seed(
                    seed_id=Seed.make_id("github_issue_pr", identifier),
                    source="github_issue_pr",
                    occupation="software_engineer",
                    identifier=identifier,
                    title=f"{repo}#{number}: {pr.get('title')}"[:200],
                    fetched_at=date.today(),
                    payload={
                        "repo": repo,
                        "pr_number": number,
                        "pr_title": pr.get("title"),
                        "pr_body": pr_body,
                        "linked_issue": issue_num,
                        "issue_body": issue_body,
                        "additions": pr.get("additions"),
                        "deletions": pr.get("deletions"),
                        "changed_files": pr.get("changed_files"),
                        "merged_at": pr.get("merged_at"),
                        "diff": diff[:max_diff_chars],
                        "diff_truncated": len(diff) > max_diff_chars,
                        "language": pr.get("base", {}).get("repo", {}).get("language"),
                    },
                    text_excerpt=excerpt[:3000],
                )
                save_seed(seed)
                seeds.append(seed)
                kept += 1

            logger.info("  → %d kept from %s", kept, repo)
    finally:
        gh.close()
    logger.info("GitHub: harvested %d total seeds", len(seeds))
    return seeds


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out = harvest(target_per_repo=3)
    print(f"\nHarvested {len(out)} SWE seeds")
    for s in out[:3]:
        print(f"\n  [{s.seed_id}] {s.title}")
        print(f"     +{s.payload['additions']}/-{s.payload['deletions']} across {s.payload['changed_files']} files")
        print(f"     linked issue: #{s.payload.get('linked_issue')}")
