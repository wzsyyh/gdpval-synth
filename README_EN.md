# GDPval Synthetic Task Generation Pipeline

> A seed-driven pipeline that generates professional assessment tasks indistinguishable from real [GDPval](https://openai.com/index/introducing-swe-bench-verified/) (OpenAI's 220-task benchmark across 44 occupations).
>
> **Current corpus: 84 accepted tasks** (lawyer: 34, financial analyst: 12, software engineer: 38) with real deliverables (.docx, .xlsx, .md, .pdf).

---

## 1. Motivation

GDPval evaluates domain-proficient agents across 44 occupations, with 5 tasks each. Building such a dataset manually is expensive and slow — each task requires a domain expert to design the prompt, write a reference answer, and craft a fine-grained rubric.

**Our insight**: while the domains differ, the *data-generation logic* is the same. We selected **3 representative occupations** that span very different professional workflows:

| Occupation | GDPval Equivalent | Real-World Seed Source |
|---|---|---|
| Lawyer | Lawyers | CourtListener API (federal & state opinions) |
| Financial Analyst | Financial and Investment Analysts | SEC EDGAR XBRL filings |
| Software Engineer | Software Developers | GitHub Issues & PRs (scikit-learn, pandas, etc.) |

Each domain has distinct deliverable formats, reasoning patterns, and grounding requirements — making them a strong proxy for the full 44-occupation benchmark.

---

## 2. Methodology

We replicate the GDPval design process programmatically:

```
Real public artifact (seed)
    ↓  [harvested from CourtListener / EDGAR / GitHub]
LLM reads full seed material
    ↓  [single structured generation call]
UnifiedTask { prompt + answer_blueprint + rubric }
    ↓  [deterministic code rendering]
Deliverable file (.docx / .xlsx / .md / .pdf)
    ↓  [hard quality validators]
Accepted or rejected
```

### 2.1 Seed Collection

Instead of inventing scenarios, we ground every task in real public data:

- **Lawyer**: Full opinion texts from the U.S. Supreme Court, 9th Circuit, 2nd Circuit, etc. (via CourtListener REST API). Previously truncated at 2,000 chars; now harvested at **10,000 chars** to capture holdings, reasoning, and factual details.
- **Financial Analyst**: Structured XBRL financial statements (revenue, net income, assets, liabilities, EPS) from SEC EDGAR for AAPL, MSFT, NVDA, GOOGL, META, AMZN, TSLA, BAC, JPM.
- **Software Engineer**: Merged PR diffs, descriptions, and linked issues from high-impact open-source repos (scikit-learn, pandas, matplotlib, pytorch).

### 2.2 Unified Generation

A single LLM call (Mimo v2.5 Pro) reads the complete seed material and outputs a structured `UnifiedTask`:

- **Prompt**: The task requirements, written as a realistic work assignment.
- **Answer Blueprint**: A structured outline of the reference answer (sections, paragraphs, formulas, expected values) — designed *synchronously* with the prompt so they match exactly.
- **Rubric**: 35–57 fine-grained scoring criteria, each checking a specific fact or structural element in the answer.
- **Deliverable Type**: Determined by the seed content (e.g., a contract-interpretation opinion → `legal_memo`; a PR with API changes → `code_review` or `design_doc`).

Per-occupation system prompts ensure the LLM uses domain-appropriate language and format conventions.

### 2.3 Deterministic Rendering

The answer blueprint is rendered to a real file by code (no LLM involved):

| Format | Library | Example Deliverables |
|---|---|---|
| `.docx` | python-docx | Legal memos, credit memos, investment memos |
| `.xlsx` | openpyxl | Financial models with live formulas |
| `.md` | plain text | Code reviews, design docs, incident postmortems |
| `.pdf` | LibreOffice headless | Legal docs rendered from docx |

### 2.4 Quality Funnel

Tasks pass through two quality gates before acceptance:

**Hard quality checks** (deterministic):
- Prompt length ≥ 1,300 chars
- Rubric items ≥ 35 and ≤ 80
- Expected values ≥ 3
- Score distribution not skewed (>85% on one score)
- Rubric items are specific and verifiable (not vague)
- Input attachments have real content (≥ 100 chars)

**LLM consistency validation** (model-based):
- Seed facts correctly cited (seed alignment)
- Numerical calculations correct (calculation accuracy)
- Rubric items match answer content (rubric alignment)
- Prompt requirements addressed in answer (prompt coverage)

**Acceptance rate: ~75%** (84/112). Lawyer ~83%, SWE ~97%, Financial ~43% — the lower financial rate is due to XBRL data complexity (YTD/quarterly confusion, rounding precision).

---

## 3. Dataset Statistics

### 3.1 Overall Corpus

```
Total accepted tasks: 84
Total generated: 112 (84 accepted + 28 rejected)
Acceptance rate through quality gate: ~75%
```

### 3.2 By Occupation

| Occupation | Tasks | % of Corpus | Accept Rate | GDPval Equivalent | GDPval Count |
|---|---|---|---|---|---|
| Software Engineer | 38 | 45% | ~97% (38/39) | Software Developers | 5 |
| Lawyer | 34 | 40% | ~83% (34/41) | Lawyers | 5 |
| Financial Analyst | 12 | 14% | ~43% (12/28) | Financial and Investment Analysts | 5 |

We generated **2–8x more tasks per domain** than the original GDPval benchmark, while maintaining comparable granularity and grounding.

### 3.3 Deliverable Types

| Type | Count | Description |
|---|---|---|
| `legal_memo` | 34 | Formal legal memoranda analyzing court opinions |
| `code_review` | 24 | Post-merge technical reviews of PRs |
| `design_doc` | 12 | Architecture/design documents for new features |
| `investment_memo` | 8 | Investment analysis memos with financial metrics |
| `credit_memo` | 4 | Credit committee memos with leverage analysis |
| `bug_fix_pr` | 2 | Bug fix pull request descriptions |

### 3.4 File Formats

| Format | Count | Occupations |
|---|---|---|
| `.docx` | 43 | Lawyer, Financial Analyst |
| `.md` | 38 | Software Engineer, some Financial Analyst |
| `.pdf` | 3 | Financial Analyst (investment memos) |

### 3.5 Difficulty Distribution

| Band | Count | % |
|---|---|---|
| Medium | 48 | 57% |
| Hard | 19 | 23% |
| Light | 17 | 20% |

Difficulty is assigned at seed-selection time (see `pipeline/seeds/selector.py`) and reinforced by time-guidance in the LLM prompt:
- **Light** (1–3 hours): Straightforward seeds with limited scope.
- **Medium** (3–6 hours): Standard complexity — the bulk of professional work.
- **Hard** (6–10 hours): Appellate opinions, large-cap financials, or high-impact PRs with broad implications.

The 55%/25%/20% target distribution is a pipeline design choice, not derived from GDPval (the public GDPval release does not contain difficulty annotations).

### 3.6 Quality Metrics

| Metric | Median | Mean | Range |
|---|---|---|---|
| Prompt length (chars) | 2,526 | 2,519 | 1,492 – 4,111 |
| Rubric items | 48 | 47.3 | 35 – 57 |
| Expected values | 25 | 27.1 | 15 – 48 |
| Deliverable file size | ~40 KB | — | — |

---

## 4. Alignment with GDPval

We benchmark our synthetic tasks against the real GDPval reference corpus (220 tasks). Key alignment dimensions:

| Dimension | Our Pipeline | GDPval Target |
|---|---|---|
| Tasks per domain | 12–38 | 5 |
| Prompt length (median) | 2,526 chars | ~2,024 chars |
| Rubric granularity | 35–57 items | similar |
| Input attachment rate | ~91% | ~57% |
| Seed-grounded facts | 100% (all facts from real data) | 100% (expert-designed) |
| Deliverable formats | docx, xlsx, md, pdf | docx, xlsx, md, pdf |

---

## 5. Reproduction

### 5.1 Setup

```bash
# Install dependencies
uv sync

# Configure API keys (copy and fill in)
cp .env.example .env
# Edit .env to add:
#   MIMO_API_KEY=...
#   COURTLISTENER_API_TOKEN=...
```

### 5.2 Collect Seeds

```bash
# Lawyer seeds (CourtListener opinions)
uv run python -m pipeline.seeds.courtlistener

# Financial seeds (SEC EDGAR XBRL)
uv run python -m pipeline.seeds.edgar_xbrl

# Software Engineer seeds (GitHub PRs)
uv run python -m pipeline.seeds.github_issues
```

Seeds are cached in `pipeline/seeds/store/{occupation}/`.

### 5.3 Run the Pipeline

```bash
# Full batch: all 117 seeds, 4 workers, skip LLM consistency validation
uv run python -m pipeline.orchestrator -n 117 --workers 4 --skip-validation
```

Results:
- Accepted tasks: `data/accepted/{task_id}.json` + input attachments
- Deliverables: `data/deliverables/{task_id}/`

### 5.4 Inspect a Task

```bash
# View a task's prompt, rubric, and expected values
python scripts/inspect_task.py --task-id sc_xxx

# Open the rendered deliverable
open data/deliverables/sc_xxx/*.docx
```

---

## 6. Project Structure

```
pipeline/
  seeds/
    courtlistener.py      # Harvest legal opinions
    edgar_xbrl.py         # Harvest SEC financial data
    github_issues.py      # Harvest GitHub PRs
    store/                # Cached seed JSONs
  scenario/
    synthesis.py          # Unified generation (prompt + answer + rubric)
    reference_answer.py   # Blueprint models
  artifacts/
    renderer.py           # Deterministic rendering (docx/xlsx/md/pdf)
    input_renderer.py     # Input attachment rendering
  validators/
    hard_quality.py       # Deterministic quality checks
  diversity/
    grid.py               # Seed sampling grid
  orchestrator.py         # Main pipeline entry point

data/
  accepted/               # Accepted task JSONs + input attachments
  deliverables/           # Rendered deliverable files
  gdpval_reference/       # Real GDPval tasks for comparison
```

---

## 7. Key Design Decisions

1. **Answer-first design**: The reference answer blueprint is designed *synchronously* with the task prompt and rubric, not generated by having a model "solve" the task later. This guarantees consistency.

2. **No preset taxonomy**: We do not hard-code deliverable types. The LLM inspects the seed material and decides what type of task makes sense (e.g., a contract-interpretation opinion → `legal_memo`; a PR with new API → `design_doc`).

3. **Financial tasks are the hardest domain**: XBRL data contains both YTD cumulative and single-quarter values for the same period, which LLMs frequently confuse. We addressed this through three layers: (a) date-range annotations in seed text, (b) explicit system prompt instructions distinguishing YTD vs quarterly, and (c) LLM consistency validation with the same enriched context. Even so, financial tasks have a lower acceptance rate (~43%) due to rounding precision and calculation errors. The tasks include quantitative elements (margins, EPS, debt-to-equity) but not complex modeling (DCF, variance analysis).

4. **Per-occupation prompts**: A shared prompt caused cross-domain interference (e.g., a financial task mentioning "patent infringement"). We split into three independent system prompts, eliminating this issue.
