"""World-tick runner (TICKET-0014, BRIEF-0014-b onward; decomposed at
TICKET-0028, BRIEF-0028-a).

`run_world_tick` advances NPCs off-screen between visits and, for a
location/faction scope, proposes scope-level events on top of the per-NPC
ticks. Context assembly lives in `tick_context.py`; model-output
normalization lives in `tick_normalize.py`. This module keeps only the
orchestration: roster/context assembly per NPC, the model call + parse, the
per-NPC and scope-level proposal loops, and the single end-of-run commit.
Pure decomposition — no logic, prompt, or ordering change from the
pre-BRIEF-0028-a shape (proven by record/replay harness at decomposition
time).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .analyzer import load_analysis_prompt
from .models import Agenda, Character, Entity, FactionMembership, Knowledge, ProposedMutation
from .prompt_registry import effective_model
from .prompt_store import current_prompt
from .tick_context import (
    assemble_faction_event_context,
    assemble_location_event_context,
    assemble_tick_context,
    _reachable_locations,
)
from .tick_normalize import (
    _build_effects_roster,
    _build_roster,
    _normalize_goal_text,
    _normalize_scope_event,
    _normalize_tick_item,
)

_log = logging.getLogger(__name__)

# Scope-level event producer (TICKET-0017, BRIEF-0017-a): location- and
# faction-scoped tick invocations gain ONE additional model call proposing
# event_creation mutations, on top of the per-NPC ticks above. Events are
# decoupled from factions by design (Nia's correction, locked): the SCOPE of
# the tick determines the briefing, not the nature of the event — an
# "npcs"-scoped invocation never produces an event. Quota bounds the emit
# loop (J1 volume by construction, machine-checked like INTERVAL_HOP_RADIUS
# in tick_context.py).
SCOPE_EVENT_QUOTA = 3

# entity_creation quota (TICKET-0019, BRIEF-0019-a): one germ per scope call,
# own counter — the world grows one being at a time per tick scope, decoupled
# from events' and agendas' own budgets.
ENTITY_CREATION_QUOTA = 1


def _tick_npc_setup(db: Session, npc_id: str, interval_label: str) -> dict[str, Any]:
    """Reachable set (TICKET-0015, BRIEF-0015-a) — computed ONCE per NPC,
    BEFORE the model call, so the briefing and the destination resolver
    share the exact same candidate set (RECON-0015 F2)."""
    npc_char = db.get(Character, npc_id)
    from_location_id = npc_char.current_location_id if npc_char else None
    from_entity = db.get(Entity, from_location_id) if from_location_id else None
    from_name = from_entity.name if from_entity else None
    reachable = _reachable_locations(db, from_location_id, interval_label) if from_location_id else []
    destinations = {name.casefold(): loc_id for loc_id, name in reachable}
    return {
        "from_location_id": from_location_id,
        "from_name": from_name,
        "reachable": reachable,
        "destinations": destinations,
    }


def _tick_call_npc_model(briefing: str, interval_label: str, template, version, model: str, host: str) -> list:
    user_message = (
        version.user_template
        .replace("{tick_context}", briefing)
        .replace("{interval_label}", interval_label)
    )
    llm_messages = [
        {"role": "system", "content": version.system_prompt},
        {"role": "user", "content": user_message},
    ]
    raw = ollama_client.chat(llm_messages, model=effective_model(template, model), host=host, format="json")
    return llm_parse.extract_array(raw)


def _tick_build_npc_indexes(db: Session, npc_id: str, npc_name: str, world_id: str, from_location_id: str | None) -> dict[str, Any]:
    roster = _build_roster(db, npc_id, npc_name, from_location_id)
    effects_roster = _build_effects_roster(db, world_id)
    secret_subjects = {
        k.subject.casefold()
        for k in db.exec(
            select(Knowledge).where(Knowledge.entity_id == npc_id, Knowledge.is_secret == True)  # noqa: E712
        ).all()
        if k.subject
    }
    # Owner-restricted agendas_index (TICKET-0020, BRIEF-0020-b): name -> id
    # over ACTIVE agendas OWNED BY THIS NPC ONLY (zero or one, by the
    # one-active-personal-agenda invariant, BRIEF-0020-a) — never the
    # faction/scope indexes, and never widened to agendas the NPC merely
    # serves via a goal_agenda_link.
    npc_agenda_candidates: dict[str, list[str]] = {}
    for agenda in db.exec(
        select(Agenda).where(Agenda.owner_entity_id == npc_id, Agenda.status == "active")
    ).all():
        npc_agenda_candidates.setdefault(agenda.title.casefold(), []).append(agenda.id)
    agendas_index = {title: ids[0] for title, ids in npc_agenda_candidates.items() if len(ids) == 1}
    return {
        "roster": roster,
        "effects_roster": effects_roster,
        "secret_subjects": secret_subjects,
        "agendas_index": agendas_index,
    }


def _tick_new_npc_dedup_state() -> dict[str, Any]:
    return {"goal": set(), "knowledge": set(), "relation": set(), "move": False, "agenda_creation": False}


def _tick_npc_dedup_note(mutation_type: str, payload: dict, state: dict[str, Any]) -> str | None:
    """Emit-time dedup (item 6) — one NET change per key within this NPC's
    item list; keeps the FIRST occurrence, drops the rest. Returns a drop
    note, or None to keep the item (mutating `state` on keep)."""
    if mutation_type == "goal_change":
        key = (payload["action"], _normalize_goal_text(payload["goal"]))
        if key in state["goal"]:
            return f"duplicate goal_change dropped: {payload['action']} {payload['goal']!r}"
        state["goal"].add(key)
    elif mutation_type == "new_knowledge":
        key = (payload["entity_id"], payload["subject"])
        if key in state["knowledge"]:
            return f"duplicate new_knowledge dropped: subject={payload['subject']!r}"
        state["knowledge"].add(key)
    elif mutation_type == "npc_move":
        if state["move"]:
            return f"duplicate npc_move dropped: to={payload['to_name']!r}"
        state["move"] = True
    elif mutation_type == "agenda_creation":
        # At most ONE agenda_creation per per-NPC call (mirrors the
        # scope-level agenda_creation_emitted flag) — the NPC's own
        # canon-existence guard (inside _normalize_tick_item) already blocks
        # a SECOND creation once one is canon; this additional per-call cap
        # blocks two creations proposed in the SAME call, before either is
        # canon.
        if state["agenda_creation"]:
            return f"duplicate agenda_creation dropped: {payload['title']!r}"
        state["agenda_creation"] = True
    elif mutation_type == "agenda_step_change":
        pass  # at most one active agenda/step exists per NPC — no additional dedup needed
    else:  # relation_change
        key = (payload["entity_a_id"], payload["entity_b_id"])
        if key in state["relation"]:
            return f"duplicate relation_change dropped: other={payload['entity_b_id']}"
        state["relation"].add(key)
    return None


def _tick_normalize_npc_items(
    items: list, *, npc_id: str, world_id: str, roster: dict[str, str], secret_subjects: set[str],
    destinations: dict[str, str], from_location_id: str | None, from_name: str | None,
    agendas_index: dict[str, str], effects_roster: dict[str, str], db: Session,
    tick_id: str, now: datetime,
) -> tuple[list[ProposedMutation], int, int, list[str]]:
    rows: list[ProposedMutation] = []
    proposed = 0
    dropped = 0
    notes: list[str] = []
    state = _tick_new_npc_dedup_state()

    for raw_item in items:
        normalized = _normalize_tick_item(
            raw_item, npc_id=npc_id, world_id=world_id, roster=roster,
            secret_subjects=secret_subjects, destinations=destinations,
            from_location_id=from_location_id, from_name=from_name,
            agendas_index=agendas_index, effects_roster=effects_roster, db=db,
        )
        if normalized is None:
            dropped += 1
            continue

        mutation_type = normalized["mutation_type"]
        payload = normalized["payload"]
        drop_note = _tick_npc_dedup_note(mutation_type, payload, state)
        if drop_note is not None:
            dropped += 1
            notes.append(drop_note)
            continue

        rows.append(ProposedMutation(
            world_id=world_id, source_type="world_tick", conversation_id=None, pass_play_id=None,
            tick_id=tick_id, mutation_type=mutation_type, target_table=normalized["target_table"],
            target_id=None, payload=payload, status="proposed", rationale=normalized["rationale"],
            proposed_by="local_ai_tick", proposed_at=now,
        ))
        proposed += 1

    return rows, proposed, dropped, notes


def _tick_process_npc(
    db: Session, npc_id: str, interval_label: str, model: str, host: str, template, version,
    tick_id: str, now: datetime,
) -> tuple[dict, list[ProposedMutation]]:
    """Advance one NPC. Degrade-don't-abort (R3): any exception assembling
    the briefing or calling/parsing the model is recorded as a note for
    this NPC — nothing is written for it, and the other NPCs still
    proceed."""
    npc_entity = db.get(Entity, npc_id)
    npc_name = npc_entity.name if npc_entity else npc_id
    world_id = npc_entity.world_id if npc_entity else ""
    setup = _tick_npc_setup(db, npc_id, interval_label)

    try:
        briefing = assemble_tick_context(npc_id, db, destinations=setup["reachable"])
    except ValueError as exc:
        return {"id": npc_id, "name": npc_name, "proposed": 0, "dropped": 0, "notes": [str(exc)]}, []

    try:
        items = _tick_call_npc_model(briefing, interval_label, template, version, model, host)
    except Exception as exc:  # noqa: BLE001 — one NPC's failure must never abort the others (R3)
        return {"id": npc_id, "name": npc_name, "proposed": 0, "dropped": 0, "notes": [f"model call failed: {exc}"]}, []

    indexes = _tick_build_npc_indexes(db, npc_id, npc_name, world_id, setup["from_location_id"])
    rows, proposed, dropped, notes = _tick_normalize_npc_items(
        items, npc_id=npc_id, world_id=world_id, roster=indexes["roster"],
        secret_subjects=indexes["secret_subjects"], destinations=setup["destinations"],
        from_location_id=setup["from_location_id"], from_name=setup["from_name"],
        agendas_index=indexes["agendas_index"], effects_roster=indexes["effects_roster"],
        db=db, tick_id=tick_id, now=now,
    )
    return {"id": npc_id, "name": npc_name, "proposed": proposed, "dropped": dropped, "notes": notes}, rows


def _tick_scope_setup_location(db: Session, scope_id: str, interval_label: str) -> dict[str, Any]:
    scope_entity = db.get(Entity, scope_id)
    if scope_entity is None:
        raise ValueError(f"location {scope_id!r} not found")
    world_id = scope_entity.world_id
    briefing = assemble_location_event_context(scope_id, db, interval_label=interval_label)
    roster: dict[str, str] = {}
    for char in db.exec(select(Character).where(Character.current_location_id == scope_id)).all():
        member_entity = db.get(Entity, char.id)
        if member_entity is not None:
            roster[member_entity.name.casefold()] = char.id
    return {"world_id": world_id, "briefing": briefing, "roster": roster, "locations_index": {}, "agendas_index": {}}


def _tick_scope_setup_faction(db: Session, scope_id: str) -> dict[str, Any]:
    scope_entity = db.get(Entity, scope_id)
    if scope_entity is None:
        raise ValueError(f"faction {scope_id!r} not found")
    world_id = scope_entity.world_id
    briefing = assemble_faction_event_context(scope_id, db)
    roster: dict[str, str] = {}
    for membership in db.exec(
        select(FactionMembership).where(
            FactionMembership.faction_id == scope_id, FactionMembership.left_at.is_(None)
        )
    ).all():
        member_entity = db.get(Entity, membership.entity_id)
        if member_entity is not None:
            roster[member_entity.name.casefold()] = membership.entity_id
    locations_index = {
        e.name.casefold(): e.id
        for e in db.exec(
            select(Entity).where(Entity.world_id == world_id, Entity.type == "location", Entity.status == "active")
        ).all()
    }
    # A1 structural: agenda types are resolvable ONLY for faction scopes —
    # the location branch above leaves agendas_index empty, making them
    # structurally unresolvable there (RECON-0018 F3).
    agenda_candidates: dict[str, list[str]] = {}
    for agenda in db.exec(
        select(Agenda).where(Agenda.owner_entity_id == scope_id, Agenda.status == "active")
    ).all():
        agenda_candidates.setdefault(agenda.title.casefold(), []).append(agenda.id)
    agendas_index = {title: ids[0] for title, ids in agenda_candidates.items() if len(ids) == 1}
    return {
        "world_id": world_id, "briefing": briefing, "roster": roster,
        "locations_index": locations_index, "agendas_index": agendas_index,
    }


def _tick_scope_setup(db: Session, scope_type: str, scope_id: str, interval_label: str) -> dict[str, Any]:
    if scope_type == "location":
        setup = _tick_scope_setup_location(db, scope_id, interval_label)
    else:  # faction
        setup = _tick_scope_setup_faction(db, scope_id)
    # entity_creation collision guard (TICKET-0019, BRIEF-0019-a, RECON
    # F5/F7): every ACTIVE entity of the world, any type — built once per
    # scope call for BOTH scope types (unlike agendas_index).
    setup["actives_index"] = {
        e.name.casefold(): e.id
        for e in db.exec(
            select(Entity).where(Entity.world_id == setup["world_id"], Entity.status == "active")
        ).all()
    }
    return setup


def _tick_call_scope_model(db: Session, briefing: str, interval_label: str, model: str, host: str) -> list:
    events_template = load_analysis_prompt(db, world_id=None, usage="world_tick_events")
    events_version = current_prompt(db, events_template)
    events_user_message = (
        events_version.user_template
        .replace("{event_context}", briefing)
        .replace("{interval_label}", interval_label)
    )
    events_llm_messages = [
        {"role": "system", "content": events_version.system_prompt},
        {"role": "user", "content": events_user_message},
    ]
    raw_events = ollama_client.chat(
        events_llm_messages, model=effective_model(events_template, model), host=host, format="json",
    )
    return llm_parse.extract_array(raw_events)


def _tick_new_scope_dedup_state() -> dict[str, Any]:
    return {
        "titles": set(), "step_change_agendas": set(), "delegations": set(),
        "agenda_creation": False, "entity_creation": False, "proposed": 0,
    }


def _tick_scope_dedup_note(normalized: dict, state: dict[str, Any]) -> str | None:
    """Both agenda types sit OUTSIDE SCOPE_EVENT_QUOTA — events keep their
    own quota (RECON-0018, brief item 5). `state["proposed"]` is the
    SHARED running count of every scope-level item accepted so far
    (verbatim mechanics) — the event_creation quota gate compares against
    it, not an events-only counter. Returns a drop note, or None to keep
    the item (mutating `state`; for agenda_step_change, popping its
    temporary 'agenda_id' key regardless of outcome)."""
    mutation_type = normalized["mutation_type"]
    if mutation_type == "agenda_step_change":
        agenda_id = normalized.pop("agenda_id")
        if agenda_id in state["step_change_agendas"]:
            return f"duplicate agenda_step_change dropped for agenda {agenda_id!r}"
        state["step_change_agendas"].add(agenda_id)
    elif mutation_type == "agenda_creation":
        if state["agenda_creation"]:
            return "agenda_creation dropped: cap of one per scope call reached"
        state["agenda_creation"] = True
    elif mutation_type == "entity_creation":
        # ENTITY_CREATION_QUOTA=1 — own seen-counter, outside
        # SCOPE_EVENT_QUOTA and the agenda caps (TICKET-0019).
        if state["entity_creation"]:
            return f"entity_creation dropped (quota {ENTITY_CREATION_QUOTA} reached): {normalized['payload']['name']!r}"
        state["entity_creation"] = True
    elif mutation_type == "agenda_delegation":
        key = (normalized["payload"]["npc_id"], _normalize_goal_text(normalized["payload"]["goal"]))
        if key in state["delegations"]:
            return f"duplicate agenda_delegation dropped for npc {normalized['payload']['npc_id']!r}"
        state["delegations"].add(key)
    else:  # event_creation
        event_title = normalized["payload"]["title"]
        title_key = _normalize_goal_text(event_title)
        if title_key in state["titles"]:
            return f"duplicate event_creation dropped: {event_title!r}"
        state["titles"].add(title_key)
        if state["proposed"] >= SCOPE_EVENT_QUOTA:
            return f"event_creation dropped (quota {SCOPE_EVENT_QUOTA} reached): {event_title!r}"
    return None


def _tick_normalize_scope_items(
    event_items: list, *, scope_type: str, scope_id: str, setup: dict[str, Any], db: Session,
    tick_id: str, now: datetime,
) -> tuple[list[ProposedMutation], int, int, list[str]]:
    world_id = setup["world_id"]
    rows: list[ProposedMutation] = []
    dropped_events = 0
    event_notes: list[str] = []
    state = _tick_new_scope_dedup_state()

    for raw_item in event_items:
        normalized = _normalize_scope_event(
            raw_item, scope_type=scope_type, scope_id=scope_id, roster=setup["roster"],
            locations=setup["locations_index"], agendas_index=setup["agendas_index"],
            actives=setup["actives_index"], db=db, notes=event_notes,
        )
        if normalized is None:
            dropped_events += 1
            continue

        drop_note = _tick_scope_dedup_note(normalized, state)
        if drop_note is not None:
            dropped_events += 1
            event_notes.append(drop_note)
            continue

        rows.append(ProposedMutation(
            world_id=world_id, source_type="world_tick", conversation_id=None, pass_play_id=None,
            tick_id=tick_id, mutation_type=normalized["mutation_type"], target_table=normalized["target_table"],
            target_id=None, payload=normalized["payload"], status="proposed", rationale=normalized["rationale"],
            proposed_by="local_ai_tick", proposed_at=now,
        ))
        state["proposed"] += 1

    return rows, state["proposed"], dropped_events, event_notes


def _tick_run_scope_events(
    db: Session, scope_type: str, scope_id: str, interval_label: str, model: str, host: str,
    tick_id: str, now: datetime,
) -> tuple[dict, list[ProposedMutation]]:
    event_notes: list[str] = []
    event_items: list = []
    setup: dict[str, Any] = {
        "world_id": "", "briefing": "", "roster": {}, "locations_index": {}, "agendas_index": {}, "actives_index": {},
    }
    try:
        setup = _tick_scope_setup(db, scope_type, scope_id, interval_label)
        event_items = _tick_call_scope_model(db, setup["briefing"], interval_label, model, host)
    except Exception as exc:  # noqa: BLE001 — degrade-don't-abort (R3), same as the per-NPC loop
        event_notes.append(f"scope event call failed: {exc}")
        event_items = []

    rows, proposed, dropped, item_notes = _tick_normalize_scope_items(
        event_items, scope_type=scope_type, scope_id=scope_id, setup=setup, db=db, tick_id=tick_id, now=now,
    )
    event_notes.extend(item_notes)
    return {"proposed": proposed, "dropped": dropped, "notes": event_notes}, rows


def run_world_tick(
    db: Session,
    npc_ids: list[str],
    interval_label: str,
    model: str = ollama_client.DEFAULT_MODEL,
    host: str = ollama_client.OLLAMA_HOST,
    scope_type: str = "npcs",
    scope_id: str | None = None,
) -> dict:
    """Advance each NPC in `npc_ids` off-screen for `interval_label`.

    One `tick_id` per invocation, shared by every row written. Per NPC,
    degrade-don't-abort (R3, `_tick_process_npc`): any exception assembling
    the briefing or calling/parsing the model is recorded as a note for
    that NPC — nothing is written for it, and the other NPCs still
    proceed. ONE transaction for the whole invocation: every surviving
    proposal across every NPC commits together at the end; a crashed
    invocation (before that point) writes nothing.

    `scope_type`/`scope_id` (TICKET-0017, BRIEF-0017-a): when `scope_type`
    is `"location"` or `"faction"` (never `"npcs"`), ONE additional
    scope-level model call proposes `event_creation` mutations for that
    location/faction, on top of the per-NPC ticks above — sharing this
    invocation's `tick_id` and single end-of-run transaction. Same
    degrade-don't-abort envelope as the per-NPC loop (`_tick_run_scope_events`).

    Returns the R3 summary:
    `{"tick_id", "interval", "npcs": [{"id","name","proposed","dropped","notes"}], "total_proposed"}`,
    plus `"scope_events": {"proposed","dropped","notes"}` when `scope_type`
    is `"location"` or `"faction"`.
    """
    tick_id = str(uuid4())
    template = load_analysis_prompt(db, world_id=None, usage="world_tick")
    version = current_prompt(db, template)
    now = datetime.now(UTC)

    npc_summaries: list[dict] = []
    rows_to_write: list[ProposedMutation] = []

    for npc_id in npc_ids:
        summary, rows = _tick_process_npc(db, npc_id, interval_label, model, host, template, version, tick_id, now)
        npc_summaries.append(summary)
        rows_to_write.extend(rows)

    scope_events: dict | None = None
    if scope_type in ("location", "faction"):
        scope_events, scope_rows = _tick_run_scope_events(
            db, scope_type, scope_id, interval_label, model, host, tick_id, now
        )
        rows_to_write.extend(scope_rows)

    for row in rows_to_write:
        db.add(row)
    db.commit()

    result = {
        "tick_id": tick_id,
        "interval": interval_label,
        "npcs": npc_summaries,
        "total_proposed": sum(n["proposed"] for n in npc_summaries),
    }
    if scope_events is not None:
        result["scope_events"] = scope_events
    return result
