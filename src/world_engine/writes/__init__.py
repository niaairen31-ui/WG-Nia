"""Shared canon-write primitives (TICKET-0028, BRIEF-0028-b — package split
of the former `writes.py`, by canon domain).

Both canon-write paths — the approval pipeline (`_apply_mutation` in
`cockpit/mutations.py`) and the author CRUD (`cockpit/crud/`) — call these
functions so that clamping and field validation live in exactly one place.
None of these functions commits; callers add the returned row to the
session (or, for `delete_world_cascade`, own the commit) themselves.

Layout, by canon domain:
    _shared.py        — closed helper set (R7): `_clamp`, `_append_history_snapshot`.
    relations.py       — `relation`: `write_relation`, `_find_relation_pair`
                          (structural), `_find_perceived_relation` (social),
                          `write_oriented_relations`, `set_target_knows`,
                          `lien_fact_of` (TICKET-0090, BRIEF-0090-a).
    knowledge.py        — `knowledge`: `write_knowledge` and the level ladder;
                          `apply_knowledge_patch`, `upsert_knowledge_row`
                          (TICKET-0091, BRIEF-0091-J).
    mentions.py         — `unresolved_mention` (non-canon worklist):
                          `record_unresolved`, `resolve_mention`,
                          `dismiss_mention` (TICKET-0091, BRIEF-0091-J);
                          `bind_mention` (BRIEF-0091-K).
    facts.py            — `fact`/`fact_participant`/`fact_default`:
                          `create_fact`, `attach_participants`
                          (TICKET-0082, BRIEF-0082-b), `create_fact_default`
                          (BRIEF-0082-c).
    facets.py           — the entity-fact writer: `add_entity_fact`,
                          `write_entity_facets`, `edit_entity_fact`,
                          `remove_entity_fact` over the fact chokepoint
                          (TICKET-0091, BRIEF-0091-E).
    characters.py       — `character`/`skill`/`ledger`: three unbaselined movers.
    factions.py         — `faction_membership`/`faction_role`.
    config.py           — the governed-config group (`npc_price`,
                          `world_law`, `obstacle`/`obstacle_vertex`).
    goals_agendas.py    — `npc_goal`/`goal_prerequisite`/`agenda`/
                          `agenda_step`/`goal_agenda_link`.
    events.py           — `event`.
    prompts.py          — `prompt_version`/`prompt_variable` (non-canon;
                          moved for module hygiene, not policy).
    pipeline.py         — `batch`/`pass_play` (TICKET-0075, BRIEF-0075-a).
    items.py            — `item_holding`: `write_holding` (TICKET-0109,
                          BRIEF-0109-A).
    quest_settlement.py — « déclarer accomplie »: `settle_quest`,
                          `settlement_refusals` (TICKET-0109, BRIEF-0109-C).
    debts.py            — `debt`/`debt_term`: `prepare_debt`, `write_debt`,
                          `create_debt`, `debt_refusals`, `settle_debt`,
                          `forgive_debt` (TICKET-0110, BRIEF-0110-B).
    debt_sources.py     — a service (`request_service`) and « régler à
                          crédit » (`credit_plan`, `settle_quest_on_credit`)
                          (TICKET-0110, BRIEF-0110-B).
    quest_terms.py      — `quest_offer_term`/`quest_term`/`quest_economy`:
                          `clean_terms`, `write_offer_terms`,
                          `copy_terms_to_quest`, `upsert_quest_economy`
                          (TICKET-0109, BRIEF-0109-B).
    quests.py           — `quest_offer`/`quest_offer_step`/`quest`:
                          `write_quest_offer`, `accept_quest`,
                          `abandon_quest` (TICKET-0108, BRIEF-0108-B).
    conditions.py       — `condition`/`condition_node`: `clean_leaf`,
                          `clean_condition`, `write_condition`,
                          `delete_offer_conditions` (TICKET-0111,
                          BRIEF-0111-C).
    worlds.py           — `delete_world_cascade` (the sole delete-side
                          helper, wildcard-allowed in canon_write_policy.txt).

This module re-exports the ENTIRE former public surface of the flat
`writes.py` — every import site elsewhere in the codebase
(`from ...writes import write_relation`, `from .writes import
_find_relation_pair`, etc.) is untouched, byte for byte, by this split.
"""

from __future__ import annotations

from ._shared import _append_history_snapshot, _clamp
from .characters import (
    SkillProgress, write_character_location, write_ledger_entry, write_skill_progress, write_skill_rank,
    write_skill_row,
)
from .config import (
    upsert_conversation_window_config,
    upsert_location_type,
    upsert_skill_rank,
    write_location_doors,
    write_location_obstacles,
    write_npc_prices,
    write_npc_schedule,
    write_world_laws,
)
from .events import write_event, write_event_update
from .facts import (
    attach_participants,
    create_fact,
    create_fact_default,
    update_typed_fact_content,
)
from .facets import (
    ScopeChoice,
    add_entity_fact,
    edit_entity_fact,
    facts_payload_keys,
    remove_entity_fact,
    write_entity_facets,
)
from .factions import (
    _validate_max_holders,
    active_role_counts,
    role_capacity_state,
    write_faction_role,
    write_membership,
)
from .goals_agendas import (
    NPC_GOAL_HORIZONS,
    NPC_GOAL_KINDS,
    NPC_GOAL_PREREQUISITE_TYPES,
    _AGENDA_GOAL_CASCADE_MAP,
    detach_goal_agenda_link,
    write_agenda,
    write_agenda_status,
    write_agenda_step,
    write_agenda_step_status,
    write_day_plan,
    write_goal_agenda_link,
    write_npc_goal,
    write_npc_goal_prerequisites,
    write_npc_goal_status,
)
from .knowledge import (
    KNOWLEDGE_LEVEL_LADDER,
    KNOWLEDGE_LEVELS,
    _append_knowledge_history,
    apply_knowledge_patch,
    cap_knowledge_level,
    knowledge_level_rank,
    upsert_knowledge_row,
    write_knowledge,
)
from .items import write_holding
from .mentions import bind_mention, dismiss_mention, record_unresolved, resolve_mention
from .quest_settlement import settle_quest, settlement_refusals
from .debts import DebtTermSpec, create_debt, debt_refusals, debt_terms, forgive_debt, settle_debt
from .debt_sources import credit_plan, request_service, settle_quest_on_credit
from .quest_terms import (
    FACT_REWARD_LEVELS,
    PERSONAL_CURRENCIES,
    TermSpec,
    clean_terms,
    offer_terms,
    quest_terms,
    upsert_quest_economy,
)
from .quests import (
    OPEN_QUEST_STATUSES,
    QUEST_GIVER_TYPES,
    abandon_quest,
    abandon_refusal,
    accept_quest,
    acceptance_refusal,
    offer_bindings,
    write_quest_offer,
)
from .conditions import clean_condition, clean_leaf, delete_offer_conditions, write_condition
from .pipeline import (
    BATCH_RESOLVED_STATUS,
    BATCH_STATUSES,
    MAX_DECLARATION_CHARS,
    PASS_PLAY_STATUSES,
    next_day_rewrite_generation,
    read_latest_feasibility,
    read_latest_resolution,
    resolution_count,
    write_batch,
    write_day_feasibility,
    write_day_mention_choices,
    write_day_mention_review,
    write_day_rewrite,
    write_pass_play,
    write_pass_play_resolution,
)
from .prompts import (
    _PLACEHOLDER_RE,
    PromptValidationError,
    write_prompt_variables,
    write_prompt_version,
)
from .relations import (
    _find_perceived_relation,
    _find_relation_pair,
    lien_fact_of,
    set_target_knows,
    write_oriented_relations,
    write_relation,
)
from .worlds import WorldDeleteRefused, delete_world_cascade

__all__ = [
    "write_relation",
    "write_knowledge",
    "create_fact",
    "create_fact_default",
    "attach_participants",
    "write_skill_rank",
    "write_skill_progress",
    "write_skill_row",
    "SkillProgress",
    "write_ledger_entry",
    "write_membership",
    "write_event",
    "write_prompt_version",
    "delete_world_cascade",
    "WorldDeleteRefused",
    "KNOWLEDGE_LEVELS",
    "KNOWLEDGE_LEVEL_LADDER",
    "knowledge_level_rank",
    "cap_knowledge_level",
    "PromptValidationError",
    "_append_knowledge_history",
]
