# Handoff: GDPval-style Synthetic Data Pipeline → Server Run

You are picking up an in-progress take-home project. The Mac-side work is done; this document tells you what to run next on the server (where there's an A6000 GPU, persistent uptime, and decent network).

## What this project is

A pipeline that generates GDPval-style synthetic professional tasks (Lawyer / Financial Analyst / Software Engineer) from real public seeds (CourtListener / SEC EDGAR XBRL / GitHub PRs), then validates them through a multi-stage critic funnel. The take-home goal is to demonstrate the pipeline + ideally show that an SFT model trained on our synthetic data improves on real GDPval evaluation.

Detailed design: see `/Users/yangyuheng/.claude/plans/dynamic-wibbling-emerson.md` (in the user's plan dir; if missing, ignore — this doc has all you need).

## Current state when you take over

- ✅ Day 1 — Seed harvesters: 29 lawyer + 25 financial + 67 SWE seeds in `pipeline/seeds/store/`
- ✅ Day 2 — 3-stage scenario synthesis (enrichment → prompt writer → rubric generator) in `pipeline/scenario/`
- ✅ Day 3 — Markdown/docx/xlsx renderers (scaffold; not used in main path)
- ✅ Day 4 — Validators (`pipeline/validators/`) + cross-family critic + solve-rate probe + 5-stage funnel (`pipeline/critic/funnel.py`)
- ✅ Day 5 prep — Orchestrator (`pipeline/orchestrator.py`) ready, sanity-tested at n=12 with 25% accept rate
- ✅ SFT pipeline scaffold:
  - `pipeline/artifacts/best_of_n.py` — best-of-3 deliverable + LLM judge
  - `pipeline/sft/run_best_of_n.py` — driver to materialize gold across all accepted
  - `pipeline/sft/data_prep.py` — emit ChatML / Alpaca SFT files
  - `pipeline/sft/train.py` — QLoRA on Qwen2.5-7B-Instruct
  - `pipeline/sft/requirements_train.txt` — extra deps for the GPU box
  - `pipeline/eval/run_eval.py` — base vs SFT evaluation on real GDPval

## Environment

- `pyproject.toml` + `uv.lock` — managed by uv
- `.env` — has all API keys (OpenRouter, CourtListener, GitHub, SEC EDGAR UA)
- DO NOT regenerate seeds, embeddings, or the GDPval reference download — those are cached on disk:
  - `pipeline/seeds/store/` — 121 real seeds
  - `data/gdpval_reference/tasks.jsonl` — 220 real GDPval tasks
  - `data/embeddings/gdpval_reference.npy` — cached BGE embeddings

## Models in use (via OpenRouter)

| Role | Model | Why |
|---|---|---|
| Generator (synthesis) | `deepseek/deepseek-v4-flash` | Cheapest, high volume |
| Critic (realism + solvability) | `moonshotai/kimi-k2.6` | Cross-family from generator |
| Solve-rate probe | `deepseek/deepseek-v4-pro`, `xiaomi/mimo-v2.5-pro`, `moonshotai/kimi-k2.6` | 3 different labs, max=7 → reject |
| Embeddings | `BAAI/bge-small-en-v1.5` (local sentence-transformers) | No API needed |
| Best-of-3 deliverable gen | `deepseek/deepseek-v4-pro` + `kimi-k2.6` + `mimo-v2.5-pro` | Cross-family for variety |
| Best-of-3 judge | `deepseek/deepseek-v4-pro` | Same lab as one generator (best efficiency/cost; ideally a 4th lab but Path B accepted this trade-off) |

## TODO list — execute in order

You should run these autonomously. The user has set up `caffeinate` and is OK with the project running for many hours unattended. Use `nohup ... &` and `tee` so logs survive your own session restarts.

### Step 1 — sanity-check the env on the server

```bash
cd <project-root>
uv sync     # restore deps from lock
uv run python -c "from pipeline.config import settings; print(settings().generator_model)"   # should print deepseek/deepseek-v4-flash
uv run python -c "from pipeline.seeds.base import load_seeds; print(len(load_seeds('lawyer')), len(load_seeds('financial_analyst')), len(load_seeds('software_engineer')))"   # should be 29 / 25 / 67
```

If seeds are missing (transferred dir lost them), re-run `uv run python -m pipeline.seeds.{courtlistener,edgar_xbrl,github_issues}`.

### Step 2 — large volume run (60-90 min wall time)

```bash
nohup uv run python -m pipeline.orchestrator -n 400 --workers 12 > logs/orch.log 2>&1 &
echo $! > /tmp/orch.pid
```

Expected outcome at n=400 with ~25% accept rate: ~80-120 accepted candidates in `data/accepted/`. Costs ~$10-15 in API. Wall time 5-7 hours.

Monitor with:
```bash
uv run python scripts/monitor.py
```

If accept rate drops below 15%, *don't* let it finish — diagnose. Common causes:
- Critic JSON parse failures (check `grep "Structured output failed" logs/orch.log`)
- Citations validator API rate limits
- A specific bad seed selector path

If the run finishes with <60 accepted, re-run with `-n 200` to top up (orchestrator naturally appends — it doesn't clean previous accepted).

### Step 3 — best-of-3 gold deliverable generation (1-2h wall time)

```bash
nohup uv run python -m pipeline.sft.run_best_of_n --workers 4 > logs/best_of_n.log 2>&1 &
```

Each candidate runs 3 generations in parallel internally; outer 4 workers = 12 simultaneous LLM calls. With ~100 accepted, this takes 60-90 min and ~$10.

Outputs `data/gold/{candidate_id}.json` per candidate. Idempotent (skips already-done).

### Step 4 — SFT data preparation

```bash
uv run python -m pipeline.sft.data_prep
cat data/sft/dataset_summary.json
```

Look at the summary: how many examples passed `min_gold_score=0.5`? If <60 examples, lower the threshold to 0.4 in `data_prep.py:build_dataset(min_gold_score=)` and re-run. We need at least 80-100 examples for SFT to register meaningful improvement.

### Step 5 — QLoRA SFT on A6000

```bash
# Install GPU deps once on the A6000 host
pip install -r pipeline/sft/requirements_train.txt

# Train (assumes 1 A6000 with 48 GB VRAM)
nohup python -m pipeline.sft.train \
  --base Qwen/Qwen2.5-7B-Instruct \
  --epochs 5 \
  --rank 16 \
  --lr 2e-4 \
  > logs/train.log 2>&1 &
```

A6000 + 7B + QLoRA + ~100 examples × 5 epochs ≈ 30-45 min. Output goes to `outputs/{run_name}/`.

If training loss doesn't drop meaningfully in epoch 1 (e.g., stuck above 1.5), the SFT data is likely too noisy. Bail and report this finding rather than burning more compute.

### Step 6 — Evaluation: base vs SFT on real GDPval

Two backends. **Use local backend on the A6000** since both base and SFT models are loaded there.

```bash
# Local eval — 5 tasks per occupation = 15 total real GDPval tasks
nohup python -m pipeline.eval.run_eval \
  --backend local \
  --local-base Qwen/Qwen2.5-7B-Instruct \
  --local-adapter outputs/{your_run_name} \
  --n-per-occ 5 \
  > logs/eval.log 2>&1 &
```

NOTE: the current `run_eval.py` `local` backend has a bug — it can only load ONE model at a time. To compare base vs SFT properly:

1. Run twice: once with `--local-adapter ""` (renamed via `--out-name eval_base`), once with the real adapter (`--out-name eval_sft`).
2. Then merge the two `.jsonl` files into a comparison plot manually, OR
3. Fix the `_load_local` function to maintain two model instances on the same GPU (A6000 has 48GB, two 7Bs fit).

The cleanest fix is to evaluate base via OpenRouter:
```bash
# Base via OpenRouter (1 source of truth)
python -m pipeline.eval.run_eval \
  --backend openrouter \
  --base-model qwen/qwen2.5-7b-instruct \
  --sft-model qwen/qwen2.5-7b-instruct \
  --n-per-occ 5 \
  --out-name eval_base_openrouter

# SFT via local
python -m pipeline.eval.run_eval \
  --backend local \
  --local-base Qwen/Qwen2.5-7B-Instruct \
  --local-adapter outputs/{your_run_name} \
  --n-per-occ 5 \
  --out-name eval_sft_local
```

The eval script's `summary.json` reports mean rubric satisfaction. Compare across the two runs.

### Step 7 — Statistics + writeup

```bash
uv run python -m pipeline.diversity.stats > data/stats_final.json
```

This gives:
- coverage grid (how balanced our final pool is)
- rubric size distribution
- pairwise diversity vs real GDPval
- funnel rejection breakdown

Write the report at `report/report.md`. Sections:
1. Problem framing — what GDPval is, what makes synthesis hard
2. Design principles — the 8 commitments (seed-driven, canonical state, procedural numbers, API-validated citations, solve-rate calibration, cross-family critic, diversity grid, dedup)
3. Pipeline walkthrough
4. Per-occupation deep dive
5. **The SFT-eval headline result** — base vs fine-tuned mean score, per-occupation deltas
6. Funnel statistics (with chart)
7. Diversity analysis
8. Failure gallery (use `data/rejected/` examples + the critic feedback we logged)
9. Scaling discussion
10. What I'd do with another week

## Things to NOT do

- Don't re-run the seed harvesters — they're cached and rate-limited
- Don't bump `funnel.py` thresholds higher (5/5/<7 is already calibrated)
- Don't generate task candidates with the wrong canonical builder (they live in `pipeline/scenario/builders.py`, dispatched per-occupation)
- Don't use `Skill` or other agent tools; just run scripts via Bash
- Don't commit `.env` (it's already gitignored)

## Known issues

- `pipeline/llm.py:chat_structured` has been hardened against truncated JSON and `"reasoning before JSON"` preambles, but new model providers may surface new failure modes — log them and add to the strip-prefix logic.
- `pipeline/critic/realism.py` previously hit max_tokens; now bumped to 4096. If still truncated, bump to 6000.
- The orchestrator uses a thread-safe `set` for seed dedup but seeds are still sometimes reused at the boundary; this is acceptable noise.

## Status of task list (resume from)

```
#1. ✅ Day 1: Taxonomy + 3 seed harvesters + GDPval embedding
#2. ✅ Day 2: Canonical timeline + multi-agent scenario synthesis
#3. ✅ Day 3: Deliverable scaffold (deferred to future work)
#4. ✅ Day 4: Validators + cross-family critic + solve-rate filter
#5. 🟡 Day 5: Volume run n=400 → ~100 accepted candidates  (PARTIALLY ATTEMPTED)
#8. ⬜ Day 6a: Best-of-3 gold deliverable generation
#9. ⬜ Day 6b: SFT data prep + QLoRA on Qwen2.5-7B
#10. ⬜ Day 7a: Eval base vs fine-tuned on real GDPval subset
#7. ⬜ Day 7b: Final report + blind study
```

The user is offline. Make decisions and proceed. Surface results as they come in via brief summary messages. Use `caffeinate` (already running on user's Mac, but on the server `screen`/`tmux` + `nohup` is the equivalent).

If anything blocks for >30 min and you can't resolve, write a clear status note to `STATUS.md` at the repo root explaining what's stuck and what you tried, then move on to anything else still doable.
