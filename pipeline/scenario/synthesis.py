"""LLM-driven synthesis: canonical scenario → TaskCandidate.

Three structured stages (separate LLM calls, all reading the same frozen
canonical state):

  1. Enrichment        — produce explicit/implicit requirements + scenario backstory
  2. Prompt Writer     — render workplace task instruction in occupational voice
  3. Rubric Generator  — produce 30-60 atomic [+N points] machine-checkable criteria

Why three stages, not one mega-prompt:
  - Each stage has a focused responsibility, easier to debug failures.
  - Different stages can use different models if we want cross-family review.
  - Structured intermediates (Enrichment JSON) make the canonical → prompt
    relationship inspectable; users can see WHY the prompt says what it does.

All LLM stages receive `canonical.context_for_agent()` as a read-only block
and are instructed never to invent facts beyond what is pinned there.
"""

from __future__ import annotations

import logging
import random
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from pipeline.config import TAXONOMY_PATH, settings
from pipeline.llm import LLMClient, default_client
from pipeline.scenario.canonical import CanonicalScenario, DifficultyBand
from pipeline.scenario.task_candidate import (
    DeliverableSpec,
    RubricItem,
    TaskCandidate,
)
from pipeline.seeds.base import Seed

logger = logging.getLogger(__name__)


# ─────────────────────────── Stage 1: Enrichment ───────────────────────────


class Enrichment(BaseModel):
    """Structured output of the enrichment stage."""

    scenario_backstory: str = Field(
        description="2-4 sentences setting the workplace situation. Draws on canonical entities and timeline. Does NOT invent new facts."
    )
    explicit_requirements: list[str] = Field(
        description="6-12 requirements the boss states clearly. Each is a single concrete deliverable expectation."
    )
    implicit_requirements: list[str] = Field(
        description="3-8 requirements the boss assumes the analyst/lawyer/engineer already knows (industry conventions, formats, compliance norms)."
    )
    hidden_constraints: list[str] = Field(
        description="2-5 non-obvious constraints (deadline pressure, format peculiarity, audience-specific nuances)."
    )
    primary_deliverable_format: Literal[
        "docx", "pdf", "xlsx", "pptx", "repo_tarball", "markdown", "docx+pdf", "xlsx+pptx"
    ]


_ENRICH_SYS_TMPL = """You are an expert {occupation_title} with {years} years of experience designing realistic professional tasks. You will receive a canonical scenario state with PINNED facts (real public data from {seed_source}). Your job is to enrich the scenario with structured workplace context.

Hard rules:
- NEVER invent new facts (no new dates, names, dollar amounts, citations, ticker symbols).
- ONLY reference entities/facts/timeline events by their canonical ids.
- Requirements and constraints must be concrete enough to be testable in a rubric.
- Voice: how a busy senior {occupation_title} would brief a junior teammate — tight, assumes domain literacy, leaves some details to be inferred (real workplace ambiguity).
- Calibrate scope to the difficulty band: {difficulty} → expected expert hours: {expected_hours}.
- The deliverable format must match the deliverable_id: {deliverable_id} ({archetype}).

Common mistakes to avoid:
- Don't write requirements like "ensure quality" or "be thorough" — these aren't testable.
- Don't restate canonical facts as requirements; requirements describe what the deliverable must DO.
- Don't include AI-typical phrasing ("Please ensure", "Make sure to", "It is important that").
- Implicit requirements are about industry conventions, NOT obvious things like "use English".
"""


_OCCUPATION_TITLES = {
    "lawyer": "lawyer",
    "financial_analyst": "investment banking analyst",
    "software_engineer": "software engineer",
}

_OCCUPATION_YEARS = {
    "lawyer": 14,
    "financial_analyst": 12,
    "software_engineer": 11,
}

_DIFFICULTY_HOURS = {
    DifficultyBand.LIGHT: "1-3 hours",
    DifficultyBand.MEDIUM: "3-6 hours",
    DifficultyBand.HARD: "6-10 hours",
}


def _occupation_seed_source(canonical: CanonicalScenario) -> str:
    return {
        "courtlistener": "CourtListener (real federal/circuit court opinion)",
        "sec_edgar_xbrl": "SEC EDGAR XBRL (real public-company filings)",
        "github": "real merged GitHub PR + issue thread",
    }.get(canonical.seed.source, canonical.seed.source)


def enrich(canonical: CanonicalScenario, client: LLMClient | None = None) -> Enrichment:
    client = client or default_client()
    sys_prompt = _ENRICH_SYS_TMPL.format(
        occupation_title=_OCCUPATION_TITLES[canonical.occupation.value],
        years=_OCCUPATION_YEARS[canonical.occupation.value],
        difficulty=canonical.difficulty.value,
        expected_hours=_DIFFICULTY_HOURS[canonical.difficulty],
        deliverable_id=canonical.deliverable_id,
        archetype=canonical.archetype,
        seed_source=_occupation_seed_source(canonical),
    )
    user_prompt = (
        canonical.context_for_agent()
        + "\n\nGenerate the enrichment for the deliverable above. "
        "Return a SINGLE valid JSON object. All string values must be on a single line (no newlines inside strings). "
        "Escape any quotes inside strings with backslash. Do NOT include markdown code fences."
    )
    return client.chat_structured(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        Enrichment,
        temperature=0.7,
    )


# ─────────────────────────── Stage 2: Prompt Writer ───────────────────────────


_PROMPT_WRITER_SYS = """You write workplace task instructions in the natural voice of the field. The instruction will be given to a model that must produce a real professional deliverable (8+ pages, full spreadsheet model, working code, etc.) — so the instruction must be specific and grounded.

You will receive: a CANONICAL state (entities, dates, facts, citations — all real and pinned), an ENRICHMENT (backstory, explicit/implicit reqs, hidden constraints), and a DELIVERABLE BLUEPRINT describing the expected structure of the answer.

Hard rules:
- Reference canonical facts by their actual values (e.g., "based on $REVENUE_VALUE in Q3 revenue").
- The instruction must read like one a senior {occupation_title} actually wrote — direct, mildly assumes context.
- DO NOT use AI hedging ("Please ensure", "It is important to note", "Make sure that you").
- DO NOT restate the rubric. The rubric is for grading; the instruction is the brief.
- DO NOT reveal the answer blueprint to the candidate. The blueprint is for YOU to understand what structure to ask for, not to give away.
- Length target: {min_chars}-{max_chars} characters (real GDPval median is ~2,000 chars).
- NEVER mention deadlines, due dates, time pressure, or urgency in the prompt. Real GDPval tasks almost never include deadlines (only ~3% do). Do NOT write phrases like "by Friday", "due by", "end of day", "ASAP", "urgent", "time-sensitive", or "deadline".
- Avoid numbered lists for requirements (only ~17% of real GDPval tasks use them). Use flowing paragraphs or brief bullet points (~36% use bullets).
- When input attachments exist, reference them naturally in the prompt body: "see the attached spreadsheet", "using the provided contract draft", "review the excerpt below".
- FIRST SENTENCE MUST be a 'You are a...' role framing. This is mandatory — 78% of real GDPval tasks start this way. Example: "You are a junior associate at Hartwell & Mosby LLP." The very first words of the prompt must be "You are a". Keep the role frame to 1-2 sentences max.
- Then set the situational context (what the task is about, who the client/stakeholder is, what triggered the work).
- Close with the deliverable specification and any format requirements.
- Embed all explicit_requirements; weave implicit ones in implicitly (don't enumerate them).
- It is OK to leave one or two minor things ambiguous if a real boss would (real workplace ambiguity).
- For SWE tasks: file paths must be the actual paths shown in the canonical diff (e.g. "pandas/core/reshape/merge.py"), NOT prefixed with the repo slug.
- Don't fabricate repository conventions: only mention deliverable locations (e.g. `docs/design/`) if you have actual evidence they exist; otherwise say "the document" without a path.
- NEVER invent specific line numbers, line ranges, section IDs, or specific exhibit numbers that aren't pinned in canonical facts. Use general references ("the affected method", "the relevant section") instead.
- For financial tasks: financial figures must be referenced from a SINGLE consistent period. Do NOT mix Q3 2024 revenue with Q1 2025 operating income as if they were comparable. Income statement structure: Revenue → COGS → Gross Profit → Opex (SG&A, R&D) → Operating Income → Net Income (NOT vice versa).
- Watch the timeline: if the canonical reference event (PR merged, opinion filed) is more than 2 years before the assignment date, frame it as historical context, not "recent" or "newly merged".
- For lawyer tasks: the precedent in canonical facts is the ONLY case you may rely on, and it covers ONLY the legal proposition it actually stands for. If the canonical case is a Federal Circuit patent decision and the archetype is "breach_of_contract", DO NOT pretend the patent decision controls contract law — instead, recast the scenario so the deliverable is about the case's actual subject matter (IP / patent issues), or downgrade the archetype to align. NEVER cite a case for a proposition it does not actually hold.

Calibration examples — what real GDPval Lawyer prompts look like:
  "You work at a new estate planning law firm in Texas. It is April 2023, and your supervising attorney has asked you to draft the first formal and comprehensive Last Will and Testament for a client residing in Austin, Texas..."

Real Financial Analyst:
  "It is April 11, 2025 and you are an Investment Banking Analyst in the Equity Capital Markets group..."

Match this voice and concreteness.
"""


_LENGTH_BANDS = {
    DifficultyBand.LIGHT: (1000, 1600),
    DifficultyBand.MEDIUM: (1400, 2200),
    DifficultyBand.HARD: (1800, 2800),
}


def _attachment_hint(canonical: CanonicalScenario) -> str:
    """Generate a hint about input attachments for the prompt writer."""
    bp = canonical.reference_answer
    if not bp or not bp.input_attachments:
        return ""
    lines = ["\n## Input Attachments (reference naturally in the prompt)\n"]
    for att in bp.input_attachments:
        lines.append(f"- {att.filename} ({att.format}): {att.description}")
    lines.append("\nReference these attachments naturally in the prompt body — do NOT list them as a separate section.")
    return "\n".join(lines)


def _blueprint_hint(canonical: CanonicalScenario) -> str:
    """Generate a hint about deliverable structure for the prompt writer."""
    bp = canonical.reference_answer
    if not bp:
        return ""
    lines = ["\n## Deliverable Blueprint (for YOUR reference only — DO NOT reveal to candidate)\n"]
    if bp.format == "xlsx" and bp.sheets:
        lines.append(f"Format: Excel workbook with {len(bp.sheets)} sheets:")
        for s in bp.sheets:
            lines.append(f"  - {s.name}")
        lines.append("The candidate must build this structure with live formulas.")
    elif bp.format == "docx" and bp.sections:
        lines.append(f"Format: Word document with {len(bp.sections)} sections:")
        for s in bp.sections:
            lines.append(f"  - {s.heading}: must cover {len(s.required_content)} key points")
        lines.append("The candidate must produce a professionally formatted document.")
    elif bp.format == "markdown" and bp.md_sections:
        lines.append(f"Format: Markdown document with {len(bp.md_sections)} sections:")
        for s in bp.md_sections:
            lines.append(f"  - {s.heading}")
    return "\n".join(lines)


def write_prompt(
    canonical: CanonicalScenario,
    enrichment: Enrichment,
    client: LLMClient | None = None,
) -> str:
    client = client or default_client()
    min_c, max_c = _LENGTH_BANDS[canonical.difficulty]
    sys_prompt = _PROMPT_WRITER_SYS.format(
        occupation_title=_OCCUPATION_TITLES[canonical.occupation.value],
        min_chars=min_c,
        max_chars=max_c,
    )
    user_prompt = (
        canonical.context_for_agent()
        + "\n\n## Enrichment\n"
        + enrichment.model_dump_json(indent=2)
        + _attachment_hint(canonical)
        + _blueprint_hint(canonical)
        + f"\n\nWrite the workplace task instruction now. Target {min_c}-{max_c} chars. "
        "Output the instruction text only — no preamble, no JSON, no quotes around it."
    )
    content, _ = client.chat(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=3000,
    )
    return content.strip()


# ─────────────────────────── Stage 3: Rubric Generator ───────────────────────────


class GeneratedRubric(BaseModel):
    items: list[RubricItem] = Field(
        description="45-55 atomic, machine-checkable criteria. Calibrated to real GDPval: median 47 items, mostly +1/+2 points, total 60-90."
    )


_RUBRIC_SYS = """You generate machine-checkable evaluation rubrics for professional deliverables in the exact GDPval style.

Real GDPval statistics (calibrated against 220 public tasks):
  - Median items per rubric: 47
  - Point distribution: 52% are +1, 42% are +2, ~6% are +3 or higher, 0.9% are penalties
  - Median total points: ~70
  - Most common category keywords: format (511 occurrences), reference (399), data (310), style (179), content (139)
  - 73% of tasks have at least one item requiring exact match of a named entity/number

Rubric format reference (real GDPval items):
  [+1] The Will identifies the testator by the full legal name Grace J. Parsons.
  [+2] The Will is at least 7 but no more than 12 pages in length.
  [+1] Provides deliverable as a single PDF file.
  [+2] Includes all unique individual companies that is part of the S&P 500 as of April 11, 2025
  [-1] The document uses Comic Sans or other unprofessional font. (penalty example)

CRITICAL — these are mistakes a real expert reviewer would never make:

1. POINT BUDGET — match real GDPval STRICTLY:
   - Total items: 45-55 (real median is 47)
   - Total points: 60-90 (NOT higher; real median is ~70)
   - HARD MAX per item: 3 points. NEVER assign +4, +5, +6, +7, or +8 to any item.
   - Point distribution target: ~50% of items should be +1, ~40% should be +2, ~10% should be +3
   - Include 1-2 penalty items (score -1 or -2) for critical errors like wrong file format or missing confidentiality notice
   - If you find yourself writing +4 or higher, BREAK IT INTO multiple smaller +1/+2 items instead

2. CATEGORY DISTRIBUTION — match real GDPval emphasis (check your counts):
   format        — file type, page/slide count, naming (~20% of items, i.e., 9-11 items)
   reference     — citations, case names, statutory refs, data sources (~20%, i.e., 9-11 items)
   data          — specific numbers, calculations, financial figures (~15%, i.e., 7-8 items)
   style         — tone, formatting conventions, professional standards (~10%, i.e., 4-5 items)
   accuracy      — factual correctness of named entities/numbers (~15%, i.e., 7-8 items)
   content       — substantive coverage (~15%, i.e., 7-8 items)
   judgment      — qualitative reasoning (~5%, i.e., 2-3 items MAX)
   structure     — required sections, organization (bundled into format/content)
   completeness  — coverage of required topics (bundled into content)
   After generating the rubric, VERIFY the category counts are close to these targets.

3. EXACT-MATCH ITEMS (MANDATORY): In ~73% of real GDPval tasks, at least one rubric item requires an exact match of a named entity, number, or citation. You MUST include at least 4 exact-match items per rubric. These are NOT optional:
   - "[+1] The document identifies the testator as Grace J. Parsons"
   - "[+2] The DCF model uses a terminal growth rate of 2.3%"
   - "[+1] Correctly cites the precedent case as 139 F.4th 1340 (Fed. Cir. 2025)"
   - "[+1] The memo identifies the client as Atlas Holdings, Inc."
   These must reference SPECIFIC pinned facts from the canonical state. If you do not include at least 4 exact-match items, the rubric is INVALID.

4. DON'T over-weight trivial mechanical compliance. NO points for things like:
   - Mentioning a teammate's name (e.g. "+1 if mentions that Rin Sato left")
   - Specific font sizes / margins (irrelevant unless task explicitly demands)
   - Word/phrase compliance ("uses the word 'covenant' three times")
   These are gaming-the-rubric items, not quality evaluation.

5. Bundle related format checks. Real GDPval has format as a dominant category but items are bundled (e.g., one item covers page count + file type + professional formatting).

6. GROUNDING:
   - Reference SPECIFIC facts from the canonical state for accuracy/reference/data items.
   - For judgment items (minimal), use relative phrasing ("plausibly justifies", "identifies a credible trade-off").
"""


def _rubric_blueprint_hint(canonical: CanonicalScenario) -> str:
    """Generate blueprint information to ground rubric accuracy items."""
    bp = canonical.reference_answer
    if not bp:
        return ""
    lines = ["\n## Answer Blueprint (for rubric grounding)\n"]
    if bp.expected_values:
        lines.append("Expected values that accuracy items should check:")
        for ev in bp.expected_values:
            lines.append(f"  - {ev.description}: {ev.value} (location: {ev.location})")
    if bp.format == "xlsx" and bp.sheets:
        lines.append(f"\nWorkbook structure: {len(bp.sheets)} sheets")
        for s in bp.sheets:
            lines.append(f"  - Sheet '{s.name}': {len(s.cells)} cells")
    elif bp.format == "docx" and bp.sections:
        lines.append(f"\nDocument structure: {len(bp.sections)} sections")
        for s in bp.sections:
            lines.append(f"  - {s.heading}: must cover {', '.join(s.required_content[:3])}")
    elif bp.format == "markdown" and bp.md_sections:
        lines.append(f"\nMarkdown structure: {len(bp.md_sections)} sections")
        for s in bp.md_sections:
            lines.append(f"  - {s.heading}")
    return "\n".join(lines)


def generate_rubric(
    canonical: CanonicalScenario,
    enrichment: Enrichment,
    prompt: str,
    client: LLMClient | None = None,
    model: str | None = None,
) -> list[RubricItem]:
    client = client or default_client()
    user_prompt = (
        canonical.context_for_agent()
        + "\n\n## Enrichment\n"
        + enrichment.model_dump_json(indent=2)
        + "\n\n## Final Task Prompt\n"
        + prompt
        + f"\n\n## Deliverable format\n{enrichment.primary_deliverable_format}"
        + _rubric_blueprint_hint(canonical)
        + "\n\nGenerate the rubric now. Return a SINGLE valid JSON object. "
        "All string values must be on a single line (no newlines inside strings). "
        "Escape any quotes inside strings with backslash. Do NOT include markdown code fences."
    )
    rubric = client.chat_structured(
        [
            {"role": "system", "content": _RUBRIC_SYS},
            {"role": "user", "content": user_prompt},
        ],
        GeneratedRubric,
        temperature=0.5,
        max_tokens=4096,
        model=model,
    )
    return rubric.items


# ─────────────────────────── End-to-end ───────────────────────────


def _generate_narrative(
    canonical: CanonicalScenario,
    enrichment: Enrichment,
    client: LLMClient | None = None,
) -> CanonicalScenario:
    """Generate paragraph text for docx/md blueprints and update canonical."""
    bp = canonical.reference_answer
    if not bp or not bp.narrative_prompt:
        return canonical

    client = client or default_client()

    if bp.format in ("docx", "pdf") and bp.sections:
        # Generate paragraphs for each section (pdf uses same section blueprint as docx)
        updated_sections = []
        for section in bp.sections:
            sys_prompt = bp.narrative_prompt
            user_prompt = (
                f"Write the content for the '{section.heading}' section.\n\n"
                f"Required content to cover:\n"
                + "\n".join(f"- {r}" for r in section.required_content)
                + f"\n\nWrite 2-4 professional paragraphs. Total length: 200-600 words."
            )
            try:
                content, _ = client.chat(
                    [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.6,
                    max_tokens=2000,
                )
                paragraphs = [p.strip() for p in content.strip().split("\n\n") if p.strip()]
            except Exception as e:
                logger.warning("narrative generation failed for section %s: %s", section.heading, e)
                paragraphs = [f"[{section.heading} content placeholder]"]

            from pipeline.scenario.reference_answer import SectionBlueprint
            updated_sections.append(
                SectionBlueprint(
                    heading=section.heading,
                    heading_level=section.heading_level,
                    required_content=section.required_content,
                    paragraphs=paragraphs,
                )
            )

        from pipeline.scenario.reference_answer import ReferenceAnswer
        new_bp = ReferenceAnswer(
            format=bp.format,
            sections=updated_sections,
            doc_header=bp.doc_header,
            title=bp.title,
            signature_block=bp.signature_block,
            page_settings=bp.page_settings,
            expected_values=bp.expected_values,
            narrative_prompt=bp.narrative_prompt,
            input_attachments=bp.input_attachments,
        )
        canonical = canonical.model_copy(update={"reference_answer": new_bp})

    elif bp.format == "markdown" and bp.md_sections:
        # Generate paragraphs for each md section
        updated_sections = []
        for section in bp.md_sections:
            sys_prompt = bp.narrative_prompt
            user_prompt = (
                f"Write the content for the '{section.heading}' section.\n\n"
                f"Required content to cover:\n"
                + "\n".join(f"- {r}" for r in section.required_content)
                + f"\n\nWrite 1-3 clear paragraphs. Total length: 150-400 words."
            )
            try:
                content, _ = client.chat(
                    [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.6,
                    max_tokens=1500,
                )
                paragraphs = [p.strip() for p in content.strip().split("\n\n") if p.strip()]
            except Exception as e:
                logger.warning("narrative generation failed for section %s: %s", section.heading, e)
                paragraphs = [f"[{section.heading} content placeholder]"]

            from pipeline.scenario.reference_answer import MdSectionBlueprint
            updated_sections.append(
                MdSectionBlueprint(
                    heading=section.heading,
                    heading_level=section.heading_level,
                    required_content=section.required_content,
                    paragraphs=paragraphs,
                )
            )

        from pipeline.scenario.reference_answer import ReferenceAnswer
        new_bp = ReferenceAnswer(
            format=bp.format,
            md_sections=updated_sections,
            md_title=bp.md_title,
            expected_values=bp.expected_values,
            narrative_prompt=bp.narrative_prompt,
            input_attachments=bp.input_attachments,
        )
        canonical = canonical.model_copy(update={"reference_answer": new_bp})

    return canonical


def synthesize_task(
    seed: Seed,
    deliverable_id: str,
    archetype: str,
    difficulty: DifficultyBand,
    rng: random.Random | None = None,
    client: LLMClient | None = None,
) -> TaskCandidate:
    from pipeline.scenario.builders import build_canonical

    client = client or default_client()
    rng = rng or random.Random()

    canonical = build_canonical(seed, deliverable_id, archetype, difficulty, rng)
    logger.info("synthesized canonical %s for %s", canonical.scenario_id, seed.seed_id)

    enrichment = enrich(canonical, client=client)
    logger.info("  enrichment: %d explicit, %d implicit, %d hidden",
                len(enrichment.explicit_requirements),
                len(enrichment.implicit_requirements),
                len(enrichment.hidden_constraints))

    # Update canonical with the enriched requirements (canonical is the source of truth).
    canonical = canonical.model_copy(update={
        "explicit_requirements": enrichment.explicit_requirements,
        "implicit_requirements": enrichment.implicit_requirements,
    })

    # Generate narrative paragraphs for docx/md blueprints (B方案: synthesis阶段生成)
    canonical = _generate_narrative(canonical, enrichment, client=client)
    if canonical.reference_answer and canonical.reference_answer.format in ("docx", "markdown"):
        logger.info("  generated narrative paragraphs for %s sections",
                    len(canonical.reference_answer.sections or canonical.reference_answer.md_sections or []))

    prompt_text = write_prompt(canonical, enrichment, client=client)
    logger.info("  prompt: %d chars", len(prompt_text))

    rubric_items = generate_rubric(canonical, enrichment, prompt_text, client=client)
    logger.info("  rubric: %d items, %d total points",
                len(rubric_items),
                sum(r.score for r in rubric_items))

    deliverable = DeliverableSpec(
        deliverable_id=deliverable_id,
        primary_format=enrichment.primary_deliverable_format,
    )

    input_specs = []
    if canonical.reference_answer and canonical.reference_answer.input_attachments:
        input_specs = [att.model_dump() for att in canonical.reference_answer.input_attachments]

    return TaskCandidate(
        candidate_id=canonical.scenario_id,
        occupation=canonical.occupation.value,
        archetype=archetype,
        difficulty=difficulty.value,
        seed_id=seed.seed_id,
        prompt=prompt_text,
        deliverable=deliverable,
        rubric=rubric_items,
        canonical=canonical,
        input_attachment_specs=input_specs,
        generator_model=settings().generator_model,
        rubric_model=settings().generator_model,
    )


def load_taxonomy() -> dict:
    return yaml.safe_load(TAXONOMY_PATH.read_text())
