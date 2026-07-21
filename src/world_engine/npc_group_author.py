"""NPC group agent — staging substrate: journal and placement vocabulary
(TICKET-0037, BRIEF-0037-a).

First step of the standalone NPC group generation agent that replaces the
region wizard's retired NPC machinery (BRIEF-0037-d). This module currently
holds only the read-only vocabulary resolver and the append-only journal —
generation (`generate_entity_draft` per NPC, composite-brief composition,
anti-clone sibling injection) and the commit path arrive in BRIEF-0037-b/-c.
`npc_batch`/`npc_batch_row` stay ephemeral stratum (models/ephemeral.py
NOTE), never a canon write site (`tooling/verify/checks/npc_agent_strata.py`
enforces).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session, select

from . import link_author
from .models import Entity, Faction, World

JOURNAL_DIR = Path.home() / ".world_engine" / "npc_agent_journal"


def journal_append(batch_id: str, event: dict) -> None:
    """Append one JSON line {ts, **event} to this batch's journal file,
    creating ~/.world_engine/npc_agent_journal/ if absent. Absolute
    home-anchored path, never repo-relative — outside the git tree and
    outside the DB's npc_batch retention purge."""
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    line = {"ts": datetime.now(UTC).isoformat(), **event}
    path = JOURNAL_DIR / f"{batch_id}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


def resolve_vocabulary(db: Session, root_location_id: str) -> dict:
    """Expand `root_location_id` (S1 BFS descent, `link_author.
    expand_location_ids`) into the placement vocabulary available to a batch
    anchored on this region root: the expanded location set and the active
    world's active faction entities. Read-only, writes nothing."""
    expanded = sorted(link_author.expand_location_ids(db, [root_location_id]))

    location_rows = db.exec(
        select(Entity.id, Entity.name).where(Entity.id.in_(expanded))
    ).all()
    locations = [{"id": eid, "name": name} for eid, name in location_rows]

    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
    factions: list[dict] = []
    if world is not None:
        faction_rows = db.exec(
            select(Entity.id, Entity.name)
            .join(Faction, Faction.id == Entity.id)
            .where(Entity.world_id == world.id, Entity.status == "active")
        ).all()
        factions = [{"id": eid, "name": name} for eid, name in faction_rows]

    return {
        "expanded_location_ids": expanded,
        "locations": locations,
        "factions": factions,
    }
