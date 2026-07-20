"""NPC link agent — roster resolution and journal substrate (TICKET-0036,
BRIEF-0036-a).

`resolve_roster` is the S1 location-subtree expansion: code-owned, no model
call. `journal_append` is the append-only generation journal (R1) — long
memory for a batch, kept OUTSIDE the git tree and outside the DB's last-2
retention purge. Neither function writes canon; this module has no
`writes/` import and appears nowhere in canon_write_policy.txt.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session, select

from .models import Character, Entity, Location

JOURNAL_DIR = Path.home() / ".world_engine" / "link_agent_journal"


def resolve_roster(db: Session, root_location_ids: list[str]) -> dict:
    """BFS-expand `root_location_ids` through `parent_location_id` descent,
    then collect the present NPC roster over the expanded set.

    Roster = characters with character_type='npc', vital_status='alive',
    entity.status='active', current_location_id in the expanded set.
    Returns {expanded_location_ids, npcs: [{id, name}], pair_count} where
    pair_count = N*(N-1)/2. Writes nothing."""
    expanded: set[str] = set(root_location_ids)
    frontier = list(root_location_ids)
    while frontier:
        children = db.exec(
            select(Location.id).where(Location.parent_location_id.in_(frontier))
        ).all()
        new_children = [c for c in children if c not in expanded]
        expanded.update(new_children)
        frontier = new_children

    rows = db.exec(
        select(Entity, Character)
        .join(Character, Character.id == Entity.id)
        .where(Character.character_type == "npc")
        .where(Character.vital_status == "alive")
        .where(Entity.status == "active")
        .where(Character.current_location_id.in_(list(expanded)))
    ).all()
    npcs = [{"id": e.id, "name": e.name} for e, _ in rows]

    n = len(npcs)
    return {
        "expanded_location_ids": sorted(expanded),
        "npcs": npcs,
        "pair_count": n * (n - 1) // 2,
    }


def journal_append(batch_id: str, event: dict) -> None:
    """Append one JSON line {ts, **event} to this batch's journal file,
    creating ~/.world_engine/link_agent_journal/ if absent. Absolute
    home-anchored path, never repo-relative — outside the git tree and
    outside the DB's link_batch retention purge."""
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    line = {"ts": datetime.now(UTC).isoformat(), **event}
    path = JOURNAL_DIR / f"{batch_id}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
