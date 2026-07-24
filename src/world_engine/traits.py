"""Trait registry — code-source-of-truth (A1, TICKET-0045, BRIEF-0045-b).

Each trait is a bundle: a column set, an optional FK spec, and an IMPORTABLE
reference to its reader. "No structure without a reader" (E2) is enforced
structurally here (`TraitDef.__post_init__` rejects a trait declared with
zero or multiple reader forms) and completed by `trait_reader.py`
(BRIEF-0045-c), which actually resolves each declared reader. The registry
is edited only via Claude Code — never hot-editable by the creator at
runtime; new traits (e.g. `rideable`) are added here and become available to
every entity type.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TraitDef:
    key: str
    label: str
    checkable: bool
    columns: tuple[str, ...]
    fk: str | None
    reader_callable: str | None
    reader_guard: tuple[str, str] | None
    reader_deferred: str | None

    def __post_init__(self) -> None:
        forms = (self.reader_callable, self.reader_guard, self.reader_deferred)
        if sum(1 for form in forms if form is not None) != 1:
            raise ValueError(
                f"trait {self.key!r} must declare exactly one reader form "
                "(reader_callable | reader_guard | reader_deferred)"
            )


TRAITS: tuple[TraitDef, ...] = (
    TraitDef(
        key="describable",
        label="Descriptible",
        checkable=False,
        columns=("name", "description"),
        fk=None,
        reader_callable="world_engine.context:_npc_context_identity",
        reader_guard=None,
        reader_deferred=None,
    ),
    TraitDef(
        key="spatial",
        label="Spatial",
        checkable=True,
        columns=("location_id",),
        fk="location_id -> location.id",
        reader_callable="world_engine.placement:spawn_point",
        reader_guard=None,
        reader_deferred=None,
    ),
    TraitDef(
        key="knowable",
        label="Connaissable",
        checkable=True,
        columns=(),
        fk=None,
        reader_callable="world_engine.context:_npc_context_speak",
        reader_guard=None,
        reader_deferred=None,
    ),
    TraitDef(
        key="secretable",
        label="Peut receler un secret",
        checkable=True,
        columns=("is_secret",),
        fk=None,
        reader_callable=None,
        reader_guard=("world_engine.context", "is_secret"),
        reader_deferred=None,
    ),
    # E2 exception, B2(ii): the ONLY trait permitted a deferred reader. Its
    # reader is the canon-write dispatch of TICKET-0047 (write_authorities /
    # ai_proposable, reserved at the socle, schema v1.87). trait_reader.py
    # tolerates this trait by name; no other trait may set reader_deferred.
    TraitDef(
        key="mutable_by_ai",
        label="Modifiable par l'IA",
        checkable=True,
        columns=(),
        fk=None,
        reader_callable=None,
        reader_guard=None,
        reader_deferred="TICKET-0047",
    ),
)


def trait_keys() -> tuple[str, ...]:
    return tuple(trait.key for trait in TRAITS)


def checkable_traits() -> tuple[TraitDef, ...]:
    return tuple(trait for trait in TRAITS if trait.checkable)


def socle_traits() -> tuple[TraitDef, ...]:
    """Non-checkable traits, implicit on every entity_type (describable
    today) — never a palette checkbox, never an entity_trait row. The
    counterpart to checkable_traits(): together they partition TRAITS."""
    return tuple(trait for trait in TRAITS if not trait.checkable)
