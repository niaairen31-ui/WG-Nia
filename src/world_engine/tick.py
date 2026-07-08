"""World-tick context assembly (TICKET-0014, BRIEF-0014-a).

`assemble_tick_context` builds the full-interiority briefing that drives one
NPC's off-screen advancement between visits (T1, amended at intake). Unlike
`assemble_npc_context` (dialogue, gated by an interlocutor's relation), a tick
has no interlocutor: the NPC judges its own situation, so this is a
conscious, logged exception to the secrets-excluded-at-query doctrine — the
briefing includes the NPC's own `is_secret` knowledge and secret faction
memberships with TRUE roles, structurally confined to this module's
allowlisted call sites (see `tooling/verify/checks/world_tick.py`) and never
rendered to a player or MJ surface.

Kept free of any `context.py` import (drafting decision #5, BRIEF-0014-a):
the small helpers it shares with the dialogue assembler are replicated
locally rather than imported, so this module's AST stays self-contained and
`world_tick.py`'s rules stay simple.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlmodel import Session, select

from . import ollama_client
from .analyzer import (
    _MUTATION_TYPE_MAP,
    _content_to_subject_slug,
    _extract_json_array,
    _GOAL_ACTION_MAP,
    load_analysis_prompt,
)
from .models import (
    Character,
    Entity,
    Faction,
    FactionMembership,
    Knowledge,
    Location,
    NpcGoal,
    ProposedMutation,
    Relation,
)
from .prompt_registry import effective_model
from .prompt_store import current_prompt

H_IDENTITY = "QUI TU ES"
H_GOALS = "TES OBJECTIFS"
H_KNOWLEDGE = "CE QUE TU SAIS"
H_RELATIONS = "TES RELATIONS"
H_AFFILIATIONS = "TES AFFILIATIONS"
H_SETTING = "OÙ TU TE TROUVES"
H_DESTINATIONS = "OÙ TU PEUX ALLER"
H_COMPANY = "QUI EST AUTOUR"

_BOUNDARY = (
    "Tu ne sais que ce qui est écrit ci-dessus. N'invente aucune personne, "
    "aucun lieu, aucun fait au-delà de ce contexte."
)

# Affinity adjective ladder (same boundaries as context.py's _affinity_tier),
# replicated locally — only the adjective is needed here, not the directive.
_AFFINITY_ADJECTIVES = (
    (30, "hostile"),
    (50, "méfiante"),
    (60, "neutre"),
    (76, "chaleureuse"),
    (101, "confiante"),
)

_A_PERCEIVES = ("a_to_b", "mutual")
_B_PERCEIVES = ("b_to_a", "mutual")


def _section(title: str, body: str) -> str:
    return f"=== {title} ===\n{body.rstrip()}\n"


def _affinity_adjective(intensity: int) -> str:
    for upper, adjective in _AFFINITY_ADJECTIVES:
        if intensity < upper:
            return adjective
    return _AFFINITY_ADJECTIVES[-1][1]


def _perceived_target(rel: Relation, npc_id: str) -> str | None:
    if rel.entity_a_id == npc_id and rel.entity_b_id != npc_id and rel.direction in _A_PERCEIVES:
        return rel.entity_b_id
    if rel.entity_b_id == npc_id and rel.entity_a_id != npc_id and rel.direction in _B_PERCEIVES:
        return rel.entity_a_id
    return None


def _render_perception(name: str, rel: Relation) -> str:
    adjective = _affinity_adjective(rel.intensity)
    return f"- {name} : {rel.notes} (perception : {rel.type}, disposition : {adjective})"


def _knowledge_line(k: Knowledge) -> str:
    text = k.content or f"{k.subject} ({k.level})"
    if k.is_incorrect:
        text += " (tu en es convaincu, mais c'est faux)"
    prefix = "[SECRET] " if k.is_secret else ""
    return f"- {prefix}{text}"


def assemble_tick_context(
    npc_id: str, session: Session, *, destinations: list[tuple[str, str]] | None = None
) -> str:
    """Assemble the full-interiority briefing for one NPC's world tick.

    Raises `ValueError` when `npc_id` does not resolve to an NPC character
    (same guard shape as `assemble_npc_context`, extended with the
    character-type check needed here since this builder has no caller that
    already guarantees the id is an NPC).

    `destinations` (TICKET-0015, BRIEF-0015-a) is the interval-scaled
    reachable set computed ONCE per NPC by the caller (`run_world_tick`) —
    (entity_id, name) pairs — rendered as `OÙ TU PEUX ALLER` so the model
    proposes movement only from names it was shown (T1 contract: the header
    always renders, even empty).
    """
    npc_entity = session.get(Entity, npc_id)
    npc_char = session.get(Character, npc_id)
    if npc_entity is None or npc_char is None or npc_char.character_type != "npc":
        raise ValueError(f"No NPC character found for id {npc_id!r}")

    # ----- QUI TU ES ---------------------------------------------------------
    identity_lines = [f"Tu es {npc_entity.name}."]
    if npc_char.appearance:
        identity_lines.append(npc_char.appearance)
    if npc_char.backstory:
        identity_lines.append(npc_char.backstory)
    if npc_char.aversion:
        identity_lines.append(npc_char.aversion)
    if npc_entity.description:
        identity_lines.append(npc_entity.description)
    identity = " ".join(identity_lines)

    # ----- TES OBJECTIFS — ALL active goals, both horizons, newest first,
    # long-terms first. No read-side cap (unlike the dialogue injection). ----
    long_goals = session.exec(
        select(NpcGoal)
        .where(NpcGoal.npc_id == npc_id, NpcGoal.status == "active", NpcGoal.horizon == "long")
        .order_by(NpcGoal.created_at.desc())
    ).all()
    short_goals = session.exec(
        select(NpcGoal)
        .where(NpcGoal.npc_id == npc_id, NpcGoal.status == "active", NpcGoal.horizon == "short")
        .order_by(NpcGoal.created_at.desc())
    ).all()
    goal_lines = [f"[LONG TERME] {g.description}" for g in long_goals]
    goal_lines += [f"[COURT TERME] {g.description}" for g in short_goals]
    goals_body = "\n".join(goal_lines) if goal_lines else "(aucun objectif actif)"

    # ----- CE QUE TU SAIS — ALL knowledge, no share_threshold gating, no
    # is_secret exclusion (T1 conscious exception): there is no interlocutor.-
    knowledge = session.exec(
        select(Knowledge).where(Knowledge.entity_id == npc_id).order_by(Knowledge.id)
    ).all()
    knowledge_body = (
        "\n".join(_knowledge_line(k) for k in knowledge) if knowledge else "(aucune connaissance)"
    )

    # ----- TES RELATIONS — every edge this NPC perceives --------------------
    relations = session.exec(
        select(Relation).where(
            (Relation.entity_a_id == npc_id) | (Relation.entity_b_id == npc_id)
        )
    ).all()
    perceived: dict[str, Relation] = {}
    for rel in relations:
        target = _perceived_target(rel, npc_id)
        if target and target not in perceived:
            perceived[target] = rel

    relation_lines: list[str] = []
    for target_id, rel in perceived.items():
        target_entity = session.get(Entity, target_id)
        target_name = target_entity.name if target_entity else target_id
        relation_lines.append(f"- {target_name} : {rel.type} ({rel.intensity}/100)")
        relation_lines.append(_render_perception(target_name, rel))
    relations_body = "\n".join(relation_lines) if relation_lines else "(aucune relation perçue)"

    # ----- TES AFFILIATIONS — ACTIVE memberships, TRUE role, read directly
    # from FactionMembership (never read_public_memberships). Secret rows
    # included, prefixed [AFFILIATION SECRÈTE]. Posture block per faction. ---
    memberships = session.exec(
        select(FactionMembership)
        .where(FactionMembership.entity_id == npc_id, FactionMembership.left_at.is_(None))
        .order_by(FactionMembership.is_primary.desc(), FactionMembership.joined_at.asc())
    ).all()
    affiliation_lines: list[str] = []
    for membership in memberships:
        faction_entity = session.get(Entity, membership.faction_id)
        faction_name = faction_entity.name if faction_entity else membership.faction_id
        prefix = "[AFFILIATION SECRÈTE] " if membership.is_secret else ""
        if membership.role:
            affiliation_lines.append(f"- {prefix}{faction_name} ({membership.role})")
        else:
            affiliation_lines.append(f"- {prefix}{faction_name}")

        faction = session.get(Faction, membership.faction_id)
        if faction is not None:
            posture_fields = (
                ("Philosophie : ", faction.philosophy),
                ("Buts : ", faction.goals),
                ("Tensions internes : ", faction.internal_tensions),
                ("Aversion : ", faction.aversion),
            )
            for label, value in posture_fields:
                if value:
                    affiliation_lines.append(f"  {label}{value}")
    affiliations_body = "\n".join(affiliation_lines) if affiliation_lines else "(aucune affiliation)"

    # ----- OÙ TU TE TROUVES — same composition as the dialogue setting,
    # minus the player-condition injection (scene-specific, not a tick) -----
    location_id = npc_char.current_location_id
    loc_entity = session.get(Entity, location_id) if location_id else None
    location = session.get(Location, location_id) if location_id else None
    if loc_entity is not None:
        setting_lines = [f"Tu te trouves dans un lieu nommé « {loc_entity.name} »."]
        if loc_entity.description:
            setting_lines.append(loc_entity.description)
        if location is not None and isinstance(location.subculture, dict):
            values = location.subculture.get("values")
            if values:
                setting_lines.append(values)
        setting = " ".join(setting_lines)
    else:
        setting = "Tu ne te trouves nulle part de particulier en ce moment."

    # ----- OÙ TU PEUX ALLER — interval-scaled reachable set, computed by the
    # caller (RECON-0015 F2: same set the destination resolver accepts). -----
    destination_lines: list[str] = []
    for dest_id, dest_name in destinations or []:
        dest_entity = session.get(Entity, dest_id)
        if dest_entity is not None and dest_entity.description:
            destination_lines.append(f"- {dest_name} : {dest_entity.description}")
        else:
            destination_lines.append(f"- {dest_name}")
    destinations_body = (
        "\n".join(destination_lines) if destination_lines else "(nulle part — aucun lieu accessible)"
    )

    # ----- QUI EST AUTOUR — co-located characters, public description only -
    company_lines: list[str] = []
    if location_id:
        present = session.exec(
            select(Character).where(Character.current_location_id == location_id)
        ).all()
        for other_char in present:
            if other_char.id == npc_id:
                continue
            other_entity = session.get(Entity, other_char.id)
            other_name = other_entity.name if other_entity else other_char.id
            description = (
                other_char.appearance
                or (other_entity.description if other_entity else None)
                or "(pas de description)"
            )
            company_lines.append(f"- {other_name} : {description}")
    company_body = "\n".join(company_lines) if company_lines else "(personne d'autre ici)"

    return (
        _section(H_IDENTITY, identity)
        + "\n"
        + _section(H_GOALS, goals_body)
        + "\n"
        + _section(H_KNOWLEDGE, knowledge_body)
        + "\n"
        + _section(H_RELATIONS, relations_body)
        + "\n"
        + _section(H_AFFILIATIONS, affiliations_body)
        + "\n"
        + _section(H_SETTING, setting)
        + "\n"
        + _section(H_DESTINATIONS, destinations_body)
        + "\n"
        + _section(H_COMPANY, company_body)
        + "\n"
        + _BOUNDARY
        + "\n"
    )


# -----------------------------------------------------------------------------
# Runner (TICKET-0014, BRIEF-0014-b) — makes the tick RUN. Reuses analyzer.py's
# JSON-extraction and alias-mapping helpers (analyzer never imports tick, no
# cycle); never imports cockpit/app.py.
# -----------------------------------------------------------------------------

# Closed contract (unlike conversation analysis): only these four types are
# ever proposed by a tick. Anything else is dropped with a note (item 4).
_TICK_MUTATION_TYPES = frozenset({"goal_change", "relation_change", "new_knowledge", "npc_move"})

# Tick-local alias map (TICKET-0015, BRIEF-0015-a): extends the shared
# analyzer map with npc_move aliases WITHOUT mutating it — conversation
# analysis and overhearing must never propose movement (RECON-0015 F4).
_TICK_TYPE_ALIASES: dict[str, str] = {
    **_MUTATION_TYPE_MAP,
    "npc_move": "npc_move",
    "move": "npc_move",
    "movement": "npc_move",
}

# Interval label (verbatim, cockpit/app.py's _VALID_TICK_INTERVALS) -> BFS hop
# bound over connects_to (ACTIVE locations only). None = unbounded — exhaust
# the origin's connected component (RECON-0015 F1/F3). Adjustable without
# touching logic.
INTERVAL_HOP_RADIUS: dict[str, int | None] = {
    "quelques heures": 1,
    "quelques jours": 3,
    "quelques semaines": None,
}


def _reachable_locations(
    db: Session, from_location_id: str, interval_label: str
) -> list[tuple[str, str]]:
    """BFS over `connects_to` relations among ACTIVE locations, starting at
    `from_location_id`, bounded by `INTERVAL_HOP_RADIUS[interval_label]`
    (`None` -> exhaust the connected component). Origin excluded from the
    result. Returns `(entity_id, name)` pairs.

    A NEW, tick-local `connects_to` reader — deliberately not shared with
    `_location_neighbours` (cockpit/app.py, direct-neighbours-only): decision
    D1 stands, this is now the third reader (RECON-0015 F3).

    Raises `ValueError` on an unrecognised interval label — the endpoint's
    422 gate (`_VALID_TICK_INTERVALS`) makes this unreachable in production;
    fail loud if a future caller bypasses it.
    """
    if interval_label not in INTERVAL_HOP_RADIUS:
        raise ValueError(f"unknown interval label {interval_label!r}")
    max_hops = INTERVAL_HOP_RADIUS[interval_label]

    visited: dict[str, str] = {}
    frontier = [from_location_id]
    hops = 0
    while frontier and (max_hops is None or hops < max_hops):
        next_frontier: list[str] = []
        for loc_id in frontier:
            rels = db.exec(
                select(Relation).where(
                    Relation.type == "connects_to",
                    (Relation.entity_a_id == loc_id) | (Relation.entity_b_id == loc_id),
                )
            ).all()
            for rel in rels:
                neighbour_id = rel.entity_b_id if rel.entity_a_id == loc_id else rel.entity_a_id
                if neighbour_id == from_location_id or neighbour_id in visited:
                    continue
                neighbour = db.get(Entity, neighbour_id)
                if neighbour is not None and neighbour.status == "active":
                    visited[neighbour_id] = neighbour.name
                    next_frontier.append(neighbour_id)
        frontier = next_frontier
        hops += 1

    return list(visited.items())


def _normalize_goal_text(text: str | None) -> str:
    """Casefold + whitespace-collapse for goal-text equality (twin of
    cockpit/app.py's `_normalize_goal_text`, replicated rather than imported
    to keep tick.py free of a cockpit.app dependency — same discipline as
    BRIEF-0014-a's local helper replication)."""
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
) -> dict | None:
    """Map one raw model item to the tick's CLOSED schema, or None to drop it.

    Unlike `analyzer._normalize_to_schema`, the tick's contract accepts only
    goal_change | relation_change | new_knowledge | npc_move — anything else
    (including the fallback `other`) is dropped, never proposed.
    `npc_id`/`entity_a_id`/`from_location_id` are FORCED from parameters
    (O1-mirror), never read from the model's payload.

    `destinations` (TICKET-0015, BRIEF-0015-a) is name.casefold() -> id, built
    by the caller from the SAME `_reachable_locations` pair list the briefing
    showed — destination resolution reads ONLY this candidate set, never all
    locations (RECON-0015 F2). `from_location_id`/`from_name` describe the
    NPC's own current location, needed for the npc_move payload's forced
    origin stamp and display field.
    """
    del world_id  # reserved: no payload shape carries it (entity-scoped, not world-keyed)

    if not isinstance(raw_item, dict):
        print(f"[tick] dropped: not a dict — {raw_item!r}")
        return None

    raw_mt = str(raw_item.get("mutation_type") or "").lower()
    mutation_type = _TICK_TYPE_ALIASES.get(raw_mt)
    if mutation_type not in _TICK_MUTATION_TYPES:
        print(f"[tick] dropped: unrecognised or out-of-contract mutation_type {raw_item.get('mutation_type')!r}")
        return None

    payload_in = raw_item.get("payload") if isinstance(raw_item.get("payload"), dict) else {}

    if mutation_type == "goal_change":
        raw_action = str(payload_in.get("action") or "").strip().lower()
        action = _GOAL_ACTION_MAP.get(raw_action)
        goal_text = str(
            payload_in.get("goal") or payload_in.get("description") or payload_in.get("content") or ""
        ).strip()
        if action is None or not goal_text:
            print(f"[tick] dropped goal_change: unrecognised action or empty goal text — {payload_in!r}")
            return None
        payload = {"npc_id": npc_id, "action": action, "goal": goal_text}
        target_table = "npc_goal"

    elif mutation_type == "relation_change":
        other_name = str(payload_in.get("other") or "").strip()
        other_id = roster.get(other_name.casefold())
        if not other_id:
            print(f"[tick] dropped relation_change: unresolved counterpart {other_name!r}")
            return None
        try:
            delta = int(payload_in.get("intensity_delta"))
        except (TypeError, ValueError):
            print(f"[tick] dropped relation_change: missing/invalid intensity_delta — {payload_in!r}")
            return None
        payload = {
            "entity_a_id": npc_id,
            "entity_b_id": other_id,
            "relation_type": str(payload_in.get("relation_type") or "passive_attention"),
            "intensity_delta": delta,
        }
        target_table = "relation"

    elif mutation_type == "npc_move":
        if not from_location_id:
            print("[tick] dropped npc_move: NPC has no current location")
            return None
        destination_name = str(payload_in.get("destination") or "").strip()
        to_id = destinations.get(destination_name.casefold())
        if not destination_name or not to_id:
            print(f"[tick] dropped npc_move: unresolved or out-of-radius destination {destination_name!r}")
            return None
        payload = {
            "npc_id": npc_id,
            "from_location_id": from_location_id,
            "to_location_id": to_id,
            "from_name": from_name or "",
            "to_name": destination_name,
        }
        target_table = "character"

    else:  # new_knowledge
        recipient = str(payload_in.get("recipient") or "self").strip()
        if recipient.casefold() == "self":
            entity_id = npc_id
        else:
            entity_id = roster.get(recipient.casefold())
            if not entity_id:
                print(f"[tick] dropped new_knowledge: unresolved recipient {recipient!r}")
                return None
        content = str(payload_in.get("content") or "").strip()
        if not content:
            print("[tick] dropped new_knowledge: empty content")
            return None
        subject = str(payload_in.get("subject") or "").strip() or _content_to_subject_slug(content)

        # Z3 floor (verbatim mechanics) — mechanical provenance only, never
        # touches is_secret: confidentiality is the receiving NPC's
        # disposition (model proposes, creator judges).
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
        target_table = "knowledge"

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


def run_world_tick(
    db: Session,
    npc_ids: list[str],
    interval_label: str,
    model: str = ollama_client.DEFAULT_MODEL,
    host: str = ollama_client.OLLAMA_HOST,
) -> dict:
    """Advance each NPC in `npc_ids` off-screen for `interval_label`.

    One `tick_id` per invocation, shared by every row written. Per NPC,
    degrade-don't-abort (R3): any exception assembling the briefing or
    calling/parsing the model is recorded as a note for that NPC — nothing
    is written for it, and the other NPCs still proceed. ONE transaction for
    the whole invocation: every surviving proposal across every NPC commits
    together at the end; a crashed invocation (before that point) writes
    nothing.

    Returns the R3 summary:
    `{"tick_id", "interval", "npcs": [{"id","name","proposed","dropped","notes"}], "total_proposed"}`.
    """
    tick_id = str(uuid4())
    template = load_analysis_prompt(db, world_id=None, usage="world_tick")
    version = current_prompt(db, template)
    now = datetime.now(UTC)

    npc_summaries: list[dict] = []
    rows_to_write: list[ProposedMutation] = []

    for npc_id in npc_ids:
        npc_entity = db.get(Entity, npc_id)
        npc_name = npc_entity.name if npc_entity else npc_id
        notes: list[str] = []
        proposed = 0
        dropped = 0

        # Reachable set (TICKET-0015, BRIEF-0015-a) — computed ONCE per NPC,
        # BEFORE the model call, so the briefing and the destination resolver
        # share the exact same candidate set (RECON-0015 F2). Needs npc_char
        # ahead of its other use below (roster building).
        npc_char = db.get(Character, npc_id)
        from_location_id = npc_char.current_location_id if npc_char else None
        from_entity = db.get(Entity, from_location_id) if from_location_id else None
        from_name = from_entity.name if from_entity else None
        reachable = _reachable_locations(db, from_location_id, interval_label) if from_location_id else []
        destinations = {name.casefold(): loc_id for loc_id, name in reachable}

        try:
            briefing = assemble_tick_context(npc_id, db, destinations=reachable)
        except ValueError as exc:
            npc_summaries.append(
                {"id": npc_id, "name": npc_name, "proposed": 0, "dropped": 0, "notes": [str(exc)]}
            )
            continue

        user_message = (
            version.user_template
            .replace("{tick_context}", briefing)
            .replace("{interval_label}", interval_label)
        )
        llm_messages = [
            {"role": "system", "content": version.system_prompt},
            {"role": "user", "content": user_message},
        ]

        try:
            raw = ollama_client.chat(
                llm_messages, model=effective_model(template, model), host=host, format="json"
            )
            items = json.loads(_extract_json_array(raw))
            if not isinstance(items, list):
                raise ValueError("model returned a non-list JSON value")
        except Exception as exc:  # noqa: BLE001 — one NPC's failure must never abort the others (R3)
            npc_summaries.append(
                {"id": npc_id, "name": npc_name, "proposed": 0, "dropped": 0, "notes": [f"model call failed: {exc}"]}
            )
            continue

        roster = _build_roster(db, npc_id, npc_name, from_location_id)
        secret_subjects = {
            k.subject.casefold()
            for k in db.exec(
                select(Knowledge).where(Knowledge.entity_id == npc_id, Knowledge.is_secret == True)  # noqa: E712
            ).all()
            if k.subject
        }

        seen_goal: set[tuple[str, str]] = set()
        seen_knowledge: set[tuple[str, str]] = set()
        seen_relation: set[tuple[str, str]] = set()
        seen_move = False

        for raw_item in items:
            normalized = _normalize_tick_item(
                raw_item,
                npc_id=npc_id,
                world_id=npc_entity.world_id if npc_entity else "",
                roster=roster,
                secret_subjects=secret_subjects,
                destinations=destinations,
                from_location_id=from_location_id,
                from_name=from_name,
            )
            if normalized is None:
                dropped += 1
                continue

            mutation_type = normalized["mutation_type"]
            payload = normalized["payload"]

            # Emit-time dedup (item 6) — one NET change per key within this
            # NPC's item list; keeps the FIRST occurrence, drops the rest.
            if mutation_type == "goal_change":
                key = (payload["action"], _normalize_goal_text(payload["goal"]))
                if key in seen_goal:
                    dropped += 1
                    notes.append(f"duplicate goal_change dropped: {payload['action']} {payload['goal']!r}")
                    continue
                seen_goal.add(key)
            elif mutation_type == "new_knowledge":
                key = (payload["entity_id"], payload["subject"])
                if key in seen_knowledge:
                    dropped += 1
                    notes.append(f"duplicate new_knowledge dropped: subject={payload['subject']!r}")
                    continue
                seen_knowledge.add(key)
            elif mutation_type == "npc_move":
                if seen_move:
                    dropped += 1
                    notes.append(f"duplicate npc_move dropped: to={payload['to_name']!r}")
                    continue
                seen_move = True
            else:  # relation_change
                key = (payload["entity_a_id"], payload["entity_b_id"])
                if key in seen_relation:
                    dropped += 1
                    notes.append(f"duplicate relation_change dropped: other={payload['entity_b_id']}")
                    continue
                seen_relation.add(key)

            rows_to_write.append(
                ProposedMutation(
                    world_id=npc_entity.world_id if npc_entity else "",
                    source_type="world_tick",
                    conversation_id=None,
                    pass_play_id=None,
                    tick_id=tick_id,
                    mutation_type=mutation_type,
                    target_table=normalized["target_table"],
                    target_id=None,
                    payload=payload,
                    status="proposed",
                    rationale=normalized["rationale"],
                    proposed_by="local_ai_tick",
                    proposed_at=now,
                )
            )
            proposed += 1

        npc_summaries.append(
            {"id": npc_id, "name": npc_name, "proposed": proposed, "dropped": dropped, "notes": notes}
        )

    for row in rows_to_write:
        db.add(row)
    db.commit()

    return {
        "tick_id": tick_id,
        "interval": interval_label,
        "npcs": npc_summaries,
        "total_proposed": sum(n["proposed"] for n in npc_summaries),
    }
