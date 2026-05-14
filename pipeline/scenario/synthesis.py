"""Unified generation: seed → complete TaskCandidate in ONE LLM call.

Core principle: the LLM reads the FULL seed material and designs the task,
answer, and rubric simultaneously. The prompt asks for what the answer provides;
the rubric checks what the answer contains. No template-filling, no free
invention.
"""

from __future__ import annotations

import logging
import random
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from pipeline.llm import LLMClient, default_client
from pipeline.scenario.canonical import (
    CanonicalScenario,
    DifficultyBand,
    Entity,
    FactValue,
    Occupation,
    SeedReference,
    TimelineEvent,
)
from pipeline.scenario.reference_answer import (
    CellBlueprint,
    DocHeaderBlueprint,
    ExpectedValue,
    InputAttachment,
    MdSectionBlueprint,
    ReferenceAnswer,
    SectionBlueprint,
    SheetBlueprint,
)
from pipeline.scenario.task_candidate import (
    DeliverableSpec,
    RubricItem,
    TaskCandidate,
)
from pipeline.seeds.base import Seed

logger = logging.getLogger(__name__)


# ─────────────────────────── Unified Output Schema ───────────────────────────


class UnifiedTask(BaseModel):
    """Structured output of the unified generation step."""

    deliverable_type: str = Field(
        description="Type of deliverable (e.g. motion_to_dismiss, credit_memo, bug_fix_pr). Determined from the seed content."
    )
    prompt: str = Field(
        description="Complete task description. Natural workplace voice. 1800-3000 chars."
    )
    attachments: list[str] = Field(
        default_factory=list,
        description="Descriptions of input attachments the candidate should receive.",
    )
    answer_format: Literal["docx", "pdf", "xlsx", "markdown"] = Field(
        description="Primary deliverable format"
    )

    # For docx/pdf deliverables
    docx_sections: list[SectionBlueprint] | None = None
    docx_header: DocHeaderBlueprint | None = None
    docx_title: str | None = None
    docx_signature: str | None = None

    # For markdown deliverables
    md_sections: list[MdSectionBlueprint] | None = None
    md_title: str | None = None

    # For xlsx deliverables
    xlsx_sheets: list[SheetBlueprint] | None = None

    # Universal: values that validators will check
    expected_values: list[ExpectedValue] = Field(default_factory=list)

    # Scoring criteria
    rubric: list[RubricItem] = Field(
        default_factory=list,
        description="45-55 atomic criteria. Each must be verifiable against the answer above.",
    )


# ─────────────────────────── Prompt Construction ───────────────────────────


_OCCUPATION_NAMES = {
    "lawyer": "lawyer",
    "financial_analyst": "investment banking analyst",
    "software_engineer": "software engineer",
}


_DIFFICULTY_BANDS = {
    "light": "1-3 hours",
    "medium": "3-6 hours",
    "hard": "6-10 hours",
}


_LAWYER_SYS = """You are a senior lawyer with 15+ years of experience designing professional legal assessment tasks.

You will receive a REAL court opinion, motion, or brief. Your job is to design ONE complete legal assessment task based on this material.

## Core Principle

**The task, answer, and rubric must ALL grow from the seed material.**
- Do NOT invent facts, names, numbers, or citations that are not in the material.
- Do NOT apply a template regardless of what the material says.
- Let the material determine what type of task makes sense.

## Step 1: Determine Deliverable Type

Read the legal material and decide what kind of professional deliverable it naturally supports:

- Case involving contract terms → contract_redline
- Case about employment law, jurisdiction, or procedural matters → motion_to_dismiss or legal_memo
- Case with expert testimony or depositions → deposition_outline
- Complex appellate decision with multiple issues → legal_memo

## Step 2: Design the Prompt

Write a detailed workplace task instruction (1800-3000 characters). Follow this structure closely:

1. **Role and context** (opening sentence): Start with "You are a..." — name the role (e.g., associate at a litigation firm, in-house counsel), the organization, and the immediate situation. Include 2-3 sentences of background: why this work matters, who requested it, and what is at stake.

2. **Materials provided**: List the attached documents by name and describe what they contain. Be specific (e.g., "the attached Apple v. NLRB opinion (143 F.4th 291)", "the motion to dismiss in Smith v. Jones").

3. **Task requirements**: Break the deliverable into concrete steps. Use numbered lists or bullet points. Include:
   - Specific legal analyses, arguments, or judgments required
   - Constraints (e.g., "do not exceed X pages", "cite at least three cases")
   - Formatting instructions (section headings, citation format, file names)
   - Any procedural rules or standards the candidate must follow

4. **Deliverable specification**: Clearly state the output format (Word document, PDF, or Markdown file) and any structural requirements (sections, headings, signature blocks).

Tone rules:
- Do NOT include deadlines, "ASAP", "urgent", or time pressure
- Do NOT use AI hedging ("Please ensure", "It is important that")
- Write as a real partner delegating work to a competent associate

## Step 3: Design the Answer

Generate the COMPLETE deliverable content with enough detail to support 45-55 rubric items.

**CRITICAL: Populate expected_values with every verifiable fact, name, and citation from your answer.**
- Each expected_value must contain: a description of what it checks, the exact value, and where it appears in the answer.
- Include case citations, party names, dates, statutory sections, judge names, and key holdings.
- Include specific quotes or paraphrases from the seed material.
- expected_values is NOT optional. Generate 10-25 items minimum.

**For docx/pdf:**
- Provide full paragraph text for each section (3-8 paragraphs per major section)
- Include specific facts, names, citations, and quotations from the seed
- Use professional legal tone; headings should mirror the rubric checks
- The document should be substantive enough that 20+ rubric items can check its content

**For markdown:**
- Provide full section text with specific references
- Include any quoted language if relevant (must match the actual opinion)
- Each section should contain enough specific claims to support multiple rubric items

## Step 4: Design the Rubric

Produce 45-55 atomic, verifiable scoring criteria.

**Score distribution** (match this closely):
- ~51% should be +1 point
- ~42% should be +2 points
- ~7% should be +3 or higher
- 0-2 penalty items (negative scores) for deal-breakers only

**Rubric style** (mimic professional assessment rubrics):
- Start with the deliverable noun: "The submitted [deliverable]..."
- Be precise and unambiguous: specify exact names, citations, section locations
- Include boundary conditions where relevant
- Each criterion must be independently verifiable by an evaluator reading only the answer
- Spread criteria across categories: format (20%), structure (25%), legal content (40%), citations/references (15%)

**Examples of good criteria:**
- [+2] The submitted document is a Word file titled exactly 'Legal Memo - Apple v. NLRB'.
- [+1] The memorandum header 'Re' line includes the correct citation: 143 F.4th 291.
- [+2] The motion argues that the court lacks personal jurisdiction under Rule 12(b)(2).
- [+1] The contract redline preserves the indemnification clause in Section 4.2.

Do NOT create criteria that check things not in your answer.
Do NOT merge multiple independent checks into one criterion.

## Output Format

Return a single valid JSON object matching the schema. All string values on single lines. Escape quotes with backslash. No markdown code fences.
"""


_FINANCIAL_SYS = """You are a senior investment banking analyst with 15+ years of experience designing professional financial assessment tasks.

You will receive a REAL company's 10-K or 10-Q filing data. Your job is to design ONE complete financial assessment task based on this material.

## Core Principle

**The task, answer, and rubric must ALL grow from the seed material.**
- Do NOT invent facts, names, numbers, or data points that are not in the material.
- Do NOT apply a template regardless of what the material says.
- Let the material determine what type of task makes sense.

## Step 1: Determine Deliverable Type

Read the financial material and decide what kind of professional deliverable it naturally supports:

- Company with debt/credit concerns, leverage issues, or covenant risks → credit_memo
- Company with growth potential, M&A activity, or expansion story → investment_memo
- Company facing industry disruption, competitive pressure, or regulatory changes → industry_analysis
- Company with complex capital structure or refinancing needs → credit_memo

## Step 2: Design the Prompt

Write a detailed workplace task instruction (1800-3000 characters). Follow this structure closely:

1. **Role and context** (opening sentence): Start with "You are a..." — name the role (e.g., credit analyst at a commercial bank, associate at a PE firm), the organization or team, and the immediate situation. Include 2-3 sentences of background: why this analysis matters, who requested it, and what decision it will inform.

2. **Materials provided**: List the attached documents / input files by name and describe what they contain. Be specific (e.g., "the Q1 FY2026 10-Q filing for Deere & Co", "the attached financial data package").

3. **Task requirements**: Break the deliverable into concrete steps. Use numbered lists or bullet points. Include:
   - Specific analyses, judgments, or recommendations required
   - Constraints (e.g., "focus on the last three fiscal years", "address both upside and downside scenarios")
   - Formatting instructions (section headings, page limits, file names)
   - Any analytical frameworks or benchmarks the candidate should apply

4. **Deliverable specification**: Clearly state the output format (Word document or PDF) and any structural requirements (sections, headings, executive summary).

Tone rules:
- Do NOT include deadlines, "ASAP", "urgent", or time pressure
- Do NOT use AI hedging ("Please ensure", "It is important that")
- Write as a real managing director delegating work to a competent analyst

## Step 3: Design the Answer

Generate the COMPLETE deliverable content with enough detail to support 45-55 rubric items.

**CRITICAL: Populate expected_values with every verifiable fact, metric, name, and data point from your answer.**
- Each expected_value must contain: a description of what it checks, the exact value, and where it appears in the answer.
- Include company names, ticker symbols, key financial metrics, business segment names, and cited data points.
- Include specific facts about the company's operations, competitive position, or risk factors.
- expected_values is NOT optional. Generate 10-25 items minimum.

**For docx/pdf:**
- Provide full paragraph text for each section (3-8 paragraphs per major section)
- Include specific facts, metrics, and data points from the seed
- Use professional investment banking tone; headings should mirror the rubric checks
- The document should be substantive enough that 20+ rubric items can check its content

## Step 4: Design the Rubric

Produce 45-55 atomic, verifiable scoring criteria.

**Score distribution** (match this closely):
- ~51% should be +1 point
- ~42% should be +2 points
- ~7% should be +3 or higher
- 0-2 penalty items (negative scores) for deal-breakers only

**Rubric style** (mimic professional assessment rubrics):
- Start with the deliverable noun: "The submitted [deliverable]..."
- Be precise and unambiguous: specify exact names, metrics, section locations
- Include boundary conditions where relevant
- Each criterion must be independently verifiable by an evaluator reading only the answer
- Spread criteria across categories: format (20%), structure (25%), analytical content (40%), data/references (15%)

**Examples of good criteria:**
- [+2] The submitted document is a PDF file titled exactly 'Credit Memo - Exxon Mobil Corporation'.
- [+1] The executive summary identifies the borrower's primary revenue concentration risk.
- [+2] The industry analysis discusses the impact of regulatory changes on competitive dynamics in Section 3.
- [+1] The investment memo cites the company's Q1 FY2026 revenue of $83.1 billion.

Do NOT create criteria that check things not in your answer.
Do NOT merge multiple independent checks into one criterion.

## Output Format

Return a single valid JSON object matching the schema. All string values on single lines. Escape quotes with backslash. No markdown code fences.
"""


_SWE_SYS = """You are a senior software engineer with 15+ years of experience designing professional engineering assessment tasks.

You will receive a REAL pull request diff and description. Your job is to design ONE complete engineering assessment task based on this material.

## Core Principle

**The task, answer, and rubric must ALL grow from the seed material.**
- Do NOT invent facts, file names, function names, or issue numbers that are not in the material.
- Do NOT apply a template regardless of what the material says.
- Let the material determine what type of task makes sense.

## Step 1: Determine Deliverable Type

Read the PR material and decide what kind of professional deliverable it naturally supports:

- Bug fix PR with root cause and patch → bug_fix_pr
- New feature, API change, or architectural addition → design_doc
- Large refactor with significant code movement → code_review
- Post-incident remediation or follow-up → incident_postmortem

## Step 2: Design the Prompt

Write a detailed workplace task instruction (1800-3000 characters). Follow this structure closely:

1. **Role and context** (opening sentence): Start with "You are a..." — name the role (e.g., senior engineer at a tech company, staff engineer on the platform team), the organization or team, and the immediate situation. Include 2-3 sentences of background: why this work matters, who requested it, and what is at stake.

2. **Materials provided**: List the attached documents / input files by name and describe what they contain. Be specific (e.g., "PR #132833 diff and stabilization report", "the attached RFC for the new caching layer").

3. **Task requirements**: Break the deliverable into concrete steps. Use numbered lists or bullet points. Include:
   - Specific technical analyses, designs, or judgments required
   - Constraints (e.g., "must be backward compatible", "within X lines of code")
   - Formatting instructions (section headings, code block conventions, file names)
   - Any standards, patterns, or frameworks the candidate must follow

4. **Deliverable specification**: Clearly state the output format (Markdown file, Word document, or text file) and any structural requirements (sections, code blocks, naming conventions).

Tone rules:
- Do NOT include deadlines, "ASAP", "urgent", or time pressure
- Do NOT use AI hedging ("Please ensure", "It is important that")
- Write as a real tech lead delegating work to a competent engineer

## Step 3: Design the Answer

Generate the COMPLETE deliverable content with enough detail to support 45-55 rubric items.

**CRITICAL: Populate expected_values with every verifiable fact, number, name, and reference from your answer.**
- Each expected_value must contain: a description of what it checks, the exact value, and where it appears in the answer.
- Include PR numbers, issue numbers, file names, function names, class names, and any specific values referenced.
- Include specific code references or architectural decisions mentioned in the seed.
- expected_values is NOT optional. Generate 10-25 items minimum.

**For markdown:**
- Provide full section text with specific references
- Include code snippets if relevant (must match the actual diff)
- Use technical but accessible tone; headings should mirror the rubric checks
- Each section should contain enough specific claims to support multiple rubric items

**For docx/pdf:**
- Provide full paragraph text for each section (3-8 paragraphs per major section)
- Include specific facts, names, and references from the seed
- Use professional tone; headings should mirror the rubric checks

## Step 4: Design the Rubric

Produce 45-55 atomic, verifiable scoring criteria.

**Score distribution** (match this closely):
- ~51% should be +1 point
- ~42% should be +2 points
- ~7% should be +3 or higher
- 0-2 penalty items (negative scores) for deal-breakers only

**Rubric style** (mimic professional assessment rubrics):
- Start with the deliverable noun: "The submitted [deliverable]..."
- Be precise and unambiguous: specify exact names, file paths, section locations
- Include boundary conditions where relevant
- Each criterion must be independently verifiable by an evaluator reading only the answer
- Spread criteria across categories: format (20%), structure (25%), technical content (40%), references (15%)

**Examples of good criteria:**
- [+2] The submitted document is a Markdown file titled exactly 'Design Doc - Distributed Cache v2'.
- [+1] The design document references RFC 2497 in the Overview section.
- [+2] The code review identifies the race condition in `src/scheduler.py` line 142.
- [+1] The incident postmortem links to issue #4427 in the Root Cause section.

Do NOT create criteria that check things not in your answer.
Do NOT merge multiple independent checks into one criterion.

## Output Format

Return a single valid JSON object matching the schema. All string values on single lines. Escape quotes with backslash. No markdown code fences.
"""


_OCCUPATION_SYS = {
    "lawyer": _LAWYER_SYS,
    "financial_analyst": _FINANCIAL_SYS,
    "software_engineer": _SWE_SYS,
}


def _build_seed_text(seed: Seed) -> str:
    """Render the full seed material as text for the LLM."""
    p = seed.payload
    lines = [f"# Seed Material: {seed.title}", f"Source: {seed.source}", f"Identifier: {seed.identifier}", ""]

    if seed.source == "courtlistener":
        lines.extend([
            f"Case Name: {p.get('case_name', 'N/A')}",
            f"Citation: {p.get('citation', 'N/A')}",
            f"Court: {p.get('court', 'N/A')}",
            f"Date Filed: {p.get('date_filed', 'N/A')}",
            f"Judges: {p.get('judges', 'N/A')}",
            "",
            "## Opinion Text",
            seed.text_excerpt or "(no excerpt)",
        ])

    elif seed.source == "sec_edgar_xbrl":
        lines.extend([
            f"Company: {p.get('entity_name', 'N/A')}",
            f"Ticker: {p.get('ticker', 'N/A')}",
            f"CIK: {p.get('cik', 'N/A')}",
            f"Sector: {p.get('sector', 'N/A')}",
            "",
            "## Financial Data (XBRL)",
        ])
        key_facts = p.get("key_facts", {})
        for concept, observations in key_facts.items():
            lines.append(f"\n### {concept}")
            for obs in observations[:5]:  # Last 5 periods
                val = obs.get("val")
                if val is not None:
                    # Preserve precision for small values (EPS, ratios) while formatting large ones
                    if abs(val) < 1000 or val != int(val):
                        lines.append(f"  {obs.get('fp', '')} {obs.get('fy', '')}: {val}")
                    else:
                        lines.append(f"  {obs.get('fp', '')} {obs.get('fy', '')}: {val:,.0f}")
        lines.extend([
            "",
            "## Recent Filings",
        ])
        for f in p.get("recent_filings", [])[:5]:
            lines.append(f"  {f.get('form')} — {f.get('date')}")

    elif seed.source == "github_issue_pr":
        lines.extend([
            f"Repository: {p.get('repo', 'N/A')}",
            f"PR Number: #{p.get('pr_number', 'N/A')}",
            f"PR Title: {p.get('pr_title', 'N/A')}",
            f"Merged At: {p.get('merged_at', 'N/A')}",
            f"Changed Files: {p.get('changed_files', 'N/A')}",
            f"Additions: +{p.get('additions', 0)}, Deletions: -{p.get('deletions', 0)}",
            "",
            "## PR Description",
            p.get("pr_body", "(no description)")[:4000],
        ])
        if p.get("linked_issue"):
            lines.extend([
                "",
                f"## Linked Issue #{p.get('linked_issue')}",
                p.get("issue_body", "(no issue body)")[:2000],
            ])
        diff = p.get("diff", "")
        if diff:
            lines.extend([
                "",
                "## Diff (first 6000 chars)",
                diff[:6000],
            ])

    return "\n".join(lines)


def _build_user_prompt(seed: Seed, occupation: str, difficulty: str) -> str:
    """Build the user prompt containing the seed material."""
    seed_text = _build_seed_text(seed)
    return (
        f"## Material\n\n{seed_text}\n\n"
        f"## Instructions\n\n"
        f"Based on the {occupation} material above, design a complete assessment task.\n"
        f"Difficulty: {difficulty} (expected expert time: {_DIFFICULTY_BANDS.get(difficulty, '3-6 hours')})\n\n"
        f"Remember:\n"
        f"- ALL facts in the answer must come from the material above\n"
        f"- The rubric must check things that are actually in your answer\n"
        f"- Do not invent names, numbers, or citations not in the material\n"
    )


# ─────────────────────────── Canonical Builder ───────────────────────────


def _build_canonical(
    seed: Seed,
    unified: UnifiedTask,
    occupation: str,
    difficulty: str,
    rng: random.Random,
) -> CanonicalScenario:
    """Build a minimal CanonicalScenario from the unified output."""
    scenario_id = f"sc_{seed.seed_id[:16]}"

    # Extract entities from expected_values
    entities: list[Entity] = []
    seen_names = set()
    for ev in unified.expected_values:
        name = str(ev.value)
        if name and name not in seen_names and len(name) > 2:
            seen_names.add(name)
            entities.append(Entity(
                id=f"ev_{len(entities)}",
                kind="company" if "company" in ev.description.lower() else "person",
                name=name,
            ))

    # Extract facts from expected_values
    facts: list[FactValue] = []
    for ev in unified.expected_values:
        facts.append(FactValue(
            id=f"fact_{len(facts)}",
            kind="string" if isinstance(ev.value, str) else "money" if isinstance(ev.value, (int, float)) else "string",
            value=ev.value,
        ))

    # Build reference_answer from unified output
    ref = ReferenceAnswer(
        format=unified.answer_format,
        sections=unified.docx_sections,
        doc_header=unified.docx_header,
        title=unified.docx_title,
        signature_block=unified.docx_signature,
        md_sections=unified.md_sections,
        md_title=unified.md_title,
        sheets=unified.xlsx_sheets,
        expected_values=unified.expected_values,
        input_attachments=[InputAttachment(
            attachment_id=f"att_{i}",
            filename=f"input_{i}.md",
            format="md",  # type: ignore[arg-type]
            description=desc,
            content_blueprint={"title": desc.split(".")[0], "body": _build_seed_text(seed)},
        ) for i, desc in enumerate(unified.attachments)],
    )

    return CanonicalScenario(
        scenario_id=scenario_id,
        occupation=Occupation(occupation),
        deliverable_id=unified.deliverable_type,
        archetype=unified.deliverable_type,
        difficulty=DifficultyBand(difficulty),
        seed=SeedReference(
            source={"github_issue_pr": "github"}.get(seed.source, seed.source),  # type: ignore[arg-type]
            identifier=seed.identifier,
        ),
        entities=entities,
        timeline=[],
        facts=facts,
        explicit_requirements=[],
        implicit_requirements=[],
        reference_answer=ref,
        seed_rng=rng.randint(0, 2**31 - 1),
    )


# ─────────────────────────── Public API ───────────────────────────


def unified_generate(
    seed: Seed,
    occupation: str,
    difficulty: str = "medium",
    client: LLMClient | None = None,
) -> TaskCandidate:
    """Generate a complete task from a seed in ONE LLM call.

    The LLM reads the full seed material and outputs:
      - deliverable type (determined by content)
      - prompt (task description)
      - answer (complete deliverable content)
      - rubric (scoring criteria grounded in the answer)
    """
    client = client or default_client()
    rng = random.Random(seed.seed_id)

    sys_prompt = _OCCUPATION_SYS.get(
        occupation, _SWE_SYS
    ).format(
        occupation_name=_OCCUPATION_NAMES.get(occupation, occupation),
    )
    user_prompt = _build_user_prompt(seed, occupation, difficulty)

    logger.info("unified generation for seed %s (%s)", seed.seed_id, seed.source)

    unified = client.chat_structured(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        UnifiedTask,
        temperature=0.5,
        max_tokens=16000,
    )

    logger.info(
        "  unified output: %s, format=%s, sections=%s, rubric=%d items",
        unified.deliverable_type,
        unified.answer_format,
        len(unified.docx_sections or unified.md_sections or unified.xlsx_sheets or []),
        len(unified.rubric),
    )

    canonical = _build_canonical(seed, unified, occupation, difficulty, rng)

    input_specs = []
    if canonical.reference_answer and canonical.reference_answer.input_attachments:
        input_specs = [att.model_dump() for att in canonical.reference_answer.input_attachments]

    return TaskCandidate(
        candidate_id=canonical.scenario_id,
        occupation=occupation,
        archetype=unified.deliverable_type,
        difficulty=difficulty,
        seed_id=seed.seed_id,
        prompt=unified.prompt,
        deliverable=DeliverableSpec(
            deliverable_id=unified.deliverable_type,
            primary_format=unified.answer_format,
        ),
        rubric=unified.rubric,
        canonical=canonical,
        input_attachment_specs=input_specs,
        generator_model=client.default_model,
        rubric_model=client.default_model,
    )


# Backward-compatible wrapper
synthesize_task = unified_generate
