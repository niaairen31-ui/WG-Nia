"""The NPC group agent's row commit (TICKET-0129, BRIEF-0129-A): one staged
row written to canon through the creator-direct cores, in the caller's
transaction; shared by the agent's batch commit and the character approval.

Moved verbatim out of `cockpit/routes/npc_agent.py` (pure move). Rides only
`_crud._create_entity_core` / `_crud._create_knowledge_core` /
`write_npc_goal`; never commits.
"""

from __future__ import annotations

from sqlmodel import Session

from ..models import NpcBatch, NpcBatchRow
from ..writes import write_npc_goal
from . import crud as _crud


def _commit_npc_row_goals(db: Session, world_id: str, npc_id: str, goals: dict | None) -> None:
    """Writes the row's attached goals block (long + shorts) via
    `write_npc_goal` — commit-free, same transaction as its NPC (G1)."""
    if not isinstance(goals, dict):
        return
    long_desc = (goals.get("long") or "").strip()
    if long_desc:
        write_npc_goal(
            db, world_id=world_id, npc_id=npc_id,
            description=long_desc, horizon="long", changed_by="creator",
        )
    for short_desc in (goals.get("shorts") or []):
        short_desc = (short_desc or "").strip()
        if short_desc:
            write_npc_goal(
                db, world_id=world_id, npc_id=npc_id,
                description=short_desc, horizon="short", changed_by="creator",
            )


def _commit_npc_row(row: NpcBatchRow, batch: NpcBatch, db: Session) -> dict:
    """Writes one staged row's NPC + knowledge + goals into canon — the
    `_commit_region_npcs` recipe, byte-same posture, adapted to a staged row
    instead of an untrusted client draft entry. Commit-free (caller's
    transaction); returns `{row_id, entity_id, name}`."""
    draft = row.payload["draft"]
    pub, sec = draft["public"], draft["secret"]
    entity_data = {
        "type": "character",
        "name": pub.get("name"),
    }
    ext_data: dict = {
        "character_type": "npc",
        "current_location_id": row.payload["location_id"],
    }
    faction_id = pub.get("faction_id")
    if faction_id is not None:
        ext_data["faction_id"] = faction_id

    # The draft's carrure becomes the NPC's physical skill row (TICKET-0107, E1).
    npc_body = _crud.EntityWriteBody(entity=entity_data, extension=ext_data, facets=draft["facets"],
                                     carrure=pub.get("physical_tier"))
    npc_entity = _crud._create_entity_core(npc_body, db)

    for k in (sec.get("knowledge") or []):
        k_body = _crud.KnowledgeWriteBody(
            level=k.get("level"),
            content=k.get("content"),
            source=None,
            is_incorrect=False,
            is_secret=True,
            share_threshold=50,
        )
        _crud._create_knowledge_core(npc_entity.id, k_body, db)

    _commit_npc_row_goals(db, batch.world_id, npc_entity.id, row.payload.get("goals"))

    return {"row_id": row.id, "entity_id": npc_entity.id, "name": npc_entity.name}
