"""World-tick context assembly (TICKET-0014, BRIEF-0014-a; decomposed from
`tick.py` at TICKET-0028, BRIEF-0028-a).

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

Also carries `assemble_location_event_context` / `assemble_faction_event_context`
(TICKET-0017/0018, BRIEF-0017-a/0018-a) and `_reachable_locations` +
`INTERVAL_HOP_RADIUS` (TICKET-0015, BRIEF-0015-a) — every context-assembly
helper `run_world_tick` (`tick.py`) calls into. Pure move, no logic change.
"""

from __future__ import annotations

import logging

from sqlmodel import Session, select

from .ledger import get_balance
from .models import (
    Agenda,
    AgendaStep,
    Character,
    Entity,
    Event,
    EventEntity,
    Faction,
    FactionMembership,
    GoalAgendaLink,
    GoalPrerequisite,
    Knowledge,
    Location,
    LocationSubculture,
    NpcGoal,
    Relation,
)
from .writes import _find_relation_pair

_log = logging.getLogger(__name__)

H_IDENTITY = "QUI TU ES"
H_GOALS = "TES OBJECTIFS"
H_KNOWLEDGE = "CE QUE TU SAIS"
H_RELATIONS = "TES RELATIONS"
H_AFFILIATIONS = "TES AFFILIATIONS"
H_SETTING = "OÙ TU TE TROUVES"
H_DESTINATIONS = "OÙ TU PEUX ALLER"
H_COMPANY = "QUI EST AUTOUR"
H_INTRIGUE = "TON INTRIGUE"

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

# Interval label (verbatim, cockpit/app.py's _VALID_TICK_INTERVALS) -> BFS hop
# bound over connects_to (ACTIVE locations only). None = unbounded — exhaust
# the origin's connected component (RECON-0015 F1/F3). Adjustable without
# touching logic.
INTERVAL_HOP_RADIUS: dict[str, int | None] = {
    "quelques heures": 1,
    "quelques jours": 3,
    "quelques semaines": None,
}


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


def _goal_provenance_suffix(goal_id: str, session: Session) -> str:
    """` (sert : « <title> »[, « <title> »...])` for every ACTIVE link
    (`detached_at IS NULL`) to a still-ACTIVE agenda (TICKET-0020,
    BRIEF-0020-b). FULL interiority — same T1 tier as the affiliation block
    above it: secret-faction agendas are included, no gating. Empty string
    when the goal serves no active agenda."""
    links = session.exec(
        select(GoalAgendaLink).where(
            GoalAgendaLink.goal_id == goal_id, GoalAgendaLink.detached_at.is_(None)
        )
    ).all()
    titles = []
    for link in links:
        agenda = session.get(Agenda, link.agenda_id)
        if agenda is not None and agenda.status == "active":
            titles.append(agenda.title)
    if not titles:
        return ""
    return " (sert : " + ", ".join(f"« {t} »" for t in titles) + ")"


def _goal_prerequisite_lines(goal: NpcGoal, session: Session) -> list[str]:
    """One line per `relation_gte` prerequisite, resolved to live state
    (TICKET-0024, BRIEF-0024-b; relationalized TICKET-0025, BRIEF-0025-c) —
    code resolves, injects; the model never sees or evaluates a threshold
    itself (G1). Reuses `_find_relation_pair` (the same pair-search helper
    `_apply_mutation`'s judge uses) so the briefing and the judge can never
    disagree. Empty for a goal with no prerequisites (prose-only goals stay
    clean)."""
    rows = session.exec(
        select(GoalPrerequisite).where(GoalPrerequisite.goal_id == goal.id)
    ).all()
    lines = []
    for row in rows:
        if row.type != "relation_gte":
            continue
        target = session.get(Entity, row.target_entity_id)
        target_name = target.name if target else row.target_entity_id
        rel = _find_relation_pair(session, goal.npc_id, row.target_entity_id)
        current = rel.intensity if rel else 0
        lines.append(f"  (prérequis : relation >= {row.threshold} avec {target_name} — actuel : {current})")
    return lines


def _tick_identity_block(npc_entity: Entity, npc_char: Character) -> str:
    identity_lines = [f"Tu es {npc_entity.name}."]
    if npc_char.appearance:
        identity_lines.append(npc_char.appearance)
    if npc_char.backstory:
        identity_lines.append(npc_char.backstory)
    if npc_char.aversion:
        identity_lines.append(npc_char.aversion)
    if npc_entity.description:
        identity_lines.append(npc_entity.description)
    return " ".join(identity_lines)


def _tick_goals_block(npc_id: str, session: Session) -> str:
    """ALL active goals, both horizons, newest first, long-terms first. No
    read-side cap (unlike the dialogue injection)."""
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
    goal_lines = []
    for g in long_goals:
        goal_lines.append(f"[LONG TERME] {g.description}{_goal_provenance_suffix(g.id, session)}")
        goal_lines.extend(_goal_prerequisite_lines(g, session))
    for g in short_goals:
        goal_lines.append(f"[COURT TERME] {g.description}{_goal_provenance_suffix(g.id, session)}")
        goal_lines.extend(_goal_prerequisite_lines(g, session))
    return "\n".join(goal_lines) if goal_lines else "(aucun objectif actif)"


def _tick_intrigue_section(npc_id: str, session: Session) -> str:
    """The NPC's own personal agenda, if it owns one (TICKET-0020,
    BRIEF-0020-b). Singular mirror of AGENDA EN COURS (faction scope,
    `assemble_faction_event_context`): title, active step objective +
    visibility_trace, last 2 completed outcomes. Omitted ENTIRELY when the
    NPC owns no active agenda — unlike the faction section, no placeholder."""
    own_agenda = session.exec(
        select(Agenda).where(Agenda.owner_entity_id == npc_id, Agenda.status == "active")
    ).first()
    if own_agenda is None:
        return ""
    own_steps = session.exec(
        select(AgendaStep).where(AgendaStep.agenda_id == own_agenda.id).order_by(AgendaStep.step_order)
    ).all()
    intrigue_lines = [own_agenda.title]
    own_active_step = next((s for s in own_steps if s.status == "active"), None)
    if own_active_step is not None:
        trace = f" ({own_active_step.visibility_trace})" if own_active_step.visibility_trace else ""
        intrigue_lines.append(f"Étape en cours : {own_active_step.objective}{trace}")
    for step in [s for s in own_steps if s.status == "completed"][-2:]:
        if step.outcome:
            intrigue_lines.append(f"Résultat précédent : {step.outcome}")
    return _section(H_INTRIGUE, "\n".join(intrigue_lines)) + "\n"


def _tick_knowledge_block(npc_id: str, session: Session) -> str:
    """ALL knowledge, no share_threshold gating, no is_secret exclusion (T1
    conscious exception): there is no interlocutor."""
    knowledge = session.exec(
        select(Knowledge).where(Knowledge.entity_id == npc_id).order_by(Knowledge.id)
    ).all()
    return "\n".join(_knowledge_line(k) for k in knowledge) if knowledge else "(aucune connaissance)"


def _tick_relations_block(npc_id: str, session: Session) -> str:
    """Every edge this NPC perceives."""
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
    return "\n".join(relation_lines) if relation_lines else "(aucune relation perçue)"


def _tick_affiliations_block(npc_id: str, session: Session) -> str:
    """ACTIVE memberships, TRUE role, read directly from FactionMembership
    (never read_public_memberships). Secret rows included, prefixed
    [AFFILIATION SECRÈTE]. Posture block per faction."""
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
    return "\n".join(affiliation_lines) if affiliation_lines else "(aucune affiliation)"


def _tick_setting_block(npc_char: Character, session: Session) -> str:
    """Same composition as the dialogue setting, minus the player-condition
    injection (scene-specific, not a tick)."""
    location_id = npc_char.current_location_id
    loc_entity = session.get(Entity, location_id) if location_id else None
    location = session.get(Location, location_id) if location_id else None
    if loc_entity is None:
        return "Tu ne te trouves nulle part de particulier en ce moment."
    setting_lines = [f"Tu te trouves dans un lieu nommé « {loc_entity.name} »."]
    if loc_entity.description:
        setting_lines.append(loc_entity.description)
    if location is not None:
        values_row = session.exec(
            select(LocationSubculture).where(
                LocationSubculture.location_id == location_id,
                LocationSubculture.key == "values",
                LocationSubculture.is_hidden == False,  # noqa: E712
            )
        ).first()
        if values_row and values_row.value:
            setting_lines.append(values_row.value)
    return " ".join(setting_lines)


def _tick_destinations_block(destinations: list[tuple[str, str]] | None, session: Session) -> str:
    """Interval-scaled reachable set, computed by the caller (RECON-0015 F2:
    same set the destination resolver accepts)."""
    destination_lines: list[str] = []
    for dest_id, dest_name in destinations or []:
        dest_entity = session.get(Entity, dest_id)
        if dest_entity is not None and dest_entity.description:
            destination_lines.append(f"- {dest_name} : {dest_entity.description}")
        else:
            destination_lines.append(f"- {dest_name}")
    return "\n".join(destination_lines) if destination_lines else "(nulle part — aucun lieu accessible)"


def _tick_company_block(location_id: str | None, npc_id: str, session: Session) -> str:
    """Co-located characters, public description only."""
    if not location_id:
        return "(personne d'autre ici)"
    company_lines: list[str] = []
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
    return "\n".join(company_lines) if company_lines else "(personne d'autre ici)"


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

    location_id = npc_char.current_location_id

    return (
        _section(H_IDENTITY, _tick_identity_block(npc_entity, npc_char))
        + "\n"
        + _section(H_GOALS, _tick_goals_block(npc_id, session))
        + "\n"
        + _tick_intrigue_section(npc_id, session)
        + _section(H_KNOWLEDGE, _tick_knowledge_block(npc_id, session))
        + "\n"
        + _section(H_RELATIONS, _tick_relations_block(npc_id, session))
        + "\n"
        + _section(H_AFFILIATIONS, _tick_affiliations_block(npc_id, session))
        + "\n"
        + _section(H_SETTING, _tick_setting_block(npc_char, session))
        + "\n"
        + _section(H_DESTINATIONS, _tick_destinations_block(destinations, session))
        + "\n"
        + _section(H_COMPANY, _tick_company_block(location_id, npc_id, session))
        + "\n"
        + _BOUNDARY
        + "\n"
    )


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


def assemble_location_event_context(
    location_id: str, session: Session, *, interval_label: str
) -> str:
    """Assemble the briefing for a location-scoped scope-event call
    (TICKET-0017, BRIEF-0017-a). French, T1 section discipline (headers
    always present, placeholders when empty): LE LIEU, QUI S'Y TROUVE, LES
    ENVIRONS, ÉVÉNEMENTS RÉCENTS ICI.
    """
    loc_entity = session.get(Entity, location_id)
    location = session.get(Location, location_id)

    place_lines: list[str] = []
    if loc_entity is not None:
        place_lines.append(loc_entity.name)
        if loc_entity.description:
            place_lines.append(loc_entity.description)
    if location is not None:
        values_row = session.exec(
            select(LocationSubculture).where(
                LocationSubculture.location_id == location_id,
                LocationSubculture.key == "values",
                LocationSubculture.is_hidden == False,  # noqa: E712
            )
        ).first()
        if values_row and values_row.value:
            place_lines.append(values_row.value)
    place_body = " ".join(place_lines) if place_lines else "(lieu inconnu)"

    present = session.exec(
        select(Character).where(Character.current_location_id == location_id)
    ).all()
    who_lines: list[str] = []
    for char in present:
        entity = session.get(Entity, char.id)
        if entity is not None:
            who_lines.append(f"- {entity.name}")
    who_body = "\n".join(who_lines) if who_lines else "(personne)"

    neighbours = _reachable_locations(session, location_id, interval_label)
    around_body = (
        "\n".join(f"- {name}" for _, name in neighbours)
        if neighbours
        else "(aucun lieu connecté)"
    )

    recent = session.exec(
        select(Event)
        .where(
            Event.location_id == location_id,
            Event.knowledge_status.in_(("public", "confirmed")),
        )
        .order_by(Event.recorded_at.desc())
        .limit(5)
    ).all()
    recent_body = (
        "\n".join(f"- {e.title}" for e in recent)
        if recent
        else "(aucun événement public récent)"
    )

    return (
        _section("LE LIEU", place_body)
        + "\n"
        + _section("QUI S'Y TROUVE", who_body)
        + "\n"
        + _section("LES ENVIRONS", around_body)
        + "\n"
        + _section("ÉVÉNEMENTS RÉCENTS ICI", recent_body)
    )


def _tick_faction_identity_block(faction_entity: Entity | None, faction: Faction | None) -> str:
    la_faction_lines: list[str] = []
    if faction_entity is not None:
        la_faction_lines.append(faction_entity.name)
        if faction_entity.description:
            la_faction_lines.append(faction_entity.description)
    if faction is not None:
        if faction.faction_type:
            la_faction_lines.append(f"Type : {faction.faction_type}")
        if faction.philosophy:
            la_faction_lines.append(faction.philosophy)
    return " ".join(la_faction_lines) if la_faction_lines else "(faction inconnue)"


def _tick_faction_posture_block(faction: Faction | None) -> str:
    posture_lines: list[str] = []
    if faction is not None:
        posture_fields = (
            ("Buts : ", faction.goals),
            ("Tensions internes : ", faction.internal_tensions),
            ("Aversion : ", faction.aversion),
            ("Connaissance de la magie : ", faction.magic_knowledge_level),
        )
        for label, value in posture_fields:
            if value:
                posture_lines.append(f"{label}{value}")
    return "\n".join(posture_lines) if posture_lines else "(aucune posture connue)"


def _tick_faction_agenda_block(faction_id: str, session: Session) -> str:
    agendas = session.exec(
        select(Agenda).where(Agenda.owner_entity_id == faction_id, Agenda.status == "active")
    ).all()
    agenda_lines: list[str] = []
    for agenda in agendas:
        steps = session.exec(
            select(AgendaStep)
            .where(AgendaStep.agenda_id == agenda.id)
            .order_by(AgendaStep.step_order)
        ).all()
        agenda_lines.append(f"- {agenda.title}")
        active_step = next((s for s in steps if s.status == "active"), None)
        if active_step is not None:
            trace = f" ({active_step.visibility_trace})" if active_step.visibility_trace else ""
            agenda_lines.append(f"  Étape en cours : {active_step.objective}{trace}")
        completed_steps = [s for s in steps if s.status == "completed"][-2:]
        for step in completed_steps:
            if step.outcome:
                agenda_lines.append(f"  Résultat précédent : {step.outcome}")
    return "\n".join(agenda_lines) if agenda_lines else "(aucune intrigue en cours)"


def _tick_faction_members_block(faction_id: str, session: Session) -> str:
    memberships = session.exec(
        select(FactionMembership).where(
            FactionMembership.faction_id == faction_id, FactionMembership.left_at.is_(None)
        )
    ).all()
    member_lines: list[str] = []
    for membership in memberships:
        member_entity = session.get(Entity, membership.entity_id)
        name = member_entity.name if member_entity is not None else membership.entity_id
        if membership.role:
            member_lines.append(f"- {name} ({membership.role})")
        else:
            member_lines.append(f"- {name}")
    return "\n".join(member_lines) if member_lines else "(aucun membre actif)"


def _tick_faction_recent_events_block(faction_id: str, faction_entity: Entity | None, session: Session) -> str:
    """Faction event filter is a join/EXISTS on event_entity (TICKET-0025,
    BRIEF-0025-c) — was a Python `in` over event.involved_entities JSON."""
    recent = session.exec(
        select(Event)
        .join(EventEntity, EventEntity.event_id == Event.id)
        .where(
            Event.world_id == (faction_entity.world_id if faction_entity else None),
            Event.knowledge_status.in_(("public", "confirmed")),
            EventEntity.entity_id == faction_id,
        )
        .order_by(Event.recorded_at.desc())
    ).all()[:5]
    return "\n".join(f"- {e.title}" for e in recent) if recent else "(aucun événement public récent)"


def assemble_faction_event_context(faction_id: str, session: Session) -> str:
    """Assemble the briefing for a faction-scoped scope-event call
    (TICKET-0017, BRIEF-0017-a; AGENDA EN COURS added TICKET-0018,
    BRIEF-0018-a). French, T1 section discipline: LA FACTION, POSTURE,
    AGENDA EN COURS, MEMBRES, TRÉSORERIE, ÉVÉNEMENTS RÉCENTS.

    AGENDA EN COURS lists each ACTIVE agenda of this faction: its title, the
    active step's objective + visibility_trace, and the last 2 completed
    steps' outcomes (continuity, lean context — RECON-0018 note 2). Header
    always present; `(aucune intrigue en cours)` placeholder when none (T1).

    MEMBRES reads RAW `FactionMembership` (`left_at IS NULL`), never
    `read_public_memberships` — the full-interiority tick exception (T1,
    BRIEF-0014-a) EXTENDED to this surface: same creator-gated surface as
    the per-NPC briefing's TES AFFILIATIONS, re-logged as a conscious
    extension (ARCHITECTURE_DECISIONS.md).
    """
    faction_entity = session.get(Entity, faction_id)
    faction = session.get(Faction, faction_id)

    return (
        _section("LA FACTION", _tick_faction_identity_block(faction_entity, faction))
        + "\n"
        + _section("POSTURE", _tick_faction_posture_block(faction))
        + "\n"
        + _section("AGENDA EN COURS", _tick_faction_agenda_block(faction_id, session))
        + "\n"
        + _section("MEMBRES", _tick_faction_members_block(faction_id, session))
        + "\n"
        + _section("TRÉSORERIE", str(get_balance(session, faction_id)))
        + "\n"
        + _section("ÉVÉNEMENTS RÉCENTS", _tick_faction_recent_events_block(faction_id, faction_entity, session))
    )
