"""Author CRUD — direct canonical writes for creator-mode world editing.

This is the **author's** master tool: a second canonical write path,
alongside the approval pipeline (`_apply_mutation` in
`cockpit/routes/mutations.py`). It is deliberately a *direct* write with no
`proposed_mutation` checkpoint — that checkpoint exists to contain the local
model's drift during play, not to gate the creator, who is the authority
over world state.

Package split from a single `crud.py` (TICKET-0027, BRIEF-0027-d, R5): one
domain module per concern (`entities`, `relations`, `knowledge`, `goals`,
`agendas`, `events`, `factions`, `skills`, `locations`, `ledger`,
`prompts`), all decorating the single shared `router` (`_router.py`). This
`__init__.py` is a re-export surface only — no logic lives here — so every
existing call site (`from . import crud as _crud`, `_crud.<name>`) keeps
working unchanged.

Scope (see Claude Code Brief — Author CRUD):
- Composite editors for `character`, `faction`, `location` (entity + its
  extension row, written transactionally).
- In-context `relation` / `knowledge` row editors, reached from an entity's
  sheet.
- `relation_change`/`new_knowledge` write rules are shared with
  `_apply_mutation` via `..writes.write_relation` / `..writes.write_knowledge`
  so the two paths cannot diverge.

Deletion policy:
- Entities: **soft delete** (`entity.status = 'inactive'`) — reversible,
  relations/knowledge pointing at it survive.
- `relation` / `knowledge` rows: **hard delete** — they are edges/facts the
  author poses and must be able to remove cleanly.
- `ledger` rows: **append-only, no delete, no update, ever** (schema v1.31,
  BRIEF-18) — a deliberate divergence from the policy above. A mistake is
  corrected with a new compensating line (`source_type='correction'`), never
  by editing or deleting an existing row. `write_ledger_entry` (`..writes`)
  is the single chokepoint; this package's `POST /api/ledger` is one of only
  two sanctioned canon-write paths into `ledger` (the other is
  `_apply_mutation`'s `resource_change` branch, BRIEF-19, which reuses the
  same helper).
- `event` rows: **no delete, ever** (TICKET-0022, C3) — an event either
  happened or did not; `event` is history. Retraction is
  `knowledge_status = 'secret'`, which structurally excludes the row from
  all four readers (`context.py`, `tick.py` x2, the play routes' return-visit
  delta). Mirrors `ledger`'s append-only policy above.

Author edits to `relation` are state-setting, not delta accumulation —
but still append the previous state to `change_history` first (history is
sacred on both write paths; see `writes.write_relation(mode="set")`).
Author edits pass through **no** `proposed_mutation` (decision 1).

Creator-mode-only: this router is mounted on the cockpit app, which is the
creator's tool (bound to 127.0.0.1, no auth, "creator review dashboard").
The player-facing app is a separate, not-yet-built surface; nothing here is
linked or routed from it.

Type -> extension registry (`ENTITY_TYPE_REGISTRY`): adding a future type
(e.g. `artifact`) is one registry entry — the composite form, validation and
serialization are all driven from here.
"""
from __future__ import annotations

from ._router import router

from .entities import (
    ENTITY_BASE_FIELDS,
    ENTITY_STATUSES,
    ENTITY_TYPE_REGISTRY,
    EntityWriteBody,
    LocationSubcultureBody,
    NpcPricesBody,
    _apply_base_fields,
    _build_extension_kwargs,
    _coerce_field,
    _create_entity_core,
    _entity_dict,
    _entity_summary,
    _extension_dict,
    _get_entity,
    _iso,
    _link_entity_creation,
    _location_subculture_rows,
    _npc_prices_dict,
    _player_character_id,
    _validate_entity_ref,
    _world_id,
    create_entity,
    delete_entity,
    get_entity,
    get_entity_types,
    list_entities,
    list_entity_items,
    set_location_subculture,
    set_npc_prices,
    update_entity,
)
from .relations import (
    RELATION_DIRECTIONS,
    RELATION_FIELDS,
    RELATION_TYPES,
    RelationWriteBody,
    _RELATION_GRAPH_EXCLUDED_TYPES,
    _list_relations,
    _relation_dict,
    create_relation,
    delete_relation,
    get_character_relation_graph,
    list_entity_relations,
    update_relation,
)
from .knowledge import (
    KNOWLEDGE_FIELDS,
    KNOWLEDGE_LEVELS_ORDERED,
    KnowledgeWriteBody,
    _create_knowledge_core,
    _knowledge_dict,
    _list_knowledge,
    create_knowledge,
    delete_knowledge,
    list_entity_knowledge,
    update_knowledge,
)
from .goals import (
    GoalAgendaLinkCreateBody,
    GoalBackfillBody,
    GoalPrerequisitesBody,
    GoalStatusBody,
    GoalWriteBody,
    _goal_dict,
    _goal_links,
    _goal_prerequisites_dict,
    _list_goals,
    _npc_faction_goals,
    backfill_npc_goals,
    create_goal,
    create_goal_agenda_link,
    detach_goal_agenda_link_route,
    list_entity_goals,
    set_goal_prerequisites,
    set_goal_status,
)
from .agendas import (
    AgendaCreateBody,
    AgendaStatusBody,
    AgendaStepCreateBody,
    AgendaStepPatchBody,
    _agenda_dict,
    _agenda_linked_goals,
    _agenda_step_dict,
    create_agenda,
    list_agendas,
    update_agenda_status,
    update_agenda_step,
)
from .events import (
    EVENT_FIELDS,
    EVENT_KNOWLEDGE_STATUSES,
    EVENT_TYPE_LABELS_FR,
    EventCreateBody,
    EventUpdateBody,
    _event_dict,
    _validate_event_involved,
    _validate_event_location,
    create_event,
    get_event,
    list_events,
    update_event,
)
from .factions import (
    FactionRoleCreateBody,
    FactionRoleReorderBody,
    FactionRoleUpdateBody,
    MembershipOpenBody,
    _active_role_counts,
    _faction_role_dict,
    _membership_dict,
    _open_membership_core,
    close_entity_membership,
    create_faction_role,
    delete_faction_role,
    get_faction_roster,
    list_entity_memberships,
    list_faction_role_rows,
    list_faction_roles,
    open_entity_membership,
    reorder_faction_roles,
    update_faction_role,
)
from .skills import (
    SKILL_DOMAINS,
    SKILL_TIERS,
    SkillDefinitionWriteBody,
    SkillTierBody,
    _skill_definition_dict,
    _skill_dict,
    create_skill_definition,
    delete_skill_definition,
    list_skill_definitions,
    list_skill_player_characters,
    list_skills,
    update_skill_definition,
    update_skill_tier,
)
from .locations import (
    ACCESS_LEVELS,
    DiscoverableDetailBody,
    DiscoverableDetailPatchBody,
    _detail_dict,
    create_discoverable_detail,
    delete_discoverable_detail,
    get_locations_graph,
    list_discoverable_details,
    list_locations,
    update_discoverable_detail,
)
from .ledger import (
    LEDGER_SOURCE_TYPES_CREATOR,
    LedgerWriteBody,
    _ledger_dict,
    create_ledger_entry,
    get_entity_ledger,
    get_ledger_journal,
)
from .prompts import (
    PromptModelBody,
    PromptTextBody,
    _effective_prompt_row,
    _prompt_row_summary,
    _version_summary,
    get_prompt_detail,
    get_prompt_version,
    list_ollama_models,
    list_prompt_versions,
    list_prompts,
    restore_prompt_version,
    update_prompt_model,
    update_prompt_text,
)

__all__ = ["router", "ENTITY_TYPE_REGISTRY"]
