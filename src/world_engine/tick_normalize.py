"""World-tick model-output normalization (TICKET-0014 onward; decomposed
from `tick.py` at TICKET-0028, BRIEF-0028-a).

Maps raw model items to the tick's closed schemas — the scope-level events
contract (`_normalize_scope_event`) and the per-NPC contract
(`_normalize_tick_item`) — plus the shared roster/effects helpers both
`run_world_tick` (`tick.py`) and these normalizers use. Pure move, no logic
change: every branch below is the same code that used to live inline in
`tick.py`, split at its existing per-mutation-type seams so each piece fits
under the 80-line function ceiling (R1).

Closed contract (unlike conversation analysis): only the types in
`_TICK_MUTATION_TYPES` are ever proposed by a per-NPC tick call; the
scope-level call has its own, separate closed set of types, dispatched
entirely inside `_normalize_scope_event`. Anything else is dropped with a
note (item 4, TICKET-0014).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlmodel import Session, select

from .analyzer import _GOAL_ACTION_MAP, _MUTATION_TYPE_MAP, _content_to_subject_slug
from .models import Agenda, AgendaStep, Character, Entity, Faction, Relation
from .tick_context import _perceived_target

_log = logging.getLogger(__name__)

# DELIBERATELY EXTENDED (TICKET-0020, BRIEF-0020-b): `agenda_step_change`/
# `agenda_creation` join the per-NPC contract, restricted to agendas the NPC
# itself OWNS (its own owner-restricted `agendas_index`; `owner_entity_id`
# FORCED to `npc_id` on creation, never read from the payload — the H1/O1
# forcing precedent). This supersedes the 0018/0017 doctrine that these two
# types were "FACTION SCOPE ONLY" among SCOPE events — they remain exactly
# that among SCOPE events (`_normalize_scope_event`'s explicit
# `scope_type == "faction"` gate, unchanged); the per-NPC path is a SEPARATE,
# newly-opened door, not a widening of the scope gate.
_TICK_MUTATION_TYPES = frozenset({
    "goal_change", "relation_change", "new_knowledge", "npc_move",
    "agenda_step_change", "agenda_creation",
})

# Tick-local alias map (TICKET-0015, BRIEF-0015-a): extends the shared
# analyzer map with npc_move aliases WITHOUT mutating it — conversation
# analysis and overhearing must never propose movement (RECON-0015 F4).
_TICK_TYPE_ALIASES: dict[str, str] = {
    **_MUTATION_TYPE_MAP,
    "npc_move": "npc_move",
    "move": "npc_move",
    "movement": "npc_move",
    # Per-NPC agenda extension (TICKET-0020, BRIEF-0020-b) — absent from the
    # shared analyzer map by design (the conversation/analyzer path must
    # never propose these), so they need their own local entries here, same
    # idiom as npc_move above.
    "agenda_step_change": "agenda_step_change",
    "agenda_creation": "agenda_creation",
}

# event.type vocabulary (world-engine-schema.md); anything else falls back to
# "other" rather than being dropped. Imported by several crud modules and
# entity_author.py for their own type-field validation — external fan-out,
# not a tick-only constant.
_EVENT_TYPES = frozenset(
    {"political", "magical", "criminal", "military", "social", "mystery", "other"}
)


def _normalize_goal_text(text: str | None) -> str:
    """Casefold + whitespace-collapse for goal-text equality (twin of
    cockpit/app.py's `_normalize_goal_text`, replicated rather than imported
    to keep this domain free of a cockpit.app dependency — same discipline
    as BRIEF-0014-a's local helper replication)."""
    return " ".join(str(text or "").split()).casefold()


def _build_roster(
    db: Session, npc_id: str, npc_name: str, location_id: str | None
) -> dict[str, str]:
    """name.casefold() -> id, built from EXACTLY what the tick briefing names:
    the ticked NPC itself, characters at its `current_location_id` (QUI EST
    AUTOUR), and the targets of its perceived relations (TES RELATIONS). No
    faction-mate expansion. A casefolded name carried by two different ids is
    AMBIGUOUS and removed from the roster — resolution then fails for that
    name, and the caller drops the item with a note rather than guess.
    """
    candidates: dict[str, list[str]] = {}

    def _add(name: str, entity_id: str) -> None:
        candidates.setdefault(name.casefold(), []).append(entity_id)

    _add(npc_name, npc_id)

    if location_id:
        present = db.exec(
            select(Character).where(Character.current_location_id == location_id)
        ).all()
        for other_char in present:
            if other_char.id == npc_id:
                continue
            other_entity = db.get(Entity, other_char.id)
            if other_entity is not None:
                _add(other_entity.name, other_char.id)

    relations = db.exec(
        select(Relation).where(
            (Relation.entity_a_id == npc_id) | (Relation.entity_b_id == npc_id)
        )
    ).all()
    for rel in relations:
        target_id = _perceived_target(rel, npc_id)
        if target_id:
            target_entity = db.get(Entity, target_id)
            if target_entity is not None:
                _add(target_entity.name, target_id)

    return {name: ids[0] for name, ids in candidates.items() if len(ids) == 1}


def _build_effects_roster(db: Session, world_id: str) -> dict[str, str]:
    """name.casefold() -> entity_id for every ACTIVE character (`vital_status
    == 'alive'`) and ACTIVE faction in the world (TICKET-0024, BRIEF-0024-c)
    — feeds completion-effect name resolution (`relation_delta`/
    `ledger_transfer` target/from/to, `role_change` faction) at
    tick-normalize time. Same ambiguity discipline as `_build_roster`/
    `entity_author.build_world_roster`: a casefolded name shared by two ids
    is removed from the roster, resolution then fails cleanly for that
    name rather than guessing."""
    candidates: dict[str, list[str]] = {}

    char_rows = db.exec(
        select(Entity.id, Entity.name)
        .join(Character, Character.id == Entity.id)
        .where(
            Entity.world_id == world_id,
            Entity.status == "active",
            Character.vital_status == "alive",
        )
    ).all()
    for entity_id, name in char_rows:
        candidates.setdefault(name.casefold(), []).append(entity_id)

    faction_rows = db.exec(
        select(Entity.id, Entity.name)
        .join(Faction, Faction.id == Entity.id)
        .where(Entity.world_id == world_id, Entity.status == "active")
    ).all()
    for entity_id, name in faction_rows:
        candidates.setdefault(name.casefold(), []).append(entity_id)

    return {name: ids[0] for name, ids in candidates.items() if len(ids) == 1}


def _normalize_effect_item(raw_eff: Any, *, effects_roster: dict[str, str]) -> dict | None:
    """One raw completion effect -> the closed effect shape, or `None` to
    drop it (TICKET-0024, BRIEF-0024-c) — names resolve to ids here, the
    model never emits ids. Malformed or an unresolved name DROPS the
    single effect with a note; the completion itself survives (apply-time,
    `_apply_completion_effects`, stays whole-reject because canon is at
    stake there — this is pre-canon and cheap)."""
    if not isinstance(raw_eff, dict):
        _log.warning("[tick] dropped effect: not a dict — %r", raw_eff)
        return None
    eff_type = str(raw_eff.get("type") or "").strip().casefold()

    if eff_type == "relation_delta":
        target_name = str(raw_eff.get("target") or "").strip()
        target_id = effects_roster.get(target_name.casefold())
        relation_type = str(raw_eff.get("relation_type") or "").strip()
        try:
            value = int(raw_eff.get("value"))
        except (TypeError, ValueError):
            _log.warning("[tick] dropped effect relation_delta: invalid value %r", raw_eff.get("value"))
            return None
        if not target_id:
            _log.warning("[tick] dropped effect relation_delta: unresolved target %r", target_name)
            return None
        if not relation_type:
            _log.warning("[tick] dropped effect relation_delta: missing relation_type")
            return None
        return {
            "type": "relation_delta", "target_entity_id": target_id,
            "value": value, "relation_type": relation_type,
        }

    if eff_type == "ledger_transfer":
        from_name = str(raw_eff.get("from") or "").strip()
        to_name = str(raw_eff.get("to") or "").strip()
        from_id = effects_roster.get(from_name.casefold())
        to_id = effects_roster.get(to_name.casefold())
        try:
            amount = int(raw_eff.get("amount"))
        except (TypeError, ValueError):
            _log.warning("[tick] dropped effect ledger_transfer: invalid amount %r", raw_eff.get("amount"))
            return None
        if not from_id or not to_id:
            _log.warning("[tick] dropped effect ledger_transfer: unresolved from/to — %r/%r", from_name, to_name)
            return None
        return {
            "type": "ledger_transfer", "from_entity_id": from_id, "to_entity_id": to_id,
            "amount": amount, "reason": str(raw_eff.get("reason") or "") or None,
        }

    if eff_type == "role_change":
        faction_name = str(raw_eff.get("faction") or "").strip()
        faction_id = effects_roster.get(faction_name.casefold())
        role = str(raw_eff.get("role") or "").strip()
        if not faction_id or not role:
            _log.warning("[tick] dropped effect role_change: unresolved faction %r or empty role", faction_name)
            return None
        return {
            "type": "role_change", "faction_id": faction_id, "role": role,
            "declare": bool(raw_eff.get("declare", False)),
        }

    _log.warning("[tick] dropped effect: unknown type %r", raw_eff.get("type"))
    return None


def _normalize_effects_list(raw_effects: Any, *, effects_roster: dict[str, str]) -> list[dict]:
    """Normalize a raw `effects` list: drop malformed/unresolved items,
    then cap at 3 keeping the first 3 (N1), noting the excess."""
    if not isinstance(raw_effects, list):
        return []
    normalized = [
        item for raw_eff in raw_effects
        if (item := _normalize_effect_item(raw_eff, effects_roster=effects_roster)) is not None
    ]
    if len(normalized) > 3:
        _log.warning("[tick] effects: %d excess effect(s) dropped (cap 3)", len(normalized) - 3)
        normalized = normalized[:3]
    return normalized


# -----------------------------------------------------------------------------
# Scope-level events normalizer (TICKET-0017, BRIEF-0017-a onward)
# -----------------------------------------------------------------------------

def _tick_normalize_scope_agenda_step_change(
    payload_in: dict, rationale: str, *, scope_type: str, agendas_index: dict[str, str],
    actives: dict[str, str], db: Session, notes: list[str],
) -> dict | None:
    """FACTION SCOPE ONLY (TICKET-0018, BRIEF-0018-a)."""
    if scope_type != "faction":
        notes.append("dropped agenda_step_change: not a faction scope")
        return None

    agenda_title = str(payload_in.get("agenda") or "").strip()
    agenda_id = agendas_index.get(agenda_title.casefold()) if agenda_title else None
    if not agenda_id:
        notes.append(f"dropped agenda_step_change: unresolved agenda {agenda_title!r}")
        return None

    action = str(payload_in.get("action") or "").strip().casefold()
    if action not in ("complete", "fail"):
        notes.append(f"dropped agenda_step_change: unrecognised action {payload_in.get('action')!r}")
        return None

    # The step is NEVER addressed by the model — it is derived here as the
    # agenda's unique active step (F2 guarantees at most one), loaded fresh
    # so a since-closed agenda drops with a note rather than acting on stale
    # state.
    active_step = db.exec(
        select(AgendaStep).where(AgendaStep.agenda_id == agenda_id, AgendaStep.status == "active")
    ).first()
    if active_step is None:
        notes.append(f"dropped agenda_step_change: agenda {agenda_title!r} has no active step (closed since)")
        return None

    outcome = payload_in.get("outcome")
    outcome = str(outcome).strip() or None if outcome else None
    step_id = active_step.id

    step_payload = {
        "agenda_id": agenda_id,
        "step_id": step_id,
        "action": action,
        "outcome": outcome,
    }
    # Completion effects (TICKET-0024, BRIEF-0024-c) — `complete` only.
    if action == "complete" and isinstance(payload_in.get("effects"), list):
        step_payload["effects"] = _normalize_effects_list(payload_in["effects"], effects_roster=actives)

    return {
        "mutation_type": "agenda_step_change",
        "target_table": "agenda_step",
        "target_id": None,
        "payload": step_payload,
        "rationale": rationale,
        "agenda_id": agenda_id,
    }


def _tick_normalize_scope_agenda_creation(
    payload_in: dict, rationale: str, *, scope_type: str, scope_id: str, notes: list[str],
) -> dict | None:
    """FACTION SCOPE ONLY (TICKET-0018, BRIEF-0018-a)."""
    if scope_type != "faction":
        notes.append("dropped agenda_creation: not a faction scope")
        return None

    title = str(payload_in.get("title") or "").strip()
    if not title:
        notes.append("dropped agenda_creation: empty title")
        return None

    raw_steps = payload_in.get("steps")
    if not isinstance(raw_steps, list):
        notes.append(f"dropped agenda_creation {title!r}: steps not a list")
        return None
    steps = [str(s).strip() for s in raw_steps if str(s).strip()]
    if not (2 <= len(steps) <= 5):
        notes.append(f"dropped agenda_creation {title!r}: steps count {len(steps)} out of range 2-5")
        return None

    return {
        "mutation_type": "agenda_creation",
        "target_table": "agenda",
        "target_id": None,
        # owner_entity_id is FORCED from scope_id — never read from the
        # model's payload.
        "payload": {"owner_entity_id": scope_id, "title": title, "steps": steps},
        "rationale": rationale,
    }


def _tick_normalize_scope_agenda_delegation(
    payload_in: dict, rationale: str, *, scope_type: str, scope_id: str,
    roster: dict[str, str], agendas_index: dict[str, str], notes: list[str],
) -> dict | None:
    """FACTION SCOPE ONLY (TICKET-0020, BRIEF-0020-b)."""
    if scope_type != "faction":
        notes.append("dropped agenda_delegation: not a faction scope")
        return None

    npc_name = str(payload_in.get("npc") or "").strip()
    npc_id = roster.get(npc_name.casefold()) if npc_name else None
    # The faction id itself is appended to this scope's roster (see
    # `_normalize_scope_event`'s docstring) — a delegation targets a MEMBER,
    # never the faction tasking itself.
    if npc_id == scope_id:
        npc_id = None
    if not npc_id:
        notes.append(f"dropped agenda_delegation: unresolved npc {npc_name!r}")
        return None

    goal_text = str(payload_in.get("goal") or "").strip()
    if not goal_text:
        notes.append("dropped agenda_delegation: empty goal text")
        return None

    agenda_title = str(payload_in.get("agenda") or "").strip()
    agenda_id = agendas_index.get(agenda_title.casefold()) if agenda_title else None
    if not agenda_id:
        notes.append(f"dropped agenda_delegation: unresolved agenda {agenda_title!r}")
        return None

    # O1 relaxation, SCOPED to this branch only: horizon is the sole field
    # anywhere in this domain read from a raw payload rather than
    # hard-coded — clamped to 'short' on anything unrecognised (missing
    # included), never dropped for a bad horizon alone.
    raw_horizon = str(payload_in.get("horizon") or "").strip().casefold()
    if raw_horizon in ("short", "long"):
        horizon = raw_horizon
    else:
        horizon = "short"
        notes.append(
            f"agenda_delegation {agenda_title!r}: horizon "
            f"{payload_in.get('horizon')!r} clamped to 'short'"
        )

    return {
        "mutation_type": "agenda_delegation",
        "target_table": "npc_goal",
        "target_id": None,
        "payload": {"npc_id": npc_id, "goal": goal_text, "horizon": horizon, "agenda_id": agenda_id},
        "rationale": rationale,
    }


def _tick_normalize_scope_entity_creation(
    payload_in: dict, rationale: str, *, actives: dict[str, str], notes: list[str],
) -> dict | None:
    """BOTH SCOPE TYPES (TICKET-0019, BRIEF-0019-a)."""
    # Literal frozenset mirroring entity_author._TYPE_FIELDS' keys — never
    # import entity_author into this domain (RECON F1's generation-side
    # purity stays there; this module only validates the germ's shape).
    entity_creation_types = frozenset({"character", "location", "faction"})

    entity_type = str(payload_in.get("entity_type") or "").strip().casefold()
    if entity_type not in entity_creation_types:
        notes.append(f"dropped entity_creation: unrecognised entity_type {payload_in.get('entity_type')!r}")
        return None

    name = str(payload_in.get("name") or "").strip()
    if not name:
        notes.append("dropped entity_creation: empty name")
        return None

    concept = str(payload_in.get("concept") or "").strip()
    if not concept:
        notes.append(f"dropped entity_creation {name!r}: empty concept")
        return None

    # Collision guard, emit-time (RECON F5) — any active entity of the
    # world, any type: a faction named like a location is confusion, not
    # richness. Re-checked fresh at approval time (F3/F5's other half).
    if name.casefold() in actives:
        notes.append(f"dropped entity_creation: an active entity already named {name!r}")
        return None

    anchor = payload_in.get("anchor")
    anchor = str(anchor).strip() or None if anchor else None

    payload_out: dict[str, Any] = {"entity_type": entity_type, "name": name, "concept": concept}
    if anchor:
        payload_out["anchor"] = anchor

    return {
        "mutation_type": "entity_creation",
        "target_table": "entity",
        "target_id": None,
        "payload": payload_out,
        "rationale": rationale,
    }


def _tick_normalize_scope_event_creation(
    payload_in: dict, rationale: str, *, scope_type: str, scope_id: str,
    roster: dict[str, str], locations: dict[str, str], notes: list[str],
) -> dict | None:
    """The default shape (TICKET-0017, BRIEF-0017-a)."""
    title = str(payload_in.get("title") or "").strip()
    if not title:
        notes.append("dropped event_creation: empty title")
        return None

    description = payload_in.get("description")
    description = str(description).strip() or None if description else None

    raw_type = str(payload_in.get("type") or "").strip().casefold()
    event_type = raw_type if raw_type in _EVENT_TYPES else "other"

    raw_status = str(payload_in.get("knowledge_status") or "").strip().casefold()
    if raw_status in ("secret", "public"):
        knowledge_status = raw_status
    else:
        knowledge_status = "secret"
        notes.append(
            f"event {title!r}: knowledge_status {payload_in.get('knowledge_status')!r} "
            "coerced to 'secret'"
        )

    involved_entities: list[str] = []
    for name in payload_in.get("involved_entities") or []:
        entity_id = roster.get(str(name).casefold())
        if entity_id:
            involved_entities.append(entity_id)
        else:
            notes.append(f"event {title!r}: unresolved involved_entities name {name!r} dropped")
    if scope_type == "faction" and scope_id not in involved_entities:
        involved_entities.append(scope_id)

    if scope_type == "location":
        location_id = scope_id
    else:
        location_name = str(payload_in.get("location") or "").strip()
        location_id = locations.get(location_name.casefold()) if location_name else None

    return {
        "mutation_type": "event_creation",
        "target_table": "event",
        "target_id": None,
        "payload": {
            "title": title,
            "description": description,
            "type": event_type,
            "knowledge_status": knowledge_status,
            "involved_entities": involved_entities,
            "location_id": location_id,
        },
        "rationale": rationale,
    }


def _normalize_scope_event(
    raw_item: Any,
    *,
    scope_type: str,
    scope_id: str,
    roster: dict[str, str],
    locations: dict[str, str],
    agendas_index: dict[str, str],
    actives: dict[str, str],
    db: Session,
    notes: list[str],
) -> dict | None:
    """Map one raw model item to the scope-level schema, or None to drop it
    (TICKET-0017, BRIEF-0017-a; grown to four types TICKET-0018/0019,
    BRIEF-0018-a/BRIEF-0019-a; `agenda_delegation` added TICKET-0020,
    BRIEF-0020-b). Separate from `_normalize_tick_item` — `event_creation`,
    `entity_creation`, and `agenda_delegation` never enter the per-NPC
    frozenset; `agenda_step_change`/`agenda_creation` DO now also enter it,
    but via a wholly separate branch in `_normalize_tick_item`, restricted to
    agendas the NPC owns (BRIEF-0020-b) — this function's own dispatch for
    those two types stays faction-scope-only, unchanged.

    `roster` is name.casefold() -> id for this scope (location: public
    occupants; faction: members, with the faction id itself appended here
    for faction scope). `locations` is name.casefold() -> id for ACTIVE
    locations of the world (faction scope's optional payload location
    resolution only). `agendas_index` is name.casefold() -> id for ACTIVE
    agendas of the faction (empty for a location scope). `actives` is
    name.casefold() -> id for EVERY active entity of the world, any type —
    the entity_creation collision guard. `notes` is the caller's shared
    notes list — parse-time drops and clamps are appended to it.
    """
    if not isinstance(raw_item, dict):
        notes.append(f"dropped scope item: not a dict — {raw_item!r}")
        return None

    raw_mutation_type = str(raw_item.get("mutation_type") or "").strip().casefold()
    payload_in = raw_item.get("payload") if isinstance(raw_item.get("payload"), dict) else {}
    rationale = str(raw_item.get("rationale") or "")

    if raw_mutation_type == "agenda_step_change":
        return _tick_normalize_scope_agenda_step_change(
            payload_in, rationale, scope_type=scope_type, agendas_index=agendas_index,
            actives=actives, db=db, notes=notes,
        )
    if raw_mutation_type == "agenda_creation":
        return _tick_normalize_scope_agenda_creation(
            payload_in, rationale, scope_type=scope_type, scope_id=scope_id, notes=notes,
        )
    if raw_mutation_type == "agenda_delegation":
        return _tick_normalize_scope_agenda_delegation(
            payload_in, rationale, scope_type=scope_type, scope_id=scope_id,
            roster=roster, agendas_index=agendas_index, notes=notes,
        )
    if raw_mutation_type == "entity_creation":
        return _tick_normalize_scope_entity_creation(payload_in, rationale, actives=actives, notes=notes)

    return _tick_normalize_scope_event_creation(
        payload_in, rationale, scope_type=scope_type, scope_id=scope_id,
        roster=roster, locations=locations, notes=notes,
    )


# -----------------------------------------------------------------------------
# Per-NPC normalizer (TICKET-0014, BRIEF-0014-b onward)
# -----------------------------------------------------------------------------

def _tick_normalize_goal_change(
    payload_in: dict, *, agendas_index: dict[str, str], effects_roster: dict[str, str], npc_id: str,
) -> tuple[dict, str] | None:
    raw_action = str(payload_in.get("action") or "").strip().lower()
    action = _GOAL_ACTION_MAP.get(raw_action)
    goal_text = str(
        payload_in.get("goal") or payload_in.get("description") or payload_in.get("content") or ""
    ).strip()
    if action is None or not goal_text:
        _log.warning("[tick] dropped goal_change: unrecognised action or empty goal text — %r", payload_in)
        return None
    payload = {"npc_id": npc_id, "action": action, "goal": goal_text}

    # Own-agenda reference (TICKET-0020, BRIEF-0020-b), create_short only:
    # an optional agenda TITLE, resolved against the SAME owner-only
    # agendas_index as agenda_step_change/agenda_creation. Unknown title ->
    # the key is dropped with a note; the goal_change itself survives (the
    # reference is an enrichment, not a requirement).
    if action == "create_short":
        agenda_title = payload_in.get("agenda")
        if agenda_title:
            agenda_id = agendas_index.get(str(agenda_title).strip().casefold())
            if agenda_id:
                payload["agenda_id"] = agenda_id
            else:
                _log.warning("[tick] goal_change: unresolved agenda reference %r dropped", agenda_title)

    # Completion effects (TICKET-0024, BRIEF-0024-c) — `complete` only.
    if action == "complete" and isinstance(payload_in.get("effects"), list):
        payload["effects"] = _normalize_effects_list(payload_in["effects"], effects_roster=effects_roster)
    return payload, "npc_goal"


def _tick_normalize_npc_agenda_step_change(
    payload_in: dict, *, agendas_index: dict[str, str], effects_roster: dict[str, str], db: Session,
) -> tuple[dict, str] | None:
    """Per-NPC extension (TICKET-0020, BRIEF-0020-b) — mirrors the
    scope-level branch, but resolved against the OWNER-RESTRICTED per-NPC
    agendas_index (at most one entry, the 0020-a invariant) rather than a
    faction's."""
    agenda_title = str(payload_in.get("agenda") or "").strip()
    agenda_id = agendas_index.get(agenda_title.casefold()) if agenda_title else None
    if not agenda_id:
        _log.warning("[tick] dropped agenda_step_change: unresolved agenda %r", agenda_title)
        return None

    raw_step_action = str(payload_in.get("action") or "").strip().casefold()
    if raw_step_action not in ("complete", "fail"):
        _log.warning("[tick] dropped agenda_step_change: unrecognised action %r", payload_in.get("action"))
        return None

    # The step is NEVER addressed by the model — derived here as the
    # agenda's unique active step, loaded fresh so a since-closed agenda
    # drops with a note rather than acting on stale state.
    active_step = db.exec(
        select(AgendaStep).where(AgendaStep.agenda_id == agenda_id, AgendaStep.status == "active")
    ).first()
    if active_step is None:
        _log.warning("[tick] dropped agenda_step_change: agenda %r has no active step (closed since)", agenda_title)
        return None

    step_outcome = payload_in.get("outcome")
    step_outcome = str(step_outcome).strip() or None if step_outcome else None
    step_id = active_step.id
    payload = {
        "agenda_id": agenda_id,
        "step_id": step_id,
        "action": raw_step_action,
        "outcome": step_outcome,
    }
    # Completion effects (TICKET-0024, BRIEF-0024-c) — `complete` only.
    if raw_step_action == "complete" and isinstance(payload_in.get("effects"), list):
        payload["effects"] = _normalize_effects_list(payload_in["effects"], effects_roster=effects_roster)
    return payload, "agenda_step"


def _tick_normalize_npc_agenda_creation(payload_in: dict, *, npc_id: str, db: Session) -> tuple[dict, str] | None:
    """Per-NPC extension (TICKET-0020, BRIEF-0020-b): owner_entity_id is
    FORCED to npc_id — never read from the payload (H1/O1 forcing
    precedent). CANON-EXISTENCE dedup (0014 tick-guard doctrine): the NPC
    may own at most one active agenda (0020-a invariant) — a second
    creation is dropped here, never proposed."""
    agenda_title = str(payload_in.get("title") or "").strip()
    if not agenda_title:
        _log.warning("[tick] dropped agenda_creation: empty title")
        return None

    raw_agenda_steps = payload_in.get("steps")
    if not isinstance(raw_agenda_steps, list):
        _log.warning("[tick] dropped agenda_creation %r: steps not a list", agenda_title)
        return None
    agenda_steps = [str(s).strip() for s in raw_agenda_steps if str(s).strip()]
    if not (2 <= len(agenda_steps) <= 5):
        _log.warning("[tick] dropped agenda_creation %r: steps count %d out of range 2-5", agenda_title, len(agenda_steps))
        return None

    existing_own_agenda = db.exec(
        select(Agenda).where(Agenda.owner_entity_id == npc_id, Agenda.status == "active")
    ).first()
    if existing_own_agenda is not None:
        _log.warning("[tick] dropped agenda_creation %r: NPC already owns an active agenda", agenda_title)
        return None

    return {"owner_entity_id": npc_id, "title": agenda_title, "steps": agenda_steps}, "agenda"


def _tick_normalize_relation_change(payload_in: dict, *, npc_id: str, roster: dict[str, str]) -> tuple[dict, str] | None:
    other_name = str(payload_in.get("other") or "").strip()
    other_id = roster.get(other_name.casefold())
    if not other_id:
        _log.warning("[tick] dropped relation_change: unresolved counterpart %r", other_name)
        return None
    try:
        delta = int(payload_in.get("intensity_delta"))
    except (TypeError, ValueError):
        _log.warning("[tick] dropped relation_change: missing/invalid intensity_delta — %r", payload_in)
        return None
    payload = {
        "entity_a_id": npc_id,
        "entity_b_id": other_id,
        "relation_type": str(payload_in.get("relation_type") or "passive_attention"),
        "intensity_delta": delta,
    }
    return payload, "relation"


def _tick_normalize_npc_move(
    payload_in: dict, *, npc_id: str, from_location_id: str | None, from_name: str | None,
    destinations: dict[str, str],
) -> tuple[dict, str] | None:
    if not from_location_id:
        _log.warning("[tick] dropped npc_move: NPC has no current location")
        return None
    destination_name = str(payload_in.get("destination") or "").strip()
    to_id = destinations.get(destination_name.casefold())
    if not destination_name or not to_id:
        _log.warning("[tick] dropped npc_move: unresolved or out-of-radius destination %r", destination_name)
        return None
    payload = {
        "npc_id": npc_id,
        "from_location_id": from_location_id,
        "to_location_id": to_id,
        "from_name": from_name or "",
        "to_name": destination_name,
    }
    return payload, "character"


def _tick_normalize_new_knowledge(
    payload_in: dict, *, npc_id: str, roster: dict[str, str], secret_subjects: set[str],
) -> tuple[dict, str] | None:
    recipient = str(payload_in.get("recipient") or "self").strip()
    if recipient.casefold() == "self":
        entity_id = npc_id
    else:
        entity_id = roster.get(recipient.casefold())
        if not entity_id:
            _log.warning("[tick] dropped new_knowledge: unresolved recipient %r", recipient)
            return None
    content = str(payload_in.get("content") or "").strip()
    if not content:
        _log.warning("[tick] dropped new_knowledge: empty content")
        return None
    subject = str(payload_in.get("subject") or "").strip() or _content_to_subject_slug(content)

    # Z3 floor (verbatim mechanics) — mechanical provenance only, never
    # touches is_secret: confidentiality is the receiving NPC's disposition
    # (model proposes, creator judges).
    secret_derived = bool(payload_in.get("secret_derived", False))
    subject_cf = subject.casefold()
    content_cf = content.casefold()
    if subject_cf in secret_subjects or any(s in content_cf for s in secret_subjects):
        secret_derived = True

    payload = {
        "entity_id": entity_id,
        "subject": subject,
        "level": str(payload_in.get("level") or "rumor"),
        "content": content,
        "source": str(payload_in.get("source") or "world_tick"),
        "is_secret": bool(payload_in.get("is_secret", False)),
        "secret_derived": secret_derived,
    }
    return payload, "knowledge"


def _normalize_tick_item(
    raw_item: Any,
    *,
    npc_id: str,
    world_id: str,
    roster: dict[str, str],
    secret_subjects: set[str],
    destinations: dict[str, str],
    from_location_id: str | None,
    from_name: str | None,
    agendas_index: dict[str, str],
    effects_roster: dict[str, str],
    db: Session,
) -> dict | None:
    """Map one raw model item to the tick's CLOSED schema, or None to drop it.

    Unlike `analyzer._normalize_to_schema`, the tick's contract accepts only
    goal_change | relation_change | new_knowledge | npc_move |
    agenda_step_change | agenda_creation — anything else (including the
    fallback `other`) is dropped, never proposed. `npc_id`/`entity_a_id`/
    `from_location_id`/`owner_entity_id` are FORCED from parameters
    (O1-mirror), never read from the model's payload.

    `destinations` (TICKET-0015, BRIEF-0015-a) is name.casefold() -> id,
    built by the caller from the SAME `_reachable_locations` pair list the
    briefing showed — destination resolution reads ONLY this candidate set,
    never all locations (RECON-0015 F2).
    """
    del world_id  # reserved: no payload shape carries it (entity-scoped, not world-keyed)

    if not isinstance(raw_item, dict):
        _log.warning("[tick] dropped: not a dict — %r", raw_item)
        return None

    raw_mt = str(raw_item.get("mutation_type") or "").lower()
    mutation_type = _TICK_TYPE_ALIASES.get(raw_mt)
    if mutation_type not in _TICK_MUTATION_TYPES:
        _log.warning("[tick] dropped: unrecognised or out-of-contract mutation_type %r", raw_item.get("mutation_type"))
        return None

    payload_in = raw_item.get("payload") if isinstance(raw_item.get("payload"), dict) else {}

    if mutation_type == "goal_change":
        outcome = _tick_normalize_goal_change(payload_in, agendas_index=agendas_index, effects_roster=effects_roster, npc_id=npc_id)
    elif mutation_type == "agenda_step_change":
        outcome = _tick_normalize_npc_agenda_step_change(payload_in, agendas_index=agendas_index, effects_roster=effects_roster, db=db)
    elif mutation_type == "agenda_creation":
        outcome = _tick_normalize_npc_agenda_creation(payload_in, npc_id=npc_id, db=db)
    elif mutation_type == "relation_change":
        outcome = _tick_normalize_relation_change(payload_in, npc_id=npc_id, roster=roster)
    elif mutation_type == "npc_move":
        outcome = _tick_normalize_npc_move(
            payload_in, npc_id=npc_id, from_location_id=from_location_id, from_name=from_name,
            destinations=destinations,
        )
    else:  # new_knowledge
        outcome = _tick_normalize_new_knowledge(payload_in, npc_id=npc_id, roster=roster, secret_subjects=secret_subjects)

    if outcome is None:
        return None
    payload, target_table = outcome

    rationale = raw_item.get("rationale")
    if not rationale:
        for key in ("reason", "details", "content", "value"):
            if payload_in.get(key):
                rationale = payload_in[key]
                break
    rationale = str(rationale or "")

    return {
        "mutation_type": mutation_type,
        "target_table": target_table,
        "target_id": None,
        "payload": payload,
        "rationale": rationale,
    }
