# GDPval Synthetic Task Generation Pipeline

> A seed-driven pipeline that generates professional assessment tasks indistinguishable from real [GDPval](https://openai.com/index/introducing-swe-bench-verified/) (OpenAI's 220-task benchmark across 44 occupations).
>
> **Current corpus: 97 accepted tasks** (lawyer: 34, financial analyst: 25, software engineer: 38) with real deliverables (.docx, .xlsx, .md, .pdf).

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

Tasks pass through deterministic checks before acceptance:

- Prompt length ≥ 1,300 chars
- Rubric items ≥ 35 and ≤ 80
- Expected values ≥ 3
- Score distribution not skewed (>85% on one score)
- Rubric items are specific and verifiable (not vague)
- Input attachments have real content (≥ 100 chars)

**Acceptance rate: ~95%** (111/117 in the full batch; 37/39 for the lawyer re-run with longer seeds).

---

## 3. Dataset Statistics

### 3.1 Overall Corpus

```
Total accepted tasks: 97
Total generated (incl. old versions): 147
Acceptance rate through quality gate: ~95%
```

### 3.2 By Occupation

| Occupation | Tasks | % of Corpus | GDPval Equivalent | GDPval Count |
|---|---|---|---|---|
| Software Engineer | 38 | 39% | Software Developers | 5 |
| Lawyer | 34 | 35% | Lawyers | 5 |
| Financial Analyst | 25 | 26% | Financial and Investment Analysts | 5 |

We generated **6–8x more tasks per domain** than the original GDPval benchmark, while maintaining comparable granularity and grounding.

### 3.3 Deliverable Types

| Type | Count | Description |
|---|---|---|
| `legal_memo` | 34 | Formal legal memoranda analyzing court opinions |
| `code_review` | 24 | Post-merge technical reviews of PRs |
| `investment_memo` | 13 | One-page investment overviews with financial metrics |
| `credit_memo` | 12 | Credit committee memos with leverage analysis |
| `design_doc` | 12 | Architecture/design documents for new features |
| `bug_fix_pr` | 2 | Bug fix pull request descriptions |

### 3.4 File Formats

| Format | Count | Occupations |
|---|---|---|
| `.docx` | 44 | Lawyer, Financial Analyst |
| `.md` | 38 | Software Engineer, some Financial Analyst |
| `.pdf` | 15 | Lawyer (rendered from docx via LibreOffice) |

### 3.5 Difficulty Distribution

| Band | Count | % |
|---|---|---|
| Medium | 54 | 56% |
| Hard | 22 | 23% |
| Light | 21 | 21% |

Calibrated to the real GDPval distribution (~55% medium).

### 3.6 Quality Metrics

| Metric | Median | Mean | Range |
|---|---|---|---|
| Prompt length (chars) | 2,572 | 2,599 | 1,492 – 4,465 |
| Rubric items | 47 | 46.9 | 35 – 57 |
| Expected values | 25 | 25.9 | 15 – 48 |
| Deliverable file size | ~40 KB | — | — |

---

## 4. Alignment with GDPval

We benchmark our synthetic tasks against the real GDPval reference corpus (220 tasks). Key alignment dimensions:

| Dimension | Our Pipeline | GDPval Target |
|---|---|---|
| Tasks per domain | 25–38 | 5 |
| Prompt length (median) | 2,572 chars | ~2,024 chars |
| Rubric granularity | 35–57 items | similar |
| Input attachment rate | ~60% | ~57% |
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
  old/                    # Superseded task versions
  gdpval_reference/       # Real GDPval tasks for comparison
```

---

## 7. Key Design Decisions

1. **Answer-first design**: The reference answer blueprint is designed *synchronously* with the task prompt and rubric, not generated by having a model "solve" the task later. This guarantees consistency.

2. **No preset taxonomy**: We do not hard-code deliverable types. The LLM inspects the seed material and decides what type of task makes sense (e.g., a contract-interpretation opinion → `legal_memo`; a PR with new API → `design_doc`).

3. **Financial tasks are qualitative**: After discovering that LLMs misremember XBRL numbers when asked to perform calculations, we switched financial tasks to qualitative analysis (credit memos, investment memos, industry analysis) rather than quantitative models (DCF, variance analysis).

4. **Per-occupation prompts**: A shared prompt caused cross-domain interference (e.g., a financial task mentioning "patent infringement"). We split into three independent system prompts, eliminating this issue.
