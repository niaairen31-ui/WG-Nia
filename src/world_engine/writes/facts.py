"""`fact`/`fact_participant`/`fact_default` canon-write chokepoint
(TICKET-0082, BRIEF-0082-b; `fact_default` added at BRIEF-0082-c).

The single sanctioned write site for all three tables — every
`db.add(Fact(...))`, `db.add(FactParticipant(...))` and
`db.add(FactDefault(...))` in `src/` goes through `create_fact`,
`attach_participants` and `create_fact_default` respectively (enforced by
`tooling/verify/checks/fact_spine.py`'s AST scan for the first two;
`single_canon_write.py`'s policy-file allowlist for the third).

`attach_participants` enforces in code the one rule SQLite cannot express as
a CHECK because it spans two tables: a participant may be attached only to a
fact whose typed FKs (`relation_id`, `event_id`, `world_law_id`) are ALL
NULL. A typed fact already IS the row it points to; `fact_participant`
exists only to carry arity for a free-standing fact.

`create_fact_default` performs no duplicate check of its own — the creator
route (`cockpit/crud/knowledge.py`) queries for an existing
`(fact_id, scope_type, scope_id)` row and returns 409 before ever calling
this function, so a duplicate never reaches the write site.

`update_typed_fact_content` (TICKET-0090, BRIEF-0090-a) rewrites a typed
fact's `content` — the lien fact of a social relation whose type changed.
History is sacred: the previous content is appended to the fact's
`change_history` (`{"content", "changed_by", "at"}`) before the overwrite.

TICKET-0091, BRIEF-0091-A: `create_fact` requires a `facet` (a `FACETS` key,
`facets.py`) with no default — NULL facet is reserved for facts predating the
ticket — and checks it against the typed FK: a typed fact takes exactly its
`TYPED_FACET_BY_FK` facet, a free fact never a `typed`-granularity one.
`update_fact_content` is the general content rewrite (free or typed fact),
same history-first shape as `update_typed_fact_content`. `delete_free_fact`
is a creator-CRUD hard delete of a free fact: its `knowledge`, `fact_default`
and `fact_participant` rows, then the fact, children first (FKs are on); it
refuses a typed fact, which belongs to its relation/event/world_law row.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, select

from ..facets import FACETS, TYPED_FACET_BY_FK, normalize_aspect
from ..models import Fact, FactDefault, FactParticipant, Knowledge


def create_fact(
    db: Session,
    *,
    world_id: str,
    content: str,
    created_by: str,
    facet: Optional[str],
    aspect: Optional[str] = None,
    default_level: str = "unaware",
    relation_id: Optional[str] = None,
    event_id: Optional[str] = None,
    world_law_id: Optional[str] = None,
) -> Fact:
    """Insert a new `fact` row — the single sanctioned `fact` write site.

    Raises `ValueError` on a NULL or unknown `facet`, on a typed fact whose
    facet is not its FK's (`TYPED_FACET_BY_FK`), and on a free fact with a
    `typed`-granularity facet (C-02)."""
    _check_facet(facet, relation_id=relation_id, event_id=event_id, world_law_id=world_law_id)
    fact = Fact(
        world_id=world_id,
        content=content,
        facet=facet,
        aspect=normalize_aspect(aspect),
        created_by=created_by,
        default_level=default_level,
        relation_id=relation_id,
        event_id=event_id,
        world_law_id=world_law_id,
    )
    db.add(fact)
    return fact


def _check_facet(
    facet: Optional[str], *, relation_id: Optional[str], event_id: Optional[str],
    world_law_id: Optional[str],
) -> None:
    if facet is None:
        raise ValueError("create_fact: NULL facet is reserved for facts predating TICKET-0091")
    spec = FACETS.get(facet)
    if spec is None:
        raise ValueError(f"create_fact: unknown facet {facet!r}")
    fks = {"relation_id": relation_id, "event_id": event_id, "world_law_id": world_law_id}
    set_fks = [name for name, value in fks.items() if value is not None]
    if set_fks:
        expected = TYPED_FACET_BY_FK[set_fks[0]]
        if facet != expected:
            raise ValueError(
                f"create_fact: a fact with {set_fks[0]} takes facet {expected!r}, not {facet!r}"
            )
    elif spec.granularity == "typed":
        raise ValueError(f"create_fact: typed facet {facet!r} on a free fact")


def update_fact_content(db: Session, *, fact: Fact, content: str, changed_by: str) -> Fact:
    """Overwrite `fact.content` on a free or typed fact, appending the previous
    content to `fact.change_history` first (TICKET-0091, BRIEF-0091-A, C-03)."""
    history = list(fact.change_history or [])
    history.append({
        "content": fact.content,
        "changed_by": changed_by,
        "at": datetime.now(UTC).isoformat(),
    })
    fact.change_history = history
    sa_attrs.flag_modified(fact, "change_history")
    fact.content = content
    db.add(fact)
    return fact


def delete_free_fact(db: Session, *, fact: Fact) -> None:
    """Hard delete of a free fact and its dependents — creator-CRUD only
    (TICKET-0091, BRIEF-0091-A, C-04). Raises `ValueError` on a typed fact.
    Order: `knowledge`, `fact_default`, `fact_participant`, then the fact."""
    if fact.relation_id is not None or fact.event_id is not None or fact.world_law_id is not None:
        raise ValueError(
            f"delete_free_fact: fact {fact.id!r} is typed — it belongs to its "
            "relation/event/world_law row"
        )
    for knowledge in db.exec(select(Knowledge).where(Knowledge.fact_id == fact.id)).all():
        db.delete(knowledge)
    for default in db.exec(select(FactDefault).where(FactDefault.fact_id == fact.id)).all():
        db.delete(default)
    for participant in db.exec(
        select(FactParticipant).where(FactParticipant.fact_id == fact.id)
    ).all():
        db.delete(participant)
    db.flush()
    db.delete(fact)


def update_typed_fact_content(db: Session, *, fact: Fact, content: str, changed_by: str) -> Fact:
    """Overwrite `fact.content`, appending the previous content to
    `fact.change_history` first (TICKET-0090, BRIEF-0090-a)."""
    history = list(fact.change_history or [])
    history.append({
        "content": fact.content,
        "changed_by": changed_by,
        "at": datetime.now(UTC).isoformat(),
    })
    fact.change_history = history
    sa_attrs.flag_modified(fact, "change_history")
    fact.content = content
    db.add(fact)
    return fact


def attach_participants(
    db: Session,
    *,
    fact: Fact,
    entity_ids: list[str],
    role: Optional[str] = None,
) -> list[FactParticipant]:
    """Attach one or more entities as participants on a free-standing fact.

    Raises `ValueError` if `fact` carries any typed FK (`relation_id`/
    `event_id`/`world_law_id`) — never silently drops. `position` is
    assigned in `entity_ids` order, starting at 0.
    """
    if fact.relation_id is not None or fact.event_id is not None or fact.world_law_id is not None:
        raise ValueError(
            f"attach_participants: fact {fact.id!r} is typed (relation_id/event_id/"
            "world_law_id set) — a participant may attach only to a free-standing fact"
        )
    rows = []
    for position, entity_id in enumerate(entity_ids):
        row = FactParticipant(
            world_id=fact.world_id, fact_id=fact.id, entity_id=entity_id,
            role=role, position=position,
        )
        db.add(row)
        rows.append(row)
    return rows


def create_fact_default(
    db: Session,
    *,
    world_id: str,
    fact_id: str,
    scope_type: str,
    scope_id: Optional[str],
    level: str,
    created_by: str,
) -> FactDefault:
    """Insert a new `fact_default` row — the single sanctioned `fact_default`
    write site (TICKET-0082, BRIEF-0082-c)."""
    row = FactDefault(
        world_id=world_id, fact_id=fact_id, scope_type=scope_type,
        scope_id=scope_id, level=level, created_by=created_by,
    )
    db.add(row)
    return row
