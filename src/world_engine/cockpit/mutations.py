"""Per-mutation-type canon appliers (TICKET-0027, BRIEF-0027-c).

Decomposition of `_apply_mutation` (formerly 682 lines, one `elif` branch
per type, `cockpit/app.py`). `_apply_mutation` itself is a thin dispatcher
in `cockpit/routes/mutations.py` (BRIEF-0027-d): duplicate guard, payload
extraction, then one call into a `_mutation_apply_<type>()` function here
per `mutation_type`. Pure move — no write reordering, no validation change,
every DB write still flows through the same `writes.py` helpers as before.

Imported lazily by `routes/mutations.py` (inside `_apply_mutation`'s body)
to avoid a circular import — this module imports
`from .routes import mutations as _routes_mutations` at module level to
reach helpers that live there because they are used elsewhere too
(`_normalize_goal_text` by `_find_applied_duplicate`, `_append_note` by
`approve_mutation`/`batch_review_mutations`), same pattern as
`cockpit/play.py`.

Sanctioned canon-write site (relocated from the single `_apply_mutation`
entry in `canon_write_policy.txt`, TICKET-0027 stage c — see that file's
comment at the relocated entries): the direct (non-`writes.py`) writes
formerly inside `_apply_mutation` — `entity` (status_change), `item`
(item_update), `discoverable_detail` (new_knowledge's discovery flip) — now
live in their own named functions below.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from sqlmodel import Session, select

from ..gathering import close_open_memberships
from ..ledger import get_balance as _get_balance
from ..models import (
    Agenda,
    AgendaStep,
    Character,
    Conversation,
    DiscoverableDetail,
    Entity,
    Faction,
    FactionMembership,
    FactionRole,
    GoalPrerequisite,
    Item,
    Knowledge,
    NpcGoal,
    ProposedMutation,
)
from ..writes import (
    _find_relation_pair,
    knowledge_level_rank,
    write_agenda,
    write_agenda_status,
    write_agenda_step,
    write_agenda_step_status,
    write_character_location,
    write_event,
    write_faction_role,
    write_goal_agenda_link,
    write_knowledge,
    write_ledger_entry,
    write_membership,
    write_npc_goal,
    write_npc_goal_status,
    write_relation,
)
from .routes import mutations as _routes_mutations


def _knowledge_leg_already_applied(
    db: Session,
    conversation_id: str,
    entity_id: str,
    subject: str,
) -> bool:
    """True if an equivalent knowledge acquisition was already applied for this
    conversation — scanning BOTH applied `new_knowledge` rows (payload
    `entity_id`+`subject`) AND applied `resource_change` knowledge legs
    (payload `knowledge.entity_id`+`knowledge.subject`). Part of the
    resource_change knowledge-leg block-whole guard (4c, BRIEF-19).

    KNOWN ACCEPTED GAP, one-directional by design: this guard protects a
    resource_change knowledge leg from colliding with a prior new_knowledge
    or resource_change row, but the new_knowledge branch's own
    `_find_applied_duplicate` (routes/mutations.py) is deliberately NOT extended to scan
    resource_change knowledge legs. Do not touch that guard to close this —
    see ARCHITECTURE_DECISIONS.md "Deferred decisions".
    """
    rows = db.exec(
        select(ProposedMutation).where(
            ProposedMutation.conversation_id == conversation_id,
            ProposedMutation.status == "applied",
            ProposedMutation.mutation_type.in_(("new_knowledge", "resource_change")),
        )
    ).all()
    for row in rows:
        p = row.payload if isinstance(row.payload, dict) else {}
        if row.mutation_type == "new_knowledge":
            if p.get("entity_id") == entity_id and p.get("subject") == subject:
                return True
        else:
            k = p.get("knowledge")
            if isinstance(k, dict) and k.get("entity_id") == entity_id and k.get("subject") == subject:
                return True
    return False


# ── Completion effects (TICKET-0024, BRIEF-0024-c) ─────────────────────────
# Closed vocabulary shared by `goal_change complete` and
# `agenda_step_change complete` — B1: one effect type per concrete named
# case, expand only at a second concrete case.

_EFFECT_TYPES = frozenset({"relation_delta", "ledger_transfer", "role_change"})
_MAX_EFFECTS = 3


def _h1_strip_satisfied_prerequisite_deltas(
    goal: NpcGoal, effects: list, db: Session
) -> tuple[list, list[str]]:
    # H1 (TICKET-0024): the ONLY sanctioned partial application of a
    # mutation. Scope: relation_delta on a satisfied relation_gte pair,
    # nothing else. Any other invalid element remains a whole reject.
    """`goal_change complete` only, called AFTER the BRIEF-0024-b
    prerequisite judge has passed — every `relation_gte` prerequisite on
    this goal is therefore satisfied at this point. Strips any
    `relation_delta` effect whose {subject, target_entity_id} pair (either
    direction) equals a prerequisite pair (anti-double-count, H1). Returns
    the kept effects and one note per stripped effect."""
    prereq_rows = db.exec(select(GoalPrerequisite).where(GoalPrerequisite.goal_id == goal.id)).all()
    if not effects or not prereq_rows:
        return effects, []
    satisfied_pairs = {
        frozenset((goal.npc_id, row.target_entity_id))
        for row in prereq_rows
        if row.type == "relation_gte"
    }
    kept: list = []
    notes: list[str] = []
    for eff in effects:
        pair = (
            frozenset((goal.npc_id, eff.get("target_entity_id")))
            if isinstance(eff, dict) else None
        )
        if isinstance(eff, dict) and eff.get("type") == "relation_delta" and pair in satisfied_pairs:
            target = db.get(Entity, eff.get("target_entity_id"))
            notes.append(f"stripped: relation_delta on prerequisite pair {target.name if target else eff.get('target_entity_id')}")
        else:
            kept.append(eff)
    return kept, notes


def _apply_effect_relation_delta(
    db: Session, world_id: str, subject_id: str, mutation_id: str, item: dict,
) -> Optional[str]:
    target_id = item.get("target_entity_id")
    relation_type = item.get("relation_type")
    try:
        value = int(item.get("value"))
    except (TypeError, ValueError):
        return "relation_delta: value must be a nonzero int in [-10, 10]"
    if value == 0 or not (-10 <= value <= 10):
        return "relation_delta: value must be a nonzero int in [-10, 10]"
    if not target_id or db.get(Entity, target_id) is None:
        return f"relation_delta: target entity {target_id!r} not found"
    if not isinstance(relation_type, str) or not relation_type.strip():
        return "relation_delta: relation_type is required"
    write_relation(
        db, mode="delta", world_id=world_id, entity_a_id=subject_id,
        entity_b_id=target_id, type=relation_type, value=value,
        mutation_id=mutation_id,
    )
    return None


def _apply_effect_ledger_transfer(db: Session, world_id: str, item: dict) -> Optional[str]:
    from_id = item.get("from_entity_id")
    to_id = item.get("to_entity_id")
    reason = item.get("reason")
    try:
        amount = int(item.get("amount"))
    except (TypeError, ValueError):
        return "ledger_transfer: amount must be a positive int"
    if amount <= 0:
        return "ledger_transfer: amount must be a positive int"
    if not from_id or db.get(Entity, from_id) is None:
        return f"ledger_transfer: from entity {from_id!r} not found"
    if not to_id or db.get(Entity, to_id) is None:
        return f"ledger_transfer: to entity {to_id!r} not found"
    if _get_balance(db, from_id) - amount < 0:
        return "insufficient balance"
    # BRIEF-19 idiom: two INSERT-only legs, mutual counterparty, both
    # source_type="tick" (M1 — new documented enum value).
    write_ledger_entry(
        db, world_id=world_id, entity_id=from_id, amount=-amount,
        counterparty_id=to_id, reason=reason, source_type="tick",
    )
    write_ledger_entry(
        db, world_id=world_id, entity_id=to_id, amount=amount,
        counterparty_id=from_id, reason=reason, source_type="tick",
    )
    return None


def _resolve_role_change_role(
    db: Session, world_id: str, faction_id: str, faction_entity: Entity,
    role_key: str, mutation_id: str, declare: bool,
) -> tuple[Optional[str], Optional[str]]:
    """Resolve role_key against faction_role, exact case-insensitive
    (TICKET-0024, BRIEF-0024-d — corrective, replaces
    faction.role_capacities). Matched in Python (`.casefold()`), not SQL
    `lower()` — SQLite's NOCASE/lower() is ASCII-only and would mishandle
    accented French role names. Returns (final_role, error) — exactly one
    is None."""
    declared_roles = db.exec(
        select(FactionRole).where(FactionRole.faction_id == faction_id)
    ).all()
    declared = next(
        (r for r in declared_roles if r.name.casefold() == role_key.casefold()), None
    )
    if declared is not None:
        resolved_key = declared.name
        limit = declared.max_holders
        if limit is not None:
            holders = db.exec(
                select(FactionMembership).where(
                    FactionMembership.faction_id == faction_id,
                    FactionMembership.left_at.is_(None),
                )
            ).all()
            count = sum(
                1 for m in holders if (m.role or "").casefold() == resolved_key.casefold()
            )
            if count >= limit:
                return None, f"role_change: role {resolved_key} is full ({count}/{limit})"
        return resolved_key, None
    if declare:
        # L2 declare-and-occupy: a role is never created without a holder —
        # declaration (INSERT) and occupation (close+reopen, by the caller)
        # commit in the same SAVEPOINT as the rest of this mutation. Newly
        # declared role is always unlimited; only the creator sets a limit
        # thereafter.
        new_role = write_faction_role(
            db, mode="create", world_id=world_id, faction_id=faction_id,
            name=role_key, description=None, max_holders=None,
            changed_by=f"mutation:{mutation_id}",
        )
        return new_role.name, None
    return None, f"role_change: role {role_key} is not declared for {faction_entity.name}"


def _apply_effect_role_change(
    db: Session, world_id: str, subject_id: str, subject_is_character: bool,
    mutation_id: str, item: dict,
) -> Optional[str]:
    if not subject_is_character:
        return "role_change: subject of a faction-owned agenda is not a character"
    faction_id = item.get("faction_id")
    role = item.get("role")
    declare = bool(item.get("declare", False))
    if not faction_id or not isinstance(role, str) or not role.strip():
        return "role_change: faction_id and role are required"
    faction_entity = db.get(Entity, faction_id)
    faction = db.get(Faction, faction_id)
    if faction_entity is None or faction_entity.world_id != world_id or faction is None:
        return f"role_change: faction {faction_id!r} not found"
    role_key = role.strip()

    # (i) subject must hold an ACTIVE membership in this faction.
    membership = db.exec(
        select(FactionMembership).where(
            FactionMembership.entity_id == subject_id,
            FactionMembership.faction_id == faction_id,
            FactionMembership.left_at.is_(None),
        )
    ).first()
    if membership is None:
        return f"role_change: NPC is not an active member of {faction_entity.name}"

    # (ii) resolve the role name, declaring-and-occupying it first if needed.
    final_role, error = _resolve_role_change_role(
        db, world_id, faction_id, faction_entity, role_key, mutation_id, declare,
    )
    if error:
        return error

    write_membership(db, mode="close", membership_id=membership.id)
    write_membership(
        db, mode="open", world_id=world_id, entity_id=subject_id,
        faction_id=faction_id, role=final_role,
        cover_role=membership.cover_role, is_primary=membership.is_primary,
        is_secret=membership.is_secret,
    )
    return None


def _apply_completion_effects(
    db: Session,
    *,
    world_id: str,
    subject_id: str,
    subject_is_character: bool,
    effects: Optional[list],
    mutation_id: str,
) -> Optional[str]:
    """Validate and apply up to `_MAX_EFFECTS` completion effects — shared
    by `goal_change complete` and `agenda_step_change complete`. Returns an
    error string on any invalid effect (whole-mutation reject; the
    caller's SAVEPOINT rolls back everything this call already wrote) or
    `None` on success. `effects` is expected already H1-stripped by the
    caller when applicable (goal_change only). The subject is FORCED by
    the caller (O1/H1 forcing precedent) — never read from the payload
    here. Per-type validation/write logic lives in `_apply_effect_*`.
    """
    if not effects:
        return None
    if len(effects) > _MAX_EFFECTS:
        return f"too many effects ({len(effects)} > {_MAX_EFFECTS})"

    for item in effects:
        eff_type = item.get("type") if isinstance(item, dict) else None
        if eff_type not in _EFFECT_TYPES:
            return f"unknown effect type {eff_type!r}"

        if eff_type == "relation_delta":
            error = _apply_effect_relation_delta(db, world_id, subject_id, mutation_id, item)
        elif eff_type == "ledger_transfer":
            error = _apply_effect_ledger_transfer(db, world_id, item)
        else:  # role_change
            error = _apply_effect_role_change(db, world_id, subject_id, subject_is_character, mutation_id, item)
        if error:
            return error

    return None


# ── relation_change ─────────────────────────────────────────────────────────

def _mutation_apply_relation_change(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """Find / create the relation, apply intensity delta, clamp to 1-100,
    append previous state to change_history."""
    a_id = payload.get("entity_a_id")
    b_id = payload.get("entity_b_id")
    if not a_id or not b_id:
        return "relation_change: payload must contain entity_a_id and entity_b_id"

    try:
        delta = int(payload.get("intensity_delta", 0))
    except (TypeError, ValueError):
        return "relation_change: intensity_delta must be an integer"

    rel_type = str(payload.get("relation_type") or "other")

    write_relation(
        db,
        mode="delta",
        world_id=mut.world_id,
        entity_a_id=a_id,
        entity_b_id=b_id,
        type=rel_type,
        value=delta,
        mutation_id=mut.id,
    )
    return None


# ── new_knowledge ────────────────────────────────────────────────────────────

def _mutation_apply_new_knowledge(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """Insert a knowledge row for the target entity. Flips `discovered=TRUE`
    on the source `discoverable_detail` when this knowledge came from an
    engine-proposed discovery — on APPLY (creator-approved), not on propose,
    so a rejected proposal leaves the detail available for re-selection."""
    entity_id = payload.get("entity_id") or mut.target_id
    if not entity_id:
        return "new_knowledge: payload must contain entity_id (or set target_id)"

    session_id: Optional[str] = None
    if mut.conversation_id:
        conv = db.get(Conversation, mut.conversation_id)
        if conv:
            session_id = conv.session_id

    write_knowledge(
        db,
        entity_id=entity_id,
        subject=str(payload.get("subject") or "unknown"),
        level=str(payload.get("level") or "rumor"),
        content=str(payload.get("content") or ""),
        source=str(payload.get("source") or "conversation"),
        is_incorrect=bool(payload.get("is_incorrect", False)),
        is_secret=bool(payload.get("is_secret", False)),
        session_id=session_id,
    )
    # Both the in-conversation _find_applied_duplicate guard (routes/mutations.py) and the
    # discovered=FALSE query in _stream() prevent double-proposing the same
    # detail (in-conversation guard) and re-proposing in future conversations
    # (discovered flag guard), respectively.
    detail_id = payload.get("discoverable_detail_id")
    if detail_id:
        detail = db.get(DiscoverableDetail, str(detail_id))
        if detail is not None:
            detail.discovered = True
            detail.updated_at = datetime.now(UTC)
            db.add(detail)
    return None


# ── status_change ────────────────────────────────────────────────────────────

def _mutation_apply_status_change(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """Update entity.status and entity.updated_at."""
    entity_id = payload.get("entity_id") or mut.target_id
    new_status = (
        payload.get("status")
        or payload.get("new_status")
        or payload.get("value")
    )

    if not entity_id:
        return "status_change: need entity_id in payload or target_id on mutation"
    if not new_status:
        return "status_change: need 'status' (or 'new_status') in payload"

    entity = db.get(Entity, str(entity_id))
    if entity is None:
        return f"status_change: entity {entity_id!r} not found"

    entity.status = str(new_status)
    entity.updated_at = datetime.now(UTC)
    db.add(entity)
    return None


# ── item_update (BRIEF-07, schema v1.19 — equip toggle) ────────────────────
# Dormant since BRIEF-08/D2a.1: no live code path produces this mutation type
# anymore; the apply branch and cockpit toggle remain functional for
# reactivation (see "Auto-applied mutations" in ARCHITECTURE_DECISIONS.md).

def _mutation_apply_item_update(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """Set item.equipped."""
    item_id = payload.get("item_id") or mut.target_id
    if not item_id:
        return "item_update: payload must contain item_id (or set target_id)"
    if "equipped" not in payload:
        return "item_update: payload must contain 'equipped'"

    item = db.get(Item, str(item_id))
    if item is None:
        return f"item_update: item {item_id!r} not found"
    if item.owner_id is None:
        return f"item_update: item {item_id!r} has no owner — cannot equip (schema CHECK)"

    item.equipped = bool(payload.get("equipped"))
    db.add(item)
    return None


# ── knowledge_change ──────────────────────────────────────────────────────────

def _mutation_apply_knowledge_change(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """Find the knowledge row by entity_id + subject, append its previous
    state to change_history, update level and source. Monotone — never
    applies a level that is not strictly higher than the row's current
    level."""
    entity_id = payload.get("entity_id") or mut.target_id
    subject = payload.get("subject")
    if not entity_id or not subject:
        return "knowledge_change: payload must contain entity_id and subject"

    row = db.exec(
        select(Knowledge).where(
            Knowledge.entity_id == entity_id,
            Knowledge.subject == subject,
        )
    ).first()
    if row is None:
        return "knowledge row not found"

    to_level = payload.get("to_level")
    if knowledge_level_rank(row.level) >= knowledge_level_rank(to_level):
        return "level already >= proposed"

    write_knowledge(
        db,
        mode="level_change",
        knowledge_id=row.id,
        level=to_level,
        source=payload.get("source"),
        changed_by="apply_mutation",
    )
    return None


# ── goal_change (TICKET-0013, BRIEF-0013-c, H1/O1) ──────────────────────────

def _mutation_apply_goal_change(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """npc_id is FORCED to conv.npc_id at emit time (analyzer.py) — never
    trusted from the model beyond that. Dispatches complete/abandon (goal
    matched by exact normalized description text) and create_short (horizon
    hard-coded, O1 structural) to their own helpers below."""
    npc_id = payload.get("npc_id")
    action = payload.get("action")
    goal_text = payload.get("goal")
    if not npc_id or not action or not goal_text:
        return "goal_change: payload must contain npc_id, action and goal"

    if action in ("complete", "abandon"):
        return _mutation_goal_change_close(mut, payload, db, npc_id, action, goal_text)
    if action == "create_short":
        return _mutation_goal_change_create_short(mut, payload, db, npc_id, goal_text)
    return f"goal_change: unrecognised action {action!r}"


def _mutation_goal_change_close(
    mut: ProposedMutation, payload: dict, db: Session, npc_id: str, action: str, goal_text: str
) -> Optional[str]:
    """complete/abandon: match an ACTIVE goal (either horizon) by exact
    normalized description text; no match -> Needs attention, nothing
    written. `complete` additionally runs the relation_gte prerequisite
    judge (TICKET-0024, BRIEF-0024-b, G1) and completion effects
    (TICKET-0024, BRIEF-0024-c) before closing the goal."""
    normalized = _routes_mutations._normalize_goal_text(goal_text)
    candidates = db.exec(
        select(NpcGoal).where(NpcGoal.npc_id == npc_id, NpcGoal.status == "active")
    ).all()
    matches = [g for g in candidates if _routes_mutations._normalize_goal_text(g.description) == normalized]
    if len(matches) != 1:
        return f"goal_change: no active goal matching {goal_text!r}"
    goal = matches[0]

    # Fail-closed on an unrecognised type (the row is creator-authored, but a
    # hand-written row could still be malformed). Gates `complete` only,
    # never `abandon`.
    goal_prerequisites = db.exec(
        select(GoalPrerequisite).where(GoalPrerequisite.goal_id == goal.id)
    ).all()
    if action == "complete" and goal_prerequisites:
        for row in goal_prerequisites:
            if row.type != "relation_gte":
                return f"goal_change: unknown prerequisite type {row.type!r}"
            rel = _find_relation_pair(db, npc_id, row.target_entity_id)
            current = rel.intensity if rel else 0
            if current < row.threshold:
                target = db.get(Entity, row.target_entity_id)
                target_name = target.name if target else row.target_entity_id
                return (
                    f"goal_change: prerequisite not met — relation "
                    f"with {target_name} is {current}, requires >= {row.threshold}"
                )

    # Completion effects run AFTER the prerequisite judge above, so
    # goal_prerequisites (if any) are all satisfied here.
    extra_history: dict[str, Any] = {}
    if action == "complete":
        effects = payload.get("effects")
        stripped_notes: list[str] = []
        if isinstance(effects, list):
            effects, stripped_notes = _h1_strip_satisfied_prerequisite_deltas(goal, effects, db)

        effect_error = _apply_completion_effects(
            db, world_id=mut.world_id, subject_id=npc_id, subject_is_character=True,
            effects=effects, mutation_id=mut.id,
        )
        if effect_error:
            return effect_error

        if stripped_notes:
            mut.creator_notes = _routes_mutations._append_note(mut.creator_notes, "; ".join(stripped_notes))
            extra_history["stripped"] = stripped_notes

        # A1: zero prerequisites and zero effects applied (absent, empty, or
        # fully H1-stripped) is legitimate (Nia's type 3).
        if not goal_prerequisites and not effects:
            extra_history["no_footprint"] = True

    write_npc_goal_status(
        db, goal=goal, new_status="completed" if action == "complete" else "abandoned",
        changed_by=f"mutation:{mut.id}", extra=extra_history or None,
    )
    return None


def _mutation_goal_change_create_short(
    mut: ProposedMutation, payload: dict, db: Session, npc_id: str, goal_text: str
) -> Optional[str]:
    """O1 structural: horizon is hard-coded "short" — the payload carries no
    horizon field and none is read, so the model cannot create a long-term
    goal by any input. S1: no active-count check — the injection's read-side
    LIMIT is the bound. Own-agenda reference (TICKET-0020, BRIEF-0020-b):
    normalize-time resolved an optional agenda title into agenda_id
    (owner-only index) — link preconditions are re-validated here (the
    agenda may have closed since the tick). A ValueError is caught and
    returned as a string (this function's "never raises" contract) — the
    caller's outer SAVEPOINT then rolls back the goal insert too, so a
    failed link means NO goal either, exactly as if the whole mutation had
    been rejected."""
    goal = write_npc_goal(
        db, world_id=mut.world_id, npc_id=npc_id, description=goal_text,
        horizon="short", changed_by=f"mutation:{mut.id}",
    )
    agenda_id = payload.get("agenda_id")
    if agenda_id:
        try:
            write_goal_agenda_link(
                db, world_id=mut.world_id, goal_id=goal.id, agenda_id=agenda_id,
                created_by=f"mutation:{mut.id}", mutation_id=mut.id,
            )
        except ValueError as exc:
            return f"goal_change: {exc}"
    return None


# ── npc_move (TICKET-0015, BRIEF-0015-a) ────────────────────────────────────

def _mutation_apply_npc_move(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """Tick-only. Stale-from gate: character.current_location_id must still
    equal payload's from_location_id, else "Needs attention" (covers
    duplicate re-approval, cross-run duplicates, and a manual move since the
    proposal — RECON-0015 F6). close_open_memberships is called on apply
    regardless of player co-presence (Nia's locked decision)."""
    npc_id = payload.get("npc_id")
    from_location_id = payload.get("from_location_id")
    to_location_id = payload.get("to_location_id")
    if not npc_id or not from_location_id or not to_location_id:
        return "npc_move: payload must contain npc_id, from_location_id and to_location_id"

    character = db.get(Character, npc_id)
    if character is None:
        return f"npc_move: character {npc_id!r} not found"

    if character.current_location_id != from_location_id:
        return "npc_move: NPC no longer at the proposal's origin — world moved since the tick"

    destination = db.get(Entity, to_location_id)
    if (
        destination is None
        or destination.type != "location"
        or destination.status != "active"
        or destination.world_id != mut.world_id
    ):
        return f"npc_move: destination {to_location_id!r} is not an active location in this world"

    write_character_location(db, entity_id=npc_id, to_location_id=to_location_id, mutation_id=mut.id)
    # BRIEF-53 seam: closes the NPC's open gathering_member rows, PLAYER
    # PRESENT OR NOT — Nia's locked decision.
    close_open_memberships(npc_id, db)
    return None


# ── event_creation (TICKET-0017, BRIEF-0017-a) ──────────────────────────────

def _mutation_apply_event_creation(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """Tolerant of BOTH payload generations — the scope-level tick's closed
    shape and the analyzer's minimal conversation-sourced shape.
    knowledge_status clamped to secret|public|confirmed (defense in depth).
    A present location_id must resolve to an ACTIVE location entity of this
    world, else "Needs attention", nothing written."""
    title = payload.get("title")
    if not title:
        return "event_creation: payload must contain title"

    knowledge_status = payload.get("knowledge_status")
    if knowledge_status not in ("secret", "public", "confirmed"):
        knowledge_status = "secret"

    location_id = payload.get("location_id")
    if location_id:
        location_entity = db.get(Entity, location_id)
        if (
            location_entity is None
            or location_entity.type != "location"
            or location_entity.status != "active"
            or location_entity.world_id != mut.world_id
        ):
            return f"event_creation: location {location_id!r} is not an active location in this world"

    write_event(
        db,
        world_id=mut.world_id,
        title=str(title),
        description=payload.get("description"),
        type=payload.get("type"),
        knowledge_status=knowledge_status,
        involved_entities=payload.get("involved_entities"),
        location_id=location_id,
        mutation_id=mut.id,
    )
    return None


# ── resource_change (BRIEF-19) ───────────────────────────────────────────────

def _mutation_apply_resource_change(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """Two-leg write, both inside this one SAVEPOINT — the single sanctioned
    exception to one-branch-one-table. Money leg via write_ledger_entry
    (always); optional knowledge leg via write_knowledge (fresh acquisition
    only). Guards: non-negative player balance; knowledge-leg block-whole
    (existing row, or an equivalent knowledge already applied this
    conversation) -> Needs attention, nothing written."""
    entity_id = payload.get("entity_id")
    counterparty_id = payload.get("counterparty_id")
    reason = payload.get("reason")
    if not entity_id:
        return "resource_change: payload must contain entity_id"
    try:
        amount = int(payload.get("amount"))
    except (TypeError, ValueError):
        return "resource_change: payload must contain an integer 'amount'"

    knowledge_leg = payload.get("knowledge")
    if not isinstance(knowledge_leg, dict):
        knowledge_leg = None

    # Non-negative guard — AI path only; the creator CRUD path stays
    # god-mode (no balance check on POST /api/ledger).
    if amount < 0 and _get_balance(db, entity_id) + amount < 0:
        return "insufficient balance"

    # Knowledge-leg guard (block-whole) — if a clean fresh row cannot be
    # created, the WHOLE mutation is routed to Needs attention and nothing
    # is written (not even the money leg).
    if knowledge_leg is not None:
        k_entity_id = knowledge_leg.get("entity_id")
        k_subject = knowledge_leg.get("subject")
        if not k_entity_id or not k_subject:
            return "resource_change: knowledge leg must contain entity_id and subject"

        existing_row = db.exec(
            select(Knowledge).where(
                Knowledge.entity_id == k_entity_id,
                Knowledge.subject == k_subject,
            )
        ).first()
        if existing_row is not None:
            return "knowledge already held (upgrade-by-purchase deferred)"

        if mut.conversation_id and _knowledge_leg_already_applied(
            db, mut.conversation_id, k_entity_id, k_subject
        ):
            return "duplicate knowledge leg"

    session_id: Optional[str] = None
    if mut.conversation_id:
        conv = db.get(Conversation, mut.conversation_id)
        if conv:
            session_id = conv.session_id

    write_ledger_entry(
        db, world_id=mut.world_id, entity_id=entity_id, amount=amount,
        counterparty_id=counterparty_id, reason=reason, source_type="conversation",
        conversation_id=mut.conversation_id, session_id=session_id,
    )

    if knowledge_leg is not None:
        write_knowledge(
            db,
            entity_id=knowledge_leg.get("entity_id"),
            subject=str(knowledge_leg.get("subject") or "unknown"),
            level=str(knowledge_leg.get("level") or "rumor"),
            content=str(knowledge_leg.get("content") or ""),
            source=str(knowledge_leg.get("source") or "conversation"),
            is_incorrect=bool(knowledge_leg.get("is_incorrect", False)),
            is_secret=bool(knowledge_leg.get("is_secret", False)),
            session_id=session_id,
        )
    return None


# ── agenda_step_change (TICKET-0018, BRIEF-0018-a) ──────────────────────────

def _mutation_apply_agenda_step_change(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """Stale guard (0014 doctrine, canon-existence): the step must still be
    the ACTIVE one. Completion effects (TICKET-0024, BRIEF-0024-c) —
    `complete` only, never `fail`. Subject is FORCED to the agenda's owner;
    a role_change effect on a faction-owned agenda is a whole reject."""
    step_id = payload.get("step_id")
    action = payload.get("action")
    if not step_id or action not in ("complete", "fail"):
        return "agenda_step_change: payload must contain step_id and action in {complete, fail}"

    step = db.get(AgendaStep, step_id)
    if step is None:
        return f"agenda_step_change: step {step_id!r} not found"

    if step.status != "active":
        return "agenda_step_change: step no longer active — world moved since the tick"

    agenda = db.get(Agenda, step.agenda_id)
    if agenda is None:
        return f"agenda_step_change: agenda {step.agenda_id!r} not found"

    extra_history: dict[str, Any] = {}
    if action == "complete":
        owner = db.get(Entity, agenda.owner_entity_id)
        subject_is_character = owner is not None and owner.type == "character"
        effects = payload.get("effects")

        effect_error = _apply_completion_effects(
            db, world_id=mut.world_id, subject_id=agenda.owner_entity_id,
            subject_is_character=subject_is_character, effects=effects, mutation_id=mut.id,
        )
        if effect_error:
            return effect_error

        # agenda_step has no prerequisites column (G3 deferred) — A1's "zero
        # prerequisites" side is always true here.
        if not effects:
            extra_history["no_footprint"] = True

    new_status = "completed" if action == "complete" else "failed"
    write_agenda_step_status(
        db, step=step, status=new_status, outcome=payload.get("outcome"), mutation_id=mut.id,
        extra=extra_history or None,
    )

    if action == "complete":
        next_step = db.exec(
            select(AgendaStep)
            .where(AgendaStep.agenda_id == agenda.id, AgendaStep.status == "pending")
            .order_by(AgendaStep.step_order)
        ).first()
        if next_step is not None:
            write_agenda_step_status(db, step=next_step, status="active", mutation_id=mut.id)
        else:
            write_agenda_status(db, agenda=agenda, status="completed", mutation_id=mut.id)
    else:  # fail — the WHOLE agenda fails, no branching (creator can reactivate via PATCH)
        write_agenda_status(db, agenda=agenda, status="failed", mutation_id=mut.id)
    return None


# ── agenda_creation (TICKET-0018, BRIEF-0018-a) ─────────────────────────────

def _mutation_apply_agenda_creation(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """Writes one Agenda + N AgendaStep rows (step 1 born active) in this one
    SAVEPOINT — a parent-child aggregate, not a one-branch-one-table
    exception of the resource_change kind."""
    owner_entity_id = payload.get("owner_entity_id")
    title = payload.get("title")
    steps = payload.get("steps")
    if (
        not owner_entity_id
        or not title
        or not isinstance(steps, list)
        or not (2 <= len(steps) <= 5)
        or not all(isinstance(s, str) and s.strip() for s in steps)
    ):
        return "agenda_creation: payload must contain owner_entity_id, title, and 2-5 non-empty steps"

    try:
        agenda = write_agenda(
            db, world_id=mut.world_id, owner_entity_id=owner_entity_id, title=str(title),
            mutation_id=mut.id,
        )
    except ValueError as exc:
        return f"agenda_creation: {exc}"

    for order, objective in enumerate(steps, start=1):
        write_agenda_step(
            db,
            agenda_id=agenda.id,
            step_order=order,
            objective=str(objective),
            # Step 1 is born active — the creator's approval IS the
            # activation (symmetric with the creator-CRUD create route).
            status="active" if order == 1 else "pending",
        )
    return None


# ── agenda_delegation (TICKET-0020, BRIEF-0020-b) ───────────────────────────

def _mutation_apply_agenda_delegation(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """Re-validates at apply (stale-proof, canon-existence): the agenda is
    still ACTIVE; the NPC holds an ACTIVE FactionMembership (secret OR
    public — a faction may task a secret member) in the agenda's owner
    faction. Writes one NpcGoal + one GoalAgendaLink in this one SAVEPOINT
    (same parent-child-aggregate shape as agenda_creation)."""
    npc_id = payload.get("npc_id")
    goal_text = payload.get("goal")
    horizon = payload.get("horizon")
    agenda_id = payload.get("agenda_id")
    if not npc_id or not goal_text or horizon not in ("short", "long") or not agenda_id:
        return "agenda_delegation: payload must contain npc_id, goal, horizon in {short, long}, and agenda_id"

    agenda = db.get(Agenda, agenda_id)
    if agenda is None or agenda.status != "active":
        return f"agenda_delegation: agenda {agenda_id!r} is not active — world moved since the tick"

    membership = db.exec(
        select(FactionMembership).where(
            FactionMembership.entity_id == npc_id,
            FactionMembership.faction_id == agenda.owner_entity_id,
            FactionMembership.left_at.is_(None),
        )
    ).first()
    if membership is None:
        return f"agenda_delegation: NPC {npc_id!r} is not an active member of the agenda's owner faction"

    goal = write_npc_goal(
        db, world_id=mut.world_id, npc_id=npc_id, description=str(goal_text),
        horizon=horizon, changed_by=f"mutation:{mut.id}",
    )
    try:
        write_goal_agenda_link(
            db, world_id=mut.world_id, goal_id=goal.id, agenda_id=agenda_id,
            created_by=f"mutation:{mut.id}", mutation_id=mut.id,
        )
    except ValueError as exc:
        return f"agenda_delegation: {exc}"
    return None
