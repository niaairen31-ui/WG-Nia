"""SQLModel table classes for the World Engine — package entry point
(TICKET-0028, BRIEF-0028-c: split of the former flat `models.py` into a
package by schema stratum).

Layout, by stratum:
    canon.py      — every table in canon_write_policy.txt's [CANON_TABLES],
                     plus GoalPrerequisite/EventEntity (canon-domain writes,
                     absent from [CANON_TABLES] by a known governance gap —
                     Nia's stratum escalation, 2026-07-15).
    ephemeral.py  — session/scene-lifetime tables.
    pipeline.py   — prompt/pipeline/approval machinery, plus User (app/
                     account infrastructure — Nia's stratum escalation).

This module re-exports the ENTIRE former public surface of the flat
`models.py` — every class, constant, and the two module functions
(`_uuid`, `_created_ts`) — so every existing `from .models import X` /
`from world_engine.models import X` in `src/` and `scripts/` resolves
unchanged. Import order (canon, ephemeral, pipeline) keeps table
registration on `SQLModel.metadata` deterministic; cross-stratum foreign
keys (string table-name references) resolve regardless of file order.
"""

from __future__ import annotations

from .canon import (
    BASE_SKILL_DOMAINS,
    Agenda,
    AgendaStep,
    Artifact,
    Character,
    DiscoverableDetail,
    Door,
    Entity,
    Event,
    EventEntity,
    Faction,
    FactionMembership,
    FactionRole,
    GoalAgendaLink,
    GoalPrerequisite,
    Item,
    Knowledge,
    Ledger,
    Location,
    LocationSubculture,
    NpcGoal,
    NpcPrice,
    Obstacle,
    ObstacleVertex,
    Relation,
    Skill,
    SkillDefinition,
    World,
    WorldLaw,
    _created_ts,
    _uuid,
)
from .ephemeral import (
    Conversation,
    ConversationMessage,
    Gathering,
    GatheringMember,
    Session,
    Visit,
)
from .pipeline import (
    Batch,
    PassPlay,
    ProposedMutation,
    PromptTemplate,
    PromptVariable,
    PromptVersion,
    User,
)

__all__ = [
    "World",
    "WorldLaw",
    "Entity",
    "Character",
    "NpcPrice",
    "Location",
    "LocationSubculture",
    "Obstacle",
    "ObstacleVertex",
    "Door",
    "Faction",
    "FactionRole",
    "FactionMembership",
    "Relation",
    "Knowledge",
    "NpcGoal",
    "GoalPrerequisite",
    "Ledger",
    "Session",
    "Batch",
    "PassPlay",
    "Gathering",
    "GatheringMember",
    "Conversation",
    "ConversationMessage",
    "ProposedMutation",
    "Event",
    "EventEntity",
    "Artifact",
    "Item",
    "SkillDefinition",
    "Skill",
    "DiscoverableDetail",
    "User",
    "PromptTemplate",
    "PromptVariable",
    "PromptVersion",
    "Visit",
    "Agenda",
    "AgendaStep",
    "GoalAgendaLink",
    "BASE_SKILL_DOMAINS",
]
