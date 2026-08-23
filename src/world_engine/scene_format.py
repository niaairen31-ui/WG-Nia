"""Player-facing scene and inventory formatters (TICKET-0073, BRIEF-0073-a).

Extracted verbatim from `context.py`, which was at 979/1000 lines and had
no room for BRIEF-0073-b's new prompt section. These three functions are
not context assembly: no assembler in `context.py` calls them, and their
callers are all on the play surface. Behaviour is unchanged from the
pre-extraction code — this module is a relocation, not a rewrite.
"""

from __future__ import annotations

from sqlmodel import Session, select

from .models import DiscoverableDetail, Entity, Item, Knowledge


def active_signposts(db: Session, location_id: str, player_character_id: str) -> list[str]:
    """Return the `content` strings of ambient signpost rows that should be
    narrated on entry (schema v1.30, BRIEF-17).

    Runs BEFORE any assembler, never through `assemble_mj_context`: this is
    the I3 code-predicate doctrine — the exhaustion judgment is a code
    predicate, never a prompt instruction. Returns ONLY ambient `content`
    prose; no `subject` or `signpost_group` value ever leaves this function.

    - Ungrouped ambient rows (`signpost_group IS NULL`) are always active.
    - Grouped ambient rows are silent iff the player holds a `knowledge` row
      (any level — existence only) for EVERY `hidden` row sharing that
      `signpost_group` (E1: silent only when the whole cluster is known).

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
    cluster_subjects: dict[str, list[str]] = {}
    if groups_needed:
        hidden_rows = db.exec(
            select(DiscoverableDetail).where(
                DiscoverableDetail.location_id == location_id,
                DiscoverableDetail.access_level == "hidden",
                DiscoverableDetail.signpost_group.in_(groups_needed),
            )
        ).all()
        for row in hidden_rows:
            cluster_subjects.setdefault(row.signpost_group, []).append(row.subject)

    all_subjects = {s for subs in cluster_subjects.values() for s in subs}
    known_subjects: set[str] = set()
    if all_subjects:
        known_subjects = set(
            db.exec(
                select(Knowledge.subject).where(
                    Knowledge.entity_id == player_character_id,
                    Knowledge.subject.in_(all_subjects),
                )
            ).all()
        )

    active: list[str] = []
    for row in ambient_rows:
        if not row.signpost_group:
            active.append(row.content)
            continue
        subjects = cluster_subjects.get(row.signpost_group, [])
        if subjects and all(s in known_subjects for s in subjects):
            continue  # E1: whole cluster known — silent
        active.append(row.content)
    return active


def format_inventory_line(db: Session, player_character_id: str) -> str:
    """Render the player's static inventory as one compact French line
    (BRIEF-08, D2a.1): a single comma-separated list of canonical item names —
    the equipped/stowed split went dormant in this step (`item.equipped`
    stays in the schema, cockpit-only; see ARCHITECTURE_DECISIONS.md).

    Read fresh from `item` at every turn (no caching).
    """
    rows = db.exec(
        select(Item, Entity)
        .join(Entity, Entity.id == Item.id)
        .where(Item.owner_id == player_character_id)
    ).all()

    if not rows:
        return "Objets du joueur : aucun."

    items = ", ".join(entity.name for item, entity in rows)
    return f"Objets du joueur : {items}."


def format_item_list_for_interpretation(db: Session, player_character_id: str) -> str:
    """Render the player's tracked items for the interpretation prompt
    (BRIEF-08, D2a.1): same single list as `format_inventory_line` — the
    equip-state annotation is dropped now that the possession check is
    binary (owned/not owned).
    """
    return format_inventory_line(db, player_character_id)
