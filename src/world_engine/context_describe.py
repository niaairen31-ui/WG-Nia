"""Descriptive NPC/MJ context helpers (TICKET-0091 BRIEF-B, pure move).

`_npc_context_setting`, `_npc_context_company` and `_mj_context_co_presents`
moved verbatim out of `context.py` for its module budget; `context.py`
imports them back. No behaviour change: the exclusion clauses (hidden
subculture rows, the PC co-presence filter, non-public co-presents,
blindfolded appearance) travel unchanged.
"""

from __future__ import annotations

from sqlmodel import Session, select

from .models import (
    Character,
    Entity,
    GatheringMember,
    Location,
    LocationSubculture,
)


def _npc_context_setting(location_id: str, player_condition: str, session: Session) -> str:
    """----- 2. Setting -----"""
    loc_entity = session.get(Entity, location_id)
    location = session.get(Location, location_id)
    loc_name = loc_entity.name if loc_entity else location_id
    setting_lines = [f"Tu te trouves dans un lieu nommé « {loc_name} »."]
    if loc_entity and loc_entity.description:
        setting_lines.append(loc_entity.description)
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
        description = co_char.appearance or co_entity.description or "(pas de description)"
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
            # Appearance excluded when blindfolded — visual data structurally
            # absent; sound/touch context (names) stays (BRIEF-12).
            "description": None if blindfolded else co_entity.description,
        })
    return co_presents
