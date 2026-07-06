"""Shared canon-write primitives for `relation` and `knowledge`.

Both canon-write paths — the approval pipeline (`_apply_mutation` in
`cockpit/app.py`) and the author CRUD (`cockpit/crud.py`) — call these
functions so that clamping and field validation live in exactly one place.

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
from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, select

from .models import FactionMembership, Knowledge, Ledger, PromptTemplate, PromptVersion, Relation, Skill

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
        rel = db.exec(
            select(Relation).where(
                ((Relation.entity_a_id == entity_a_id) & (Relation.entity_b_id == entity_b_id))
                | ((Relation.entity_a_id == entity_b_id) & (Relation.entity_b_id == entity_a_id))
            )
        ).first()

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

    mode="open" (creator CRUD only):
        Inserts a new row (`world_id`, `entity_id`, `faction_id` required).
        Setting `is_primary=True` while another active primary exists for
        this `entity_id`, or opening a second active membership in the same
        faction, violates a partial unique index
        (`idx_membership_one_primary` / `idx_membership_unique_active`) —
        the resulting `IntegrityError` propagates to the caller, which must
        surface it as an error, never silently demote the existing row.

    mode="close" (creator CRUD only):
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
    "write_prompt_version",
    "delete_world_cascade",
    "KNOWLEDGE_LEVELS",
    "KNOWLEDGE_LEVEL_LADDER",
    "knowledge_level_rank",
    "cap_knowledge_level",
    "PromptValidationError",
    "_append_knowledge_history",
]
