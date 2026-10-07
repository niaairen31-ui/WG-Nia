"""Player-facing scene and inventory formatters (TICKET-0073, BRIEF-0073-a).

Extracted verbatim from `context.py`, which was at 979/1000 lines and had
no room for BRIEF-0073-b's new prompt section. These three functions are
not context assembly: no assembler in `context.py` calls them, and their
callers are all on the play surface. Behaviour is unchanged from the
pre-extraction code — this module is a relocation, not a rewrite.
"""

from __future__ import annotations

from sqlmodel import Session, select

from .holdings import held_label, items_held
from .models import DiscoverableDetail, Knowledge


def active_signposts(db: Session, location_id: str, player_character_id: str) -> list[str]:
    """Return the `content` strings of ambient signpost rows that should be
    narrated on entry (schema v1.30, BRIEF-17).

    Runs BEFORE any assembler, never through `assemble_mj_context`: this is
    the I3 code-predicate doctrine — the exhaustion judgment is a code
    predicate, never a prompt instruction. Returns ONLY ambient `content`
    prose; no `signpost_group` value ever leaves this function.

    - Ungrouped ambient rows (`signpost_group IS NULL`) are always active.
    - Grouped ambient rows are silent iff the player holds a `knowledge` row
      (any level — existence only) on the fact of EVERY `hidden` row sharing
      that `signpost_group` (E1: silent only when the whole cluster is
      known). A hidden row's fact is `discoverable_detail.fact_id`, set by
      its first approved discovery (TICKET-0097, H1); a row without one is
      not known yet.

    `discovered` is NOT a filter here — ambient panels are not "discovered";
    their visibility is governed by the cluster predicate above.
    """
    ambient_rows = db.exec(
        select(DiscoverableDetail).where(
            DiscoverableDetail.location_id == location_id,
            DiscoverableDetail.access_level == "ambient",
        )
    ).all()
    if not ambient_rows:
        return []

    groups_needed = {row.signpost_group for row in ambient_rows if row.signpost_group}
    cluster_facts: dict[str, list[str | None]] = {}
    if groups_needed:
        hidden_rows = db.exec(
            select(DiscoverableDetail).where(
                DiscoverableDetail.location_id == location_id,
                DiscoverableDetail.access_level == "hidden",
                DiscoverableDetail.signpost_group.in_(groups_needed),
            )
        ).all()
        for row in hidden_rows:
            cluster_facts.setdefault(row.signpost_group, []).append(row.fact_id)

    all_facts = {f for facts in cluster_facts.values() for f in facts if f}
    known_facts: set[str] = set()
    if all_facts:
        known_facts = set(
            db.exec(
                select(Knowledge.fact_id).where(
                    Knowledge.entity_id == player_character_id,
                    Knowledge.fact_id.in_(all_facts),
                )
            ).all()
        )

    active: list[str] = []
    for row in ambient_rows:
        if not row.signpost_group:
            active.append(row.content)
            continue
        facts = cluster_facts.get(row.signpost_group, [])
        if facts and all(f in known_facts for f in facts):
            continue  # E1: whole cluster known — silent
        active.append(row.content)
    return active


def format_inventory_line(db: Session, player_character_id: str) -> str:
    """Render the player's inventory as one compact French line (BRIEF-08,
    D2a.1; quantities since TICKET-0109, A1): what he holds
    (`holdings.items_held`), « Fourrure de loup ×10 » for more than one.

    Read fresh at every turn (no caching).
    """
    rows = items_held(db, player_character_id)
    if not rows:
        return "Objets du joueur : aucun."
    items = ", ".join(held_label(entity.name, holding.quantity) for holding, _item, entity in rows)
    return f"Objets du joueur : {items}."


def format_item_list_for_interpretation(db: Session, player_character_id: str) -> str:
    """Render the player's items for the interpretation prompt (BRIEF-08,
    D2a.1): the canonical NAMES only, never a quantity (TICKET-0109) -- the
    model answers `used_object` with one of them, and the possession check
    matches that name exactly (`play_stream._find_player_item`).
    """
    rows = items_held(db, player_character_id)
    if not rows:
        return "Objets du joueur : aucun."
    return "Objets du joueur : " + ", ".join(entity.name for _holding, _item, entity in rows) + "."
