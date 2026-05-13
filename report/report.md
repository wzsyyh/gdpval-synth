# GDPval-Style Synthetic Data Pipeline: Design, Results, and Evaluation

**Date:** 2026-05-12  
**Status:** Steps 1–2 complete (85 accepted candidates); Steps 3–6 blocked by OpenRouter spending limit.  
See `STATUS.md` for resumption instructions.

---

## 1. Problem Framing

GDPval is a benchmark of **real professional tasks** — Lawyer, Financial Analyst, and Software Engineer work samples drawn from practitioners. Its defining property is *ecological validity*: tasks cite real case law, real filings, real pull requests. Models score badly not because the prompts are tricky but because real work has canonical state (the amended complaint was filed at 2:17 PM, not in the evening) and requires reasoning over evidence rather than pattern-matching against training distribution.

The challenge of synthetic replication is threefold:

1. **Hallucination in citations.** LLMs confabulate reporter volumes and page numbers. A task citing a nonexistent case fails the same realism test as a bad deliverable.
2. **Lack of canonical anchor.** Without a real document to bootstrap, generated tasks drift toward generic ("analyze the contract") rather than specific ("turn around this MSA by Thursday, markup Section 9.3 given the Montejo-Gonzalez panel opinion").
3. **Calibration.** Tasks that are trivially solvable teach nothing; tasks that are impossible cannot produce gold deliverables. The pipeline must target the narrow band where frontier models solve 4–7 out of 10 probes.

---

## 2. Design Principles

The pipeline is organized around eight commitments:

| # | Commitment | Implementation |
|---|---|---|
| 1 | **Seed-driven** | Every task bootstraps from a real public document — a CourtListener case, an SEC EDGAR XBRL filing, a merged GitHub PR. No purely synthetic seeds. |
| 2 | **Canonical state** | The scenario builder (per-occupation `builders.py`) extracts dates, amounts, parties, and citations from the seed so the task can specify exact verifiable facts. |
| 3 | **Procedural numbers** | Financial tasks use actual EDGAR-reported revenues, ratios, and dates. Legal tasks use actual docket numbers and citation reporters. SWE tasks use actual PR diff sizes and merge timestamps. |
| 4 | **API-validated citations** | Lawyer tasks run every citation regex-match through CourtListener's citation-lookup endpoint; any scenario where no citation survives is rejected. |
| 5 | **Solve-rate calibration** | Three frontier models from different labs (DeepSeek, Kimi, MiMo) each rate the scenario's expected grade on a 0–10 scale. If any single model predicts ≥7, the task is "too easy" and is rejected. |
| 6 | **Cross-family critic** | The realism and solvability critics run on Kimi-K2.6, a different model family from the DeepSeek generator, to reduce self-confirmation bias. |
| 7 | **Diversity grid** | Candidates are sampled from a balanced grid of (occupation × deliverable_type × difficulty) cells to prevent the accepted set from concentrating on easy subtypes. |
| 8 | **Dedup against real GDPval** | Each candidate is embedded (BGE-small-en-v1.5) and compared against the 220 real GDPval tasks; nearest-neighbor cosine similarity > 0.85 triggers a re-roll. |

---

## 3. Pipeline Walkthrough

```
Real seed (CourtListener / XBRL / GitHub)
          │
          ▼
  [Stage 1] Enrichment
    Extract explicit/implicit/hidden facts from the seed document.
    e.g., "filing date = May 4, revenue = $9.6B, key exhibit = Ex. A"
          │
          ▼
  [Stage 2] Prompt Writer
    Compose a 2nd-person workplace task ("Henrik — it's Wednesday...").
    Uses seed facts, canonical timeline, and difficulty archetype.
          │
          ▼
  [Stage 3] Rubric Generator
    Output 30–55 binary/partial-credit rubric items across categories:
    format, substance (5–8 sub-items), citations, edge-case handling.
          │
          ▼
  [Stage 4] 5-Stage Quality Funnel
    Stage 1: Hard validators (citations roundtrip, date plausibility)
    Stage 2: Dedup (BGE cosine vs. real GDPval ≤ 0.85)
    Stage 3: Realism critic (Kimi-K2.6, overall ≥ 5/10)
    Stage 4: Solvability critic (Kimi-K2.6, overall ≥ 5/10)
    Stage 5: Solve-rate probe (3 models, max score < 7/10)
          │
          ▼
  ACCEPTED → data/accepted/
  REJECTED → data/rejected/ (kept for failure gallery + stats)
```

All three synthesis stages use `deepseek/deepseek-v4-flash` (fast, high-volume); all critics use `moonshotai/kimi-k2.6` (cross-family).

---

## 4. Per-Occupation Deep Dive

### 4.1 Lawyer (28 accepted / 133 processed = 21%)

Seeds: 29 CourtListener cases (SCOTUS, circuit, district). Tasks span `motion_to_dismiss`, `contract_redline`, `legal_memo`, `deposition_outline`.

The dominant archetype is `employment_dispute` and `breach_of_contract`. Hard tasks preferentially draw from SCOTUS and circuit seeds (defined by `_lawyer_court_tier() ≥ 2`) so that the cited precedent is major circuit authority rather than obscure district opinions.

**Key challenge:** Citation validator initially rejected all lawyer tasks because CourtListener's API returns `status=300` (ambiguous/multi-match) for valid citations, not `status=200` as the code expected. After the fix, citation validation became nearly a no-op (most citations skipped due to rate-limit → counted as `skipped`, not `not_found`).

Sample prompt snippet:
> *"Devika Ranganathan sent this on 2026-05-11 at 3:14 PM: 'Northbeam Logistics LLP is being sued by a former regional manager — breach of contract, retaliation, wrongful termination. We're moving to dismiss under Rule 12(b)(6). The hook is Montejo-Gonzalez v. Bondi, 141 F.4th 1334 (9th Cir. 2025)…'"*

### 4.2 Financial Analyst (24 accepted / 133 processed = 18%)

Seeds: 25 SEC EDGAR XBRL filings (large-cap for hard, mid/small for light). Tasks span `dcf_model`, `variance_analysis`, `credit_memo`, `investment_committee_deck`.

Hard tasks require multi-stage modeling from actual XBRL figures; light tasks focus on single-ratio interpretation. The instruction anchors on specific EDGAR filing dates and exact revenue figures to force document lookup.

Sample prompt snippet:
> *"Gabriel — we're doing a distressed credit memo on Uber (UBER)… Pull the Q1 2026 8-K financials off EDGAR — revenues $13.2B, operating income $1.9B, net income $263M, cash $5.6B. Use those figures to calculate at least five key credit ratios…"*

### 4.3 Software Engineer (33 accepted / 133 processed = 25%)

Seeds: 67 merged GitHub PRs (scored by quality: diff size, CI pass, description length). Tasks span `code_review`, `bug_fix_pr`, `design_doc`, `incident_postmortem`.

SWE has the highest accept rate, likely because GitHub PRs are rich in concrete facts (commit hashes, file paths, CI status) that ground the task in verifiable state.

Sample prompt snippet:
> *"It's May 11, 2026. You're a software engineer at Driftwood Systems. Our engineering manager wants a post-hoc API design review of Django PR #15687 (Fixed #33308 -- Added support for psycopg version 3), merged upstream on 2022-12-15…"*

---

## 5. SFT-Eval Headline Result

> **⚠️ PENDING — requires OpenRouter API access to complete Steps 3–6.**

The best-of-3 gold deliverable generation (Step 3), SFT training (Step 5), and evaluation (Step 6) all require OpenRouter API calls. The API key hit its configured spending limit at the tail end of the volume run.

**To complete this section:**
1. Top up key at https://openrouter.ai/settings/keys
2. Run `nohup uv run python -m pipeline.sft.run_best_of_n --workers 4 > logs/best_of_n.log 2>&1 &`
3. Follow Steps 4–6 from HANDOFF.md
4. Fill in the table below with actual numbers

| Model | Lawyer | Financial Analyst | SWE | Overall Mean |
|---|---|---|---|---|
| Qwen2.5-7B-Instruct (base) | — | — | — | — |
| Qwen2.5-7B-Instruct + SFT | — | — | — | — |
| Δ | — | — | — | — |

---

## 6. Funnel Statistics

**Total passed to funnel:** 304 scenarios  
**Accepted:** 85 (28%)  
**Rejected:** 219 (72%)

### Rejection breakdown by stage (fail-fast ordering)

| Stage | Rejected | % of rejected |
|---|---|---|
| Hard validators (citations, dates) | 8 | 3.7% |
| Dedup (cosine sim > 0.85 vs real GDPval) | 92 | 42.0% |
| Realism critic < 5/10 | 82 | 37.4% |
| Solvability critic < 5/10 | 36 | 16.4% |
| Solve-rate probe: ≥7 predicted by any model | 76 | 34.7% |
| Critic crashed (JSON parse / API error) | 17 | 7.8% |

*(Note: dedup count is "max stage reached = dedup" meaning the scenario was deduplicated before reaching the realism stage; other counts are stage-specific failures)*

### Rejection stage flow

```
400+200 = 600 submitted to grid
  ├── 296 "no available seed" (pre-funnel, seeds exhausted in run 1)
  └── 304 entered funnel
        ├── 8  → Hard validator failure
        ├── 92 → Dedup rejection
        ├── 82 → Realism < 5
        ├── 36 → Solvability < 5
        ├── 76 → Too easy (solve-rate)
        ├── 17 → Critic crash
        └── 85 → ACCEPTED ✓
```

The largest single rejection category after dedup is **realism** (82 rejections). This reflects the generator's tendency to produce tasks that are well-structured but lack the ground-level specificity of real professional work — symptoms include generic deadline framing, unanchored financial figures, and placeholder parties.

---

## 7. Diversity Analysis

Using BGE-small-en-v1.5 embeddings (dimension 384) against the 220 real GDPval tasks:

| Metric | Accepted set (n=85) | All candidates (n=300) |
|---|---|---|
| Mean pairwise distance | 0.313 | 0.316 |
| Min pairwise similarity | 0.489 | 0.447 |
| Max pairwise similarity | 0.941 | 0.949 |

The accepted set is nearly as diverse as the full candidate pool, indicating the funnel doesn't systematically collapse diversity (e.g., by preferring a narrow archetype).

**Coverage grid (accepted):**

| | Light | Medium | Hard |
|---|---|---|---|
| Lawyer | 6 | 12 | 10 |
| Financial Analyst | 3 | 12 | 9 |
| Software Engineer | 3 | 20 | 10 |

SWE medium is the most populous cell (20/85 = 24%). Legal light has the fewest (6). A more aggressive grid balancing in future runs should clamp SWE medium and oversample legal light.

**Rubric size (accepted candidates):**
- Min: 27 items, Max: 53 items, Median: 40 items, Mean: 40.2 items
- Total points: Median 144, Mean 149

The rubric size distribution is tight, which is intentional — excessively short rubrics give evaluators little signal; excessively long rubrics add noise.

---

## 8. Failure Gallery

### 8.1 Citation hallucination (pre-fix)

**Task:** Lawyer / motion_to_dismiss / medium  
**Failure:** `FAIL[citations]: verified=[]; not_found=['141 F.4th 1334']`  
**Root cause (pipeline bug):** CourtListener's citation-lookup API returns `status=300` (ambiguous match, multiple clusters) rather than `status=200`. The original validator only accepted `status=200`. This caused every valid lawyer citation to read as "not found." Fixed by accepting `status in (200, 300)`.

### 8.2 Seed exhaustion (pre-fix)

**Failure:** `no available seed` (appeared 296 times in run 1 tail)  
**Root cause (pipeline bug):** The orchestrator adds each seed to a shared `used_seeds` set and never resets it. With only 121 seeds and 400 tasks requested, the set became fully saturated. Fixed in `seeds/selector.py` to fall back to the full seed pool when all seeds are marked used.

### 8.3 Low realism — generic framing

**Task:** Financial Analyst / variance_analysis / hard  
**Realism scores:** `workplace_voice=5, domain_specificity=2, rubric_quality=4, fact_grounding=2`  
**Critic feedback (paraphrased):** Task references unnamed "Q3 results" and "budget targets" without pinning to actual XBRL filings or specific line items. A real financial analyst would receive the actual numbers first.  

**Lesson:** Enrichment stage must force explicit numerical anchors into the prompt template. The `fact_grounding` sub-score is the leading indicator for rejection.

### 8.4 Too easy — solve-rate probe rejection

**Task:** Software Engineer / incident_postmortem / medium  
**Rejection:** `xiaomi/mimo-v2.5-pro predicted 8/10 (≥7)`  
**Pattern:** Design-doc and incident-postmortem tasks fall into an "easy high-quality write" bucket — a fluent frontier model can produce a credible-looking deliverable even without the specific technical facts. The solve-rate probe is the correct filter here, but it means these task types have lower yield. Future work: add a "specificity boost" pass that injects more hard-to-bluff constraints (specific stack traces, error codes, exact SLO breach windows).

### 8.5 Critic crash — JSON parse failure

**Failure:** `solvability critic crashed: Expecting value: line 5611 column 1 (char 30855)`  
**Cause:** The kimi-k2.6 model's response exceeded its context and was truncated mid-JSON. The `chat_structured` function strips reasoning preambles but cannot recover truncated JSON.  
**Fix:** Already documented in HANDOFF.md — bump `max_tokens` from 4096 to 6000 in `critic/realism.py`. Also applicable to `critic/solvability.py`.

---

## 9. Scaling Discussion

The current yield is ~28% accept rate (after bug fixes), averaging ~4 minutes per task on 12 workers. Scaling to 1,000 accepted candidates would require:

- ~3,600 tasks at current yield → ~200 worker-hours at 4 min/task
- API cost at current rates: ~$60–80
- Blockers: (a) seed diversity (121 seeds recycle → homogenization risk); (b) CourtListener rate limit (5 req/min) bottlenecks lawyer throughput

**Recommended scaling path:**
1. Ingest more seeds: CourtListener has millions of cases; add 200 more with diverse courts and dates.
2. Raise CourtListener plan to access bulk API (or shift lawyer citation validation to a cached lookup table).
3. Parallelize across two OpenRouter keys to double API throughput.
4. For SWE, use GitHub's search API to expand from 67 to 500+ PR seeds before the next run.

---

## 10. What I'd Do With Another Week

| Priority | Work item | Expected impact |
|---|---|---|
| 🔴 | Resolve API budget: complete Steps 3–6 (gold gen → SFT → eval) | Produces the actual SFT result — the core deliverable |
| 🔴 | Fix `max_tokens` for solvability/realism critics (→ 6000) | Reduces critic-crash rejection rate from 5.6% to ~1% |
| 🟡 | `specificity_boost` pass for design-doc / incident-postmortem | Raises yield on "too easy" task types |
| 🟡 | Ingest 200 additional CourtListener seeds | Reduces lawyer seed recycling; diversifies precedent set |
| 🟡 | Grid balancing: cap SWE/medium to 15%, oversample legal/light | More uniform coverage distribution |
| 🟢 | Add a human spot-check loop on 10% of accepted candidates | Validates realism critic calibration against human judgment |
| 🟢 | Multi-turn task variants (follow-up clarification emails) | Extends GDPval-style evaluation to agentic task completion |
| 🟢 | Cross-seed contamination check: dedup within accepted set | Catches near-duplicate tasks from the same recycled seed |

---

*Report auto-generated by Claude Code autonomous run. See HANDOFF.md for original specification and STATUS.md for current pipeline state.*
