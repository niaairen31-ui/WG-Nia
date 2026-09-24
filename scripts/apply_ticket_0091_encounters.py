"""One-shot, idempotent backfill of the `rencontre` registry from existing
play traces and authored state (TICKET-0091, BRIEF-0091-C, Scope IN 8).

Candidate pairs, each with its timestamp and source row:
- `visit`: the player x every id in `present_npc_ids`, at `entered_at`;
- `gathering_member`: two members of the same gathering whose membership
  intervals overlap, at the later `joined_at`;
- `conversation`: `player_id` x `npc_id` (when set), at `started_at`;
- `npc_schedule`: two NPCs at the same `(location_id, phase)`, at the later
  `created_at`;
- social `relation` rows: `entity_a_id` x `entity_b_id`, at `created_at`.

All candidates are sorted by timestamp and passed to `record_encounter` in
that order, so each pair keeps its earliest encounter and its source. The
registry writer's read guard makes a second run insert nothing. Ids that no
longer resolve to an `entity` row are skipped. Writes no canon.

Safe to re-run.
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from datetime import datetime
from itertools import combinations
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env not in ("prod", "test"):
    print(
        "apply_ticket_0091_encounters.py refuses to run unless "
        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
    )
    sys.exit(1)

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlmodel import Session, select  # noqa: E402

from world_engine.db import engine  # noqa: E402
from world_engine.encounters import record_encounter  # noqa: E402
from world_engine.models import (  # noqa: E402
    Conversation,
    Entity,
    ENCOUNTER_SOURCES,
    GatheringMember,
    Gathering,
    NpcSchedule,
    Relation,
    Visit,
)
from world_engine.relation_orientation import is_social  # noqa: E402

# (timestamp, world_id, a_id, b_id, source, source_ref)
Candidate = tuple[datetime, str, str, str, str, "str | None"]


def _naive(ts: datetime) -> datetime:
    """Sort key: timestamps may be stored naive or aware; compare as naive UTC."""
    return ts.replace(tzinfo=None) if ts.tzinfo is not None else ts


def _visit_candidates(db: Session) -> list[Candidate]:
    out: list[Candidate] = []
    for v in db.exec(select(Visit)).all():
        for npc_id in v.present_npc_ids or []:
            out.append((v.entered_at, v.world_id, v.player_id, npc_id, "visit", v.id))
    return out


def _overlap(a: GatheringMember, b: GatheringMember) -> bool:
    a_end = _naive(a.left_at) if a.left_at is not None else None
    b_end = _naive(b.left_at) if b.left_at is not None else None
    return (b_end is None or _naive(a.joined_at) <= b_end) and (
        a_end is None or _naive(b.joined_at) <= a_end
    )


def _gathering_candidates(db: Session) -> list[Candidate]:
    worlds = {g.id: g.world_id for g in db.exec(select(Gathering)).all()}
    by_gathering: dict[str, list[GatheringMember]] = {}
    for m in db.exec(select(GatheringMember)).all():
        by_gathering.setdefault(m.gathering_id, []).append(m)
    out: list[Candidate] = []
    for gid, members in by_gathering.items():
        for a, b in combinations(members, 2):
            if a.entity_id != b.entity_id and _overlap(a, b):
                at = max(a.joined_at, b.joined_at, key=_naive)
                out.append((at, worlds[gid], a.entity_id, b.entity_id, "gathering", gid))
    return out


def _conversation_candidates(db: Session) -> list[Candidate]:
    rows = db.exec(select(Conversation).where(Conversation.npc_id.is_not(None))).all()
    return [
        (c.started_at, c.world_id, c.player_id, c.npc_id, "conversation", c.id) for c in rows
    ]


def _schedule_candidates(db: Session) -> list[Candidate]:
    by_slot: dict[tuple[str, str, str], list[NpcSchedule]] = {}
    for s in db.exec(select(NpcSchedule)).all():
        by_slot.setdefault((s.world_id, s.location_id, s.phase), []).append(s)
    out: list[Candidate] = []
    for (world_id, _loc, _phase), rows in by_slot.items():
        for a, b in combinations(rows, 2):
            at = max(a.created_at, b.created_at, key=_naive)
            out.append((at, world_id, a.npc_id, b.npc_id, "schedule", None))
    return out


def _relation_candidates(db: Session) -> list[Candidate]:
    return [
        (r.created_at, r.world_id, r.entity_a_id, r.entity_b_id, "relation", r.id)
        for r in db.exec(select(Relation)).all()
        if is_social(r.type)
    ]


def main() -> None:
    with Session(engine) as db:
        known = set(db.exec(select(Entity.id)).all())
        candidates = (
            _visit_candidates(db) + _gathering_candidates(db) + _conversation_candidates(db)
            + _schedule_candidates(db) + _relation_candidates(db)
        )
        candidates.sort(key=lambda c: _naive(c[0]))
        seen: Counter[str] = Counter()
        inserted: Counter[str] = Counter()
        skipped = 0
        for at, world_id, a_id, b_id, source, ref in candidates:
            seen[source] += 1
            if a_id not in known or b_id not in known:
                skipped += 1
                continue
            if record_encounter(
                db, world_id=world_id, a_id=a_id, b_id=b_id, source=source, at=at,
                source_ref=ref,
            ) is not None:
                inserted[source] += 1
        db.commit()
    for source in ENCOUNTER_SOURCES:
        print(f"{source}: {seen[source]} candidate(s), {inserted[source]} inserted")
    print(f"skipped (unresolved entity): {skipped}")
    print(f"total inserted: {sum(inserted.values())}")


if __name__ == "__main__":
    main()
