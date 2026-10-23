"""SQLModel table classes for the World Engine — package entry point
(TICKET-0028, BRIEF-0028-c: split of the former flat `models.py` into a
package by schema stratum).

Layout, by stratum:
    canon.py         — every table in canon_write_policy.txt's
                        [CANON_TABLES], plus GoalPrerequisite
                        (canon-domain writes, absent from [CANON_TABLES] by
                        a known governance gap — Nia's stratum escalation,
                        2026-07-15).
    canon_skill.py   — the skill domain (SkillSystem, SkillDefinition,
                        Skill, BASE_SKILL_DOMAINS), extracted from canon.py
                        at TICKET-0126 for the module_budget cap;
                        CreationRules (v2.32).
    canon_faction.py — faction extension tables (Faction, FactionRole,
                        FactionMembership), extracted from canon.py at
                        TICKET-0048 for the module_budget cap.
    canon_knowledge.py — perception extension tables (Relation, Knowledge),
                        extracted from canon.py at TICKET-0082, BRIEF-0082-a
                        for the module_budget cap. Fact/FactParticipant (the
                        knowledge anchor spine) added at BRIEF-0082-b.
                        FactDefault (scoped default knowledge level, G2a)
                        added at BRIEF-0082-c.
    canon_attribute.py — the state of the world (AttributeDefinition,
                        AttributeDefinitionType, AttributeChoice,
                        AttributeValue, AttributeChange; TICKET-0113,
                        schema v2.22), canon.
    canon_event.py   — the event journal's vocabulary and participants
                        (EventType, EventTypeRole, EventTypeRoleType,
                        EventTypeScope, EventSorte, EventParticipant;
                        TICKET-0114, schema v2.24; EventTypeEffect,
                        TICKET-0119, schema v2.26), canon.
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
    quests.py        — quest offers and accepted quests (QuestOffer,
                        QuestOfferStep, Quest;
                        TICKET-0108, schema v2.17), their terms and a
                        world's quest economy (QuestOfferTerm, QuestTerm,
                        QuestEconomy; TICKET-0109, v2.18), and debts
                        (Debt, DebtTerm; TICKET-0110, v2.19), canon.
    pc_drafts.py    — a player's character draft (PcDraft and its four child
                        tables; TICKET-0126, schema v2.32), non-canon, pending.

This module re-exports the ENTIRE former public surface of the flat
`models.py` — every class, constant, and the two module functions
(`_uuid`, `_created_ts`) — so every existing `from .models import X` /
`from world_engine.models import X` in `src/` and `scripts/` resolves
unchanged. Import order (canon, canon_skill, canon_faction, canon_knowledge,
canon_attribute, canon_event, config,
ephemeral, pipeline, observation, quests, pc_drafts) keeps table registration on
`SQLModel.metadata` deterministic;
cross-stratum foreign keys (string table-name references) resolve
regardless of file order.
"""

from __future__ import annotations

from .canon import (
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
    GoalAgendaLink,
    GoalPrerequisite,
    Item,
    ItemHolding,
    Ledger,
    Location,
    LocationTypeCatalog,
    NpcGoal,
    NpcPrice,
    Obstacle,
    ObstacleVertex,
    World,
    WorldLaw,
    _created_ts,
    _uuid,
)
from .canon_skill import (
    BASE_SKILL_DOMAINS,
    CREATION_CAP_COLUMNS,
    CREATION_CAP_RANKS,
    CREATION_COST_COLUMNS,
    CreationRules,
    Skill,
    SkillDefinition,
    SkillSystem,
)
from .canon_faction import (
    Faction,
    FactionMembership,
    FactionRole,
)
from .canon_knowledge import Fact, FactDefault, FactParticipant, Knowledge, Relation
from .canon_attribute import (
    ATTRIBUTE_CHANGE_KINDS,
    ATTRIBUTE_KINDS,
    ATTRIBUTE_STATUSES,
    ATTRIBUTE_TYPE_SIDES,
    AttributeChange,
    AttributeChoice,
    AttributeDefinition,
    AttributeDefinitionType,
    AttributeValue,
)
from .canon_event import (
    EVENT_DOMAINS,
    EVENT_EFFECT_MODES,
    EVENT_SCOPE_KINDS,
    EVENT_SCOPE_LEVELS,
    EVENT_VOCAB_STATUSES,
    EventParticipant,
    EventSorte,
    EventType,
    EventTypeRole,
    EventTypeEffect,
    EventTypeRoleType,
    EventTypeScope,
)
from .config import (
    CONDITION_OPS,
    CONDITION_ROLES,
    CONDITION_WINDOWS,
    AgendaStep,
    Condition,
    ConditionNode,
    ConditionNodeFilter,
    ConversationWindowConfig,
    SkillRank,
)
from .schedule import SCHEDULE_PHASES, NpcSchedule
from .ephemeral import (
    ENCOUNTER_SOURCES,
    Conversation,
    ConversationMessage,
    Gathering,
    GatheringMember,
    LinkBatch,
    LinkBatchRow,
    NpcBatch,
    NpcBatchRow,
    Passage,
    Rencontre,
    Session,
    Visit,
)
from .pipeline import (
    Batch,
    DayMentionChoice,
    DayMentionChoiceCandidate,
    DayMentionChoiceEvidence,
    DayMentionResolution,
    DayMentionReview,
    DayRewrite,
    LoreEntry,
    LoreEntryRow,
    LoreUsageEvent,
    ConditionDraft,
    CONDITION_DRAFT_OUTCOMES,
    QuestRequest,
    MutationReview,
    MutationReviewChange,
    PassPlay,
    ProposedMutation,
    REVIEW_ACTIONS,
    REVIEW_CHANGE_KINDS,
    REVIEW_STATUSES,
    REVIEW_VIAS,
    STEP_VERDICTS,
    PromptTemplate,
    PromptVariable,
    PromptVersion,
    SchemaMeta,
    SkillResolution,
    UnresolvedMention,
    User,
)
from .observation import (
    ObservationBeat,
    ObservationIntent,
    ObservationMutationLink,
    ObservationRun,
    ObservationRunTemplate,
)
from .quests import (
    DEBT_CURRENCIES,
    DEBT_ORIGINS,
    DEBT_STATUSES,
    QUEST_OFFER_STATUSES,
    QUEST_TERM_CURRENCIES,
    QUEST_TERM_DIRECTIONS,
    Quest,
    QuestEconomy,
    QuestOffer,
    QuestOfferStep,
    QuestOfferTerm,
    QuestTerm,
    Debt,
    DebtTerm,
)
from .pc_drafts import (
    PC_DRAFT_ORIGINS,
    PC_DRAFT_STATUSES,
    PC_KNOWLEDGE_LEVELS,
    PC_SKETCH_KINDS,
    PC_SKETCH_MAX,
    PcDraft,
    PcDraftKnowledge,
    PcDraftMembership,
    PcDraftSketch,
    PcDraftSkill,
)

__all__ = [
    "World",
    "WorldLaw",
    "Entity",
    "Character",
    "NpcPrice",
    "Location",
    "LocationTypeCatalog",
    "Obstacle",
    "ObstacleVertex",
    "Door",
    "Faction",
    "FactionRole",
    "FactionMembership",
    "Relation",
    "Knowledge",
    "Fact",
    "FactParticipant",
    "FactDefault",
    "AttributeDefinition",
    "AttributeDefinitionType",
    "AttributeChoice",
    "AttributeValue",
    "AttributeChange",
    "ATTRIBUTE_KINDS",
    "ATTRIBUTE_TYPE_SIDES",
    "ATTRIBUTE_STATUSES",
    "ATTRIBUTE_CHANGE_KINDS",
    "EventType",
    "EventTypeRole",
    "EventTypeRoleType",
    "EventTypeScope",
    "EventSorte",
    "EventParticipant",
    "EventTypeEffect",
    "EVENT_EFFECT_MODES",
    "EVENT_DOMAINS",
    "EVENT_SCOPE_KINDS",
    "EVENT_SCOPE_LEVELS",
    "EVENT_VOCAB_STATUSES",
    "NpcGoal",
    "GoalPrerequisite",
    "Ledger",
    "Session",
    "Batch",
    "PassPlay",
    "DayRewrite",
    "LoreEntry",
    "LoreEntryRow",
    "LoreUsageEvent",
    "ConditionDraft",
    "CONDITION_DRAFT_OUTCOMES",
    "QuestRequest",
    "DayMentionResolution",
    "SkillResolution",
    "Gathering",
    "GatheringMember",
    "LinkBatch",
    "LinkBatchRow",
    "NpcBatch",
    "NpcBatchRow",
    "Conversation",
    "ConversationMessage",
    "ProposedMutation",
    "MutationReview",
    "MutationReviewChange",
    "REVIEW_ACTIONS",
    "REVIEW_CHANGE_KINDS",
    "REVIEW_STATUSES",
    "REVIEW_VIAS",
    "STEP_VERDICTS",
    "Event",
    "Artifact",
    "Item",
    "ItemHolding",
    "SkillDefinition",
    "SkillSystem",
    "SkillRank",
    "Skill",
    "DiscoverableDetail",
    "User",
    "SchemaMeta",
    "PromptTemplate",
    "PromptVariable",
    "PromptVersion",
    "Visit",
    "Passage",
    "Rencontre",
    "ENCOUNTER_SOURCES",
    "UnresolvedMention",
    "Agenda",
    "AgendaStep",
    "Condition",
    "ConditionNode",
    "ConditionNodeFilter",
    "CONDITION_OPS",
    "CONDITION_WINDOWS",
    "CONDITION_ROLES",
    "QUEST_OFFER_STATUSES",
    "Quest",
    "QuestOffer",
    "QuestOfferStep",
    "QUEST_TERM_CURRENCIES",
    "QUEST_TERM_DIRECTIONS",
    "QuestEconomy",
    "QuestOfferTerm",
    "QuestTerm",
    "DEBT_CURRENCIES",
    "DEBT_ORIGINS",
    "DEBT_STATUSES",
    "Debt",
    "DebtTerm",
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
    "CreationRules",
    "CREATION_COST_COLUMNS",
    "CREATION_CAP_RANKS",
    "CREATION_CAP_COLUMNS",
    "PcDraft",
    "PcDraftSkill",
    "PcDraftSketch",
    "PcDraftMembership",
    "PcDraftKnowledge",
    "PC_DRAFT_STATUSES",
    "PC_DRAFT_ORIGINS",
    "PC_SKETCH_KINDS",
    "PC_KNOWLEDGE_LEVELS",
    "PC_SKETCH_MAX",
]
