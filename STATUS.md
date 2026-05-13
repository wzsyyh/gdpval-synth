# Pipeline Status

**Last updated:** 2026-05-12 03:35 CDT  
**Author:** Claude (autonomous run per HANDOFF.md)

---

## Completed Steps

### Step 1 — Environment sanity-check ✅
- Seeds: 29 lawyer / 25 financial_analyst / 67 software_engineer (all present)
- Config: `deepseek/deepseek-v4-flash` confirmed as generator

### Step 2 — Volume run ✅ (85 accepted)
Two runs:
- Run 1: `n=400 --workers 12` → 32/400 accepted (8%)
- Run 2 (top-up): `n=200 --workers 12` → 53/200 accepted (26%)
- **Total: 85 accepted** (financial: 24, lawyer: 28, software_engineer: 33)
- Logs: `logs/orch.log` (run 1), `logs/orch2.log` (run 2)

**Bugs fixed during this run:**
1. `pipeline/validators/citations.py` — CourtListener API returns `status=300` for
   valid citations (ambiguous match), not `status=200`. Fixed: now accepts both.
2. `pipeline/seeds/selector.py` — After all 121 seeds were used once, selector returned
   `None` ("no available seed"). Fixed: falls back to full pool when exhausted.

---

## BLOCKED: Steps 3–6 require OpenRouter API

**Error at end of run 2:**
```
OpenRouter 403: {"error":{"message":"Key limit exceeded (total limit). 
Manage it using https://openrouter.ai/settings/keys","code":403}}
```

The API key has hit its configured spending limit.

**To unblock:** Go to https://openrouter.ai/settings/keys and increase
(or remove) the total spend limit on the active key.  
Estimated cost to complete:
- Step 3 (best-of-3, ~100 candidates × 3 models): ~$10
- Step 6 (eval, 15 tasks via OpenRouter): ~$1

---

## Steps Remaining (in order)

### Step 3 — Best-of-3 gold deliverable generation ❌ BLOCKED
```bash
nohup uv run python -m pipeline.sft.run_best_of_n --workers 4 > logs/best_of_n.log 2>&1 &
```

### Step 4 — SFT data preparation ❌ BLOCKED (needs Step 3)
```bash
uv run python -m pipeline.sft.data_prep
cat data/sft/dataset_summary.json
```
If <60 examples pass `min_gold_score=0.5`, lower to 0.4 in `data_prep.py`.

### Step 5 — QLoRA SFT training ❌ BLOCKED (needs Step 4)
```bash
pip install -r pipeline/sft/requirements_train.txt
nohup python -m pipeline.sft.train --base Qwen/Qwen2.5-7B-Instruct --epochs 5 --rank 16 --lr 2e-4 > logs/train.log 2>&1 &
```

### Step 6 — Evaluation ❌ BLOCKED (needs SFT model)
After training, evaluate base vs SFT on real GDPval.

### Step 7 — Diversity stats ✅ Can run now
```bash
uv run python -m pipeline.diversity.stats > data/stats_final.json
```

---

## Additional completed work (this session)

### Step 7 — Diversity stats ✅
```
data/stats_final.json  — coverage grid, rubric stats, diversity vs GDPval, funnel breakdown
```

### Report ✅
```
report/report.md  — complete report with all 10 sections; Section 5 (SFT-eval result) has placeholder pending API
```

### GPU training environment ✅
- PyTorch 2.5.1+cu124 installed and verified CUDA=True on NVIDIA RTX A6000
- All training deps: peft 0.19.1, transformers 5.8.0, bitsandbytes 0.49.2, accelerate

## What to do when you return

1. Top up OpenRouter key at https://openrouter.ai/settings/keys (~$15 to complete pipeline)
2. Re-run: `nohup uv run python -m pipeline.sft.run_best_of_n --workers 4 > logs/best_of_n.log 2>&1 &`
3. Proceed through Steps 4–6 as in HANDOFF.md
4. Fill in report/report.md Section 5 with actual eval numbers
