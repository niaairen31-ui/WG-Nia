"""The mutation review queue: list/reject/approve/batch-review, the
`_apply_mutation` thin dispatcher, the applied-duplicate guard, and mutation
serialization.

Split out of `cockpit/app.py` (TICKET-0027, BRIEF-0027-d) — pure move, no
logic change, no route path/method change. `_apply_mutation` lazily imports
`cockpit/mutations.py` (the per-type appliers, stage c) inside its own body
to avoid a circular import, same pattern as before the split.
"""

from __future__ import annotations

import enum
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ... import ollama_client
from ...entity_author import generate_entity_draft as _generate_entity_draft
from ...entity_author import generate_npc_goals as _generate_npc_goals
from ...entity_author import generate_player_draft as _generate_player_draft
from ...entity_author import generate_skill_catalogue_draft as _generate_skill_catalogue_draft
from ...entity_author import generate_world_draft as _generate_world_draft
from ...event_author import build_world_roster as _build_world_roster
from ...event_author import generate_agenda_draft as _generate_agenda_draft
from ...event_author import generate_event_draft as _generate_event_draft
from ...region_author import generate_region_draft as _generate_region_draft
from ...region_author import generate_region_manifest as _generate_region_manifest
from ...gathering import enter_location as _enter_location
from ...gathering import migrate_npc as _migrate_npc
from ...analyzer import analyze_overhearing as _analyze_overhearing
from ...analyzer import analyze_window as _analyze_window
from ...tick import run_world_tick as _run_world_tick
from ...prompt_registry import PROMPT_REGISTRY, effective_model
from ...prompt_store import current_prompt
from ...context import (
    _SAFE_SUBCULTURE_KEYS,
    active_signposts,
    assemble_mj_context,
    assemble_npc_context,
    format_inventory_line,
    format_item_list_for_interpretation,
    format_mj_context,
)
from ...db import engine, get_session
from ...models import (
    Agenda,
    BASE_SKILL_DOMAINS,
    Character,
    Conversation,
    ConversationMessage,
    DiscoverableDetail,
    Entity,
    Event,
    EventEntity,
    Faction,
    FactionMembership,
    Gathering,
    GatheringMember,
    Item,
    Knowledge,
    Location,
    LocationSubculture,
    NpcGoal,
    PromptTemplate,
    ProposedMutation,
    Relation,
    Session as GameSession,
    Skill,
    SkillDefinition,
    User,
    Visit,
    World,
    WorldLaw,
)
from ...resolution import resolve_physical
from ...writes import (
    KNOWLEDGE_LEVELS,
    delete_world_cascade as _delete_world_cascade,
    write_knowledge,
    write_npc_goal,
    write_relation,
    write_world_laws,
)
from .. import crud as _crud

router = APIRouter()


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _mutation_dict(m: ProposedMutation) -> dict:
    return {
        "id": m.id,
        "mutation_type": m.mutation_type,
        "target_table": m.target_table,
        "target_id": m.target_id,
        "payload": m.payload,
        "rationale": m.rationale,
        "status": m.status,
        "creator_notes": m.creator_notes,
        "proposed_by": m.proposed_by,
        "source_type": m.source_type,
        "conversation_id": m.conversation_id,
        "pass_play_id": m.pass_play_id,
        "tick_id": m.tick_id,
        "proposed_at": _iso(m.proposed_at),
        "reviewed_at": _iso(m.reviewed_at),
        "applied_at": _iso(m.applied_at),
    }


# ── Duplicate-application guard ───────────────────────────────────────────────

def _find_event_duplicate(payload: dict, world_id: str, db: Session) -> Optional[str]:
    """Canon-existence duplicate check for `event_creation` (TICKET-0017,
    BRIEF-0017-a): duplicate iff an `Event` row already exists in this world
    with the same normalized (casefold/strip) title AND the same
    `location_id` (NULL matches NULL) — never tick_id/conversation equality
    (0014 guard doctrine). Applies regardless of source (tick-sourced or
    conversation-sourced): a re-run tick or a --force re-analysis must not
    double an event either way.
    """
    title = _normalize_goal_text(payload.get("title"))
    location_id = payload.get("location_id")
    candidates = db.exec(
        select(Event).where(Event.world_id == world_id, Event.location_id == location_id)
    ).all()
    for e in candidates:
        if _normalize_goal_text(e.title) == title:
            return (
                f"event_creation for title {payload.get('title')!r} already exists "
                "at this location."
            )
    return None


def _dup_tick_goal_change_create(payload: dict, db: Session) -> Optional[str]:
    """goal_change with action == "create_short": duplicate iff an ACTIVE
    NpcGoal already exists for this NPC whose normalized description equals
    the proposal's. complete/abandon get NO guard here — the apply branch's
    exactly-one-active-match requirement is already the correct gate."""
    normalized = _normalize_goal_text(payload.get("goal"))
    candidates = db.exec(
        select(NpcGoal).where(NpcGoal.npc_id == payload.get("npc_id"), NpcGoal.status == "active")
    ).all()
    if any(_normalize_goal_text(g.description) == normalized for g in candidates):
        return (
            f"goal_change (create_short) for goal {payload.get('goal')!r} already exists "
            f"as an active goal for this NPC."
        )
    return None


def _dup_tick_new_knowledge(payload: dict, db: Session) -> Optional[str]:
    """new_knowledge: duplicate iff a Knowledge row already exists for
    (entity_id, subject)."""
    existing = db.exec(
        select(Knowledge).where(
            Knowledge.entity_id == payload.get("entity_id"),
            Knowledge.subject == payload.get("subject"),
        )
    ).first()
    if existing is not None:
        return (
            f"new_knowledge for entity {str(payload.get('entity_id',''))[:8]}… "
            f"subject={payload.get('subject')!r} already exists as a knowledge row."
        )
    return None


def _dup_tick_npc_move(payload: dict, db: Session) -> Optional[str]:
    """Mirrors the apply branch's stale-from gate (RECON-0015 F6): one canon
    check covers duplicate re-approval, cross-run tick duplicates, AND the
    world having moved since the proposal — and correctly ALLOWS a later
    legitimate A->B->A move."""
    character = db.get(Character, payload.get("npc_id"))
    if character is not None and character.current_location_id != payload.get("from_location_id"):
        return (
            f"npc_move for NPC {str(payload.get('npc_id',''))[:8]}… — NPC no longer at "
            f"the proposal's origin (world moved since the tick)."
        )
    return None


def _dup_tick_agenda_creation(payload: dict, db: Session) -> Optional[str]:
    """Canon-existence (TICKET-0018, BRIEF-0018-a): duplicate iff an ACTIVE
    agenda already exists for this owner with the same normalized title —
    EXCEPT for a `character` owner (TICKET-0020, BRIEF-0020-b), where ANY
    active agenda is a duplicate (the one-active-personal-agenda invariant
    makes title irrelevant). Faction owners keep the same-title-only guard.
    agenda_step_change gets NO clause here by design — the apply branch's
    active-status stale guard is strictly stronger (0015 F6 argument)."""
    owner_id = payload.get("owner_entity_id")
    owner = db.get(Entity, owner_id)
    if owner is not None and owner.type == "character":
        existing_personal = db.exec(
            select(Agenda).where(
                Agenda.owner_entity_id == owner_id,
                Agenda.status == "active",
            )
        ).first()
        if existing_personal is not None:
            return (
                f"agenda_creation for NPC {str(owner_id)[:8]}… already holds an active "
                f"agenda ({existing_personal.title!r})."
            )
        return None

    normalized = _normalize_goal_text(payload.get("title"))
    candidates = db.exec(
        select(Agenda).where(
            Agenda.owner_entity_id == owner_id,
            Agenda.status == "active",
        )
    ).all()
    if any(_normalize_goal_text(a.title) == normalized for a in candidates):
        return (
            f"agenda_creation for title {payload.get('title')!r} already exists "
            "as an active agenda for this owner."
        )
    return None


def _dup_tick_agenda_delegation(payload: dict, db: Session) -> Optional[str]:
    """Reuse the create_short duplicate rule: an ACTIVE goal with the same
    normalized text on that NPC is a duplicate — mirrors goal_change's own
    create_short guard, applied here since agenda_delegation is tick-sourced
    only (no conversation_id branch exists for it)."""
    normalized = _normalize_goal_text(payload.get("goal"))
    candidates = db.exec(
        select(NpcGoal).where(NpcGoal.npc_id == payload.get("npc_id"), NpcGoal.status == "active")
    ).all()
    if any(_normalize_goal_text(g.description) == normalized for g in candidates):
        return (
            f"agenda_delegation for goal {payload.get('goal')!r} already exists "
            "as an active goal for this NPC."
        )
    return None


def _find_applied_duplicate_tick_sourced(mut: ProposedMutation, db: Session) -> Optional[str]:
    """TICK SCOPE (TICKET-0014, BRIEF-0014-b, Y2/F2): a tick-sourced mutation
    (`conversation_id IS NULL`, `tick_id` set) never reaches the
    conversation-scoped branch — a re-run tick gets a NEW tick_id every
    time, so comparing WITHIN one tick_id would miss exactly the cross-run
    duplicates this guard exists for. Instead it asks the CANON directly,
    re-run-proof AND revival-safe (a closed goal reopened via creator CRUD
    is a NEW row, per 0013 doctrine, and must be allowed to re-apply). Each
    mutation_type's match key lives in its own `_dup_tick_*` helper.
    relation_change gets NO guard: same accumulating-deltas doctrine as the
    conversation-sourced branch — a double delta from a re-run tick is
    visible in the queue and the creator's to judge, never blocked.

    EVENT_CREATION (TICKET-0017, BRIEF-0017-a) routes through
    `_find_event_duplicate` — the SAME canon-existence check (title +
    location_id, this world) the conversation-sourced branch also uses, so
    neither a re-run tick nor a --force re-analysis can double an event.
    """
    if not mut.tick_id:
        return None

    payload = mut.payload if isinstance(mut.payload, dict) else {}
    mt = mut.mutation_type

    if mt == "goal_change" and payload.get("action") == "create_short":
        return _dup_tick_goal_change_create(payload, db)
    if mt == "new_knowledge":
        return _dup_tick_new_knowledge(payload, db)
    if mt == "npc_move":
        return _dup_tick_npc_move(payload, db)
    if mt == "event_creation":
        return _find_event_duplicate(payload, mut.world_id, db)
    if mt == "agenda_creation":
        return _dup_tick_agenda_creation(payload, db)
    if mt == "agenda_delegation":
        return _dup_tick_agenda_delegation(payload, db)
    return None


def _find_applied_duplicate_conversation_sourced(mut: ProposedMutation, db: Session) -> Optional[str]:
    """Only mutations from the SAME conversation are compared — the same
    knowledge acquired in two different conversations is not a duplicate.

    Match keys (design choice):
    - new_knowledge : same conversation_id + entity_id + subject. (entity,
      subject) is the identity of a fact; applying twice creates duplicate
      knowledge rows and inflates NPC context.
    - status_change : same conversation_id + entity_id. Two status changes
      on the same entity in one conversation are unlikely to both be
      correct; surface for creator review.
    - goal_change (TICKET-0013, BRIEF-0013-c): same conversation_id +
      action + normalized goal text — the opposite asymmetry from
      knowledge_change, deliberately: a repeated identical goal event (the
      same goal, same action) within ONE conversation is not legitimate — a
      goal is completed, abandoned, or created once, not twice in the same
      scene.

    event_creation routes through `_find_event_duplicate` instead (canon-
    existence, not conversation-scoped — TICKET-0017: the dormant analyzer
    channel awakens alongside the tick producer, so a --force re-analysis
    must not double an event either).

    relation_change, item_update, knowledge_change, and resource_change all
    fall through unguarded, deliberately — see `_find_applied_duplicate`'s
    docstring for the per-type rationale.
    """
    payload = mut.payload if isinstance(mut.payload, dict) else {}

    if mut.mutation_type == "event_creation":
        return _find_event_duplicate(payload, mut.world_id, db)

    applied_same_type = db.exec(
        select(ProposedMutation).where(
            ProposedMutation.conversation_id == mut.conversation_id,
            ProposedMutation.status == "applied",
            ProposedMutation.mutation_type == mut.mutation_type,
        )
    ).all()

    if not applied_same_type:
        return None

    for prev in applied_same_type:
        prev_p = prev.payload if isinstance(prev.payload, dict) else {}

        if mut.mutation_type == "new_knowledge":
            if (prev_p.get("entity_id") == payload.get("entity_id")
                    and prev_p.get("subject") == payload.get("subject")):
                return (
                    f"new_knowledge for entity {str(payload.get('entity_id',''))[:8]}… "
                    f"subject={payload.get('subject')!r} was already applied by "
                    f"mutation {prev.id[:8]}…  Applying again would create a "
                    f"duplicate knowledge row."
                )

        elif mut.mutation_type == "status_change":
            prev_eid = prev_p.get("entity_id") or prev.target_id
            cur_eid  = payload.get("entity_id") or mut.target_id
            if prev_eid == cur_eid:
                return (
                    f"status_change for entity {str(cur_eid)[:8]}… was already "
                    f"applied by mutation {prev.id[:8]}…"
                )

        elif mut.mutation_type == "goal_change":
            if (prev_p.get("action") == payload.get("action")
                    and _normalize_goal_text(prev_p.get("goal")) == _normalize_goal_text(payload.get("goal"))):
                return (
                    f"goal_change ({payload.get('action')}) for goal "
                    f"{payload.get('goal')!r} was already applied by mutation "
                    f"{prev.id[:8]}…"
                )

    return None


def _find_applied_duplicate(
    mut: ProposedMutation,
    db: Session,
) -> Optional[str]:
    """Return a warning string if an equivalent mutation was already applied for
    this conversation; return None if it is safe to apply.

    This guard prevents double-application when --force re-generates proposals
    after a previous round already applied one. Two entry points, split by
    source: `_find_applied_duplicate_tick_sourced` (canon-existence checks,
    re-run-proof) for `conversation_id IS NULL` rows, and
    `_find_applied_duplicate_conversation_sourced` (same-conversation
    already-applied comparison) otherwise — see each for its per-type match
    keys and deliberate inclusion/exclusion rationale.

    relation_change, item_update, knowledge_change, and resource_change all
    fall through BOTH entry points unguarded, deliberately:
    - relation_change deltas ACCUMULATE — two independent +5 events sum to
      +10 and must both apply. These come only from per-turn immediate
      flags (one per turn), so they are never re-proposed by the final
      pass and can never be double-applied by --force.
    - item_update is a state transition (equipped true/false); a legitimate
      draw→stow→draw sequence within one conversation must apply each
      time. Dormant since BRIEF-08/D2a.1 — no live code path produces it
      anymore (see "Auto-applied mutations" in ARCHITECTURE_DECISIONS.md).
    - knowledge_change: successive legitimate upgrades in one conversation
      (e.g. rumor → partial, then later partial → knows) must both apply —
      the monotone re-check inside _apply_mutation ("level already >=
      proposed") is the correct guard, not an identity-based duplicate
      check.
    - resource_change (BRIEF-19): its money leg accumulates exactly like
      relation_change — two genuine purchases in one conversation must
      both apply. Its knowledge leg IS idempotent, but that guard lives
      inside the resource_change branch itself
      (_knowledge_leg_already_applied, guard 4c), not here.
    """
    if not mut.conversation_id:
        return _find_applied_duplicate_tick_sourced(mut, db)
    return _find_applied_duplicate_conversation_sourced(mut, db)


def _normalize_goal_text(text: Optional[str]) -> str:
    """Casefold + whitespace-collapse a goal description for equality matching
    (TICKET-0013, BRIEF-0013-c) — goals are matched by exact description text,
    never by id (the model never receives structural ids)."""
    return " ".join(str(text or "").split()).casefold()


# ── Canon writer ──────────────────────────────────────────────────────────────
# Per-mutation-type write logic, and the helpers used only by that logic
# (`_knowledge_leg_already_applied`, `_h1_strip_satisfied_prerequisite_deltas`,
# `_apply_completion_effects`), moved to `cockpit/mutations.py`
# (TICKET-0027, BRIEF-0027-c). `_apply_mutation` stays here as a thin
# dispatcher.

def _apply_mutation(mut: ProposedMutation, db: Session) -> Optional[str]:
    """Write one mutation to the canon tables.

    Returns an error string when the apply cannot proceed, None on success.
    Never raises — errors are returned so the caller can set status='approved'
    and store the message rather than crashing the request.

    Thin dispatcher (TICKET-0027, BRIEF-0027-c): the duplicate guard runs
    here (shared by every type, and by other routes — see
    `_find_applied_duplicate`'s other call sites), then payload extraction,
    then one call into a `_mutation_apply_<type>()` function in
    `cockpit/mutations.py`, which holds the per-type documentation and
    write logic. `mutations.py` is imported lazily (inside this function
    body) to avoid a circular import — it imports `from . import app as
    _app` at module level, same pattern as `cockpit/play.py`.

    Unimplemented types (other) are left as 'approved' with a note — better
    un-applied than wrongly applied. `entity_creation` is realized through
    the Création tab (BRIEF-0019-a), never applied here: the unit approve
    endpoint short-circuits before this function ever sees that type.
    """
    from .. import mutations as _mutations

    # ── Duplicate guard ───────────────────────────────────────────────────────
    # Must run before any write.  If an equivalent mutation was already applied
    # for the same conversation, we block and surface it in the "Needs attention"
    # tab rather than silently doubling the effect.
    dup = _find_applied_duplicate(mut, db)
    if dup:
        return f"[duplicate blocked] {dup}"

    payload: dict = mut.payload if isinstance(mut.payload, dict) else {}

    appliers = {
        "relation_change": _mutations._mutation_apply_relation_change,
        "new_knowledge": _mutations._mutation_apply_new_knowledge,
        "status_change": _mutations._mutation_apply_status_change,
        "item_update": _mutations._mutation_apply_item_update,
        "knowledge_change": _mutations._mutation_apply_knowledge_change,
        "goal_change": _mutations._mutation_apply_goal_change,
        "npc_move": _mutations._mutation_apply_npc_move,
        "event_creation": _mutations._mutation_apply_event_creation,
        "resource_change": _mutations._mutation_apply_resource_change,
        "agenda_step_change": _mutations._mutation_apply_agenda_step_change,
        "agenda_creation": _mutations._mutation_apply_agenda_creation,
        "agenda_delegation": _mutations._mutation_apply_agenda_delegation,
    }
    applier = appliers.get(mut.mutation_type)
    if applier is None:
        return (
            f"mutation_type '{mut.mutation_type}' is not implemented in "
            f"_apply_mutation — left as 'approved' for manual handling."
        )
    return applier(mut, payload, db)


@router.get("/api/mutations")
def list_mutations(
    status: str = Query(default="proposed"),
    db: Session = Depends(get_session),
) -> list:
    mutations = db.exec(
        select(ProposedMutation)
        .where(ProposedMutation.status == status)
        .where(ProposedMutation.world_id == _crud._world_id(db))
        .order_by(ProposedMutation.proposed_at)
    ).all()
    result = []
    for m in mutations:
        d = _mutation_dict(m)
        # For proposed rows only: surface any already-applied equivalent so the
        # UI can show the duplicate-risk banner before the creator clicks Approve.
        d["applied_duplicate"] = (
            _find_applied_duplicate(m, db) if m.status == "proposed" else None
        )
        result.append(d)
    return result


class RejectBody(BaseModel):
    creator_notes: Optional[str] = None


@router.post("/api/mutations/{mut_id}/reject")
def reject_mutation(
    mut_id: str,
    body: RejectBody = RejectBody(),
    db: Session = Depends(get_session),
) -> dict:
    mut = db.get(ProposedMutation, mut_id)
    if mut is None:
        raise HTTPException(status_code=404, detail="Mutation not found")
    if mut.status == "applied":
        raise HTTPException(
            status_code=409,
            detail="Cannot reject a mutation that has already been applied to canon.",
        )

    mut.status = "rejected"
    mut.reviewed_at = datetime.now(UTC)
    if body.creator_notes:
        mut.creator_notes = body.creator_notes
    db.add(mut)
    db.commit()
    db.refresh(mut)
    return _mutation_dict(mut)


class ApproveBody(BaseModel):
    # The creator may edit the payload in the UI before approving.
    # Sent as a JSON string so the textarea value is passed verbatim.
    payload: Optional[str] = None
    creator_notes: Optional[str] = None


def _approve_apply_edited_payload(mut: ProposedMutation, body: "ApproveBody") -> None:
    """Apply an edited payload from the form before writing anything."""
    if body.payload is not None:
        try:
            mut.payload = json.loads(body.payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422, detail=f"Payload is not valid JSON: {exc}"
            )
    if body.creator_notes is not None:
        mut.creator_notes = body.creator_notes


def _approve_entity_creation_shortcircuit(mut: ProposedMutation, db: Session) -> Optional[dict]:
    """entity_creation short-circuit (TICKET-0019, BRIEF-0019-a): approval
    PARKS the germ — it never reaches _apply_mutation, never a savepoint,
    never the "[apply error]" framing (RECON F3): I2 forbids any synchronous
    authoring call here. A fresh canon-existence recheck (F5) routes a
    genuine collision to "Needs attention" instead of parking it. Returns
    None when mut is not an entity_creation (caller proceeds to the normal
    apply path)."""
    if mut.mutation_type != "entity_creation":
        return None

    payload = mut.payload if isinstance(mut.payload, dict) else {}
    name = str(payload.get("name") or "").strip()
    collision = any(
        e.name.casefold() == name.casefold()
        for e in db.exec(
            select(Entity).where(Entity.world_id == mut.world_id, Entity.status == "active")
        ).all()
    )
    if collision:
        mut.status = "approved"
        mut.creator_notes = _append_note(
            mut.creator_notes, f"une entité active porte déjà ce nom : {name!r}"
        )
        db.add(mut)
        db.commit()
        db.refresh(mut)
        return {
            "status": "approved",
            "error": mut.creator_notes,
            "mutation": _mutation_dict(mut),
        }

    mut.status = "approved"
    mut.creator_notes = _append_note(mut.creator_notes, "en attente de réalisation — onglet Création")
    db.add(mut)
    db.commit()
    db.refresh(mut)
    return {
        "status": "pending_realization",
        "error": "en attente de réalisation — onglet Création",
        "mutation": _mutation_dict(mut),
    }


def _approve_apply_and_commit(mut: ProposedMutation, db: Session, now: datetime) -> dict:
    """SAVEPOINT: canon writes are rolled back on failure; the outer
    transaction (mutation row update) stays live either way."""
    try:
        with db.begin_nested():
            error = _apply_mutation(mut, db)
            if error:
                raise RuntimeError(error)

        # Savepoint committed → canon updated.
        mut.status = "applied"
        mut.applied_at = now
        db.add(mut)
        db.commit()
        db.refresh(mut)
        return {"status": "applied", "mutation": _mutation_dict(mut)}

    except Exception as exc:
        # Savepoint rolled back — canon is clean.
        error_msg = str(exc)
        mut.status = "approved"
        prior = mut.creator_notes or ""
        mut.creator_notes = f"{prior}\n[apply error] {error_msg}".strip()
        db.add(mut)
        db.commit()
        db.refresh(mut)
        return {
            "status": "approved",
            "error": error_msg,
            "mutation": _mutation_dict(mut),
        }


@router.post("/api/mutations/{mut_id}/approve")
def approve_mutation(
    mut_id: str,
    body: ApproveBody = ApproveBody(),
    db: Session = Depends(get_session),
) -> dict:
    """Approve and apply a mutation to canon.

    Success path  → status='applied',  applied_at set.
    Failure path  → status='approved', error stored in creator_notes, returned
                    to the caller.  Canon is never partially written.

    The canon writes happen inside a SAVEPOINT so a failure rolls back only
    those writes — the mutation row update (reviewed_at, notes, status) lives
    in the outer transaction and is always committed.
    """
    mut = db.get(ProposedMutation, mut_id)
    if mut is None:
        raise HTTPException(status_code=404, detail="Mutation not found")

    if mut.status == "applied":
        return {"status": "already_applied", "mutation": _mutation_dict(mut)}

    _approve_apply_edited_payload(mut, body)

    now = datetime.now(UTC)
    mut.reviewed_at = now

    shortcircuit = _approve_entity_creation_shortcircuit(mut, db)
    if shortcircuit is not None:
        return shortcircuit

    return _approve_apply_and_commit(mut, db, now)


_BATCH_REVIEW_MARKER = "batch-review"


def _append_note(existing: Optional[str], note: str) -> str:
    prior = existing or ""
    return f"{prior}\n{note}".strip()


class BatchReviewBody(BaseModel):
    action: str  # "approve" | "reject"
    mutation_ids: list[str]


def _batch_approve(mutation_ids: list[str], now: datetime, db: Session) -> dict:
    """Sequential, per-row, through the SAME SAVEPOINT-isolated path as unit
    approve — a failed apply rolls back only the canon writes for that row
    and never stops the loop (lands in "Needs attention" exactly as in unit
    review). Each row is re-loaded and re-checked: only `status ==
    'proposed'` rows are processed; anything else (already reviewed, e.g. a
    stale client selection) is SKIPPED, never touched."""
    applied = 0
    needs_attention = 0
    skipped = 0

    for mut_id in mutation_ids:
        mut = db.get(ProposedMutation, mut_id)
        if mut is None or mut.status != "proposed":
            skipped += 1
            continue

        mut.reviewed_at = now

        try:
            with db.begin_nested():
                error = _apply_mutation(mut, db)
                if error:
                    raise RuntimeError(error)

            mut.status = "applied"
            mut.applied_at = now
            mut.creator_notes = _append_note(mut.creator_notes, _BATCH_REVIEW_MARKER)
            db.add(mut)
            db.commit()
            applied += 1

        except Exception as exc:
            error_msg = str(exc)
            mut.status = "approved"
            mut.creator_notes = _append_note(
                _append_note(mut.creator_notes, f"[apply error] {error_msg}"),
                _BATCH_REVIEW_MARKER,
            )
            db.add(mut)
            db.commit()
            needs_attention += 1

    return {
        "status": "ok",
        "action": "approve",
        "applied": applied,
        "needs_attention": needs_attention,
        "skipped": skipped,
    }


def _batch_reject(mutation_ids: list[str], now: datetime, db: Session) -> dict:
    """Sequential, per-row reject — same re-check/skip rule as
    `_batch_approve`: only `status == 'proposed'` rows are touched."""
    rejected = 0
    skipped = 0
    for mut_id in mutation_ids:
        mut = db.get(ProposedMutation, mut_id)
        if mut is None or mut.status != "proposed":
            skipped += 1
            continue

        mut.status = "rejected"
        mut.reviewed_at = now
        mut.creator_notes = _append_note(mut.creator_notes, _BATCH_REVIEW_MARKER)
        db.add(mut)
        db.commit()
        rejected += 1

    return {
        "status": "ok",
        "action": "reject",
        "rejected": rejected,
        "skipped": skipped,
    }


@router.post("/api/mutations/batch-review")
def batch_review_mutations(
    body: BatchReviewBody,
    db: Session = Depends(get_session),
) -> dict:
    """Approve or reject several proposed mutations in one gesture.

    Sequential, per-row, through the SAME paths as unit review
    (`_apply_mutation` for approve, the unit reject fields for reject).
    Payloads are applied exactly as proposed — no batch payload editing.
    See `_batch_approve`/`_batch_reject` for the per-row skip/isolation
    rules.

    Every processed row gets the `batch-review` marker appended to
    `creator_notes`, so a batch decision is distinguishable from a unit
    decision later.
    """
    if body.action not in ("approve", "reject"):
        raise HTTPException(
            status_code=422, detail="action must be 'approve' or 'reject'"
        )

    now = datetime.now(UTC)
    if body.action == "approve":
        return _batch_approve(body.mutation_ids, now, db)
    return _batch_reject(body.mutation_ids, now, db)
