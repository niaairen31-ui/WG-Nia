"""Shared canon-write primitives for `relation` and `knowledge`.

Both canon-write paths — the approval pipeline (`_apply_mutation` in
`cockpit/app.py`) and the author CRUD (`cockpit/crud.py`) — call these
functions so that clamping and field validation live in exactly one place.

- `_find_relation_pair(db, a, b)`      : both-directions first-match search
  for a `relation` row (TICKET-0024, BRIEF-0024-b) — the single source of
  pair semantics, shared by `write_relation(mode="delta")` and, outside
  this module, `_apply_mutation`'s `goal_change complete` prerequisite
  judge and the per-NPC tick briefing's prerequisite resolution.
- `write_relation(mode="delta", ...)`  : gameplay consequence. Find/create the
  relation by (a, b) pair, apply a clamped intensity delta, append the
  previous state to `change_history`. Used by `_apply_mutation`.
- `write_relation(mode="set", ...)`    : author CRUD. Set intensity to an
  absolute value on a specific row (or create a new edge). Updating an
  existing row appends its previous state to `change_history` first
  (history is sacred on both write paths); creating a new edge starts with
  an empty `change_history`, same as `mode="delta"`.
- `write_knowledge(...)`               : insert or update a `knowledge` row.
  `knowledge_id=None` creates; otherwise updates that row in place, appending
  the previous state to `change_history` first (history is sacred on this
  path too — see `_append_knowledge_history`).
- `write_knowledge(mode="level_change", ...)` : `_apply_mutation`'s
  `knowledge_change` branch. Narrower than the default update: only
  `level`, `source` and `updated_at` change (the previous state is still
  appended to `change_history` first) — `content`, `is_incorrect`,
  `is_secret`, `share_threshold` and `subject` on the existing row are left
  untouched, unlike a default-mode update.
- `write_skill_tier(...)`               : set a `skill` row's tier,
  appending the previous tier to `change_history` first (history is sacred
  on this path too). The sole write shape for `skill` tier changes.
- `write_ledger_entry(...)`             : pure INSERT into the append-only
  `ledger` table (BRIEF-18). No UPDATE, no DELETE, ever — a correction is a
  new compensating line. The single chokepoint for ledger writes, shared by
  the creator CRUD and `_apply_mutation`'s `resource_change` branch
  (BRIEF-19) so the two paths cannot diverge.
- `write_membership(mode="open"/"close", ...)` : the only chokepoint for
  `faction_membership` writes (BRIEF-27). Creator CRUD only — no
  `_apply_mutation` branch exists for this table this step. INSERT-only /
  close-only: never updates `role` / `is_secret` / `faction_id` /
  `is_primary` of an existing row. A role or primary change is close + open
  a fresh row — the closed-row sequence IS the history, by construction
  (no `change_history` column on `faction_membership`).
- `write_npc_goal(...)`                 : insert an `active` `npc_goal` row
  (BRIEF-0013-a). `description` is immutable after insert — a "changed" goal
  is a closed goal plus a new row, never an edit.
- `write_npc_goal_status(...)`          : the only chokepoint for `npc_goal`
  status transitions (BRIEF-0013-a). Allowed transitions are exactly
  `active -> completed` and `active -> abandoned` — anything else (including
  reopening a closed goal) raises `ValueError`. Appends the previous state to
  `change_history` first (history is sacred).
- `write_agenda(...)`                   : insert an `active` `agenda` row
  (BRIEF-0018-a). A1 structural: `owner_entity_id` must resolve to an ACTIVE
  faction entity, else `ValueError`. The only constructor of `Agenda`.
- `write_agenda_step(...)`              : insert one `agenda_step` row
  (BRIEF-0018-a). The only constructor of `AgendaStep`.
- `write_agenda_step_status(...)`       : transition an `agenda_step`'s
  status (BRIEF-0018-a), appending the previous `{status, outcome,
  updated_at}` to `change_history` first — history is sacred.
- `write_agenda_status(...)`            : transition an `agenda`'s status
  (BRIEF-0018-a), same snapshot discipline.
- `write_faction_role(...)`             : the only chokepoint for
  `faction_role` writes (TICKET-0024, BRIEF-0024-d — corrective, replaces
  `write_faction_role_capacities`). `mode="create"` / `"update"` / `"rename"`
  / `"delete"`; case-duplicate names are the unique index's job (caught as
  `IntegrityError`, re-raised as `ValueError`); `mode="rename"` realigns
  every ACTIVE membership whose true `role` casefold-matches the old name
  (close + reopen, T1); `mode="delete"` (S1) is a hard delete, blocked while
  any active membership still holds the role. No `change_history` (curated
  config, same family as `faction_type` / `philosophy`).
- `write_npc_goal_prerequisites(...)`   : the only chokepoint for
  `npc_goal.prerequisites` writes (TICKET-0024, BRIEF-0024-a). Validates
  the v1 `relation_gte` shape, appends the previous state to
  `change_history` first.
- `delete_world_cascade(world_id, db)`  : the sole delete-side helper in
  this module, and the sole sanctioned exception to "History is sacred"
  (BRIEF-54). Hard-deletes every row scoped to a world, including the
  `world` row itself. Called only from the creator-direct
  `DELETE /api/worlds/{world_id}` route — never from `_apply_mutation`,
  never in response to an AI proposal. No other delete-side helper may be
  added to this module.

Callers add the returned row to the session (or, for `delete_world_cascade`,
own the commit); none of these functions commits.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, select

from .models import Agenda, AgendaStep, Character, Entity, Event, FactionMembership, FactionRole, GoalAgendaLink, Knowledge, Ledger, NpcGoal, NpcPrice, PromptTemplate, PromptVersion, Relation, Skill

# Simple-identifier placeholder, e.g. `{player_line}` — deliberately does not
# match JSON-example braces like `{"key": ...}` (TICKET-0011, C1).
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class PromptValidationError(ValueError):
    """C1 fail-closed placeholder validation failed (TICKET-0011).

    `offending` carries the placeholder names not in the head's declared
    `variables` list, for the caller to surface as a 422.
    """

    def __init__(self, offending: list[str]):
        self.offending = offending
        super().__init__(f"undeclared placeholder(s): {', '.join(offending)}")

# knowledge.level enum (world-engine-schema.md): unaware | rumor | suspicious |
# partial | knows | fully_understands.
KNOWLEDGE_LEVELS = frozenset(
    {"unaware", "rumor", "suspicious", "partial", "knows", "fully_understands"}
)

# Ordered ladder, lowest to highest. Shared by the analyzer (overhearing /
# direct-affirmation upgrade detection) and `_apply_mutation`'s monotone
# guard for `knowledge_change` — one source of truth for level ordering.
KNOWLEDGE_LEVEL_LADDER: tuple[str, ...] = (
    "unaware", "rumor", "suspicious", "partial", "knows", "fully_understands",
)


def knowledge_level_rank(level: Optional[str]) -> int:
    """Return `level`'s position on `KNOWLEDGE_LEVEL_LADDER`, or -1 if unrecognised.

    An unrecognised level ranks below 'unaware' so it can never satisfy a
    monotone "target > existing" check — invalid levels fail safe.
    """
    try:
        return KNOWLEDGE_LEVEL_LADDER.index(level)
    except ValueError:
        return -1


def cap_knowledge_level(level: str, cap: str = "knows") -> str:
    """Clamp `level` to at most `cap` on the ladder.

    Direct-affirmation rule: a target level is never granted above `cap`
    (default `knows`) by hearsay — `fully_understands` is creator CRUD only.
    """
    if knowledge_level_rank(level) > knowledge_level_rank(cap):
        return cap
    return level


def _clamp(value: int, lo: int = 1, hi: int = 100) -> int:
    return max(lo, min(hi, int(value)))


def _append_history_snapshot(rel: Relation, mutation_id: Optional[str] = None) -> None:
    """Append a snapshot of `rel`'s current state to its `change_history`.

    Shared by both `write_relation` modes — history is sacred on either
    write path (delta or set). `mutation_id` is None for author-CRUD edits
    (no `proposed_mutation` row is involved).
    """
    history = list(rel.change_history or [])
    history.append({
        "intensity": rel.intensity,
        "last_evolved_at": rel.last_evolved_at.isoformat() if rel.last_evolved_at else None,
        "mutation_id": mutation_id,
    })
    rel.change_history = history
    # flag_modified ensures SQLAlchemy detects the JSON list change
    # even though we replaced the object (not mutated it in place).
    sa_attrs.flag_modified(rel, "change_history")


def _append_knowledge_history(row: Knowledge, changed_by: str) -> None:
    """Append a snapshot of `row`'s PREVIOUS state to its `change_history`.

    Called before any overwrite of an existing `knowledge` row — history is
    sacred on every write path that updates `knowledge` (creator CRUD via
    `write_knowledge`; `knowledge_change` apply in `_apply_mutation`).
    `changed_by` is `"creator_crud"` or `"apply_mutation"`.
    """
    history = list(row.change_history or [])
    history.append({
        "level": row.level,
        "content": row.content,
        "source": row.source,
        "is_incorrect": row.is_incorrect,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "changed_by": changed_by,
        "changed_at": datetime.now(UTC).isoformat(),
    })
    row.change_history = history
    # flag_modified ensures SQLAlchemy detects the JSON list change
    # even though we replaced the object (not mutated it in place).
    sa_attrs.flag_modified(row, "change_history")


def _find_relation_pair(db: Session, entity_a_id: str, entity_b_id: str) -> Optional[Relation]:
    """Both-directions first-match search for a `relation` row between two
    entities — the single source of pair semantics (TICKET-0024,
    BRIEF-0024-b). Shared by `write_relation(mode="delta")` and
    `_apply_mutation`'s `goal_change complete` prerequisite judge / the
    per-NPC tick briefing, so the judge and the briefing can never
    disagree with the write path about which row is "the" relation for a
    pair. No UNIQUE constraint enforces a single row per pair in schema,
    so this takes the first match if several exist (same design choice as
    the write path)."""
    return db.exec(
        select(Relation).where(
            ((Relation.entity_a_id == entity_a_id) & (Relation.entity_b_id == entity_b_id))
            | ((Relation.entity_a_id == entity_b_id) & (Relation.entity_b_id == entity_a_id))
        )
    ).first()


def write_relation(
    db: Session,
    *,
    mode: str,
    relation_id: Optional[str] = None,
    world_id: Optional[str] = None,
    entity_a_id: Optional[str] = None,
    entity_b_id: Optional[str] = None,
    type: Optional[str] = None,
    value: int = 0,
    direction: str = "mutual",
    visible_to_b: bool = True,
    notes: Optional[str] = None,
    mutation_id: Optional[str] = None,
) -> Relation:
    """Write a `relation` row. Caller adds the row to the session.

    mode="delta" (gameplay consequence, `_apply_mutation`):
        Search both directions for an existing (entity_a_id, entity_b_id)
        pair; create one if none exists. `value` is an intensity delta,
        applied on top of the existing intensity (or 50 for a new relation),
        clamped to 1-100. The previous state is appended to
        `change_history` (history is sacred). `entity_a_id`, `entity_b_id`,
        `world_id` and `type` are required.

    mode="set" (author CRUD):
        `relation_id=None` creates a new edge with intensity = clamp(value)
        (`entity_a_id`, `entity_b_id`, `world_id`, `type` required); starts
        with an empty `change_history`, same as a new `mode="delta"` edge.
        `relation_id=<id>` updates that row in place: the previous state is
        appended to `change_history` first (history is sacred), then
        intensity is set to clamp(value); `type`, `direction`,
        `visible_to_b`, `notes` are overwritten.

    Clamp 1-100 is a backstop in both modes; CRUD callers should also
    validate the input range before calling this.
    """
    if mode not in ("delta", "set"):
        raise ValueError(f"write_relation: invalid mode {mode!r}")

    now = datetime.now(UTC)

    if mode == "delta":
        if not entity_a_id or not entity_b_id or not world_id or not type:
            raise ValueError(
                "write_relation(mode='delta'): entity_a_id, entity_b_id, "
                "world_id and type are required"
            )

        # Search in both directions; take first match if several types exist.
        # Design choice: no UNIQUE constraint in schema on (a, b) pair, so we
        # take the first match. A future version could match by type too.
        rel = _find_relation_pair(db, entity_a_id, entity_b_id)

        if rel is None:
            rel = Relation(
                world_id=world_id,
                entity_a_id=entity_a_id,
                entity_b_id=entity_b_id,
                type=type,
                direction=direction,
                intensity=_clamp(50 + value),
                visible_to_b=visible_to_b,
                notes=notes,
                change_history=[],
                created_at=now,
                last_evolved_at=now,
            )
        else:
            _append_history_snapshot(rel, mutation_id=mutation_id)
            rel.intensity = _clamp(rel.intensity + value)
            rel.last_evolved_at = now

        db.add(rel)
        return rel

    # mode == "set"
    if relation_id is not None:
        rel = db.get(Relation, relation_id)
        if rel is None:
            raise ValueError(f"write_relation(mode='set'): relation {relation_id!r} not found")
        _append_history_snapshot(rel, mutation_id=None)
        if type is not None:
            rel.type = type
        rel.direction = direction
        rel.visible_to_b = visible_to_b
        rel.notes = notes
        rel.intensity = _clamp(value)
        rel.last_evolved_at = now
    else:
        if not entity_a_id or not entity_b_id or not world_id or not type:
            raise ValueError(
                "write_relation(mode='set'): entity_a_id, entity_b_id, "
                "world_id and type are required to create a relation"
            )
        rel = Relation(
            world_id=world_id,
            entity_a_id=entity_a_id,
            entity_b_id=entity_b_id,
            type=type,
            direction=direction,
            intensity=_clamp(value),
            visible_to_b=visible_to_b,
            notes=notes,
            change_history=[],
            created_at=now,
            last_evolved_at=now,
        )

    db.add(rel)
    return rel


def write_character_location(
    db: Session,
    *,
    entity_id: str,
    to_location_id: str,
    mutation_id: Optional[str] = None,
) -> Character:
    """Write a character's `current_location_id` (TICKET-0015, BRIEF-0015-a).

    Caller adds no row itself but owns the transaction/commit — same
    convention as `write_relation`. `character` has no `change_history`
    column and the creator-CRUD location edit snapshots nothing; the
    `proposed_mutation` row (from/to payload, `tick_id`, `applied_at`) is the
    durable audit trail for this write (RECON-0015 F7), so `mutation_id` is
    accepted only for call-site symmetry and is not otherwise used here.
    """
    del mutation_id
    character = db.get(Character, entity_id)
    if character is None:
        raise ValueError(f"write_character_location: character {entity_id!r} not found")
    character.current_location_id = to_location_id
    db.add(character)
    return character


def write_knowledge(
    db: Session,
    *,
    mode: str = "update",
    knowledge_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    subject: Optional[str] = None,
    level: Optional[str] = None,
    content: Optional[Any] = None,
    source: Optional[Any] = None,
    is_incorrect: bool = False,
    is_secret: bool = False,
    share_threshold: int = 50,
    session_id: Optional[str] = None,
    changed_by: str = "creator_crud",
) -> Knowledge:
    """Insert or update a `knowledge` row. Caller adds the row to the session.

    mode="update" (default; creator CRUD and `_apply_mutation`'s
    `new_knowledge`/`resource_change` branches):
        `knowledge_id=None` inserts a new row (`entity_id`, `subject` and
        `level` required); `change_history` starts empty. Otherwise updates
        that row in place and bumps `updated_at` — the previous state is
        appended to `change_history` first (history is sacred), tagged with
        `changed_by` (`"creator_crud"` or `"apply_mutation"`).

        `level` falls back to "rumor" if missing or outside
        `KNOWLEDGE_LEVELS` — matching the analyzer's existing default for
        model output that doesn't name a recognised level (the local model
        is not always reliable here; see CLAUDE.md "Local model notes").
        `share_threshold` is clamped to 1-100 (the DB CHECK constraint
        requires this regardless of `is_secret` — share_threshold is simply
        ignored at read time when `is_secret` is true).

    mode="level_change" (`_apply_mutation`'s `knowledge_change` branch
    only): narrower than "update" — requires `knowledge_id` and `level`
    (the target level, used verbatim, no `KNOWLEDGE_LEVELS` fallback — the
    caller has already validated the monotone-ladder guard). Appends the
    previous state to `change_history` first, then sets only `level`,
    `source` (falls back to the row's existing `source` if not given, same
    as the pre-existing hand-rolled branch) and `updated_at`. `content`,
    `is_incorrect`, `is_secret`, `share_threshold` and `subject` on the
    existing row are left untouched.
    """
    if mode == "level_change":
        if knowledge_id is None:
            raise ValueError("write_knowledge(mode='level_change'): knowledge_id is required")
        k = db.get(Knowledge, knowledge_id)
        if k is None:
            raise ValueError(f"write_knowledge: knowledge {knowledge_id!r} not found")
        _append_knowledge_history(k, changed_by=changed_by)
        k.level = level
        k.source = str(source or k.source)
        k.updated_at = datetime.now(UTC)
        db.add(k)
        return k

    norm_level = level if level in KNOWLEDGE_LEVELS else "rumor"
    threshold = _clamp(share_threshold)

    if knowledge_id is not None:
        k = db.get(Knowledge, knowledge_id)
        if k is None:
            raise ValueError(f"write_knowledge: knowledge {knowledge_id!r} not found")
        _append_knowledge_history(k, changed_by=changed_by)
        if subject is not None:
            k.subject = subject
        k.level = norm_level
        k.content = content
        k.source = source
        k.is_incorrect = bool(is_incorrect)
        k.is_secret = bool(is_secret)
        k.share_threshold = threshold
        k.updated_at = datetime.now(UTC)
    else:
        if not entity_id:
            raise ValueError("write_knowledge: entity_id is required to create")
        k = Knowledge(
            entity_id=entity_id,
            subject=subject or "unknown",
            level=norm_level,
            content=content,
            source=source,
            is_incorrect=bool(is_incorrect),
            is_secret=bool(is_secret),
            share_threshold=threshold,
            session_id=session_id,
        )

    db.add(k)
    return k


def write_skill_tier(
    db: Session,
    *,
    skill_id: str,
    tier: int,
    changed_by: str = "creator",
) -> Skill:
    """Set a `skill` row's tier. Caller adds the row to the session.

    The sole write shape for `skill` tier changes (`cockpit/crud.py`'s
    `update_skill_tier` is its only caller). Appends the previous tier to
    `change_history` first (history is sacred), then sets `tier` and bumps
    `updated_at`. The caller decides whether to call this at all — a
    resubmission of the same tier should be a no-op, not an empty history
    entry.
    """
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise ValueError(f"write_skill_tier: skill {skill_id!r} not found")

    history = list(skill.change_history or [])
    history.append({
        "tier": skill.tier,
        "changed_at": datetime.now(UTC).isoformat(),
        "by": changed_by,
    })
    skill.change_history = history
    sa_attrs.flag_modified(skill, "change_history")
    skill.tier = tier
    skill.updated_at = datetime.now(UTC)

    db.add(skill)
    return skill


def write_ledger_entry(
    db: Session,
    *,
    world_id: str,
    entity_id: str,
    amount: int,
    counterparty_id: Optional[str] = None,
    reason: Optional[str] = None,
    source_type: str = "creator",
    conversation_id: Optional[str] = None,
    pass_play_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Ledger:
    """Insert one `ledger` row. Caller adds the row to the session.

    Pure INSERT: no balance read, no non-negative guard (that rule belongs to
    `_apply_mutation`'s `resource_change` branch, on the AI path — BRIEF-19),
    no UPDATE, no DELETE. This is the ONLY function that writes a `ledger`
    row — both sanctioned canon-write paths (creator CRUD, `_apply_mutation`)
    call it so they cannot diverge. `amount == 0` is rejected: a zero line is
    meaningless.
    """
    if amount == 0:
        raise ValueError("write_ledger_entry: amount must be nonzero")

    entry = Ledger(
        world_id=world_id,
        entity_id=entity_id,
        amount=amount,
        counterparty_id=counterparty_id,
        reason=reason,
        source_type=source_type,
        conversation_id=conversation_id,
        pass_play_id=pass_play_id,
        session_id=session_id,
    )
    db.add(entry)
    return entry


def write_membership(
    db: Session,
    *,
    mode: str,
    membership_id: Optional[str] = None,
    world_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    faction_id: Optional[str] = None,
    role: Optional[str] = None,
    cover_role: Optional[str] = None,
    is_primary: bool = False,
    is_secret: bool = False,
) -> FactionMembership:
    """Write a `faction_membership` row. Caller adds the row to the session.

    INSERT-only / close-only — there is no third mode. A role or
    primary-status change is never an in-place update on an existing row; it
    is `mode="close"` on the old row followed by a fresh `mode="open"` call
    (history is sacred; the closed-row sequence IS the history, by
    construction — no `change_history` column on this table).

    Modes are no longer "creator CRUD only" (schema v1.74, TICKET-0024):
    `_apply_mutation`'s `role_change` completion effect (BRIEF-0024-c) is
    the second sanctioned caller — it closes the subject's current
    membership and opens a fresh one with the new role, same close+reopen
    discipline, no third path.

    mode="open":
        Inserts a new row (`world_id`, `entity_id`, `faction_id` required).
        Setting `is_primary=True` while another active primary exists for
        this `entity_id`, or opening a second active membership in the same
        faction, violates a partial unique index
        (`idx_membership_one_primary` / `idx_membership_unique_active`) —
        the resulting `IntegrityError` propagates to the caller, which must
        surface it as an error, never silently demote the existing row.

    mode="close":
        Sets `left_at` on `membership_id`. Never touches `role` /
        `cover_role` / `is_secret` / `faction_id` / `is_primary`. Closing an
        already-closed row is a no-op (idempotent), not an error.

    `cover_role` (schema v1.41, BRIEF-30): the prompt-facing façade role,
    set at open time only. Like `role`, changing it on an existing
    membership is close + reopen — no in-place update.
    """
    if mode not in ("open", "close"):
        raise ValueError(f"write_membership: invalid mode {mode!r}")

    if mode == "open":
        if not world_id or not entity_id or not faction_id:
            raise ValueError(
                "write_membership(mode='open'): world_id, entity_id and "
                "faction_id are required"
            )
        membership = FactionMembership(
            world_id=world_id,
            entity_id=entity_id,
            faction_id=faction_id,
            role=role,
            cover_role=cover_role,
            is_primary=is_primary,
            is_secret=is_secret,
        )
        db.add(membership)
        return membership

    # mode == "close"
    if not membership_id:
        raise ValueError("write_membership(mode='close'): membership_id is required")
    membership = db.get(FactionMembership, membership_id)
    if membership is None:
        raise ValueError(f"write_membership(mode='close'): membership {membership_id!r} not found")
    if membership.left_at is None:
        membership.left_at = datetime.now(UTC)
        db.add(membership)
    return membership


# npc_goal.horizon enum (world-engine-schema.md v1.69): short | long.
NPC_GOAL_HORIZONS = frozenset({"short", "long"})

# npc_goal.prerequisites[].type enum (schema v1.74, TICKET-0024, G1). v1 is a
# single type; expand only at a second concrete case.
NPC_GOAL_PREREQUISITE_TYPES = frozenset({"relation_gte"})


def _validate_max_holders(max_holders: Optional[int]) -> None:
    if max_holders is not None and (
        not isinstance(max_holders, int) or isinstance(max_holders, bool) or max_holders < 1
    ):
        raise ValueError("write_faction_role: max_holders must be null or an int >= 1")


def write_faction_role(
    db: Session,
    *,
    mode: str,
    role_id: Optional[str] = None,
    world_id: Optional[str] = None,
    faction_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    max_holders: Optional[int] = None,
    position: Optional[int] = None,
    changed_by: str = "creator",
) -> Optional[FactionRole]:
    """Write a `faction_role` row (TICKET-0024, BRIEF-0024-d). Caller adds
    the row (or, for `mode="delete"`, owns the commit of the deletion).

    The sole chokepoint for `faction_role` writes — the CRUD routes and the
    `role_change` completion effect's L2 declare branch are the only
    callers. Case-duplicate names are the unique index's job
    (`idx_faction_role_name`, `faction_id` + `name COLLATE NOCASE`), never a
    code-side casefold check: a violating `db.flush()` raises
    `IntegrityError`, caught here and re-raised as a readable `ValueError`.

    mode="create":
        Inserts a new row (`world_id`, `faction_id`, non-empty `name`
        required). `max_holders` must be null or an int >= 1. `position`
        defaults to `max(position) + 1` for the faction when not given.

    mode="update":
        Updates `description` / `max_holders` / `position` on `role_id`.
        Never touches `name` — renames go through `mode="rename"` only.

    mode="rename" (T1):
        Updates `name` on `role_id`, then closes + reopens every ACTIVE
        membership of this faction whose true `role` casefold-equals the
        OLD name, preserving `cover_role`, `is_primary`, `is_secret`.
        Closed membership rows keep the old string untouched — history is
        never rewritten. `cover_role` strings are narrative masks and are
        NEVER realigned.

    mode="delete" (S1):
        Hard delete, blocked with `ValueError` if any active membership
        (casefold) still bears the role. No `change_history` snapshot: this
        table is curated config, not event canon — role-tenure history
        already lives in closed `faction_membership` rows.
    """
    if mode not in ("create", "update", "rename", "delete"):
        raise ValueError(f"write_faction_role: invalid mode {mode!r}")

    if mode == "create":
        if not world_id or not faction_id:
            raise ValueError(
                "write_faction_role(mode='create'): world_id and faction_id are required"
            )
        if not isinstance(name, str) or not name.strip():
            raise ValueError("write_faction_role(mode='create'): name must be a non-empty string")
        _validate_max_holders(max_holders)
        if position is None:
            current_max = db.exec(
                select(func.max(FactionRole.position)).where(FactionRole.faction_id == faction_id)
            ).first()
            position = (current_max or 0) + 1
        role = FactionRole(
            world_id=world_id, faction_id=faction_id, name=name.strip(),
            description=description, max_holders=max_holders, position=position,
            created_by=changed_by,
        )
        db.add(role)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(
                f"faction_role: a role named {name.strip()!r} already exists for this faction"
            ) from exc
        return role

    # mode in ("update", "rename", "delete") — role_id is required, row must exist.
    if not role_id:
        raise ValueError(f"write_faction_role(mode={mode!r}): role_id is required")
    role = db.get(FactionRole, role_id)
    if role is None:
        raise ValueError(f"write_faction_role(mode={mode!r}): role {role_id!r} not found")

    if mode == "update":
        # Always sets description/max_holders to whatever the caller sends
        # (the editor row carries full state, so None is meaningful:
        # description=None clears it, max_holders=None means unlimited).
        # position is set only when given — the dedicated reorder route is
        # the only caller that passes it.
        _validate_max_holders(max_holders)
        role.description = description
        role.max_holders = max_holders
        if position is not None:
            role.position = position
        db.add(role)
        return role

    if mode == "rename":
        if not isinstance(name, str) or not name.strip():
            raise ValueError("write_faction_role(mode='rename'): name must be a non-empty string")
        old_name = role.name
        role.name = name.strip()
        db.add(role)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(
                f"faction_role: a role named {name.strip()!r} already exists for this faction"
            ) from exc

        # T1 realignment: close + reopen every ACTIVE membership whose true
        # `role` casefold-matches the OLD name — triggered by this rename
        # (creator:rename), never touching closed rows or `cover_role`.
        holders = db.exec(
            select(FactionMembership).where(
                FactionMembership.faction_id == role.faction_id,
                FactionMembership.left_at.is_(None),
            )
        ).all()
        for m in holders:
            if (m.role or "").casefold() != old_name.casefold():
                continue
            write_membership(db, mode="close", membership_id=m.id)
            write_membership(
                db, mode="open", world_id=m.world_id, entity_id=m.entity_id,
                faction_id=m.faction_id, role=role.name, cover_role=m.cover_role,
                is_primary=m.is_primary, is_secret=m.is_secret,
            )
        return role

    # mode == "delete"
    holders = db.exec(
        select(FactionMembership).where(
            FactionMembership.faction_id == role.faction_id,
            FactionMembership.left_at.is_(None),
        )
    ).all()
    count = sum(1 for m in holders if (m.role or "").casefold() == role.name.casefold())
    if count > 0:
        raise ValueError(f"faction_role: {count} active member(s) still hold {role.name!r}")
    db.delete(role)
    return None


def write_npc_prices(
    db: Session,
    *,
    entity: Character,
    prices: dict[str, int],
    changed_by: str,
) -> list[NpcPrice]:
    """Full-replace `npc_price` rows for one NPC (TICKET-0025, BRIEF-0025-a
    — replaces `entity.metadata['price_list']`, BRIEF-20). Caller adds the
    returned rows to the session and commits.

    Deletes every existing `npc_price` row for `entity`, then inserts one
    row per `(tag, amount)` pair — the same read-merge-write CONTRACT the
    Tarifs editor already had, now backed by a relational full-replace
    instead of a JSON blob reassignment. Curated config (faction_role
    family): no `change_history`, hard delete of the prior rows is the
    sanctioned edit.
    """
    clean: list[tuple[str, int]] = []
    for tag, amount in prices.items():
        tag = str(tag).strip()
        if not tag:
            raise ValueError("write_npc_prices: tag must be a non-empty string")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise ValueError(f"write_npc_prices: amount for {tag!r} must be an int >= 0")
        clean.append((tag, amount))

    db.execute(text("DELETE FROM npc_price WHERE entity_id = :entity_id"), {"entity_id": entity.id})
    rows = [
        NpcPrice(world_id=entity.world_id, entity_id=entity.id, tag=tag, amount=amount)
        for tag, amount in clean
    ]
    for row in rows:
        db.add(row)
    return rows


def write_npc_goal_prerequisites(
    db: Session,
    *,
    goal: NpcGoal,
    prerequisites: Optional[list],
    changed_by: str,
) -> NpcGoal:
    """Set `npc_goal.prerequisites` (BRIEF-0024-a). Caller adds the row.

    v1 accepts ONLY `relation_gte` items: `{"type": "relation_gte",
    "target_entity_id": <entity id in the goal's own world>, "threshold":
    int 1-100}`. `None` or `[]` clears the gate — a completion with zero
    prerequisites is legitimate (A1). History is sacred: the previous state
    snapshots to `change_history` first. Reassigns the list — never mutates
    the existing one in place.
    """
    clean: Optional[list[dict]] = None
    if prerequisites:
        clean = []
        for item in prerequisites:
            item_type = item.get("type") if isinstance(item, dict) else None
            if item_type not in NPC_GOAL_PREREQUISITE_TYPES:
                raise ValueError(
                    f"write_npc_goal_prerequisites: unknown prerequisite type {item_type!r}"
                )
            target_entity_id = item.get("target_entity_id")
            target = db.get(Entity, target_entity_id) if target_entity_id else None
            if target is None or target.world_id != goal.world_id:
                raise ValueError(
                    f"write_npc_goal_prerequisites: unknown target entity {target_entity_id!r}"
                )
            threshold = item.get("threshold")
            if (
                not isinstance(threshold, int)
                or isinstance(threshold, bool)
                or not (1 <= threshold <= 100)
            ):
                raise ValueError(
                    f"write_npc_goal_prerequisites: threshold must be an int 1-100, got {threshold!r}"
                )
            clean.append({
                "type": "relation_gte",
                "target_entity_id": target_entity_id,
                "threshold": threshold,
            })

    history = list(goal.change_history or [])
    history.append({
        "prerequisites": goal.prerequisites,
        "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
        "changed_by": changed_by,
    })
    goal.change_history = history
    sa_attrs.flag_modified(goal, "change_history")
    goal.prerequisites = clean
    goal.updated_at = datetime.now(UTC)

    db.add(goal)
    return goal


def write_npc_goal(
    db: Session,
    *,
    world_id: str,
    npc_id: str,
    description: str,
    horizon: str,
    changed_by: str = "creator",
) -> NpcGoal:
    """Insert an `active` `npc_goal` row. Caller adds the row to the session.

    `description` is immutable after insert — a "changed" goal is a closed
    goal (`write_npc_goal_status`) plus a new row via this function, never an
    in-place edit. `change_history` starts empty on insert, matching
    `write_knowledge`'s idiom; `changed_by` is accepted for call-site
    symmetry with `write_npc_goal_status` but has nothing to attribute on a
    fresh row.
    """
    if horizon not in NPC_GOAL_HORIZONS:
        raise ValueError(f"write_npc_goal: invalid horizon {horizon!r}")

    goal = NpcGoal(
        world_id=world_id,
        npc_id=npc_id,
        description=description,
        horizon=horizon,
        status="active",
        change_history=[],
    )
    db.add(goal)
    return goal


def write_npc_goal_status(
    db: Session,
    *,
    goal: NpcGoal,
    new_status: str,
    changed_by: str,
    extra: Optional[dict] = None,
) -> NpcGoal:
    """Transition `goal.status`. Caller adds the row to the session.

    The ONLY chokepoint for `npc_goal` status transitions. Allowed
    transitions are exactly `active -> completed` and `active -> abandoned` —
    any other transition (including reopening a closed goal) raises
    `ValueError`: a revived goal is a NEW row via `write_npc_goal`, never a
    reopened one. Appends the previous state to `change_history` first
    (history is sacred), then sets `status` and bumps `updated_at`.

    `extra` (TICKET-0024, BRIEF-0024-c) merges additional keys into that
    SAME snapshot entry — e.g. `no_footprint: True` or `stripped: [...]`
    on a `complete` — rather than opening a second write path for
    completion-event metadata.
    """
    if goal.status != "active" or new_status not in ("completed", "abandoned"):
        raise ValueError(
            f"write_npc_goal_status: invalid transition {goal.status!r} -> {new_status!r}"
        )

    entry = {
        "status": goal.status,
        "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
        "changed_by": changed_by,
    }
    if extra:
        entry.update(extra)
    history = list(goal.change_history or [])
    history.append(entry)
    goal.change_history = history
    sa_attrs.flag_modified(goal, "change_history")
    goal.status = new_status
    goal.updated_at = datetime.now(UTC)

    db.add(goal)
    return goal


def write_agenda(
    db: Session,
    *,
    world_id: str,
    owner_entity_id: str,
    title: str,
    mutation_id: Optional[str] = None,
) -> Agenda:
    """Insert an `active` `agenda` row (TICKET-0018, BRIEF-0018-a; owner
    unlock TICKET-0020, BRIEF-0020-a).

    The ONLY constructor of `Agenda` in gameplay code — both sanctioned
    canon-write paths (`_apply_mutation`'s `agenda_creation` branch and the
    creator CRUD) call this. `owner_entity_id` must resolve to an ACTIVE
    `entity` of `type` in `{"faction", "character"}` in `world_id` —
    anything else (including a missing owner) raises `ValueError`. Faction
    owners keep their multi-agenda freedom, unchanged. A `character` owner
    may hold AT MOST ONE active agenda — the one-active-personal-agenda
    invariant, enforced here (the sole canon-write path) by an explicit
    existence check. Location owners stay rejected (A2/A3 deferred).
    `mutation_id` is accepted only for call-site symmetry with the other
    `_apply_mutation` writers and is not otherwise used here.
    """
    del mutation_id
    owner = db.get(Entity, owner_entity_id)
    if owner is None or owner.world_id != world_id:
        raise ValueError(f"write_agenda: owner {owner_entity_id!r} not found in world {world_id!r}")
    if owner.type not in ("faction", "character") or owner.status != "active":
        raise ValueError(f"write_agenda: owner {owner_entity_id!r} is not an active faction or character")
    if owner.type == "character":
        existing = db.exec(
            select(Agenda).where(
                Agenda.owner_entity_id == owner_entity_id,
                Agenda.status == "active",
            )
        ).first()
        if existing is not None:
            raise ValueError("write_agenda: character owner already holds an active agenda")

    agenda = Agenda(
        world_id=world_id,
        owner_entity_id=owner_entity_id,
        title=title,
        status="active",
        change_history=[],
    )
    db.add(agenda)
    return agenda


def write_agenda_step(
    db: Session,
    *,
    agenda_id: str,
    step_order: int,
    objective: str,
    visibility_trace: Optional[str] = None,
    status: str = "pending",
) -> AgendaStep:
    """Insert one `agenda_step` row (TICKET-0018, BRIEF-0018-a).

    The ONLY constructor of `AgendaStep` in gameplay code. `status="active"`
    is passed by the caller for exactly one step per agenda (the first, at
    creation time — the partial unique index enforces this structurally);
    every other step is created `pending`.
    """
    step = AgendaStep(
        agenda_id=agenda_id,
        step_order=step_order,
        objective=objective,
        visibility_trace=visibility_trace,
        status=status,
        change_history=[],
    )
    db.add(step)
    return step


def write_agenda_step_status(
    db: Session,
    *,
    step: AgendaStep,
    status: str,
    outcome: Optional[str] = None,
    mutation_id: Optional[str] = None,
    extra: Optional[dict] = None,
) -> AgendaStep:
    """Transition `step.status` (TICKET-0018, BRIEF-0018-a).

    Appends the previous `{status, outcome, updated_at}` to `change_history`
    BEFORE overwriting (`write_npc_goal_status` discipline) — history is
    sacred. Sets `outcome` only when provided, leaving any existing outcome
    untouched otherwise. `mutation_id` is accepted only for call-site
    symmetry with the other `_apply_mutation` writers and is not otherwise
    used here.

    `extra` (TICKET-0024, BRIEF-0024-c) merges additional keys into that
    SAME snapshot entry — e.g. `no_footprint: True` on a `complete` — same
    idiom as `write_npc_goal_status`.
    """
    del mutation_id
    entry = {
        "status": step.status,
        "outcome": step.outcome,
        "updated_at": step.updated_at.isoformat() if step.updated_at else None,
    }
    if extra:
        entry.update(extra)
    history = list(step.change_history or [])
    history.append(entry)
    step.change_history = history
    sa_attrs.flag_modified(step, "change_history")
    step.status = status
    if outcome is not None:
        step.outcome = outcome
    step.updated_at = datetime.now(UTC)

    db.add(step)
    return step


def write_goal_agenda_link(
    db: Session,
    *,
    world_id: str,
    goal_id: str,
    agenda_id: str,
    created_by: str,
    mutation_id: Optional[str] = None,
) -> GoalAgendaLink:
    """Insert an ACTIVE `goal_agenda_link` row (TICKET-0020, BRIEF-0020-a).

    The ONLY constructor of `GoalAgendaLink` in gameplay code. Validates:
    the goal exists, belongs to `world_id`, and is `active`; the agenda
    exists, belongs to `world_id`, and is `active`; no ACTIVE link already
    exists for this exact pair (explicit query — a clearer error than the
    partial-unique-index violation). `mutation_id` is accepted only for
    call-site symmetry with the other `_apply_mutation` writers and is not
    otherwise used here.
    """
    del mutation_id
    goal = db.get(NpcGoal, goal_id)
    if goal is None or goal.world_id != world_id:
        raise ValueError(f"write_goal_agenda_link: goal {goal_id!r} not found in world {world_id!r}")
    if goal.status != "active":
        raise ValueError(f"write_goal_agenda_link: goal {goal_id!r} is not active")

    agenda = db.get(Agenda, agenda_id)
    if agenda is None or agenda.world_id != world_id:
        raise ValueError(f"write_goal_agenda_link: agenda {agenda_id!r} not found in world {world_id!r}")
    if agenda.status != "active":
        raise ValueError(f"write_goal_agenda_link: agenda {agenda_id!r} is not active")

    existing = db.exec(
        select(GoalAgendaLink).where(
            GoalAgendaLink.goal_id == goal_id,
            GoalAgendaLink.agenda_id == agenda_id,
            GoalAgendaLink.detached_at.is_(None),
        )
    ).first()
    if existing is not None:
        raise ValueError("write_goal_agenda_link: an active link already exists for this goal/agenda pair")

    link = GoalAgendaLink(
        world_id=world_id,
        goal_id=goal_id,
        agenda_id=agenda_id,
        created_by=created_by,
    )
    db.add(link)
    return link


def detach_goal_agenda_link(
    db: Session,
    *,
    link: GoalAgendaLink,
    detached_by: str,
) -> GoalAgendaLink:
    """Soft-detach a `goal_agenda_link` row (TICKET-0020, BRIEF-0020-a).

    Sets `detached_at`/`detached_by`. Raises `ValueError` if already
    detached. There is NO delete helper — soft detach is the only exit; a
    detached pair may be re-attached via `write_goal_agenda_link` (the
    partial unique index allows it).
    """
    if link.detached_at is not None:
        raise ValueError("detach_goal_agenda_link: link is already detached")

    link.detached_at = datetime.now(UTC)
    link.detached_by = detached_by

    db.add(link)
    return link


# agenda status -> npc_goal status, cascade mapping (E2+M1, TICKET-0020,
# BRIEF-0020-a). The goal vocabulary has no 'failed' — both non-completed
# exits collapse to 'abandoned'.
_AGENDA_GOAL_CASCADE_MAP = {
    "completed": "completed",
    "failed": "abandoned",
    "abandoned": "abandoned",
}


def write_agenda_status(
    db: Session,
    *,
    agenda: Agenda,
    status: str,
    mutation_id: Optional[str] = None,
) -> Agenda:
    """Transition `agenda.status` (TICKET-0018, BRIEF-0018-a; cascade
    TICKET-0020, BRIEF-0020-a).

    Same snapshot discipline as `write_agenda_step_status`: appends the
    previous `{status, updated_at}` to `change_history` before overwriting.
    `mutation_id` is accepted only for call-site symmetry and is not
    otherwise used here.

    When the PREVIOUS status was `active` and `status` is one of
    `completed`/`failed`/`abandoned`, cascades onto every goal linked to
    this agenda (ACTIVE link, i.e. `detached_at IS NULL`): an `active` goal
    whose link to THIS agenda is its last still-active parent transitions
    via `write_npc_goal_status` (E2+M1 mapping); a goal with another active
    link to a still-active agenda survives (last-parent rule). Links are
    never detached by the cascade — the historical tie stays readable. Runs
    identically for tick-approved transitions and creator CRUD overrides
    (both route through this helper).
    """
    del mutation_id
    was_active = agenda.status == "active"
    history = list(agenda.change_history or [])
    history.append({
        "status": agenda.status,
        "updated_at": agenda.updated_at.isoformat() if agenda.updated_at else None,
    })
    agenda.change_history = history
    sa_attrs.flag_modified(agenda, "change_history")
    agenda.status = status
    agenda.updated_at = datetime.now(UTC)

    db.add(agenda)

    goal_status = _AGENDA_GOAL_CASCADE_MAP.get(status)
    if was_active and goal_status is not None:
        active_links = db.exec(
            select(GoalAgendaLink).where(
                GoalAgendaLink.agenda_id == agenda.id,
                GoalAgendaLink.detached_at.is_(None),
            )
        ).all()
        for link in active_links:
            goal = db.get(NpcGoal, link.goal_id)
            if goal is None or goal.status != "active":
                continue
            other_active_links = db.exec(
                select(GoalAgendaLink).where(
                    GoalAgendaLink.goal_id == goal.id,
                    GoalAgendaLink.agenda_id != agenda.id,
                    GoalAgendaLink.detached_at.is_(None),
                )
            ).all()
            has_other_active_parent = any(
                (other_agenda := db.get(Agenda, other.agenda_id)) is not None
                and other_agenda.status == "active"
                for other in other_active_links
            )
            if has_other_active_parent:
                continue
            write_npc_goal_status(
                db,
                goal=goal,
                new_status=goal_status,
                changed_by=f"cascade:agenda:{agenda.id}:{status}",
            )

    return agenda


def write_event(
    db: Session,
    *,
    world_id: str,
    title: str,
    description: Optional[str] = None,
    type: Optional[str] = None,
    knowledge_status: Optional[str] = None,
    involved_entities: Optional[list] = None,
    location_id: Optional[str] = None,
    mutation_id: Optional[str] = None,
) -> Event:
    """Insert one `event` row. Caller adds nothing else — this function
    calls `db.add`. The ONLY place `Event(` is constructed in gameplay code
    (TICKET-0017, BRIEF-0017-a): both producers — the scope-level tick call
    and the analyzer's dormant conversation-sourced channel — route through
    `_apply_mutation`'s `event_creation` branch, which calls this.

    `knowledge_status=None` lets the column's `server_default` 'secret'
    apply — the analyzer's minimal payload shape carries no status.
    `occurred_at` stays None (in-fiction time unknown); `recorded_at` is the
    row's own `_created_ts` default. `session_id`/`batch_id` stay None:
    neither a play-session artifact nor a pass-play batch — the mutation
    row's `tick_id`/`conversation_id` is the provenance anchor.
    `mutation_id` is accepted only for call-site symmetry with the other
    `_apply_mutation` writers (no `change_history` column on this table) and
    is not otherwise used here.
    """
    del mutation_id
    event = Event(
        world_id=world_id,
        title=title,
        description=description,
        type=type,
        involved_entities=involved_entities,
        location_id=location_id,
    )
    if knowledge_status is not None:
        event.knowledge_status = knowledge_status
    db.add(event)
    return event


def write_event_update(
    db: Session,
    *,
    event: Event,
    title: str,
    description: Optional[str] = None,
    type: Optional[str] = None,
    knowledge_status: str,
    involved_entities: Optional[list] = None,
    location_id: Optional[str] = None,
) -> Event:
    """Creator-CRUD-only writer for an existing `event` row (TICKET-0022,
    BRIEF-0022-a). `_apply_mutation` never calls this: AI proposals create
    events (`write_event`), never edit them. Together `write_event` and
    `write_event_update` are the complete set of `event` writers.

    Sets exactly the six fields listed above and calls `db.add`. Does NOT
    touch `recorded_at`, `occurred_at`, `has_magic_impact`, `consequences`,
    `session_id`, `batch_id` — those keep whatever they had. No
    `change_history` append: the table has no such column (see
    `write_event`'s docstring above) — a known, accepted gap, not an
    oversight.
    """
    event.title = title
    event.description = description
    event.type = type
    event.knowledge_status = knowledge_status
    event.involved_entities = involved_entities
    event.location_id = location_id
    db.add(event)
    return event


def write_prompt_version(
    db: Session,
    *,
    template_id: str,
    system_prompt: str,
    user_template: str,
    note: Optional[str] = None,
) -> PromptVersion:
    """Append a new `prompt_version` row for `template_id`. Caller adds nothing
    else — this function itself calls `db.add`.

    The ONLY function that writes a `prompt_version` row (TICKET-0011, single
    write shape): the PATCH text route, the restore route, and the seed's
    v1-on-virgin-head path all call this so they cannot diverge.

    C1 fail-closed validation: every `{identifier}` placeholder found in
    EITHER field must be in the head's declared `variables` list
    (`variables` NULL/empty -> any identifier placeholder is rejected). On
    failure raises `PromptValidationError` carrying the offending names;
    nothing is written. JSON-example braces (`{"key": ...}`) don't match the
    identifier pattern and pass freely.

    `version_number` = MAX(existing) + 1 for this head (1 if none exist —
    the migration's own v1 backfill and the seed's virgin-head path both
    reach this branch). Bumps `head.updated_at`.
    """
    head = db.get(PromptTemplate, template_id)
    if head is None:
        raise ValueError(f"write_prompt_version: prompt_template {template_id!r} not found")

    declared = set(head.variables) if head.variables else set()
    found = set(_PLACEHOLDER_RE.findall(system_prompt)) | set(_PLACEHOLDER_RE.findall(user_template))
    offending = sorted(found - declared)
    if offending:
        raise PromptValidationError(offending)

    current_max = db.exec(
        select(func.max(PromptVersion.version_number)).where(
            PromptVersion.prompt_template_id == template_id
        )
    ).one()
    next_number = (current_max or 0) + 1

    version = PromptVersion(
        prompt_template_id=template_id,
        version_number=next_number,
        system_prompt=system_prompt,
        user_template=user_template,
        note=note,
    )
    db.add(version)
    head.updated_at = datetime.now(UTC)
    db.add(head)
    return version


# DOCUMENTED EXCEPTION to "History is sacred": delete_world_cascade is the only
# helper in the codebase that hard-deletes canon. It exists solely for whole-
# world block deletion (creator authority, irreversible). No other delete-side
# helper may be added here; History is sacred holds everywhere else.
def delete_world_cascade(world_id: str, db: Session) -> None:
    """Hard-delete every row scoped to `world_id`, including the `world` row
    itself. Caller owns the transaction and the commit (BRIEF-54).

    Sets `PRAGMA defer_foreign_keys = ON` on the session connection before
    any DELETE, so the self-referential columns
    (`location.parent_location_id`, `faction.parent_faction_id`,
    `character.current_location_id`) resolve without nulling — the deferral
    is per-transaction and resets after commit/rollback.

    Statement order below is NOT arbitrary despite the FK deferral: several
    deletes are correlated subqueries against `entity`/`conversation`/
    `gathering`/`session` (e.g. `knowledge` via `entity_id IN (SELECT id FROM
    entity WHERE world_id = :wid)`) — those must run while the referenced
    parent rows still exist, or the subquery returns nothing and orphans get
    left behind. So every subquery-based delete runs before its parent table
    is cleared; only the direct `world_id`-scoped deletes (no subquery) are
    free to run in any order relative to each other, per the FK deferral.

    Never touches `prompt_template` rows with `world_id IS NULL` (the global
    seeds shared by every world) or the `user` table (global accounts, no
    world scope).
    """
    db.execute(text("PRAGMA defer_foreign_keys = ON"))
    params = {"wid": world_id}

    # Subquery-based deletes — run first, while their parent rows still exist.
    db.execute(
        text("DELETE FROM conversation_message WHERE conversation_id IN "
             "(SELECT id FROM conversation WHERE world_id = :wid)"),
        params,
    )
    db.execute(
        text("DELETE FROM gathering_member WHERE gathering_id IN "
             "(SELECT id FROM gathering WHERE world_id = :wid)"),
        params,
    )
    db.execute(
        text("DELETE FROM batch WHERE session_id IN "
             "(SELECT id FROM session WHERE world_id = :wid)"),
        params,
    )
    db.execute(
        text("DELETE FROM pass_play WHERE session_id IN "
             "(SELECT id FROM session WHERE world_id = :wid)"),
        params,
    )
    db.execute(
        text("DELETE FROM knowledge WHERE entity_id IN "
             "(SELECT id FROM entity WHERE world_id = :wid)"),
        params,
    )
    db.execute(
        text("DELETE FROM skill WHERE character_id IN "
             "(SELECT id FROM entity WHERE world_id = :wid)"),
        params,
    )
    db.execute(
        text("DELETE FROM location WHERE id IN "
             "(SELECT id FROM entity WHERE world_id = :wid)"),
        params,
    )
    db.execute(
        text("DELETE FROM faction WHERE id IN "
             "(SELECT id FROM entity WHERE world_id = :wid)"),
        params,
    )
    db.execute(
        text("DELETE FROM artifact WHERE id IN "
             "(SELECT id FROM entity WHERE world_id = :wid)"),
        params,
    )
    db.execute(
        text("DELETE FROM item WHERE id IN "
             "(SELECT id FROM entity WHERE world_id = :wid)"),
        params,
    )

    # Direct world_id-scoped deletes — order free under the FK deferral.
    # `skill_definition` (BRIEF-55, schema v1.63) must still come after the
    # subquery-based `skill` delete above so no `skill.skill_definition_id`
    # is left pointing at a missing row by commit time (RESTRICT, deferred).
    for table in (
        "faction_membership", "relation", "character", "discoverable_detail",
        "proposed_mutation", "ledger", "event", "gathering", "conversation",
        "session", "skill_definition", "entity",
    ):
        db.execute(text(f"DELETE FROM {table} WHERE world_id = :wid"), params)

    # Global prompt-template seeds (world_id IS NULL) are never touched.
    db.execute(text("DELETE FROM prompt_template WHERE world_id = :wid"), params)

    # The world row itself, last.
    db.execute(text("DELETE FROM world WHERE id = :wid"), params)


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
