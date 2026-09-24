"""Descriptive NPC/MJ context helpers (TICKET-0091 BRIEF-B move; BRIEF-G
switched them to facts).

`_npc_context_setting`, `_npc_context_company` and `_mj_context_co_presents`
live here for `context.py`'s module budget; `context.py` imports them back.
They read `facet_reads` (C-10), never an entity column. The exclusion
clauses travel unchanged: a hidden custom carries no `location` default so
`notorious_at_location` drops it, the PC co-presence filter, non-public
co-presents, blindfolded visual data (physique included).
"""

from __future__ import annotations

from sqlmodel import Session, select

from .facet_reads import facts_of, joined, known_facts_of
from .models import (
    Character,
    Entity,
    GatheringMember,
    Location,
)


def _npc_context_setting(location_id: str, player_condition: str, session: Session) -> str:
    """----- 2. Setting -----"""
    loc_entity = session.get(Entity, location_id)
    location = session.get(Location, location_id)
    loc_name = loc_entity.name if loc_entity else location_id
    setting_lines = [f"Tu te trouves dans un lieu nommé « {loc_name} »."]
    loc_text = joined(facts_of(session, entity_id=location_id, facets=("description",)), sep=" ")
    if loc_text:
        setting_lines.append(loc_text)
    # Inject player condition so the NPC can observe the player's state.
    if player_condition != "unharmed":
        _condition_labels = {
            "bruised": "légèrement blessé / meurtri",
            "injured": "blessé, en mauvais état",
            "neutralized": "hors de combat / inconscient",
        }
        setting_lines.append(
            f"[ÉTAT DU JOUEUR] Le joueur est actuellement : "
            f"{_condition_labels.get(player_condition, player_condition)}."
        )
    if location:
        values_text = joined(facts_of(
            session, entity_id=location_id, facets=("coutume",), aspect="values",
            notorious_at_location=location_id,
        ), sep=" ")
        if values_text:
            setting_lines.append(values_text)
    return " ".join(setting_lines)


def _npc_context_company(
    npc_id: str, interlocutor_id: str, gathering_id: str | None, session: Session,
) -> str | None:
    """----- 4b. Gathering co-presence (D1 — simple, no relation modulation) -----"""
    if not gathering_id:
        return None
    co_rows = session.exec(
        select(GatheringMember, Entity, Character)
        .join(Entity, Entity.id == GatheringMember.entity_id)
        .join(Character, Character.id == GatheringMember.entity_id)
        .where(
            GatheringMember.gathering_id == gathering_id,
            GatheringMember.left_at.is_(None),
            Character.character_type != "player",
            Entity.status == "active",
            Character.vital_status == "alive",
        )
    ).all()
    co_lines = []
    for _member, co_entity, co_char in co_rows:
        if co_entity.id in (npc_id, interlocutor_id):
            continue
        seen = known_facts_of(
            session, perceiver_id=npc_id, entity_id=co_entity.id,
            facets=("physique", "description"),
        )
        description = (
            joined([row for row in seen if row.facet == "physique"], sep=" ")
            or joined([row for row in seen if row.facet == "description"], sep=" ")
            or "(pas de description)"
        )
        co_lines.append(f"- {co_entity.name} : {description}")
    if not co_lines:
        return None
    return "Sont avec vous, dans le même groupe :\n" + "\n".join(co_lines)


def _mj_context_co_presents(
    gathering_id: str | None, player_character_id: str, blindfolded: bool, db: Session,
) -> list[dict]:
    """Dynamic — gathering roster, public entities only."""
    if not gathering_id:
        return []
    co_rows = db.exec(
        select(GatheringMember, Entity)
        .join(Entity, Entity.id == GatheringMember.entity_id)
        .join(Character, Character.id == Entity.id)
        .where(
            GatheringMember.gathering_id == gathering_id,
            GatheringMember.left_at.is_(None),
            Entity.status == "active",
            Character.vital_status == "alive",
        )
    ).all()
    co_presents: list[dict] = []
    for _member, co_entity in co_rows:
        if co_entity.id == player_character_id or not co_entity.is_public:
            continue
        co_presents.append({
            "name": co_entity.name,
            # Visual data excluded when blindfolded — structurally absent;
            # sound/touch context (names) stays (BRIEF-12).
            "description": None if blindfolded else joined(
                facts_of(db, entity_id=co_entity.id, facets=("description",)), sep=" "),
            # Physique only once the player has met them (R-c, TICKET-0091).
            "physique": None if blindfolded else joined(known_facts_of(
                db, perceiver_id=player_character_id, entity_id=co_entity.id,
                facets=("physique",),
            ), sep=" "),
        })
    return co_presents
