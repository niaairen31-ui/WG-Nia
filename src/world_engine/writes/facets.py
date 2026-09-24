"""The entity-fact writer (TICKET-0091, BRIEF-0091-E, contract C-05).

Every descriptive statement about an entity — what the creator CRUD, the PC
route and every generator commit write — is a free `fact` carrying a
descriptive facet (`facets.DESCRIPTIVE_FACETS`), the entity as its one
participant, and a default-knowledge row picked by an explicit `ScopeChoice`
or else by the facet's preset (C-01). This module is the only place a
`create_fact(` passes a descriptive or non-literal facet
(`tooling/verify/checks/fact_facets.py` R3).

It never `db.add`s a canon row itself: rows go in through the chokepoints
(`writes/facts.py`, `writes/knowledge.py::write_knowledge`). Nothing here
commits; the caller owns the transaction.

`creator_meta` — the creator's note on an entity's true nature — becomes one
`histoire` fact with no default plus one `knowledge` row for the entity
itself at `unaware`, `is_secret=True`: the entity never knows the note
(secrets are excluded structurally, never by instruction).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlmodel import Session, select

from ..facets import DESCRIPTIVE_FACETS, facet_spec, normalize_aspect
from ..models import Entity, Fact, FactParticipant
from ..name_index import PROSE, NameScope
from ..prose_render import fact_text
from ..prose_tokens import tokenize
from .facts import (
    attach_participants,
    create_fact,
    create_fact_default,
    delete_free_fact,
    update_fact_content,
)
from .knowledge import write_knowledge
from .mentions import record_unresolved

SCOPE_TYPES = ("none", "world", "location", "faction", "rencontre")
CREATOR_META_KEY = "creator_meta"


@dataclass(frozen=True)
class ScopeChoice:
    scope_type: str            # "none"|"world"|"location"|"faction"|"rencontre"
    scope_id: Optional[str] = None


def facts_payload_keys() -> frozenset[str]:
    """The descriptive facet names a `facets` payload may carry (besides
    `creator_meta`)."""
    return DESCRIPTIVE_FACETS


def _preset_scope(preset: str, entity: Entity) -> ScopeChoice:
    """C-01 preset semantics, applied to `entity` as the subject."""
    if preset == "world":
        return ScopeChoice("world")
    if preset == "public_world":
        return ScopeChoice("world") if entity.is_public else ScopeChoice("none")
    if preset == "location":
        return ScopeChoice("location", entity.id) if entity.type == "location" else ScopeChoice("none")
    if preset == "rencontre":
        return ScopeChoice("rencontre", entity.id)
    return ScopeChoice("none")


def _check_scope(scope: ScopeChoice) -> None:
    if scope.scope_type not in SCOPE_TYPES:
        raise ValueError(f"unknown scope_type {scope.scope_type!r}")
    if scope.scope_type in ("none", "world"):
        if scope.scope_id is not None:
            raise ValueError(f"scope {scope.scope_type!r} takes no scope_id")
    elif not scope.scope_id:
        raise ValueError(f"scope {scope.scope_type!r} requires a scope_id")


def _bloc_exists(db: Session, *, entity_id: str, facet: str, aspect: Optional[str]) -> bool:
    stmt = (
        select(Fact.id)
        .join(FactParticipant, FactParticipant.fact_id == Fact.id)
        .where(FactParticipant.entity_id == entity_id, Fact.facet == facet)
    )
    stmt = stmt.where(Fact.aspect.is_(None)) if aspect is None else stmt.where(Fact.aspect == aspect)
    return db.exec(stmt).first() is not None


def add_entity_fact(
    db: Session,
    *,
    entity_id: str,
    facet: str,
    content: str,
    created_by: str,
    aspect: Optional[str] = None,
    scope: Optional[ScopeChoice] = None,
    mentions: Optional[list] = None,
) -> Fact:
    """One descriptive fact about `entity_id`, its participant, and its
    default (`scope` when given, else the facet's preset; level `knows`).

    Raises `ValueError` on a non-descriptive facet, empty content, an unknown
    entity, a malformed scope, or a second fact on a `bloc` facet with the
    same aspect. Names in `content` become identity tokens (`tokenize`, with
    the generator's `mentions`); the unresolved ones are recorded against
    the new fact (BRIEF-0091-J)."""
    if facet not in DESCRIPTIVE_FACETS:
        raise ValueError(f"facet {facet!r} is not a descriptive facet")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("fact content is empty")
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise ValueError(f"entity {entity_id!r} not found")
    spec = facet_spec(facet)
    norm_aspect = normalize_aspect(aspect)
    if spec.granularity == "bloc" and _bloc_exists(db, entity_id=entity_id, facet=facet, aspect=norm_aspect):
        raise ValueError("bloc facet already has a fact")
    chosen = scope if scope is not None else _preset_scope(spec.preset, entity)
    _check_scope(chosen)

    # An appellation's own text is tokenized on names alone, its owner
    # excluded: it is stored plain and never self-referential (N15b).
    name_scope = (NameScope("names_only", exclude_entity_id=entity_id)
                  if facet == "appellation" else PROSE)
    tokens = tokenize(db, world_id=entity.world_id, text=content, mentions=mentions,
                      scope=name_scope)
    fact = create_fact(
        db, world_id=entity.world_id, content=tokens.text, created_by=created_by,
        facet=facet, aspect=norm_aspect,
    )
    db.flush()
    if tokens.unresolved:
        record_unresolved(db, world_id=entity.world_id, fact_id=fact.id, items=tokens.unresolved)
    attach_participants(db, fact=fact, entity_ids=[entity_id])
    if chosen.scope_type != "none":
        create_fact_default(
            db, world_id=entity.world_id, fact_id=fact.id, scope_type=chosen.scope_type,
            scope_id=chosen.scope_id, level="knows", created_by=created_by,
        )
    return fact


def _affirmation_items(facet: str, value: Any) -> list[str]:
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [item.strip() for item in value if item.strip()]
    raise ValueError(f"facet {facet!r} takes a list of strings or a string")


def _write_coutumes(
    db: Session, *, entity_id: str, value: Any, created_by: str, mentions: Optional[list],
) -> list[Fact]:
    if not isinstance(value, list):
        raise ValueError("facet 'coutume' takes a list of {aspect, content, hidden}")
    facts = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("content"), str):
            raise ValueError("a 'coutume' entry is {aspect, content, hidden}")
        if not item["content"].strip():
            continue
        scope = ScopeChoice("none") if item.get("hidden") else None
        facts.append(add_entity_fact(
            db, entity_id=entity_id, facet="coutume", content=item["content"],
            created_by=created_by, aspect=item.get("aspect"), scope=scope, mentions=mentions,
        ))
    return facts


def _write_creator_meta(
    db: Session, *, entity_id: str, value: Any, created_by: str, mentions: Optional[list],
) -> list[Fact]:
    if not isinstance(value, str):
        raise ValueError("creator_meta takes a string")
    if not value.strip():
        return []
    fact = add_entity_fact(
        db, entity_id=entity_id, facet="histoire", content=value, created_by=created_by,
        scope=ScopeChoice("none"), mentions=mentions,
    )
    write_knowledge(
        db, entity_id=entity_id, fact_id=fact.id, subject=CREATOR_META_KEY,
        level="unaware", is_secret=True, changed_by=created_by,
    )
    return [fact]


def write_entity_facets(
    db: Session, *, entity_id: str, facets: dict, created_by: str,
    mentions: Optional[list] = None,
) -> list[Fact]:
    """Write a whole `facets` payload (C-05 shape) about `entity_id`.

    `bloc` facet -> a `str`; `affirmation` facet -> a `list[str]` or a `str`
    split into one fact per non-empty stripped line (Q20b); `coutume` -> a
    list of `{"aspect", "content", "hidden"}` (hidden = no default);
    `creator_meta` -> a `str` (see module docstring). Empty strings are
    skipped. Returns the created facts in input order. `mentions` (C-11, a
    generator's `[{"name", "category"}]`) reaches every `tokenize` call."""
    if not isinstance(facets, dict):
        raise ValueError("facets must be an object")
    created: list[Fact] = []
    for key, value in facets.items():
        if key == CREATOR_META_KEY:
            created += _write_creator_meta(
                db, entity_id=entity_id, value=value, created_by=created_by, mentions=mentions,
            )
            continue
        if key not in DESCRIPTIVE_FACETS:
            raise ValueError(f"facets key {key!r} is not a descriptive facet")
        if value is None:
            continue
        if key == "coutume":
            created += _write_coutumes(
                db, entity_id=entity_id, value=value, created_by=created_by, mentions=mentions,
            )
        elif facet_spec(key).granularity == "bloc":
            if not isinstance(value, str):
                raise ValueError(f"bloc facet {key!r} takes a string")
            if value.strip():
                created.append(add_entity_fact(
                    db, entity_id=entity_id, facet=key, content=value, created_by=created_by,
                    mentions=mentions,
                ))
        else:
            for item in _affirmation_items(key, value):
                created.append(add_entity_fact(
                    db, entity_id=entity_id, facet=key, content=item, created_by=created_by,
                    mentions=mentions,
                ))
    return created


def _descriptive_fact(db: Session, fact_id: str) -> Fact:
    fact = db.get(Fact, fact_id)
    if fact is None:
        raise ValueError(f"fact {fact_id!r} not found")
    if fact.facet not in DESCRIPTIVE_FACETS:
        raise ValueError(f"fact {fact_id!r} is not a descriptive fact")
    return fact


def _edit_scope(db: Session, fact: Fact) -> NameScope:
    """N15b for an edit: an appellation is tokenized on names alone, without
    its owner when it has exactly one participant; any other facet is prose."""
    if fact.facet != "appellation":
        return PROSE
    owners = db.exec(select(FactParticipant.entity_id).where(FactParticipant.fact_id == fact.id)).all()
    return NameScope("names_only", exclude_entity_id=owners[0] if len(owners) == 1 else None)


def edit_entity_fact(db: Session, *, fact_id: str, content: str, changed_by: str) -> Fact:
    """Rewrite a descriptive fact's content through `update_fact_content`
    (history appended). `ValueError` if unknown, not descriptive, or the
    content is empty. New text gets identity tokens and its unresolved names
    are recorded (BRIEF-0091-J); text equal to the stored text, raw or
    rendered, keeps the stored text as is."""
    fact = _descriptive_fact(db, fact_id)
    if not isinstance(content, str) or not content.strip():
        raise ValueError("fact content is empty")
    if content in (fact.content_raw, fact_text(db, fact)):
        return update_fact_content(db, fact=fact, content=fact.content_raw, changed_by=changed_by)
    tokens = tokenize(db, world_id=fact.world_id, text=content, scope=_edit_scope(db, fact))
    if tokens.unresolved:
        record_unresolved(db, world_id=fact.world_id, fact_id=fact.id, items=tokens.unresolved)
    return update_fact_content(db, fact=fact, content=tokens.text, changed_by=changed_by)


def remove_entity_fact(db: Session, *, fact_id: str) -> None:
    """Hard-delete a descriptive fact through `delete_free_fact`.
    `ValueError` if unknown or not descriptive."""
    delete_free_fact(db, fact=_descriptive_fact(db, fact_id))
