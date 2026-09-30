"""Reads for the Lore shell's writing panel (TICKET-0098, BRIEF-0098-E, M1).

The panel's history view: the world's `lore_entry` rows, newest first, each
with what it wrote, labelled for the creator (an entity's current name, a
fact's rendered text, who knows which fact, a membership, a possession).
A row whose target was deleted since is labelled as such, never dropped.
Reads only.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .models import (
    Entity, Fact, FactDefault, FactionMembership, FactParticipant, Knowledge, LoreEntry,
    LoreEntryRow, Relation,
)
from .prose_render import fact_text

ENTRY_LIMIT = 50
_DELETED = "(supprimé depuis)"


def _name(db: Session, entity_id: Optional[str]) -> str:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.name if entity is not None else _DELETED


def _fact_label(db: Session, fact_id: str) -> str:
    fact = db.get(Fact, fact_id)
    return fact_text(db, fact) if fact is not None else _DELETED


def _label(db: Session, row: LoreEntryRow) -> str:
    model = {"entity": Entity, "fact": Fact, "fact_participant": FactParticipant,
             "fact_default": FactDefault, "knowledge": Knowledge, "relation": Relation,
             "faction_membership": FactionMembership}[row.row_table]
    target = db.get(model, row.row_id)
    if target is None:
        return _DELETED
    if row.row_table == "entity":
        return f"{target.name} ({target.type})"
    if row.row_table == "fact":
        return _fact_label(db, target.id)
    if row.row_table == "fact_participant":
        return f"{_name(db, target.entity_id)} — {_fact_label(db, target.fact_id)}"
    if row.row_table == "fact_default":
        scope = "tout le monde" if target.scope_type == "world" else \
            f"{target.scope_type} {_name(db, target.scope_id)}"
        return f"{scope} — {_fact_label(db, target.fact_id)}"
    if row.row_table == "knowledge":
        flags = "".join((" (secret)" if target.is_secret else "",
                         " (croyance fausse)" if target.is_incorrect else ""))
        return f"{_name(db, target.entity_id)} [{target.level}]{flags} — {_fact_label(db, target.fact_id)}"
    if row.row_table == "relation":
        return f"{_name(db, target.entity_a_id)} possède {_name(db, target.entity_b_id)}"
    return f"{_name(db, target.entity_id)} membre de {_name(db, target.faction_id)}"


def list_entries(db: Session, world_id: str) -> list[dict]:
    """The world's newest `ENTRY_LIMIT` entries with their labelled rows."""
    entries = db.exec(select(LoreEntry).where(LoreEntry.world_id == world_id).order_by(
        LoreEntry.created_at.desc(), LoreEntry.id).limit(ENTRY_LIMIT)).all()
    out = []
    for entry in entries:
        rows = db.exec(select(LoreEntryRow).where(LoreEntryRow.entry_id == entry.id).order_by(
            LoreEntryRow.row_table, LoreEntryRow.id)).all()
        out.append({
            "id": entry.id, "statement": entry.statement, "questions": entry.questions,
            "answers": entry.answers, "created_at": entry.created_at.isoformat(),
            "rows": [{"row_table": r.row_table, "action": r.action, "label": _label(db, r)}
                     for r in rows],
        })
    return out
