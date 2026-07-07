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

from sqlmodel import Session, select

from .models import (
    Character,
    Entity,
    Faction,
    FactionMembership,
    Knowledge,
    Location,
    NpcGoal,
    Relation,
)

H_IDENTITY = "QUI TU ES"
H_GOALS = "TES OBJECTIFS"
H_KNOWLEDGE = "CE QUE TU SAIS"
H_RELATIONS = "TES RELATIONS"
H_AFFILIATIONS = "TES AFFILIATIONS"
H_SETTING = "OÙ TU TE TROUVES"
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


def assemble_tick_context(npc_id: str, session: Session) -> str:
    """Assemble the full-interiority briefing for one NPC's world tick.

    Raises `ValueError` when `npc_id` does not resolve to an NPC character
    (same guard shape as `assemble_npc_context`, extended with the
    character-type check needed here since this builder has no caller that
    already guarantees the id is an NPC).
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
        + _section(H_COMPANY, company_body)
        + "\n"
        + _BOUNDARY
        + "\n"
    )
