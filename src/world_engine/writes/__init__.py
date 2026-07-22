"""Shared canon-write primitives (TICKET-0028, BRIEF-0028-b — package split
of the former `writes.py`, by canon domain).

Both canon-write paths — the approval pipeline (`_apply_mutation` in
`cockpit/mutations.py`) and the author CRUD (`cockpit/crud/`) — call these
functions so that clamping and field validation live in exactly one place.
None of these functions commits; callers add the returned row to the
session (or, for `delete_world_cascade`, own the commit) themselves.

Layout, by canon domain:
    _shared.py        — closed helper set (R7): `_clamp`, `_append_history_snapshot`.
    relations.py       — `relation`: `write_relation`, `_find_relation_pair`.
    knowledge.py        — `knowledge`: `write_knowledge` and the level ladder.
    characters.py       — `character`/`skill`/`ledger`: three unbaselined movers.
    factions.py         — `faction_membership`/`faction_role`.
    config.py           — the governed-config group (`npc_price`,
                          `location_subculture`, `world_law`, `obstacle`/
                          `obstacle_vertex`).
    goals_agendas.py    — `npc_goal`/`goal_prerequisite`/`agenda`/
                          `agenda_step`/`goal_agenda_link`.
    events.py           — `event`.
    prompts.py          — `prompt_version`/`prompt_variable` (non-canon;
                          moved for module hygiene, not policy).
    worlds.py           — `delete_world_cascade` (the sole delete-side
                          helper, wildcard-allowed in canon_write_policy.txt).

This module re-exports the ENTIRE former public surface of the flat
`writes.py` — every import site elsewhere in the codebase
(`from ...writes import write_relation`, `from .writes import
_find_relation_pair`, etc.) is untouched, byte for byte, by this split.
"""

from __future__ import annotations

from ._shared import _append_history_snapshot, _clamp
from .characters import write_character_location, write_ledger_entry, write_skill_tier
from .config import (
    upsert_location_type,
    write_location_doors,
    write_location_obstacles,
    write_location_subculture,
    write_npc_prices,
    write_world_laws,
)
from .events import write_event, write_event_update
from .factions import (
    _validate_max_holders,
    write_faction_role,
    write_membership,
)
from .goals_agendas import (
    NPC_GOAL_HORIZONS,
    NPC_GOAL_PREREQUISITE_TYPES,
    _AGENDA_GOAL_CASCADE_MAP,
    detach_goal_agenda_link,
    write_agenda,
    write_agenda_status,
    write_agenda_step,
    write_agenda_step_status,
    write_goal_agenda_link,
    write_npc_goal,
    write_npc_goal_prerequisites,
    write_npc_goal_status,
)
from .knowledge import (
    KNOWLEDGE_LEVEL_LADDER,
    KNOWLEDGE_LEVELS,
    _append_knowledge_history,
    cap_knowledge_level,
    knowledge_level_rank,
    write_knowledge,
)
from .prompts import (
    _PLACEHOLDER_RE,
    PromptValidationError,
    write_prompt_variables,
    write_prompt_version,
)
from .relations import _find_relation_pair, write_relation
from .worlds import delete_world_cascade

__all__ = [
    "write_relation",
    "write_knowledge",
    "write_skill_tier",
    "write_ledger_entry",
    "write_membership",
    "write_event",
    "write_prompt_version",
    "delete_world_cascade",
    "KNOWLEDGE_LEVELS",
    "KNOWLEDGE_LEVEL_LADDER",
    "knowledge_level_rank",
    "cap_knowledge_level",
    "PromptValidationError",
    "_append_knowledge_history",
]
