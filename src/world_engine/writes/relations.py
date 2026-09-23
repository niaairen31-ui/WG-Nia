"""`relation` canon-write chokepoint (TICKET-0028, BRIEF-0028-b — decomposed
from `writes.py`; oriented at TICKET-0090, BRIEF-0090-a).

Orientation rule (TICKET-0090): a social relation — any type
`relation_orientation.is_social` accepts — is one perceiver's feeling
toward one target: `entity_a` feels, `entity_b` receives, `direction` is
always `'a_to_b'` (the default). `write_relation` refuses any other
direction on a social type. `connects_to` and `controls` are structural and
keep their own direction semantics.

Two finders, one per class of relation:
- `_find_perceived_relation(db, perceiver, target)` : the social finder.
  Exactly `entity_a == perceiver` and `entity_b == target`, social types
  only. Shared by `write_relation(mode="delta")` on a social type, and,
  outside this module, `_apply_mutation`'s `goal_change complete`
  prerequisite judge and the per-NPC tick briefing's prerequisite line.
- `_find_relation_pair(db, a, b)` : the structural finder, both
  directions, first match (TICKET-0024, BRIEF-0024-b). Used by the delta on
  a structural type and by `cockpit/crud/relations.py`'s `connects_to`
  lookup.

Typed fact at birth: every newly created social relation gets one `lien`
fact (`lien_fact_content`, `default_level='unaware'`); every new
`connects_to` edge gets one fact (`connects_to_fact_content`,
`default_level='knows'`); `controls` gets none. The row is flushed before
`create_fact` runs (`_birth_typed_fact`). A `mode="set"` update that
changes a social row's type rewrites its lien fact's content through
`writes/facts.py::update_typed_fact_content`, which keeps the previous
content in the fact's `change_history`.

- `write_relation(mode="delta", ...)`  : gameplay consequence. Find/create the
  relation, apply a clamped intensity delta, append the previous state to
  `change_history`. Used by `_apply_mutation`.
- `write_relation(mode="set", ...)`    : author CRUD. Set intensity to an
  absolute value on a specific row (or create a new edge). Updating an
  existing row appends its previous state to `change_history` first
  (history is sacred on both write paths); creating a new edge starts with
  an empty `change_history`, same as `mode="delta"`.
- `write_oriented_relations(...)`      : normalizes a legacy
  (`direction`, `visible_to_b`) request into one oriented row per perceiver
  (`orient_legacy`), then marks the target as knowing where required.
- `set_target_knows(...)`              : creates or deletes `entity_b`'s
  knowledge row on a social relation's lien fact (`lien_fact_of`).

`_build_relation_delta`/`_build_relation_set` are pure builds (find-or-new,
in-memory mutation, no `db.add`) carved out of `write_relation` so the
function fits the 80-line cap (R7: new extractions, new names).
`write_relation` itself owns the single `relation` `db.add` call.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import inspect as sa_inspect
from sqlmodel import Session, select

from ..models import Entity, Fact, Knowledge, Relation
from ..relation_orientation import (
    connects_to_fact_content,
    is_social,
    lien_fact_content,
    orient_legacy,
)
from ._shared import _append_history_snapshot, _clamp
from .facts import create_fact, update_typed_fact_content
from .knowledge import write_knowledge


def _find_relation_pair(db: Session, entity_a_id: str, entity_b_id: str) -> Optional[Relation]:
    """Both-directions first-match search for a `relation` row between two
    entities (TICKET-0024, BRIEF-0024-b) — the STRUCTURAL-relation finder
    since TICKET-0090. Used by `write_relation(mode="delta")` on a
    structural type and by the creator `connects_to` lookup. Social
    relations are oriented and go through `_find_perceived_relation`
    instead. No world or type filter; takes the first match if several
    exist."""
    return db.exec(
        select(Relation).where(
            ((Relation.entity_a_id == entity_a_id) & (Relation.entity_b_id == entity_b_id))
            | ((Relation.entity_a_id == entity_b_id) & (Relation.entity_b_id == entity_a_id))
        )
    ).first()


def _find_perceived_relation(db: Session, perceiver_id: str, target_id: str) -> Optional[Relation]:
    """The SOCIAL-relation finder (TICKET-0090, BRIEF-0090-a): the row where
    `perceiver_id` feels toward `target_id` — exactly `entity_a_id ==
    perceiver_id` and `entity_b_id == target_id`, `is_social(type)`. The
    reverse row (target toward perceiver) is a different relation and is
    never returned. Shared by the social delta, the `relation_gte`
    prerequisite judge and the tick briefing, so the three agree on which
    row is "the" relation."""
    rows = db.exec(
        select(Relation).where(
            Relation.entity_a_id == perceiver_id, Relation.entity_b_id == target_id,
        )
    ).all()
    return next((rel for rel in rows if is_social(rel.type)), None)


def lien_fact_of(db: Session, rel: Relation) -> Optional[Fact]:
    """The typed `fact` row whose `relation_id` is `rel.id`, or None."""
    return db.exec(select(Fact).where(Fact.relation_id == rel.id)).first()


def _require_relation_fields(mode_label: str, *, entity_a_id, entity_b_id, world_id, type) -> None:
    if not entity_a_id or not entity_b_id or not world_id or not type:
        raise ValueError(
            f"write_relation(mode={mode_label!r}): entity_a_id, entity_b_id, "
            "world_id and type are required"
        )


def _require_orientation(relation_type: Optional[str], direction: str) -> None:
    if is_social(relation_type) and direction != "a_to_b":
        raise ValueError(
            f"write_relation: social relation {relation_type} must be a_to_b, got {direction}"
        )


def _endpoint_names(db: Session, entity_a_id: str, entity_b_id: str) -> tuple[str, str]:
    names = []
    for entity_id in (entity_a_id, entity_b_id):
        entity = db.get(Entity, entity_id)
        if entity is None:
            raise ValueError(f"write_relation: entity {entity_id!r} not found")
        names.append(entity.name)
    return names[0], names[1]


def _birth_typed_fact(db: Session, rel: Relation, changed_by: str) -> Optional[Fact]:
    """Create the typed fact of a freshly flushed relation: a social lien
    fact (`unaware`), a `connects_to` fact (`knows`), or nothing for any
    other structural type."""
    name_a, name_b = _endpoint_names(db, rel.entity_a_id, rel.entity_b_id)
    if is_social(rel.type):
        content, level = lien_fact_content(name_a, rel.type, name_b), "unaware"
    elif rel.type == "connects_to":
        content, level = connects_to_fact_content(name_a, name_b), "knows"
    else:
        return None
    return create_fact(
        db, world_id=rel.world_id, content=content, created_by=changed_by,
        facet="lien", default_level=level, relation_id=rel.id,
    )


def _refresh_lien_content(db: Session, rel: Relation, old_type: Optional[str], changed_by: str) -> None:
    """Rewrite the lien fact's content after a social -> social type change.
    A row with no lien fact yet (legacy, before the v2.04 backfill) is left
    alone."""
    if not (is_social(old_type) and is_social(rel.type)) or old_type == rel.type:
        return
    lien = lien_fact_of(db, rel)
    if lien is None:
        return
    name_a, name_b = _endpoint_names(db, rel.entity_a_id, rel.entity_b_id)
    update_typed_fact_content(
        db, fact=lien, content=lien_fact_content(name_a, rel.type, name_b), changed_by=changed_by,
    )


def _build_relation_delta(
    db: Session, *, world_id, entity_a_id, entity_b_id, type, value, direction,
    visible_to_b, notes, mutation_id, now,
) -> Relation:
    """Pure build for `write_relation(mode="delta")` — find/create-or-update
    in memory. No `db.add`: the caller owns the single write site. The
    delta's `type` picks the finder and is used only when creating."""
    if is_social(type):
        rel = _find_perceived_relation(db, entity_a_id, entity_b_id)
    else:
        rel = _find_relation_pair(db, entity_a_id, entity_b_id)
    if rel is None:
        return Relation(
            world_id=world_id, entity_a_id=entity_a_id, entity_b_id=entity_b_id,
            type=type, direction=direction, intensity=_clamp(50 + value),
            visible_to_b=visible_to_b, notes=notes, change_history=[],
            created_at=now, last_evolved_at=now,
        )
    _append_history_snapshot(rel, mutation_id=mutation_id)
    rel.intensity = _clamp(rel.intensity + value)
    rel.last_evolved_at = now
    return rel


def _build_relation_set(
    db: Session, *, relation_id, world_id, entity_a_id, entity_b_id, type,
    value, direction, visible_to_b, notes, now,
) -> Relation:
    """Pure build for `write_relation(mode="set")` — same no-`db.add`
    discipline as `_build_relation_delta`."""
    if relation_id is not None:
        rel = db.get(Relation, relation_id)
        if rel is None:
            raise ValueError(f"write_relation(mode='set'): relation {relation_id!r} not found")
        _append_history_snapshot(rel, mutation_id=None)
        if type is not None:
            rel.type = type
        rel.direction = direction
        rel.visible_to_b = visible_to_b
        rel.notes = notes
        rel.intensity = _clamp(value)
        rel.last_evolved_at = now
        return rel

    _require_relation_fields(
        "set", entity_a_id=entity_a_id, entity_b_id=entity_b_id, world_id=world_id, type=type
    )
    return Relation(
        world_id=world_id, entity_a_id=entity_a_id, entity_b_id=entity_b_id,
        type=type, direction=direction, intensity=_clamp(value),
        visible_to_b=visible_to_b, notes=notes, change_history=[],
        created_at=now, last_evolved_at=now,
    )


def write_relation(
    db: Session,
    *,
    mode: str,
    relation_id: Optional[str] = None,
    world_id: Optional[str] = None,
    entity_a_id: Optional[str] = None,
    entity_b_id: Optional[str] = None,
    type: Optional[str] = None,
    value: int = 0,
    direction: str = "a_to_b",
    visible_to_b: bool = True,
    notes: Optional[str] = None,
    mutation_id: Optional[str] = None,
    changed_by: Optional[str] = None,
) -> Relation:
    """Write a `relation` row — the single sanctioned `relation` write site;
    this function adds the row, the caller only commits.

    mode="delta" (gameplay consequence, `_apply_mutation`): a social type
    finds the perceiver's own row (`_find_perceived_relation`), a structural
    type searches both directions (`_find_relation_pair`); a missing row is
    created. `value` is an intensity delta on top of the existing intensity
    (or 50 for a new relation), clamped 1-100; the previous state is
    appended to `change_history`. `entity_a_id`, `entity_b_id`, `world_id`
    and `type` are required.

    mode="set" (author CRUD): `relation_id=None` creates a new edge with
    intensity = clamp(value); `relation_id=<id>` snapshots the row into
    `change_history`, then overwrites intensity, `type`, `direction`,
    `visible_to_b` and `notes`.

    A social type with a `direction` other than `'a_to_b'` raises
    `ValueError`; so does a missing endpoint entity on create. Every create
    births its typed fact (module docstring). `changed_by` is the fact's
    provenance; it defaults to `mutation:<id>` when `mutation_id` is set,
    else `creator_crud`.
    """
    if mode not in ("delta", "set"):
        raise ValueError(f"write_relation: invalid mode {mode!r}")

    now = datetime.now(UTC)
    provenance = changed_by or (f"mutation:{mutation_id}" if mutation_id else "creator_crud")
    old_type = None
    if mode == "set" and relation_id is not None:
        existing = db.get(Relation, relation_id)
        old_type = existing.type if existing is not None else None
    _require_orientation(type if type is not None else old_type, direction)

    if mode == "delta":
        _require_relation_fields(
            "delta", entity_a_id=entity_a_id, entity_b_id=entity_b_id, world_id=world_id, type=type
        )
        rel = _build_relation_delta(
            db, world_id=world_id, entity_a_id=entity_a_id, entity_b_id=entity_b_id,
            type=type, value=value, direction=direction, visible_to_b=visible_to_b,
            notes=notes, mutation_id=mutation_id, now=now,
        )
    else:
        rel = _build_relation_set(
            db, relation_id=relation_id, world_id=world_id, entity_a_id=entity_a_id,
            entity_b_id=entity_b_id, type=type, value=value, direction=direction,
            visible_to_b=visible_to_b, notes=notes, now=now,
        )

    is_new = sa_inspect(rel).transient
    if is_new:
        _endpoint_names(db, rel.entity_a_id, rel.entity_b_id)
    db.add(rel)
    if is_new:
        db.flush()
        _birth_typed_fact(db, rel, provenance)
    elif mode == "set":
        _refresh_lien_content(db, rel, old_type, provenance)
    return rel


def write_oriented_relations(
    db: Session,
    *,
    world_id: str,
    entity_a_id: str,
    entity_b_id: str,
    type: str,
    value: int,
    direction: str,
    visible_to_b: bool = False,
    notes: Optional[str] = None,
    changed_by: str,
    mode: str = "set",
    relation_id: Optional[str] = None,
) -> list[Relation]:
    """Create the oriented social row(s) a legacy (`direction`,
    `visible_to_b`) request describes: one `write_relation(mode="set",
    direction="a_to_b")` per `orient_legacy` spec, in its order, then
    `set_target_knows(True)` for each spec whose target knows. Each row's
    `visible_to_b` mirrors that spec's `target_knows`. Accepts `mode` and
    `relation_id` only so a staged payload passes unchanged; any `mode`
    other than "set" or any `relation_id` raises `ValueError`."""
    if mode != "set" or relation_id is not None:
        raise ValueError(
            "write_oriented_relations: creates only (mode='set', relation_id=None), "
            f"got mode={mode!r}, relation_id={relation_id!r}"
        )
    specs = orient_legacy(direction, entity_a_id, entity_b_id, visible_to_b)
    rows = [
        write_relation(
            db, mode="set", world_id=world_id, entity_a_id=spec.perceiver_id,
            entity_b_id=spec.target_id, type=type, value=value, direction="a_to_b",
            visible_to_b=spec.target_knows, notes=notes, changed_by=changed_by,
        )
        for spec in specs
    ]
    for spec, rel in zip(specs, rows):
        if spec.target_knows:
            set_target_knows(db, rel=rel, knows=True, changed_by=changed_by)
    return rows


def set_target_knows(db: Session, *, rel: Relation, knows: bool, changed_by: str) -> Optional[Knowledge]:
    """Make `rel.entity_b` know (or stop knowing) the social relation's lien
    fact. True creates `entity_b`'s knowledge row on it through
    `write_knowledge` if absent, else returns the existing row unchanged.
    False deletes that row if present and returns None. Idempotent both
    ways. A structural relation, or one with no lien fact, raises
    `ValueError`."""
    if not is_social(rel.type):
        raise ValueError(f"set_target_knows: relation {rel.id!r} is structural ({rel.type})")
    lien = lien_fact_of(db, rel)
    if lien is None:
        raise ValueError(f"set_target_knows: relation {rel.id!r} has no lien fact")
    existing = db.exec(
        select(Knowledge).where(Knowledge.entity_id == rel.entity_b_id, Knowledge.fact_id == lien.id)
    ).first()
    if not knows:
        if existing is not None:
            db.delete(existing)
        return None
    if existing is not None:
        return existing
    return write_knowledge(
        db, mode="update", entity_id=rel.entity_b_id, fact_id=lien.id,
        subject=lien.content, content=lien.content, level="knows",
        source=f"relation {rel.id}", is_secret=False, is_incorrect=False,
        share_threshold=50, changed_by=changed_by,
    )
