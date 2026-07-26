"""Trait registry — code-source-of-truth (A1, TICKET-0045, BRIEF-0045-b).

Each trait is a bundle: a set of typed `ext_*` columns (BRIEF-0046-a), an
IMPORTABLE reference to its reader, plus the form field-specs those columns
render as. "No structure without a reader" (E2) is enforced structurally
here (`TraitDef.__post_init__` rejects a trait declared with zero or
multiple reader forms) and completed by `trait_reader.py` (BRIEF-0045-c),
which actually resolves each declared reader. `ext_columns_for` /
`form_fields_for` are the single derivation of both the DDL `columns`
(`writes/schema.py::create_entity_type`) and the generated-form field-specs
from a trait selection — completing the 0045 derivation gap noted at
`writes/schema.py:15`. The registry is edited only via Claude Code — never
hot-editable by the creator at runtime; new traits (e.g. `rideable`) are
added here and become available to every entity type.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .writes.schema import valid_col_types


@dataclass(frozen=True)
class ExtColumnSpec:
    name: str
    col_type: str
    field: dict

    def __post_init__(self) -> None:
        if self.field.get("name") != self.name:
            raise ValueError(
                f"ExtColumnSpec {self.name!r}: field['name'] must equal name "
                "(no free-text duplication of the column name)"
            )
        if self.col_type not in valid_col_types():
            raise ValueError(
                f"ExtColumnSpec {self.name!r}: col_type {self.col_type!r} "
                f"must be one of {sorted(valid_col_types())}"
            )
        if self.field.get("kind") == "json":
            raise ValueError(
                f"ExtColumnSpec {self.name!r}: field kind 'json' is forbidden "
                "(no JSON-UI field may be born here)"
            )


@dataclass(frozen=True)
class TraitDef:
    key: str
    label: str
    checkable: bool
    ext_columns: tuple[ExtColumnSpec, ...]
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
        ext_columns=(),
        reader_callable="world_engine.context:_npc_context_identity",
        reader_guard=None,
        reader_deferred=None,
    ),
    TraitDef(
        key="spatial",
        label="Spatial",
        checkable=True,
        ext_columns=(
            ExtColumnSpec(
                name="location_id",
                col_type="FK_ENTITY_NULLABLE",
                field={
                    "name": "location_id", "label": "Location",
                    "kind": "entity_ref", "ref_type": "location",
                },
            ),
        ),
        reader_callable="world_engine.placement:spawn_point",
        reader_guard=None,
        reader_deferred=None,
    ),
    TraitDef(
        key="knowable",
        label="Connaissable",
        checkable=True,
        ext_columns=(),
        reader_callable="world_engine.context:_npc_context_speak",
        reader_guard=None,
        reader_deferred=None,
    ),
    TraitDef(
        key="secretable",
        label="Peut receler un secret",
        checkable=True,
        ext_columns=(
            ExtColumnSpec(
                name="is_secret",
                col_type="BOOLEAN",
                field={
                    "name": "is_secret", "label": "Secret (creator-only)",
                    "kind": "bool", "default": False,
                },
            ),
        ),
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
        ext_columns=(),
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


# Base entity field names — authority: cockpit/crud/entities.py:
# ENTITY_BASE_FIELDS. Hardcoded here rather than imported: crud/entities.py
# sits in the FastAPI cockpit route layer and pulls in the whole app; this
# module is core and must stay importable (and import-cycle-free) without
# it (BRIEF-0046-a drafting decision 5).
_ENTITY_BASE_FIELD_NAMES = frozenset(
    {"name", "internal_name", "description", "is_public", "status"}
)


def _assert_no_socle_base_collision() -> None:
    for trait in socle_traits():
        for spec in trait.ext_columns:
            if spec.name in _ENTITY_BASE_FIELD_NAMES:
                raise ValueError(
                    f"socle trait {trait.key!r} declares ext column "
                    f"{spec.name!r}, which collides with an "
                    "ENTITY_BASE_FIELDS name"
                )


_assert_no_socle_base_collision()


def _ordered_ext_specs(trait_keys: Iterable[str]) -> list[ExtColumnSpec]:
    """Socle traits first, then checked keys in TRAITS declaration order —
    the single ordering both derivations below share. Raises ValueError on
    an ext-column name collision across traits."""
    keys = set(trait_keys)
    ordered_traits = list(socle_traits()) + [
        trait for trait in checkable_traits() if trait.key in keys
    ]
    specs: list[ExtColumnSpec] = []
    seen: set[str] = set()
    for trait in ordered_traits:
        for spec in trait.ext_columns:
            if spec.name in seen:
                raise ValueError(
                    f"ext column name {spec.name!r} collides across traits "
                    f"(duplicate emission at trait {trait.key!r})"
                )
            seen.add(spec.name)
            specs.append(spec)
    return specs


def ext_columns_for(trait_keys: Iterable[str]) -> list[tuple[str, str]]:
    """The `(name, col_type)` list to pass to `create_entity_type`, unioning
    `socle_traits()` ext columns with those of each checkable trait key
    present in `trait_keys`. Unknown / non-checkable keys are ignored."""
    return [(spec.name, spec.col_type) for spec in _ordered_ext_specs(trait_keys)]


def form_fields_for(trait_keys: Iterable[str]) -> list[dict]:
    """The generated-form field-spec dicts for the same effective set and
    order as `ext_columns_for`, for the created entity type's form."""
    return [spec.field for spec in _ordered_ext_specs(trait_keys)]
