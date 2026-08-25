"""SQLModel table classes for the World Engine — package entry point
(TICKET-0028, BRIEF-0028-c: split of the former flat `models.py` into a
package by schema stratum).

Layout, by stratum:
    canon.py         — every table in canon_write_policy.txt's
                        [CANON_TABLES], plus GoalPrerequisite/EventEntity
                        (canon-domain writes, absent from [CANON_TABLES] by
                        a known governance gap — Nia's stratum escalation,
                        2026-07-15).
    canon_faction.py — faction extension tables (Faction, FactionRole,
                        FactionMembership), extracted from canon.py at
                        TICKET-0048 for the module_budget cap.
    config.py        — canon curated-config tables too new/small to justify
                        growing canon.py at its module_budget cap
                        (ConversationWindowConfig, TICKET-0050).
    ephemeral.py     — session/scene-lifetime tables.
    pipeline.py      — prompt/pipeline/approval machinery, plus User (app/
                        account infrastructure — Nia's stratum escalation)
                        and SchemaMeta (static-plane schema version,
                        migration-only).
    observation.py   — observed-scene instrumentation (ObservationRun and
                        friends, TICKET-0051); telemetry, never canon —
                        absent from canon_write_policy.txt's [CANON_TABLES].

This module re-exports the ENTIRE former public surface of the flat
`models.py` — every class, constant, and the two module functions
(`_uuid`, `_created_ts`) — so every existing `from .models import X` /
`from world_engine.models import X` in `src/` and `scripts/` resolves
unchanged. Import order (canon, canon_faction, config, ephemeral, pipeline,
observation) keeps table registration on `SQLModel.metadata` deterministic;
cross-stratum foreign keys (string table-name references) resolve
regardless of file order.
"""

from __future__ import annotations

from .canon import (
    BASE_SKILL_DOMAINS,
    Agenda,
    Artifact,
    Character,
    DiscoverableDetail,
    Door,
    Entity,
    EntityTrait,
    EntityType,
    EntityTypeHistory,
    Event,
    EventEntity,
    GoalAgendaLink,
    GoalPrerequisite,
    Item,
    Knowledge,
    Ledger,
    Location,
    LocationSubculture,
    LocationTypeCatalog,
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
from .canon_faction import (
    Faction,
    FactionMembership,
    FactionRole,
)
from .config import AgendaStep, AgendaStepRequirement, ConversationWindowConfig
from .schedule import SCHEDULE_PHASES, NpcSchedule
from .ephemeral import (
    Conversation,
    ConversationMessage,
    Gathering,
    GatheringMember,
    LinkBatch,
    LinkBatchRow,
    NpcBatch,
    NpcBatchRow,
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
    SchemaMeta,
    User,
)
from .observation import (
    ObservationBeat,
    ObservationIntent,
    ObservationMutationLink,
    ObservationRun,
    ObservationRunTemplate,
)

__all__ = [
    "World",
    "WorldLaw",
    "Entity",
    "Character",
    "NpcPrice",
    "Location",
    "LocationSubculture",
    "LocationTypeCatalog",
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
    "LinkBatch",
    "LinkBatchRow",
    "NpcBatch",
    "NpcBatchRow",
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
    "SchemaMeta",
    "PromptTemplate",
    "PromptVariable",
    "PromptVersion",
    "Visit",
    "Agenda",
    "AgendaStep",
    "AgendaStepRequirement",
    "GoalAgendaLink",
    "EntityType",
    "EntityTypeHistory",
    "EntityTrait",
    "BASE_SKILL_DOMAINS",
    "ConversationWindowConfig",
    "SCHEDULE_PHASES",
    "NpcSchedule",
    "ObservationRun",
    "ObservationRunTemplate",
    "ObservationBeat",
    "ObservationIntent",
    "ObservationMutationLink",
]
