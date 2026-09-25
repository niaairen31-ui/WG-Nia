"""The name index: one source for every name surface of a world (TICKET-0092,
BRIEF-0092-A, decisions N1c, N2b, N17a).

A name surface is an active entity's `name` or the rendered text of an
`appellation` fact about an active entity. Which appellations count depends
on the regime of a `NameScope` (N1c, N2b):

- `names_only`: names only;
- `creator`: every appellation, creator-only ones included (name resolution
  for the creator: Lore question, names panel);
- `prose`: appellations that are not creator-only and have a scope (N17a:
  `fact.default_level != 'unaware'` or a `fact_default` row above
  `unaware`) — what token posing may index;
- `perceiver`: appellations that are not creator-only and whose fact id is
  in the perceiver's `known_fact_ids`.

`exclude_entity_id` removes one entity's name and appellations in every
regime. Text is returned as rendered, never normalized: callers normalize.

Read-only: no write, no commit, no model call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from .models import Entity, Fact, FactDefault, FactParticipant
from .prose_render import fact_texts

REGIMES: tuple[str, ...] = ("names_only", "creator", "prose", "perceiver")

# regime -> (appellations counted, creator-only dropped, scope required, known required)
_APPELLATION_RULES = {
    "names_only": (False, False, False, False),
    "creator": (True, False, False, False),
    "prose": (True, True, True, False),
    "perceiver": (True, True, False, True),
}


@dataclass(frozen=True)
class NameScope:
    regime: str                                   # one of REGIMES
    known_fact_ids: Optional[frozenset[str]] = None
    exclude_entity_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.regime not in REGIMES:
            raise ValueError(f"unknown name regime {self.regime!r}")
        if self.regime == "perceiver" and self.known_fact_ids is None:
            raise ValueError("the perceiver regime needs known_fact_ids")
        if self.regime != "perceiver" and self.known_fact_ids is not None:
            raise ValueError(f"known_fact_ids is only for the perceiver regime, not {self.regime!r}")


NAMES_ONLY = NameScope("names_only")
CREATOR = NameScope("creator")
PROSE = NameScope("prose")


@dataclass(frozen=True)
class NameSurface:
    text: str               # entity.name, or the appellation rendered by prose_render.fact_texts
    entity_id: str
    entity_name: str        # entity.name, for display
    entity_type: str        # entity.type
    source: str             # "name" | "appellation"
    fact_id: Optional[str]  # None iff source == "name"


def _scoped_fact_ids(db: Session, world_id: str, facts: list) -> set[str]:
    """N17a: the facts with a default above `unaware`, on the fact or a `fact_default` row."""
    scoped = {f.id for f in facts if f.default_level != "unaware"}
    rest = [f.id for f in facts if f.id not in scoped]
    if rest:
        scoped |= set(db.exec(
            select(FactDefault.fact_id).where(
                FactDefault.world_id == world_id,
                FactDefault.fact_id.in_(rest),
                FactDefault.level != "unaware",
            )
        ).all())
    return scoped


def _kept_pairs(db: Session, world_id: str, scope: NameScope, pairs: list, hidden: set) -> list:
    """`(fact, entity_id)` pairs that count under `scope`'s regime (C-01);
    `hidden` is the creator-only subset of their facts."""
    _, drop_creator_only, need_scope, need_known = _APPELLATION_RULES[scope.regime]
    facts = list({fact.id: fact for fact, _ in pairs}.values())
    if drop_creator_only:
        pairs = [(f, e) for f, e in pairs if f.id not in hidden]
    if need_scope:
        scoped = _scoped_fact_ids(db, world_id, facts)
        pairs = [(f, e) for f, e in pairs if f.id in scoped]
    if need_known:
        pairs = [(f, e) for f, e in pairs if f.id in scope.known_fact_ids]
    return pairs


def surfaces(db: Session, world_id: str, scope: NameScope) -> tuple[NameSurface, ...]:
    """Every name surface of `world_id` under `scope` (C-03): names by
    `entity_id`, then appellations by `(entity_id, fact_id)`."""
    # Function-local import: a module-level one closes the cycle
    # facet_reads -> knowledge_resolve -> writes.knowledge -> prose_tokens ->
    # lore_resolve -> name_index -> facet_reads (R-07).
    from .facet_reads import creator_only_fact_ids

    entities = [
        e for e in db.exec(
            select(Entity).where(Entity.world_id == world_id, Entity.status == "active")
        ).all()
        if e.id != scope.exclude_entity_id
    ]
    if not entities:
        return ()
    by_id = {e.id: e for e in entities}
    names = [NameSurface(e.name, e.id, e.name, e.type, "name", None)
             for e in sorted(entities, key=lambda e: e.id)]
    if not _APPELLATION_RULES[scope.regime][0]:
        return tuple(names)
    pairs = db.exec(
        select(Fact, FactParticipant.entity_id)
        .join(FactParticipant, FactParticipant.fact_id == Fact.id)
        .where(Fact.world_id == world_id, Fact.facet == "appellation")
    ).all()
    pairs = sorted(((f, e) for f, e in pairs if e in by_id), key=lambda p: (p[1], p[0].id))
    hidden = creator_only_fact_ids(db, {fact.id for fact, _ in pairs})
    pairs = _kept_pairs(db, world_id, scope, pairs, hidden)
    texts = fact_texts(db, [fact for fact, _ in pairs])
    appellations = [
        NameSurface(text, eid, by_id[eid].name, by_id[eid].type, "appellation", fact.id)
        for text, (fact, eid) in zip(texts, pairs) if text
    ]
    return tuple(names + appellations)
