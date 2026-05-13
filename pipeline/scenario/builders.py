"""Per-occupation canonical builders.

Procedural — no LLM calls. Lifts entities, dates, citations, numbers from a
real seed into a `CanonicalScenario`. The downstream LLM enrichment step then
generates only the *narrative* around these pinned values; it never invents
new facts.

NEW: Each builder now also generates a `ReferenceAnswer` blueprint — a structured,
machine-renderable description of the correct deliverable. This ensures prompt,
rubric, and answer are all grounded in the same canonical facts.
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
from datetime import date, datetime, timedelta
from typing import Any

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
from pipeline.seeds.base import Seed


def _should_attach(rng: random.Random, occupation: str, deliverable_id: str) -> bool:
    """Probabilistically decide if a task should have input attachments.

    Rates calibrated to GDPval's ~57% overall attachment rate:
    - Financial: ~70% (tasks often operate on raw data)
    - Lawyer: ~15% (mostly contract redlines, deposition transcripts)
    - SWE: ~40% (PR diffs, code snippets, specs)
    """
    rates = {
        ("financial_analyst", "dcf_model"): 0.75,
        ("financial_analyst", "variance_analysis"): 0.80,
        ("financial_analyst", "credit_memo"): 0.65,
        ("financial_analyst", "investment_committee_deck"): 0.50,
        ("lawyer", "contract_redline"): 0.85,
        ("lawyer", "deposition_outline"): 0.40,
        ("lawyer", "motion_to_dismiss"): 0.25,
        ("lawyer", "legal_memo"): 0.10,
        ("software_engineer", "code_review"): 0.60,
        ("software_engineer", "design_doc"): 0.35,
        ("software_engineer", "bug_fix_pr"): 0.50,
        ("software_engineer", "incident_postmortem"): 0.30,
    }
    rate = rates.get((occupation, deliverable_id), 0.3)
    return rng.random() < rate


def _build_financial_attachments(
    ticker: str, entity_name: str, key_facts: dict, deliverable_id: str, rng: random.Random
) -> list[InputAttachment]:
    """Build input attachments for financial analyst tasks."""
    attachments = []
    if deliverable_id in ("dcf_model", "variance_analysis", "credit_memo"):
        # Raw historical financials as a simple data table
        years = ["FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]
        revenue = _get_fact(key_facts, "Revenues") or 1_000_000_000
        # Generate plausible historical series
        growth_rates = [rng.uniform(-0.05, 0.25) for _ in range(5)]
        hist_revenue = []
        rev = revenue / ((1 + sum(growth_rates) / 5) ** 2.5)  # Back-calc roughly
        for g in growth_rates:
            rev = rev * (1 + g)
            hist_revenue.append(rev)

        attachments.append(InputAttachment(
            attachment_id=f"raw_financials_{ticker}",
            filename=f"{ticker}_historical_financials.xlsx",
            format="xlsx",
            description=f"Five-year historical financial summary for {entity_name} ({ticker})",
            content_blueprint={
                "sheet_name": "Historical Financials",
                "columns": ["Metric", *years],
                "rows": [
                    ["Revenue ($M)", *[round(r / 1_000_000, 1) for r in hist_revenue]],
                    ["COGS ($M)", *[round(r * rng.uniform(0.50, 0.70) / 1_000_000, 1) for r in hist_revenue]],
                    ["Gross Profit ($M)", *[round(r * rng.uniform(0.30, 0.50) / 1_000_000, 1) for r in hist_revenue]],
                    ["Operating Income ($M)", *[round(r * rng.uniform(0.15, 0.35) / 1_000_000, 1) for r in hist_revenue]],
                    ["Net Income ($M)", *[round(r * rng.uniform(0.10, 0.25) / 1_000_000, 1) for r in hist_revenue]],
                    ["D\u0026A ($M)", *[round(r * rng.uniform(0.03, 0.08) / 1_000_000, 1) for r in hist_revenue]],
                    ["CapEx ($M)", *[round(r * rng.uniform(0.05, 0.15) / 1_000_000, 1) for r in hist_revenue]],
                    ["Shares Outstanding (M)", *[round(rng.uniform(20, 50), 1) for _ in years]],
                ],
            },
        ))
    return attachments


def _build_legal_attachments(
    case_name: str, deliverable_id: str, archetype: str, rng: random.Random
) -> list[InputAttachment]:
    """Build input attachments for lawyer tasks."""
    attachments = []
    if deliverable_id == "contract_redline":
        attachments.append(InputAttachment(
            attachment_id="original_contract",
            filename="original_agreement.docx",
            format="docx",
            description="The original SaaS Master Services Agreement draft for redlining",
            content_blueprint={
                "title": "MASTER SERVICES AGREEMENT",
                "parties": ["VendorCo, Inc.", "ClientCorp, LLC"],
                "clauses": [
                    {"name": "Term", "text": "Initial term of twelve (12) months, automatically renewing for successive one-year periods unless either party provides written notice of non-renewal at least sixty (60) days prior to the end of the then-current term."},
                    {"name": "Service Levels", "text": "VendorCo shall maintain 99.9% uptime measured monthly. Downtime exceeding four (4) hours in any calendar month shall entitle ClientCorp to a service credit equal to 5% of the monthly fee."},
                    {"name": "Liability", "text": "Each party's aggregate liability under this Agreement shall not exceed the total amount paid by ClientCorp to VendorCo in the twelve (12) months preceding the event giving rise to liability."},
                    {"name": "Data Security", "text": "VendorCo shall implement commercially reasonable administrative, physical, and technical safeguards to protect ClientCorp Data."},
                    {"name": "Indemnification", "text": "VendorCo shall indemnify, defend, and hold harmless ClientCorp from any third-party claim arising from VendorCo's breach of its data security obligations."},
                ],
            },
        ))
    elif deliverable_id == "deposition_outline":
        attachments.append(InputAttachment(
            attachment_id="transcript_excerpt",
            filename="witness_transcript_excerpt.pdf",
            format="pdf",
            description="Excerpt from the witness's prior deposition testimony",
            content_blueprint={
                "witness_name": "Dr. Patricia Okonkwo",
                "excerpt": "Q: And what methodology did you use to calculate the damages figure? A: I applied a discounted cash flow analysis using the projections provided by the plaintiff's counsel. Q: Did you independently verify those projections? A: No, I relied on the representations made by counsel.",
            },
        ))
    elif deliverable_id == "motion_to_dismiss":
        attachments.append(InputAttachment(
            attachment_id="complaint_excerpt",
            filename="complaint_excerpt.pdf",
            format="pdf",
            description="Relevant excerpt from the complaint and supporting exhibits",
            content_blueprint={
                "caption": f"IN THE UNITED STATES DISTRICT COURT FOR THE {rng.choice(['NORTHERN', 'SOUTHERN', 'EASTERN', 'WESTERN'])} DISTRICT OF {rng.choice(['TEXAS', 'CALIFORNIA', 'NEW YORK', 'FLORIDA'])}",
                "claims": ["Breach of Contract", "Negligent Misrepresentation", "Unjust Enrichment"],
                "relief_sought": "Damages in excess of $75,000, plus attorneys' fees and costs.",
            },
        ))
    return attachments


def _build_swe_attachments(
    repo: str, pr_num: int, diff: str, deliverable_id: str, rng: random.Random
) -> list[InputAttachment]:
    """Build input attachments for SWE tasks."""
    attachments = []
    if deliverable_id == "code_review":
        # Extract first ~30 lines of diff as an attachment
        diff_lines = diff.split("\n")[:50]
        attachments.append(InputAttachment(
            attachment_id="pr_diff",
            filename=f"pr_{pr_num}_diff.md",
            format="md",
            description=f"The diff for PR #{pr_num} from {repo}",
            content_blueprint={
                "repo": repo,
                "pr_num": pr_num,
                "diff_excerpt": "\n".join(diff_lines),
            },
        ))
    elif deliverable_id == "design_doc":
        attachments.append(InputAttachment(
            attachment_id="api_spec",
            filename="api_requirements.md",
            format="md",
            description="Internal API requirements and compatibility constraints",
            content_blueprint={
                "title": "API Compatibility Requirements",
                "requirements": [
                    "All public methods must maintain backward compatibility for at least two major versions.",
                    "New optional parameters must have sensible defaults.",
                    "Breaking changes require a deprecation cycle of at least one release.",
                ],
            },
        ))
    elif deliverable_id == "bug_fix_pr":
        attachments.append(InputAttachment(
            attachment_id="bug_report",
            filename="issue_description.md",
            format="md",
            description="The bug report and reproduction steps",
            content_blueprint={
                "title": f"Bug Report: Issue affecting {repo}",
                "repro_steps": [
                    "1. Install latest version from main branch",
                    "2. Run the reproduction script with the provided test case",
                    "3. Observe the error in the output",
                ],
                "expected_behavior": "The operation should complete without errors.",
                "actual_behavior": "A TypeError or unexpected exception is raised.",
            },
        ))
    return attachments

logger = logging.getLogger(__name__)


def _scenario_id(seed_id: str, deliverable_id: str, archetype: str, salt: int) -> str:
    h = hashlib.sha256(f"{seed_id}|{deliverable_id}|{archetype}|{salt}".encode()).hexdigest()
    return f"sc_{h[:16]}"


def _parse_iso_date(s: str | None) -> date:
    if not s:
        return date.today()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return date.today()


# ─────────────────────────── LAWYER ───────────────────────────

_FICTIONAL_LAW_FIRMS = [
    "Hartwell & Mosby LLP",
    "Caldera, Voss & Tanaka, P.C.",
    "Thornberg Reyes & Associates",
    "Granger | Penrose | Vidal LLP",
    "Wexford Strait & Akiyama LLP",
]
_FICTIONAL_PARTNERS = [
    "Sandra Pietersen", "Marcus Yeong", "Devika Ranganathan", "Alex Carbonneau",
    "Hye-Jin Park", "Tomás Aguilar", "Reema Soltani", "Quentin Brossard",
]


def _design_legal_blueprint(
    case_name: str,
    citation: str | None,
    court_code: str,
    date_filed: date,
    firm_name: str,
    partner_name: str,
    client_name: str,
    deliverable_id: str,
    archetype: str,
    difficulty: DifficultyBand,
    text_excerpt: str,
) -> ReferenceAnswer:
    """Design a legal document blueprint based on canonical facts."""

    assignment_date = date.today()
    sections: list[SectionBlueprint] = []

    if deliverable_id == "legal_memo":
        sections = [
            SectionBlueprint(
                heading="Question Presented",
                heading_level=1,
                required_content=[
                    "State the precise legal issue",
                    "Reference the precedent case",
                ],
            ),
            SectionBlueprint(
                heading="Brief Answer",
                heading_level=1,
                required_content=[
                    "Summary conclusion based on precedent",
                    f"Must cite {citation or case_name}",
                ],
            ),
            SectionBlueprint(
                heading="Facts",
                heading_level=1,
                required_content=[
                    f"Client: {client_name}",
                    f"Precedent: {case_name} ({court_code}, filed {date_filed.isoformat()})",
                ],
            ),
            SectionBlueprint(
                heading="Analysis",
                heading_level=1,
                required_content=[
                    "Apply precedent to client's facts",
                    "Discuss legal standard from the case",
                    "Address counterarguments",
                ],
            ),
            SectionBlueprint(
                heading="Conclusion",
                heading_level=1,
                required_content=["Clear recommendation"],
            ),
        ]
    elif deliverable_id in ("motion_to_dismiss", "contract_redline", "deposition_outline"):
        # Generic legal doc structure
        sections = [
            SectionBlueprint(
                heading="Introduction",
                heading_level=1,
                required_content=["Context and purpose of the document"],
            ),
            SectionBlueprint(
                heading="Background",
                heading_level=1,
                required_content=[
                    f"Reference to {case_name}",
                    f"Client: {client_name}",
                ],
            ),
            SectionBlueprint(
                heading="Analysis / Argument",
                heading_level=1,
                required_content=[
                    "Legal reasoning based on precedent",
                    f"Cite {citation or case_name}",
                ],
            ),
            SectionBlueprint(
                heading="Conclusion",
                heading_level=1,
                required_content=["Recommendation or request for relief"],
            ),
        ]

    fmt = "pdf" if deliverable_id in ("motion_to_dismiss", "deposition_outline", "legal_memo") else "docx"

    return ReferenceAnswer(
        format=fmt,
        sections=sections,
        doc_header=DocHeaderBlueprint(
            to="File",
            from_=partner_name,
            date=assignment_date.isoformat(),
            re=f"{deliverable_id.replace('_', ' ').title()} — {client_name}",
        ),
        title=f"{deliverable_id.replace('_', ' ').title()}: {client_name}",
        expected_values=[
            ExpectedValue(
                description="Precedent case citation",
                value=citation or case_name,
                location="Document header or first paragraph",
            ),
            ExpectedValue(
                description="Client name",
                value=client_name,
                location="Facts section",
            ),
        ],
        narrative_prompt=f"""You are a {partner_name}, a partner at {firm_name}. Write professional legal prose for the following document structure. Use formal legal tone. Reference the precedent case {case_name} ({citation or ''}, {court_code}) correctly. Do NOT use AI hedging language. Write with authority.""",
    )


def build_lawyer_canonical(
    seed: Seed,
    deliverable_id: str,
    archetype: str,
    difficulty: DifficultyBand,
    rng: random.Random,
) -> CanonicalScenario:
    p = seed.payload
    court_code = p.get("court", "unknown")
    case_name = p.get("case_name", seed.title)
    citation = p.get("citation")
    date_filed = _parse_iso_date(p.get("date_filed"))

    firm_name = rng.choice(_FICTIONAL_LAW_FIRMS)
    partner_name = rng.choice(_FICTIONAL_PARTNERS)
    fictional_client = f"{rng.choice(['Atlas', 'Meridian', 'Cardinal', 'Northbeam', 'Saltspring'])} {rng.choice(['Holdings', 'Industries', 'Logistics', 'Partners', 'Capital'])}, {rng.choice(['LLC', 'Inc.', 'LLP', 'Corp.'])}"

    entities = [
        Entity(
            id="precedent_case",
            kind="court",
            name=case_name,
            attrs={
                "court_code": court_code,
                "citation": citation or "",
                "date_filed": date_filed.isoformat(),
            },
        ),
        Entity(id="firm", kind="law_firm", name=firm_name),
        Entity(
            id="supervising_partner",
            kind="person",
            name=partner_name,
            attrs={"role": "supervising partner", "firm": firm_name},
        ),
        Entity(id="client", kind="company", name=fictional_client),
    ]

    assignment_date = date.today() - timedelta(days=rng.randint(0, 7))
    deadline_days = {
        DifficultyBand.LIGHT: rng.randint(2, 5),
        DifficultyBand.MEDIUM: rng.randint(5, 10),
        DifficultyBand.HARD: rng.randint(10, 21),
    }[difficulty]
    deadline = assignment_date + timedelta(days=deadline_days)

    timeline = [
        TimelineEvent(
            id="precedent_filed",
            date=date_filed,
            description=f"{case_name} decided",
            entities=["precedent_case"],
        ),
        TimelineEvent(
            id="assignment",
            date=assignment_date,
            description="Supervising partner assigned the work",
            entities=["supervising_partner", "firm"],
        ),
        TimelineEvent(
            id="deadline",
            date=deadline,
            description="Internal deadline for first draft",
            entities=["supervising_partner"],
        ),
    ]

    facts: list[FactValue] = [
        FactValue(
            id="precedent_citation",
            kind="citation",
            value=citation or case_name,
            source=f"courtlistener:{p.get('cluster_id')}",
        ),
        FactValue(id="precedent_court", kind="string", value=court_code),
        FactValue(
            id="precedent_text_excerpt",
            kind="string",
            value=seed.text_excerpt[:1500],
            source=f"courtlistener:{p.get('opinion_id')}",
        ),
    ]

    blueprint = _design_legal_blueprint(
        case_name=case_name,
        citation=citation,
        court_code=court_code,
        date_filed=date_filed,
        firm_name=firm_name,
        partner_name=partner_name,
        client_name=fictional_client,
        deliverable_id=deliverable_id,
        archetype=archetype,
        difficulty=difficulty,
        text_excerpt=seed.text_excerpt[:1500],
    )

    # Add input attachments probabilistically
    if _should_attach(rng, "lawyer", deliverable_id):
        attachments = _build_legal_attachments(case_name, deliverable_id, archetype, rng)
        blueprint = blueprint.model_copy(update={"input_attachments": attachments})

    return CanonicalScenario(
        scenario_id=_scenario_id(seed.seed_id, deliverable_id, archetype, rng.randint(0, 9999)),
        occupation=Occupation.LAWYER,
        deliverable_id=deliverable_id,
        archetype=archetype,
        difficulty=difficulty,
        seed=SeedReference(source="courtlistener", identifier=seed.identifier),
        entities=entities,
        timeline=timeline,
        facts=facts,
        explicit_requirements=[],
        implicit_requirements=[],
        seed_rng=rng.randint(0, 2**32 - 1),
        reference_answer=blueprint,
    )


# ─────────────────────────── FINANCIAL ANALYST ───────────────────────────

_FICTIONAL_BANKS = [
    "Westlake Capital Markets",
    "Brennan Brothers & Co.",
    "Pemberton Crest Securities",
    "Halverson Stuyvesant",
    "Marshfield Croft Partners",
]


def _get_fact(key_facts: dict, concept: str) -> float | None:
    """Extract the latest numeric value for a given XBRL concept."""
    observations = key_facts.get(concept)
    if not observations:
        return None
    latest = observations[0]
    val = latest.get("val")
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _design_dcf_blueprint(
    ticker: str,
    entity_name: str,
    sector: str,
    key_facts: dict[str, list[dict]],
    deliverable_id: str,
    archetype: str,
    difficulty: DifficultyBand,
    rng: random.Random,
) -> ReferenceAnswer:
    """Design a DCF model blueprint from EDGAR XBRL facts.

    Extracts real financial data and builds a 5-sheet Excel workbook with
    live formulas. All assumptions are derived deterministically from facts.
    """

    # ── Extract key financials (in millions USD) ──
    revenue = _get_fact(key_facts, "Revenues")
    if revenue is None:
        revenue = _get_fact(key_facts, "RevenueFromContractWithCustomerExcludingAssessedTax") or 1_000_000_000

    gross_profit = _get_fact(key_facts, "GrossProfit")
    operating_income = _get_fact(key_facts, "OperatingIncomeLoss")
    net_income = _get_fact(key_facts, "NetIncomeLoss")
    total_assets = _get_fact(key_facts, "Assets")
    total_liabilities = _get_fact(key_facts, "Liabilities")
    stockholders_equity = _get_fact(key_facts, "StockholdersEquity")
    cash = _get_fact(key_facts, "CashAndCashEquivalentsAtCarryingValue")
    eps_diluted = _get_fact(key_facts, "EarningsPerShareDiluted")
    shares = _get_fact(key_facts, "CommonStockSharesOutstanding")
    if shares is None:
        shares = _get_fact(key_facts, "CommonStockSharesIssued")

    # Derive missing values
    cogs = revenue - gross_profit if gross_profit else revenue * 0.55
    sga = _get_fact(key_facts, "SellingGeneralAndAdministrativeExpense") or revenue * 0.15
    rd = _get_fact(key_facts, "ResearchAndDevelopmentExpense") or 0
    da = _get_fact(key_facts, "DepreciationAndAmortization") or revenue * 0.05
    capex = _get_fact(key_facts, "PaymentsToAcquirePropertyPlantAndEquipment") or revenue * 0.08
    debt = total_liabilities if total_liabilities else 0

    # Convert to millions for the model
    rev_m = revenue / 1_000_000
    cogs_m = cogs / 1_000_000
    sga_m = sga / 1_000_000
    rd_m = rd / 1_000_000
    da_m = da / 1_000_000
    capex_m = capex / 1_000_000
    cash_m = (cash or 0) / 1_000_000
    debt_m = debt / 1_000_000
    shares_m = (shares or 1_000_000_000) / 1_000_000
    equity_m = (stockholders_equity or (total_assets - total_liabilities if total_assets and total_liabilities else revenue * 2)) / 1_000_000

    # ── Derive DCF assumptions deterministically ──
    # Revenue growth: sector-based default with small randomization
    sector_growth = {
        "Technology": 0.08, "Software": 0.10, "Semiconductors": 0.07,
        "Health Care": 0.06, "Pharmaceuticals": 0.05,
        "Financials": 0.04, "Banks": 0.03, "Insurance": 0.03,
        "Industrials": 0.04, "Aerospace": 0.05, "Defense": 0.03,
        "Consumer Discretionary": 0.05, "Retail": 0.04,
        "Consumer Staples": 0.03, "Food": 0.02,
        "Energy": 0.03, "Oil & Gas": 0.03,
        "Utilities": 0.02, "Telecommunication": 0.02,
        "Materials": 0.03, "Real Estate": 0.03,
    }.get(sector, 0.04)

    growth = round(sector_growth + rng.uniform(-0.01, 0.01), 3)
    cogs_pct = round(cogs_m / rev_m, 4) if rev_m > 0 else 0.55
    sga_pct = round(sga_m / rev_m, 4) if rev_m > 0 else 0.15
    rd_pct = round(rd_m / rev_m, 4) if rev_m > 0 else 0.03
    da_pct = round(da_m / rev_m, 4) if rev_m > 0 else 0.05
    capex_pct = round(capex_m / rev_m, 4) if rev_m > 0 else 0.08
    tax_rate = 0.21 if net_income and operating_income else 0.25

    # WACC assumptions
    rf = 0.0435
    erp = 0.055
    beta = round(rng.uniform(0.9, 1.3), 2)
    ke = rf + beta * erp
    kd = 0.045
    wd = round(debt_m / (debt_m + equity_m), 3) if (debt_m + equity_m) > 0 else 0.25
    we = 1 - wd
    wacc = round(we * ke + wd * kd * (1 - tax_rate), 4)
    term_growth = round(rng.uniform(0.018, 0.025), 3)

    # Working capital as % of revenue change
    wc_pct = 0.02

    # ── Build 5-year projection ──
    years = ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]
    projections = []
    for i, yr in enumerate(years, 1):
        rev = rev_m * ((1 + growth) ** i)
        cogs_val = rev * cogs_pct
        gp = rev - cogs_val
        sga_val = rev * sga_pct
        rd_val = rev * rd_pct
        da_val = rev * da_pct
        ebit = gp - sga_val - rd_val - da_val
        tax = ebit * tax_rate if ebit > 0 else 0
        nopat = ebit - tax
        capex_val = rev * capex_pct
        wc_change = (rev - rev_m * ((1 + growth) ** (i - 1))) * wc_pct if i > 1 else rev_m * growth * wc_pct
        fcff = nopat + da_val - capex_val - wc_change
        projections.append({
            "rev": rev, "cogs": cogs_val, "gp": gp,
            "sga": sga_val, "rd": rd_val, "da": da_val,
            "ebit": ebit, "tax": tax, "nopat": nopat,
            "capex": capex_val, "wc_change": wc_change, "fcff": fcff,
        })

    # Terminal value and valuation
    tv = projections[-1]["fcff"] * (1 + term_growth) / (wacc - term_growth)
    pv_fcff = sum(p["fcff"] / ((1 + wacc) ** (i + 1)) for i, p in enumerate(projections))
    pv_tv = tv / ((1 + wacc) ** 5)
    ev = pv_fcff + pv_tv
    equity_val = ev - debt_m + cash_m
    per_share = equity_val / shares_m if shares_m > 0 else 0

    # ── Build Excel blueprint ──
    def _fmt(v: float) -> float:
        return round(v, 1)

    # Sheet 1: Assumptions
    assumption_cells = [
        CellBlueprint(ref="A1", value="DCF Model Assumptions", bold=True, fill="header"),
        CellBlueprint(ref="A3", value="Base-Year Financials (TTM, $M)", bold=True),
        CellBlueprint(ref="A4", value="Revenue", fill="input"),
        CellBlueprint(ref="B4", value=_fmt(rev_m), fill="input", number_format="#,##0"),
        CellBlueprint(ref="A5", value="COGS", fill="input"),
        CellBlueprint(ref="B5", value=_fmt(cogs_m), fill="input", number_format="#,##0"),
        CellBlueprint(ref="A6", value="SG&A", fill="input"),
        CellBlueprint(ref="B6", value=_fmt(sga_m), fill="input", number_format="#,##0"),
        CellBlueprint(ref="A7", value="R&D", fill="input"),
        CellBlueprint(ref="B7", value=_fmt(rd_m), fill="input", number_format="#,##0"),
        CellBlueprint(ref="A8", value="D&A", fill="input"),
        CellBlueprint(ref="B8", value=_fmt(da_m), fill="input", number_format="#,##0"),
        CellBlueprint(ref="A9", value="CapEx", fill="input"),
        CellBlueprint(ref="B9", value=_fmt(capex_m), fill="input", number_format="#,##0"),
        CellBlueprint(ref="A10", value="Cash", fill="input"),
        CellBlueprint(ref="B10", value=_fmt(cash_m), fill="input", number_format="#,##0"),
        CellBlueprint(ref="A11", value="Total Debt", fill="input"),
        CellBlueprint(ref="B11", value=_fmt(debt_m), fill="input", number_format="#,##0"),
        CellBlueprint(ref="A12", value="Shares Outstanding (M)", fill="input"),
        CellBlueprint(ref="B12", value=_fmt(shares_m), fill="input", number_format="#,##0"),
        CellBlueprint(ref="A14", value="Growth & Margin Assumptions", bold=True),
        CellBlueprint(ref="A15", value="Revenue Growth", fill="input"),
        CellBlueprint(ref="B15", value=growth, fill="input", number_format="0.0%"),
        CellBlueprint(ref="A16", value="COGS % of Revenue", fill="input"),
        CellBlueprint(ref="B16", value=cogs_pct, fill="input", number_format="0.0%"),
        CellBlueprint(ref="A17", value="SG&A % of Revenue", fill="input"),
        CellBlueprint(ref="B17", value=sga_pct, fill="input", number_format="0.0%"),
        CellBlueprint(ref="A18", value="R&D % of Revenue", fill="input"),
        CellBlueprint(ref="B18", value=rd_pct, fill="input", number_format="0.0%"),
        CellBlueprint(ref="A19", value="D&A % of Revenue", fill="input"),
        CellBlueprint(ref="B19", value=da_pct, fill="input", number_format="0.0%"),
        CellBlueprint(ref="A20", value="CapEx % of Revenue", fill="input"),
        CellBlueprint(ref="B20", value=capex_pct, fill="input", number_format="0.0%"),
        CellBlueprint(ref="A21", value="Tax Rate", fill="input"),
        CellBlueprint(ref="B21", value=tax_rate, fill="input", number_format="0.0%"),
        CellBlueprint(ref="A22", value="ΔWC % of ΔRevenue", fill="input"),
        CellBlueprint(ref="B22", value=wc_pct, fill="input", number_format="0.0%"),
        CellBlueprint(ref="A24", value="WACC Components", bold=True),
        CellBlueprint(ref="A25", value="Risk-Free Rate", fill="input"),
        CellBlueprint(ref="B25", value=rf, fill="input", number_format="0.00%"),
        CellBlueprint(ref="A26", value="Equity Risk Premium", fill="input"),
        CellBlueprint(ref="B26", value=erp, fill="input", number_format="0.00%"),
        CellBlueprint(ref="A27", value="Beta", fill="input"),
        CellBlueprint(ref="B27", value=beta, fill="input", number_format="0.00"),
        CellBlueprint(ref="A28", value="Cost of Equity (Ke)", fill="subtotal"),
        CellBlueprint(ref="B28", formula="=B25+B27*B26", fill="subtotal", number_format="0.00%"),
        CellBlueprint(ref="A29", value="Pre-tax Cost of Debt (Kd)", fill="input"),
        CellBlueprint(ref="B29", value=kd, fill="input", number_format="0.00%"),
        CellBlueprint(ref="A30", value="Weight of Debt (Wd)", fill="input"),
        CellBlueprint(ref="B30", value=wd, fill="input", number_format="0.0%"),
        CellBlueprint(ref="A31", value="Weight of Equity (We)", fill="subtotal"),
        CellBlueprint(ref="B31", formula="=1-B30", fill="subtotal", number_format="0.0%"),
        CellBlueprint(ref="A32", value="WACC", bold=True, fill="total"),
        CellBlueprint(ref="B32", formula="=B31*B28+B30*B29*(1-B21)", bold=True, fill="total", number_format="0.00%"),
        CellBlueprint(ref="A34", value="Terminal Growth Rate", fill="input"),
        CellBlueprint(ref="B34", value=term_growth, fill="input", number_format="0.00%"),
    ]

    # Sheet 2: Income Statement Projection
    is_cells = [
        CellBlueprint(ref="A1", value="Income Statement Projection ($M)", bold=True, fill="header"),
        CellBlueprint(ref="A3", value="Line Item"),
        CellBlueprint(ref="B3", value="Base (TTM)"),
    ]
    for i, yr in enumerate(years):
        is_cells.append(CellBlueprint(ref=chr(67 + i) + "3", value=yr))

    is_rows = [
        ("Revenue", [rev_m] + [p["rev"] for p in projections]),
        ("(-) COGS", [cogs_m] + [p["cogs"] for p in projections]),
        ("Gross Profit", None),
        ("(-) SG&A", [sga_m] + [p["sga"] for p in projections]),
        ("(-) R&D", [rd_m] + [p["rd"] for p in projections]),
        ("(-) D&A", [da_m] + [p["da"] for p in projections]),
        ("EBIT", None),
        ("(-) Taxes", None),
        ("NOPAT", None),
    ]

    row_num = 4
    for label, values in is_rows:
        is_cells.append(CellBlueprint(ref=f"A{row_num}", value=label, bold=(label in ("Revenue", "Gross Profit", "EBIT", "NOPAT"))))
        if values is not None:
            for j, v in enumerate(values):
                col = chr(66 + j)
                is_cells.append(CellBlueprint(ref=f"{col}{row_num}", value=_fmt(v), number_format="#,##0"))
        else:
            # Formula row
            if label == "Gross Profit":
                for j in range(6):
                    col = chr(66 + j)
                    is_cells.append(CellBlueprint(ref=f"{col}{row_num}", formula=f"={col}{row_num-2}-{col}{row_num-1}", number_format="#,##0"))
            elif label == "EBIT":
                for j in range(6):
                    col = chr(66 + j)
                    is_cells.append(CellBlueprint(ref=f"{col}{row_num}", formula=f"={col}{row_num-4}-{col}{row_num-3}-{col}{row_num-2}-{col}{row_num-1}", number_format="#,##0"))
            elif label == "(-) Taxes":
                for j in range(6):
                    col = chr(66 + j)
                    is_cells.append(CellBlueprint(ref=f"{col}{row_num}", formula=f"=MAX({col}{row_num-1}*Assumptions!$B$21,0)", number_format="#,##0"))
            elif label == "NOPAT":
                for j in range(6):
                    col = chr(66 + j)
                    is_cells.append(CellBlueprint(ref=f"{col}{row_num}", formula=f"={col}{row_num-2}-{col}{row_num-1}", number_format="#,##0"))
        row_num += 1

    # Sheet 3: DCF
    dcf_cells = [
        CellBlueprint(ref="A1", value="Unlevered Free Cash Flow ($M)", bold=True, fill="header"),
        CellBlueprint(ref="A3", value="Line Item"),
    ]
    for i, yr in enumerate(years):
        dcf_cells.append(CellBlueprint(ref=chr(66 + i) + "3", value=yr))

    dcf_rows = [
        ("NOPAT", None),
        ("(+) D&A", [p["da"] for p in projections]),
        ("(-) CapEx", [p["capex"] for p in projections]),
        ("(-) Δ Working Capital", [p["wc_change"] for p in projections]),
        ("Unlevered FCFF", None),
    ]

    row_num = 4
    for label, values in dcf_rows:
        dcf_cells.append(CellBlueprint(ref=f"A{row_num}", value=label, bold=(label == "Unlevered FCFF")))
        if values is not None:
            for j, v in enumerate(values):
                col = chr(66 + j)
                dcf_cells.append(CellBlueprint(ref=f"{col}{row_num}", value=_fmt(v), number_format="#,##0"))
        else:
            if label == "NOPAT":
                for j in range(5):
                    col = chr(66 + j)
                    dcf_cells.append(CellBlueprint(ref=f"{col}{row_num}", formula=f"='Income Statement'!{col}12", number_format="#,##0"))
            elif label == "Unlevered FCFF":
                for j in range(5):
                    col = chr(66 + j)
                    dcf_cells.append(CellBlueprint(ref=f"{col}{row_num}", formula=f"={col}{row_num-4}+{col}{row_num-3}-{col}{row_num-2}-{col}{row_num-1}", bold=True, fill="total", number_format="#,##0"))
        row_num += 1

    # Terminal value
    dcf_cells.append(CellBlueprint(ref="A10", value="Terminal Value", bold=True))
    dcf_cells.append(CellBlueprint(ref="B10", formula="=F8*(1+Assumptions!$B$34)/(Assumptions!$B$32-Assumptions!$B$34)", bold=True, fill="total", number_format="#,##0"))

    # Sheet 4: Valuation
    val_cells = [
        CellBlueprint(ref="A1", value="DCF Valuation ($M)", bold=True, fill="header"),
        CellBlueprint(ref="A3", value="Year"),
        CellBlueprint(ref="B3", value="FCFF"),
        CellBlueprint(ref="C3", value="Discount Factor"),
        CellBlueprint(ref="D3", value="PV of FCFF"),
    ]
    for i in range(5):
        yr_col = chr(66 + i)
        val_cells.append(CellBlueprint(ref=f"A{4+i}", value=f"Year {i+1}"))
        val_cells.append(CellBlueprint(ref=f"B{4+i}", formula=f"='DCF'!{yr_col}8", number_format="#,##0"))
        val_cells.append(CellBlueprint(ref=f"C{4+i}", formula=f"=1/(1+Assumptions!$B$32)^{i+1}", number_format="0.0000"))
        val_cells.append(CellBlueprint(ref=f"D{4+i}", formula=f"=B{4+i}*C{4+i}", number_format="#,##0"))

    val_cells.append(CellBlueprint(ref="A9", value="PV of Terminal Value", bold=True))
    val_cells.append(CellBlueprint(ref="B9", formula="='DCF'!B10*C8", number_format="#,##0"))
    val_cells.append(CellBlueprint(ref="A10", value="Enterprise Value", bold=True, fill="total"))
    val_cells.append(CellBlueprint(ref="B10", formula="=SUM(D4:D8)+B9", bold=True, fill="total", number_format="#,##0"))
    val_cells.append(CellBlueprint(ref="A11", value="(-) Total Debt"))
    val_cells.append(CellBlueprint(ref="B11", formula="=Assumptions!B11", number_format="#,##0"))
    val_cells.append(CellBlueprint(ref="A12", value="(+) Cash"))
    val_cells.append(CellBlueprint(ref="B12", formula="=Assumptions!B10", number_format="#,##0"))
    val_cells.append(CellBlueprint(ref="A13", value="Equity Value", bold=True, fill="total"))
    val_cells.append(CellBlueprint(ref="B13", formula="=B10-B11+B12", bold=True, fill="total", number_format="#,##0"))
    val_cells.append(CellBlueprint(ref="A14", value="Shares Outstanding (M)"))
    val_cells.append(CellBlueprint(ref="B14", formula="=Assumptions!B12", number_format="#,##0"))
    val_cells.append(CellBlueprint(ref="A15", value="Implied Value Per Share", bold=True, fill="total"))
    val_cells.append(CellBlueprint(ref="B15", formula="=B13/B14", bold=True, fill="total", number_format="$#,##0.00"))

    # Sheet 5: Sensitivity
    sens_wacc_range = [wacc - 0.02, wacc - 0.01, wacc, wacc + 0.01, wacc + 0.02]
    sens_g_range = [term_growth - 0.01, term_growth - 0.005, term_growth, term_growth + 0.005, term_growth + 0.01]

    sens_cells = [
        CellBlueprint(ref="A1", value="Sensitivity: Equity Value Per Share", bold=True, fill="header"),
        CellBlueprint(ref="A3", value="WACC \\ g"),
    ]
    for i, g in enumerate(sens_g_range):
        sens_cells.append(CellBlueprint(ref=chr(66 + i) + "3", value=g, number_format="0.0%"))
    for i, w in enumerate(sens_wacc_range):
        sens_cells.append(CellBlueprint(ref=f"A{4+i}", value=w, number_format="0.0%"))
        for j, g in enumerate(sens_g_range):
            col = chr(66 + j)
            sens_cells.append(CellBlueprint(
                ref=f"{col}{4+i}",
                formula=f"=IF({chr(66+i)}3<$A{4+j},'Valuation'!$B$13/'Valuation'!$B$14*('DCF'!$F$8*(1+{chr(66+i)}3)/($A{4+j}-{chr(66+i)}3)/((1+$A{4+j})^5)+SUM('Valuation'!$D$4:$D$8))/'Valuation'!$B$14,\"N/A\")",
                number_format="$#,##0.00",
            ))

    expected_values = [
        ExpectedValue(description="WACC", value=round(wacc, 4), tolerance=0.001, location="Assumptions B32"),
        ExpectedValue(description="Terminal Growth Rate", value=term_growth, tolerance=0.001, location="Assumptions B34"),
        ExpectedValue(description="Year 5 FCFF", value=_fmt(projections[-1]["fcff"]), tolerance=0.5, location="DCF F8"),
        ExpectedValue(description="Enterprise Value", value=_fmt(ev), tolerance=1.0, location="Valuation B10"),
        ExpectedValue(description="Equity Value", value=_fmt(equity_val), tolerance=1.0, location="Valuation B13"),
        ExpectedValue(description="Value Per Share", value=round(per_share, 2), tolerance=0.01, location="Valuation B15"),
    ]

    return ReferenceAnswer(
        format="xlsx",
        sheets=[
            SheetBlueprint(name="Assumptions", cells=assumption_cells, column_widths={"A": 30, "B": 16}),
            SheetBlueprint(name="Income Statement", cells=is_cells, column_widths={"A": 20, "B": 14, "C": 14, "D": 14, "E": 14, "F": 14, "G": 14}),
            SheetBlueprint(name="DCF", cells=dcf_cells, column_widths={"A": 25, "B": 14, "C": 14, "D": 14, "E": 14, "F": 14}),
            SheetBlueprint(name="Valuation", cells=val_cells, column_widths={"A": 25, "B": 16, "C": 16, "D": 16}),
            SheetBlueprint(name="Sensitivity", cells=sens_cells, column_widths={"A": 12, "B": 14, "C": 14, "D": 14, "E": 14, "F": 14}),
        ],
        expected_values=expected_values,
        narrative_prompt=f"""You are an associate analyst at an investment bank. You have built a 5-year unlevered DCF model for {entity_name} ({ticker}) based on its latest SEC filings.

The model includes:
- Base-year financials from EDGAR XBRL
- Revenue growth assumption of {growth:.1%} (sector-typical for {sector})
- WACC of {wacc:.2%} derived from beta={beta:.2f}, Rf={rf:.2%}, ERP={erp:.2%}
- Terminal growth of {term_growth:.2%}

Write a one-page summary memo explaining the key assumptions and valuation conclusion. Be specific with numbers. Do NOT use AI hedging.""",
    )


def _design_variance_blueprint(
    ticker: str,
    entity_name: str,
    sector: str,
    key_facts: dict[str, list[dict]],
    rng: random.Random,
) -> ReferenceAnswer:
    """Design a variance analysis workbook: Actual vs Budget vs Prior Period."""
    revenue = _get_fact(key_facts, "Revenues") or _get_fact(key_facts, "RevenueFromContractWithCustomerExcludingAssessedTax") or 1_000_000_000
    gross_profit = _get_fact(key_facts, "GrossProfit")
    operating_income = _get_fact(key_facts, "OperatingIncomeLoss")
    net_income = _get_fact(key_facts, "NetIncomeLoss")

    rev_m = revenue / 1_000_000
    gp_m = (gross_profit or revenue * 0.4) / 1_000_000
    oi_m = (operating_income or revenue * 0.15) / 1_000_000
    ni_m = (net_income or revenue * 0.10) / 1_000_000
    cogs_m = rev_m - gp_m

    # Build a simple 2-sheet workbook
    actual_cells = [
        CellBlueprint(ref="A1", value="Variance Analysis: Actual vs Budget", bold=True, fill="header"),
        CellBlueprint(ref="A3", value="Line Item", bold=True, fill="header"),
        CellBlueprint(ref="B3", value="Actual ($M)", bold=True, fill="header"),
        CellBlueprint(ref="C3", value="Budget ($M)", bold=True, fill="header"),
        CellBlueprint(ref="D3", value="Variance ($M)", bold=True, fill="header"),
        CellBlueprint(ref="E3", value="Variance (%)", bold=True, fill="header"),
        CellBlueprint(ref="A4", value="Revenue"),
        CellBlueprint(ref="B4", value=round(rev_m, 1)),
        CellBlueprint(ref="C4", value=round(rev_m * rng.uniform(0.92, 1.08), 1)),
        CellBlueprint(ref="D4", formula="=B4-C4"),
        CellBlueprint(ref="E4", formula="=D4/C4", number_format="0.0%"),
        CellBlueprint(ref="A5", value="COGS"),
        CellBlueprint(ref="B5", value=round(cogs_m, 1)),
        CellBlueprint(ref="C5", value=round(cogs_m * rng.uniform(0.95, 1.05), 1)),
        CellBlueprint(ref="D5", formula="=B5-C5"),
        CellBlueprint(ref="E5", formula="=D5/C5", number_format="0.0%"),
        CellBlueprint(ref="A6", value="Gross Profit"),
        CellBlueprint(ref="B6", value=round(gp_m, 1)),
        CellBlueprint(ref="C6", value=round(gp_m * rng.uniform(0.90, 1.10), 1)),
        CellBlueprint(ref="D6", formula="=B6-C6"),
        CellBlueprint(ref="E6", formula="=D6/C6", number_format="0.0%"),
        CellBlueprint(ref="A7", value="Operating Income"),
        CellBlueprint(ref="B7", value=round(oi_m, 1)),
        CellBlueprint(ref="C7", value=round(oi_m * rng.uniform(0.85, 1.15), 1)),
        CellBlueprint(ref="D7", formula="=B7-C7"),
        CellBlueprint(ref="E7", formula="=D7/C7", number_format="0.0%"),
        CellBlueprint(ref="A8", value="Net Income"),
        CellBlueprint(ref="B8", value=round(ni_m, 1)),
        CellBlueprint(ref="C8", value=round(ni_m * rng.uniform(0.85, 1.15), 1)),
        CellBlueprint(ref="D8", formula="=B8-C8"),
        CellBlueprint(ref="E8", formula="=D8/C8", number_format="0.0%"),
    ]

    summary_cells = [
        CellBlueprint(ref="A1", value="Key Variances", bold=True, fill="header"),
        CellBlueprint(ref="A3", value="Primary driver of revenue variance"),
        CellBlueprint(ref="B3", value="Volume / price mix"),
        CellBlueprint(ref="A4", value="Primary driver of margin variance"),
        CellBlueprint(ref="B4", value="Input cost inflation vs pricing power"),
        CellBlueprint(ref="A5", value="Largest $ variance line item"),
        CellBlueprint(ref="B5", formula="=MAX('Actual vs Budget'!D4:D8)"),
    ]

    return ReferenceAnswer(
        format="xlsx",
        sheets=[
            SheetBlueprint(name="Actual vs Budget", cells=actual_cells, column_widths={"A": 20, "B": 14, "C": 14, "D": 14, "E": 14}),
            SheetBlueprint(name="Summary", cells=summary_cells, column_widths={"A": 35, "B": 30}),
        ],
        expected_values=[
            ExpectedValue(description="Revenue", value=str(round(rev_m, 1)), location="Actual vs Budget B4"),
            ExpectedValue(description="Gross Profit", value=str(round(gp_m, 1)), location="Actual vs Budget B6"),
        ],
        narrative_prompt=f"Build a variance analysis workbook for {entity_name} ({ticker}) comparing actuals to budget and prior period.",
    )


def _design_financial_docx_blueprint(
    ticker: str,
    entity_name: str,
    sector: str,
    key_facts: dict[str, list[dict]],
    deliverable_id: str,
    archetype: str,
    rng: random.Random,
) -> ReferenceAnswer:
    """Design a Word document blueprint for credit memo or investment deck."""
    revenue = _get_fact(key_facts, "Revenues") or 1_000_000_000
    rev_m = revenue / 1_000_000
    net_income = _get_fact(key_facts, "NetIncomeLoss")
    ni_m = (net_income or revenue * 0.10) / 1_000_000
    debt = _get_fact(key_facts, "Liabilities") or revenue * 0.5
    debt_m = debt / 1_000_000

    if deliverable_id == "credit_memo":
        sections = [
            SectionBlueprint(heading="Executive Summary", heading_level=1, required_content=["Recommendation", "Facility amount", "Key risks"]),
            SectionBlueprint(heading="Borrower Overview", heading_level=1, required_content=[f"{entity_name} ({ticker})", f"Sector: {sector}"]),
            SectionBlueprint(heading="Financial Analysis", heading_level=1, required_content=[f"Revenue: ${rev_m:.0f}M", f"Net Income: ${ni_m:.0f}M", f"Total Debt: ${debt_m:.0f}M"]),
            SectionBlueprint(heading="Risk Factors", heading_level=1, required_content=["Industry risks", "Financial covenant headroom", "Mitigants"]),
            SectionBlueprint(heading="Recommendation", heading_level=1, required_content=["Go/no-go", "Key terms", "Conditions precedent"]),
        ]
    else:
        # investment_committee_deck
        sections = [
            SectionBlueprint(heading="Investment Thesis", heading_level=1, required_content=["Clear thesis in 2-3 sentences", "Target return"]),
            SectionBlueprint(heading="Company Overview", heading_level=1, required_content=[f"{entity_name} ({ticker})", f"Sector: {sector}", "Business model"]),
            SectionBlueprint(heading="Financial Highlights", heading_level=1, required_content=[f"Revenue: ${rev_m:.0f}M", f"Net Income: ${ni_m:.0f}M", "Growth trajectory"]),
            SectionBlueprint(heading="Valuation", heading_level=1, required_content=["Entry multiple", "Comparable transactions", "Exit assumptions"]),
            SectionBlueprint(heading="Risks & Mitigants", heading_level=1, required_content=["Key risks", "How to mitigate"]),
            SectionBlueprint(heading="Recommendation", heading_level=1, required_content=["Go/no-go", "Target ownership", "Capital deployment"]),
        ]

    return ReferenceAnswer(
        format="docx",
        sections=sections,
        doc_header=DocHeaderBlueprint(
            to="Committee" if deliverable_id == "investment_committee_deck" else "Credit Committee",
            from_="Associate Analyst",
            date=date.today().isoformat(),
            re=f"{deliverable_id.replace('_', ' ').title()}: {entity_name}",
        ),
        title=f"{deliverable_id.replace('_', ' ').title()}: {entity_name}",
        expected_values=[
            ExpectedValue(description="Company", value=entity_name, location="Overview section"),
            ExpectedValue(description="Ticker", value=ticker, location="Overview section"),
            ExpectedValue(description="Revenue", value=f"${rev_m:.0f}M", location="Financial section"),
        ],
        narrative_prompt=f"Write a professional {deliverable_id.replace('_', ' ')} for {entity_name} ({ticker}) in the {sector} sector.",
    )


def build_financial_canonical(
    seed: Seed,
    deliverable_id: str,
    archetype: str,
    difficulty: DifficultyBand,
    rng: random.Random,
) -> CanonicalScenario:
    p = seed.payload
    ticker = p["ticker"]
    entity_name = p["entity_name"]
    sector = p["sector"]

    key_facts: dict[str, list[dict]] = p.get("key_facts", {})
    facts: list[FactValue] = []
    for concept, observations in key_facts.items():
        if not observations:
            continue
        latest = observations[0]
        val = latest.get("val")
        if val is None:
            continue
        end = latest.get("end", "?")
        unit = "USD" if "Share" not in concept else "USD/share"
        facts.append(
            FactValue(
                id=f"fact_{concept[:30]}",
                kind="money" if "Share" not in concept else "string",
                value=val,
                unit=unit,
                source=f"EDGAR:{ticker}:{concept}:{end}",
            )
        )

    employer = rng.choice(_FICTIONAL_BANKS)
    analyst_name = rng.choice([
        "Priya Doshi", "Gabriel Ostrowski", "Yuki Beaumont",
        "Nadia Kowalczyk", "Henrik Ådahl",
    ])
    senior_name = rng.choice([
        "James Marchetti", "Lin Wei-chen", "Rashida Holm",
        "Andre Thibault", "Kara Vossberg",
    ])

    entities = [
        Entity(
            id="target_company",
            kind="company",
            name=entity_name,
            attrs={"ticker": ticker, "sector": sector, "cik": p["cik"]},
        ),
        Entity(id="employer", kind="company", name=employer),
        Entity(
            id="analyst",
            kind="person",
            name=analyst_name,
            attrs={"role": "associate analyst", "employer": employer},
        ),
        Entity(
            id="senior",
            kind="person",
            name=senior_name,
            attrs={"role": "managing director", "employer": employer},
        ),
    ]

    filings = p.get("recent_filings", [])
    most_recent_filing = filings[0] if filings else {}
    filing_date = _parse_iso_date(most_recent_filing.get("date"))

    deadline_days = {
        DifficultyBand.LIGHT: rng.randint(1, 3),
        DifficultyBand.MEDIUM: rng.randint(3, 7),
        DifficultyBand.HARD: rng.randint(7, 14),
    }[difficulty]
    assignment_date = max(filing_date, date.today() - timedelta(days=rng.randint(0, 5)))
    deadline = assignment_date + timedelta(days=deadline_days)

    timeline = [
        TimelineEvent(
            id="latest_filing",
            date=filing_date,
            description=f"{ticker} filed {most_recent_filing.get('form', 'recent filing')}",
            entities=["target_company"],
        ),
        TimelineEvent(
            id="assignment",
            date=assignment_date,
            description="Senior analyst assigned the work",
            entities=["analyst", "senior"],
        ),
        TimelineEvent(
            id="deadline",
            date=deadline,
            description="Deadline for deliverable",
            entities=["analyst"],
        ),
    ]

    # Generate blueprint based on deliverable type
    if deliverable_id == "dcf_model":
        blueprint = _design_dcf_blueprint(
            ticker=ticker,
            entity_name=entity_name,
            sector=sector,
            key_facts=key_facts,
            deliverable_id=deliverable_id,
            archetype=archetype,
            difficulty=difficulty,
            rng=rng,
        )
    elif deliverable_id == "variance_analysis":
        blueprint = _design_variance_blueprint(
            ticker=ticker,
            entity_name=entity_name,
            sector=sector,
            key_facts=key_facts,
            rng=rng,
        )
    elif deliverable_id in ("credit_memo", "investment_committee_deck"):
        blueprint = _design_financial_docx_blueprint(
            ticker=ticker,
            entity_name=entity_name,
            sector=sector,
            key_facts=key_facts,
            deliverable_id=deliverable_id,
            archetype=archetype,
            rng=rng,
        )
    else:
        # Ultimate fallback: DCF blueprint
        blueprint = _design_dcf_blueprint(
            ticker=ticker,
            entity_name=entity_name,
            sector=sector,
            key_facts=key_facts,
            deliverable_id=deliverable_id,
            archetype=archetype,
            difficulty=difficulty,
            rng=rng,
        )

    # Add input attachments probabilistically
    if _should_attach(rng, "financial_analyst", deliverable_id):
        attachments = _build_financial_attachments(ticker, entity_name, key_facts, deliverable_id, rng)
        blueprint = blueprint.model_copy(update={"input_attachments": attachments})

    return CanonicalScenario(
        scenario_id=_scenario_id(seed.seed_id, deliverable_id, archetype, rng.randint(0, 9999)),
        occupation=Occupation.FINANCIAL_ANALYST,
        deliverable_id=deliverable_id,
        archetype=archetype,
        difficulty=difficulty,
        seed=SeedReference(source="sec_edgar_xbrl", identifier=seed.identifier),
        entities=entities,
        timeline=timeline,
        facts=facts,
        explicit_requirements=[],
        implicit_requirements=[],
        seed_rng=rng.randint(0, 2**32 - 1),
        reference_answer=blueprint,
    )


# ─────────────────────────── SOFTWARE ENGINEER ───────────────────────────


def _design_swe_blueprint(
    repo: str,
    pr_num: int,
    pr_title: str,
    pr_body: str,
    diff: str,
    issue_body: str,
    deliverable_id: str,
    archetype: str,
    difficulty: DifficultyBand,
    manager_name: str,
    teammate_name: str,
    fictional_company: str,
) -> ReferenceAnswer:
    """Design a markdown document blueprint for SWE tasks."""

    # Extract key file paths from diff
    files_changed = []
    for line in diff.split("\n")[:50]:
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                # parts[2] = "a/...", parts[3] = "b/..."
                p = parts[3] if parts[3].startswith("b/") else parts[2]
                files_changed.append(p.replace("b/", "").replace("a/", ""))

    main_files = files_changed[:3] if files_changed else ["unknown_file.py"]

    if deliverable_id == "design_doc":
        md_sections = [
            MdSectionBlueprint(
                heading="Executive Summary",
                heading_level=2,
                required_content=["One-paragraph summary of the proposal"],
            ),
            MdSectionBlueprint(
                heading="Background",
                heading_level=2,
                required_content=[
                    f"Reference to {repo} PR #{pr_num}",
                    "Context for why this change is needed",
                ],
            ),
            MdSectionBlueprint(
                heading="Goals",
                heading_level=2,
                required_content=["2-4 concrete, measurable goals"],
            ),
            MdSectionBlueprint(
                heading="Non-Goals",
                heading_level=2,
                required_content=["Explicitly out-of-scope items"],
            ),
            MdSectionBlueprint(
                heading="Proposed Design",
                heading_level=2,
                required_content=[
                    f"Must reference affected files: {', '.join(main_files)}",
                    "Technical approach with justification",
                ],
            ),
            MdSectionBlueprint(
                heading="Alternatives Considered",
                heading_level=2,
                required_content=["At least 2 alternatives with tradeoff analysis"],
            ),
            MdSectionBlueprint(
                heading="Risks & Mitigations",
                heading_level=2,
                required_content=["Specific risks and how to address them"],
            ),
            MdSectionBlueprint(
                heading="Rollout Plan",
                heading_level=2,
                required_content=["Phased deployment strategy"],
            ),
        ]
    elif deliverable_id == "code_review":
        md_sections = [
            MdSectionBlueprint(
                heading="Executive Summary",
                heading_level=2,
                required_content=["Go/no-go recommendation"],
            ),
            MdSectionBlueprint(
                heading="PR Overview",
                heading_level=2,
                required_content=[f"{repo}#{pr_num}: {pr_title}"],
            ),
            MdSectionBlueprint(
                heading="Files Changed",
                heading_level=2,
                required_content=[f"Analysis of {', '.join(main_files)}"],
            ),
            MdSectionBlueprint(
                heading="Code Quality Assessment",
                heading_level=2,
                required_content=["Readability, test coverage, edge cases"],
            ),
            MdSectionBlueprint(
                heading="Security & Performance",
                heading_level=2,
                required_content=["Security implications and performance impact"],
            ),
            MdSectionBlueprint(
                heading="Recommendations",
                heading_level=2,
                required_content=["Actionable feedback"],
            ),
        ]
    elif deliverable_id == "incident_postmortem":
        md_sections = [
            MdSectionBlueprint(
                heading="Executive Summary",
                heading_level=2,
                required_content=["What happened, impact, and root cause"],
            ),
            MdSectionBlueprint(
                heading="Timeline",
                heading_level=2,
                required_content=["Minute-by-minute incident timeline"],
            ),
            MdSectionBlueprint(
                heading="Root Cause Analysis",
                heading_level=2,
                required_content=["5 Whys or equivalent RCA methodology"],
            ),
            MdSectionBlueprint(
                heading="Impact Assessment",
                heading_level=2,
                required_content=["Users affected, data lost, revenue impact"],
            ),
            MdSectionBlueprint(
                heading="Remediation Actions",
                heading_level=2,
                required_content=["Immediate fixes and long-term improvements"],
            ),
            MdSectionBlueprint(
                heading="Lessons Learned",
                heading_level=2,
                required_content=["What went well, what could be better"],
            ),
        ]
    else:
        # bug_fix_pr or generic
        md_sections = [
            MdSectionBlueprint(
                heading="Problem Statement",
                heading_level=2,
                required_content=["Clear description of the bug"],
            ),
            MdSectionBlueprint(
                heading="Root Cause",
                heading_level=2,
                required_content=["Technical explanation of why the bug occurred"],
            ),
            MdSectionBlueprint(
                heading="Proposed Fix",
                heading_level=2,
                required_content=["Code change description"],
            ),
            MdSectionBlueprint(
                heading="Testing Strategy",
                heading_level=2,
                required_content=["Unit tests, integration tests, edge cases"],
            ),
        ]

    return ReferenceAnswer(
        format="markdown",
        md_sections=md_sections,
        md_title=f"{deliverable_id.replace('_', ' ').title()}: {repo}#{pr_num}",
        expected_values=[
            ExpectedValue(
                description="Repository name",
                value=repo,
                location="Document title or first paragraph",
            ),
            ExpectedValue(
                description="PR number",
                value=str(pr_num),
                location="Document title or first paragraph",
            ),
        ] + [
            ExpectedValue(
                description=f"Affected file {i+1}",
                value=f,
                location="Proposed Design or Files Changed section",
            )
            for i, f in enumerate(main_files)
        ],
        narrative_prompt=f"""You are a senior software engineer at {fictional_company}. Your manager {manager_name} has asked you to write a professional {deliverable_id.replace('_', ' ')} for the open-source project {repo}.

The reference PR is #{pr_num}: {pr_title}

Key technical context:
- Files changed: {', '.join(main_files)}
- PR description excerpt: {pr_body[:500] if pr_body else 'N/A'}

Write in a clear, professional technical tone. Reference specific files and code patterns. Do NOT use AI hedging language. Be specific and actionable.""",
    )


def build_swe_canonical(
    seed: Seed,
    deliverable_id: str,
    archetype: str,
    difficulty: DifficultyBand,
    rng: random.Random,
) -> CanonicalScenario:
    p = seed.payload
    repo = p["repo"]
    pr_num = p["pr_number"]
    pr_title = p["pr_title"]
    pr_body = p.get("pr_body") or ""
    diff = p.get("diff") or ""
    issue_body = p.get("issue_body") or ""

    fictional_company = rng.choice([
        "Driftwood Systems", "Northpath Labs", "Kalpa AI",
        "Solstice Networks", "Brookspring Software",
    ])
    teammate_name = rng.choice([
        "Dani Olarte", "Rin Sato", "Mateusz Kruk", "Saskia van Hout",
    ])
    manager_name = rng.choice([
        "Theo Acharya", "Mira Fontaine", "Esteban Ruiz", "Aurora Lindqvist",
    ])

    entities = [
        Entity(
            id="oss_project",
            kind="repo",
            name=repo,
            attrs={"pr_number": pr_num, "pr_title": pr_title},
        ),
        Entity(id="employer", kind="company", name=fictional_company),
        Entity(
            id="teammate",
            kind="person",
            name=teammate_name,
            attrs={"role": "former teammate"},
        ),
        Entity(
            id="manager",
            kind="person",
            name=manager_name,
            attrs={"role": "engineering manager"},
        ),
    ]

    merged = _parse_iso_date(p.get("merged_at"))
    assignment_date = date.today() - timedelta(days=rng.randint(0, 4))
    deadline_days = {
        DifficultyBand.LIGHT: rng.randint(1, 2),
        DifficultyBand.MEDIUM: rng.randint(2, 5),
        DifficultyBand.HARD: rng.randint(5, 10),
    }[difficulty]

    timeline = [
        TimelineEvent(
            id="reference_pr_merged",
            date=merged,
            description=f"Reference PR {repo}#{pr_num} merged upstream",
            entities=["oss_project"],
        ),
        TimelineEvent(
            id="assignment",
            date=assignment_date,
            description="Manager assigned the task",
            entities=["manager"],
        ),
        TimelineEvent(
            id="deadline",
            date=assignment_date + timedelta(days=deadline_days),
            description="Internal deadline",
            entities=["manager"],
        ),
    ]

    facts: list[FactValue] = [
        FactValue(id="repo_name", kind="string", value=repo),
        FactValue(id="pr_number", kind="count", value=pr_num),
        FactValue(id="pr_title", kind="string", value=pr_title),
    ]
    if pr_body:
        facts.append(
            FactValue(
                id="pr_body_excerpt",
                kind="string",
                value=pr_body[:2000],
                source=f"github:{repo}#{pr_num}",
            )
        )
    if issue_body:
        facts.append(
            FactValue(
                id="issue_body_excerpt",
                kind="string",
                value=issue_body[:2000],
                source=f"github:{repo}#{p.get('linked_issue')}",
            )
        )
    if diff:
        facts.append(
            FactValue(
                id="diff_excerpt",
                kind="string",
                value=diff[:3000],
                source=f"github:{repo}#{pr_num}.diff",
            )
        )

    blueprint = _design_swe_blueprint(
        repo=repo,
        pr_num=pr_num,
        pr_title=pr_title,
        pr_body=pr_body,
        diff=diff,
        issue_body=issue_body,
        deliverable_id=deliverable_id,
        archetype=archetype,
        difficulty=difficulty,
        manager_name=manager_name,
        teammate_name=teammate_name,
        fictional_company=fictional_company,
    )

    # Add input attachments probabilistically
    if _should_attach(rng, "software_engineer", deliverable_id):
        attachments = _build_swe_attachments(repo, pr_num, diff or "", deliverable_id, rng)
        blueprint = blueprint.model_copy(update={"input_attachments": attachments})

    return CanonicalScenario(
        scenario_id=_scenario_id(seed.seed_id, deliverable_id, archetype, rng.randint(0, 9999)),
        occupation=Occupation.SOFTWARE_ENGINEER,
        deliverable_id=deliverable_id,
        archetype=archetype,
        difficulty=difficulty,
        seed=SeedReference(source="github", identifier=seed.identifier),
        entities=entities,
        timeline=timeline,
        facts=facts,
        explicit_requirements=[],
        implicit_requirements=[],
        seed_rng=rng.randint(0, 2**32 - 1),
        reference_answer=blueprint,
    )


# ─────────────────────────── DISPATCHER ───────────────────────────


def build_canonical(
    seed: Seed,
    deliverable_id: str,
    archetype: str,
    difficulty: DifficultyBand,
    rng: random.Random | None = None,
) -> CanonicalScenario:
    rng = rng or random.Random(int(seed.seed_id, 16))
    if seed.occupation == "lawyer":
        return build_lawyer_canonical(seed, deliverable_id, archetype, difficulty, rng)
    if seed.occupation == "financial_analyst":
        return build_financial_canonical(seed, deliverable_id, archetype, difficulty, rng)
    if seed.occupation == "software_engineer":
        return build_swe_canonical(seed, deliverable_id, archetype, difficulty, rng)
    raise ValueError(f"unsupported occupation: {seed.occupation}")
