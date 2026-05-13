"""Canonical scenario state.

Single source of truth shared by every agent in the synthesis pipeline. No agent
invents entities, dates, numbers, or citations — they only render prose around
the values pinned here. This is what eliminates cross-attachment contradictions
("email says Q3, spreadsheet says Q2") that plague naive multi-agent pipelines.

Numbers that must reconcile (financial statements, dates, citations) are filled
procedurally or pulled from real APIs *before* any LLM call. LLMs receive the
canonical state as read-only context.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from pipeline.scenario.reference_answer import ReferenceAnswer


class Occupation(StrEnum):
    LAWYER = "lawyer"
    FINANCIAL_ANALYST = "financial_analyst"
    SOFTWARE_ENGINEER = "software_engineer"


class DifficultyBand(StrEnum):
    LIGHT = "light"
    MEDIUM = "medium"
    HARD = "hard"


class Entity(BaseModel):
    """A named actor in the scenario — company, court, person, repo."""

    id: str
    kind: Literal["company", "person", "court", "repo", "agency", "law_firm"]
    name: str
    attrs: dict[str, str | int | float | bool] = Field(default_factory=dict)


class TimelineEvent(BaseModel):
    """An event with a fixed date. Agents reference these by id, never invent dates."""

    id: str
    date: date
    description: str
    entities: list[str] = Field(default_factory=list)  # entity ids


class FactValue(BaseModel):
    """A pinned fact — numeric, string, or citation. Procedurally generated or API-sourced."""

    id: str
    kind: Literal["money", "percentage", "count", "string", "citation", "ticker"]
    value: str | float | int
    unit: str | None = None
    source: str | None = None  # e.g. "EDGAR:AAPL:10K:2024:Revenue"


class SeedReference(BaseModel):
    """Pointer to the real-world artifact this scenario is grounded in."""

    source: Literal["courtlistener", "recap", "sec_edgar_xbrl", "fred", "fdic", "github"]
    identifier: str  # e.g. CourtListener cluster id, EDGAR accession, GitHub PR url
    local_path: str | None = None


class CanonicalScenario(BaseModel):
    """The locked scenario state. Constructed once, read everywhere.

    Once frozen (via .freeze()), agents may only read; any mutation raises.
    """

    scenario_id: str
    occupation: Occupation
    deliverable_id: str
    archetype: str
    difficulty: DifficultyBand

    seed: SeedReference
    entities: list[Entity]
    timeline: list[TimelineEvent]
    facts: list[FactValue]

    # Hidden requirements that the deliverable must satisfy. The boss email
    # mentions some explicitly and leaves others implicit (real-work realism).
    explicit_requirements: list[str]
    implicit_requirements: list[str]

    # Answer blueprint — designed synchronously with the task.
    reference_answer: ReferenceAnswer | None = None

    # Predicted expert hours; populated after solve-rate calibration.
    estimated_hours: float | None = None

    # Generation provenance for reproducibility / debugging.
    seed_rng: int

    _frozen: bool = False

    @model_validator(mode="after")
    def _check_unique_ids(self) -> CanonicalScenario:
        for collection_name, items in [
            ("entities", self.entities),
            ("timeline", self.timeline),
            ("facts", self.facts),
        ]:
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate ids in {collection_name}")
        # Timeline entity references must resolve.
        entity_ids = {e.id for e in self.entities}
        for event in self.timeline:
            for ref in event.entities:
                if ref not in entity_ids:
                    raise ValueError(f"timeline event {event.id} references unknown entity {ref}")
        return self

    def freeze(self) -> None:
        object.__setattr__(self, "_frozen", True)

    def fact(self, fact_id: str) -> FactValue:
        for f in self.facts:
            if f.id == fact_id:
                return f
        raise KeyError(fact_id)

    def entity(self, entity_id: str) -> Entity:
        for e in self.entities:
            if e.id == entity_id:
                return e
        raise KeyError(entity_id)

    def event(self, event_id: str) -> TimelineEvent:
        for ev in self.timeline:
            if ev.id == event_id:
                return ev
        raise KeyError(event_id)

    def context_for_agent(self) -> str:
        """Render canonical state as read-only prompt context.

        Agents see this block and are instructed to reference items by id rather
        than restating values, so contradictions are caught at parse time.
        """
        lines = [
            f"# Canonical Scenario State (READ-ONLY, scenario_id={self.scenario_id})",
            f"Occupation: {self.occupation.value}",
            f"Deliverable: {self.deliverable_id} ({self.archetype}, {self.difficulty.value})",
            "",
            "## Entities",
        ]
        for e in self.entities:
            attrs = ", ".join(f"{k}={v}" for k, v in e.attrs.items())
            lines.append(f"- [{e.id}] {e.kind}: {e.name} ({attrs})")
        lines.append("\n## Timeline")
        for ev in sorted(self.timeline, key=lambda x: x.date):
            ents = ",".join(ev.entities)
            lines.append(f"- [{ev.id}] {ev.date.isoformat()}: {ev.description} ({ents})")
        lines.append("\n## Pinned Facts")
        for f in self.facts:
            unit = f" {f.unit}" if f.unit else ""
            src = f"  (src: {f.source})" if f.source else ""
            lines.append(f"- [{f.id}] {f.kind}: {f.value}{unit}{src}")
        lines.append("\n## Explicit Requirements (boss states these)")
        for r in self.explicit_requirements:
            lines.append(f"- {r}")
        lines.append("\n## Implicit Requirements (boss assumes you know these)")
        for r in self.implicit_requirements:
            lines.append(f"- {r}")
        return "\n".join(lines)
