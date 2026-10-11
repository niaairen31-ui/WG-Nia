<!-- slug: attribute-store -->
# BRIEF 0113-A — "The state of the world, stored -- attribute definitions, their types and labels, one value per entity, its history row by row (schema v2.22)"

Lot: LOT-0113-world-state.md (authoritative on conflict)
Depends on: none (first of the lot; `main` at `d9230a7` or later)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (on `main`).

- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.21"`
- `world-engine-schema.md:3` -> `Current schema version: v2.21`
- `world-engine-schema.md:2607` -> `CREATE INDEX idx_debt_term_debt ON debt_term(debt_id);`
- `world-engine-schema.md:2612` -> ``### `goal_agenda_link` ``
- `world-engine-schema-changelog.md:16` -> `- **v2.21** — TICKET-0112, BRIEF-0112-B: the condition interpreter's`
- `src/world_engine/models/__init__.py:83` -> `from .canon_faction import (`
- `src/world_engine/writes/worlds.py:77` -> `"world_law", "quest", "quest_offer", "quest_offer_step",`
- `src/world_engine/writes/facts.py:56` -> `FACT_CHANGE_KINDS: tuple[str, ...] = ("correction", "changement")`
- `src/world_engine/lore_resolve.py:73` -> `def normalize_surface(text: str) -> str:`
- `tooling/verify/canon_write_policy.txt:7` -> `npc_schedule condition condition_node fact fact_participant fact_default`
- `tooling/verify/checks/world_cascade.py:67` -> `_FIXTURE: tuple[tuple[str, dict], ...] = (`
- No `src/world_engine/attributes.py`, `src/world_engine/models/canon_attribute.py`, `src/world_engine/writes/attributes.py`, `scripts/migrate_v2_22_attributes.py`, `tooling/verify/checks/attributes.py` exist.

## Facts carried

### R-01 — the canon already keeps three states, and an item's wear [M]
Opened: `src/world_engine/models/canon.py:117` (`Entity`), `:126` (`type`),
`:133` (`status`), `:143` (`Character`), `:168` (`vital_status`), `:206`
(`Location`), `:215` (`magic_status`), `:549` (`Item`), `:554`
(`condition`). Vocabularies: `src/world_engine/cockpit/crud/entities.py:117`
(`ENTITY_STATUSES`), `:128` (`ENTITY_TYPE_REGISTRY`), `:139`
(`vital_status` select), `:157` (`magic_status` select) -- no CHECK on any.
Consequence: three system attributes, `sys:vital_status`, `sys:status`,
`sys:magic_status`, read in place, their values the creator forms' (AA4
keeps them equal); never copied (G3), never written by the attribute
writer. `item.condition` untouched (WF1).

### R-02 — the entity types of a world [M]
Opened: `src/world_engine/models/canon.py:870-890` (`EntityType`:
`world_id`, `slug` unique per world NOCASE, `status` in
`active` / `retired` / `quarantined`); the built-in four are
`ENTITY_TYPE_REGISTRY`'s keys (`cockpit/crud/entities.py:128`), a runtime
type's entities carry its slug in `entity.type`.
Consequence: a definition's types are the built-in four then the world's
active runtime types (`attributes.world_entity_types`); AA4 keeps the
built-in list equal to the registry.

### R-03 — a change is `correction` or `changement` since TICKET-0105 [M]
Opened: `src/world_engine/writes/facts.py:38` (the docstring's two
meanings), `:56` (`FACT_CHANGE_KINDS = ("correction", "changement")`),
`:61-62` (refusal); `src/world_engine/cockpit/crud/facets.py:45`
(`kind: Literal["correction", "changement"]`, required).
Consequence: `ATTRIBUTE_CHANGE_KINDS` is the same pair in the same order
(AA1), required on every value write, never defaulted -- the panel
preselects neither (AC3).

### R-14 — the canon-write gate names every table and every site [M]
Opened: `tooling/verify/canon_write_policy.txt:1-8` (`[CANON_TABLES]`),
`:65-66` (an allowed site with its reason); `tooling/verify/checks/single_canon_write.py:81`
(the docstring naming each full-replace writer).
Consequence: the five tables join `CANON_TABLES`; the writer's five sites
are allowed with their reason; `_write_types` is named full-replace.

### R-15 — deleting a world deletes its rows [M]
Opened: `src/world_engine/writes/worlds.py:66-77`
(`_DIRECT_WORLD_SCOPED_DELETES`); `tooling/verify/checks/world_cascade.py:67`
(`_FIXTURE`, one row per world-scoped table).
Consequence: every table carries `world_id` (`attribute_value`,
`attribute_change` too: a direct delete, no subquery); the five join the
list and the fixture.

### R-16 — the schema version moves in three places; a migration converges [M]
Opened: `src/world_engine/schema_version.py:15` (`"v2.21"`);
`world-engine-schema.md:3`; `world-engine-schema-changelog.md:16`;
`scripts/migrate_v2_21_condition_draft.py:54` (`_PREVIOUS_VERSION`),
`:133-145` (`_converge_schema_meta` writes the CODE's version).
Consequence: two versions in one lot. Each migration converges
`schema_meta` to ITS OWN version (v2.22, v2.23), not the code's: a
database migrated by v2.22 alone stays refused by the boot guard
(measured: « schema_meta says DB is at 'v2.22', code expects 'v2.23' »)
until v2.23 has run.

### R-17 — the `subject` census [M]
Opened: `tooling/verify/checks/knowledge_identity.py:31-33` (K3: every
`subject` reference in `src/world_engine`, counted per file, equals
`_SUBJECT_CENSUS`), `:109-119`.
Consequence: the side of a definition's types is named `holder` (and
`holder_types`, the parameter `holder`), not `subject` -- a word K3 would
count in four new files. The condition leaf's `subject` is untouched.

### R-19 — fifteen seconds per check [M]
Opened: `tooling/verify/checks/corpus_gate.py:21-28` (per-check timeout,
`TIMEOUT` a failure); `.claude/rules/verify-checks.md` (15 s).
Consequence: the rules are split over three checks -- `attributes.py`
(AA, AC; ~5 s measured), `attribute_conditions.py` (AB; ~7 s),
`attribute_interpreter.py` (AD, AE; ~6 s) -- each wrapping every rule so a
crash is a named failure.

## Contracts

### C-01 — the five tables (v2.22)
Produced by: BRIEF-0113-A   Consumed by: BRIEF-0113-B to E (through C-02, C-03)
`attribute_definition (id, world_id FK, name, kind, default_integer,
is_hidden, status, created_at, updated_at)`: CHECK kind in
`choice|integer|entity`; CHECK `kind = 'integer' OR default_integer IS
NULL`; CHECK status in `active|retired`; unique
`idx_attribute_definition_name (world_id, name COLLATE NOCASE)`.
`attribute_definition_type (id, world_id, definition_id FK, side,
entity_type)`: CHECK side in `holder|value`; unique (definition_id, side,
entity_type).
`attribute_choice (id, world_id, definition_id FK, label, position,
is_default, status)`: CHECK `is_default = 0 OR status = 'active'`; unique
(definition_id, label NOCASE); partial unique: one default per definition.
`attribute_value (id, world_id, definition_id FK, entity_id FK, choice_id
FK, integer_value, entity_value_id FK, updated_at)`: CHECK at most one of
the three set; unique (definition_id, entity_id); index on entity_id.
`attribute_change (id, world_id, value_id FK, kind, changed_by,
before_choice_id, before_integer, before_entity_id, after_choice_id,
after_integer, after_entity_id, changed_at)`: CHECK kind in
`correction|changement`; INSERT-only.
Constants (`models`): `ATTRIBUTE_KINDS`, `ATTRIBUTE_TYPE_SIDES =
("holder", "value")`, `ATTRIBUTE_STATUSES`, `ATTRIBUTE_CHANGE_KINDS =
("correction", "changement")`.

### C-02 — `attributes` (reads)
Produced by: BRIEF-0113-A (C adds the last four)   Consumed by: B, C, D, E
`ATTRIBUTE_FORM = "attribute"`; `BUILTIN_ENTITY_TYPES`; `SYSTEM_ATTRIBUTES`
(`sys:vital_status` on characters, `sys:status` on every entity,
`sys:magic_status` on locations; each `(stored value, French label)`).
`AttributeView(key, name, kind, system, hidden, status, holder_types
(None: every type), value_types, choices ((key, label), ...), default)`;
`StateValue(raw, label, is_default)`.
`attribute_view(db, world_id, key) -> Optional[AttributeView]`;
`view_of(db, key)` (any world, for a stored leaf -- B);
`world_attributes(db, world_id, include_retired=False)` (system first,
then the world's by name); `applies_to(view, entity_type) -> bool`;
`value_label(db, view, raw) -> str`; `current_value(db, view, entity) ->
StateValue` (the default when the entity holds none; writes nothing).
C: `world_entity_type_labels(db, world_id) -> [{type, label}]`;
`near_attributes(db, world_id, name, exclude_key=None) ->
tuple[NearAttribute(key, name, system, score)]` (retired included, best
first); `entity_states(db, world_id, entity) -> [{key, name, kind, system,
hidden, raw, label, is_default, choices, value_types, history}]` (history
newest first, `[]` for a system attribute).

### C-03 — `writes.attributes` (the one writer)
Produced by: BRIEF-0113-A   Consumed by: C (routes), E (proposals, save)
`ChoiceSpec(label, id=None)`; `DefinitionSpec(name, kind, holder_types,
value_types=(), choices=(), default=None, is_hidden=False)` -- `default` a
choice's LABEL, an integer, or None.
`clean_definition(db, world_id, spec, definition_id=None) ->
DefinitionSpec`: writes nothing; case b-1.
`write_attribute_definition(db, *, world_id, spec, definition_id=None) ->
AttributeDefinition` (flushed; types replaced whole; a dropped label
retired, a named retired one revived).
`set_attribute_status(db, *, world_id, definition_id, status)`: retiring
refused while a leaf of form `attribute` names it.
`write_attribute_value(db, *, world_id, definition_id, entity_id, value,
kind, changed_by) -> Optional[AttributeChange]`: `value` a choice id, an
integer or an entity id (None: none); unchanged -> None, nothing written;
`before` is the stored value or the default.
Error cases: `ValueError` naming the problem; none commits; a system key is
never accepted (no row holds it).

## Context

The canon cannot say that a door is open or a throne occupied by Ysa. This brief gives a world its own vocabulary of states: a definition per idea, with its kind, the entity types it applies to, its labels and default; one value per entity; a history row per change, `correction` or `changement`. The three states the canon already keeps are read in place as system attributes. Nothing reads attributes yet but the check: the condition form (B), Création (C) and the interpreter (D, E) follow.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `models/canon_attribute.py` (the five tables, C-01) and exports them from `models/__init__.py`;
   - creates `attributes.py` (reads, `SYSTEM_ATTRIBUTES`, C-02) and `writes/attributes.py` (the one writer, C-03), exported from `writes/__init__.py`;
   - creates `scripts/migrate_v2_22_attributes.py` (creates the five tables, refuses below v2.21, converges `schema_meta` to v2.22 -- its own version, R-16 -- idempotent);
   - adds the five tables to `writes/worlds.py`'s delete list and `world_cascade.py`'s fixture (R-15), to `canon_write_policy.txt` with five allowed sites, and names `_write_types` full-replace in `single_canon_write.py` (R-14);
   - bumps `schema_version.py`, documents the five tables in `world-engine-schema.md` (before `goal_agenda_link`) and the changelog (v2.22);
   - creates check `attributes.py` (AA1-AA7) and appends the decision entry above the footer.
   The files it touches, exactly:
   - scripts/migrate_v2_22_attributes.py
   - src/world_engine/attributes.py
   - src/world_engine/models/__init__.py
   - src/world_engine/models/canon_attribute.py
   - src/world_engine/schema_version.py
   - src/world_engine/writes/__init__.py
   - src/world_engine/writes/attributes.py
   - src/world_engine/writes/worlds.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/canon_write_policy.txt
   - tooling/verify/checks/attributes.py
   - tooling/verify/checks/single_canon_write.py
   - tooling/verify/checks/world_cascade.py
   - world-engine-schema-changelog.md
   - world-engine-schema.md

````diff
diff --git a/scripts/migrate_v2_22_attributes.py b/scripts/migrate_v2_22_attributes.py
new file mode 100644
index 0000000..7a64381
--- /dev/null
+++ b/scripts/migrate_v2_22_attributes.py
@@ -0,0 +1,144 @@
+"""Migration v2.22 — the state of the world (TICKET-0113, BRIEF-0113-A;
+decisions WA3, WB2, WC1, WD1 and WH1 of the conditions series).
+
+Creates the five attribute tables, each with its CHECKs and indexes,
+exactly as `models/canon_attribute.py` declares them (`Table.create`, the
+`migrate_v1_89_conversation_window_config.py` precedent):
+`attribute_definition`, `attribute_definition_type`, `attribute_choice`,
+`attribute_value`, `attribute_change`.
+
+Purely additive, zero rows created: a world's attributes are defined by
+the creator going forward; the states the canon already keeps
+(`character.vital_status`, `entity.status`, `location.magic_status`) are
+read in place as system attributes and never copied (G3 of the series).
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.21 (the migrations are sequential).
+
+Idempotent: each table's existence is checked before creating it; all five
+are created in one transaction.
+
+Post-check, before `schema_meta` moves: the five tables exist and hold zero
+rows. `schema_meta` then moves to v2.22 -- this migration's own version, not
+the code's: v2.23 (BRIEF-0113-B) converts data this one does not, and the
+boot guard must keep refusing until it has run.
+
+Run from the project root:
+
+    python scripts/migrate_v2_22_attributes.py
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+from datetime import UTC, datetime
+from pathlib import Path
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
+    print(
+        "migrate_v2_22_attributes.py refuses to run without WORLD_ENGINE_ENV "
+        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+from sqlalchemy import inspect, text  # noqa: E402
+from sqlmodel import Session  # noqa: E402
+
+from world_engine import models  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.21"
+_THIS_VERSION = "v2.22"
+# Parents first: each table's foreign keys name a table created before it.
+_MODELS = (
+    models.AttributeDefinition,
+    models.AttributeDefinitionType,
+    models.AttributeChoice,
+    models.AttributeValue,
+    models.AttributeChange,
+)
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+def _refuse_if_behind() -> None:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
+    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
+        found = row[0] if row is not None else "no schema_meta row"
+        raise SystemExit(
+            f"Migration v2.22 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _apply_ddl() -> list[str]:
+    present = set(inspect(engine).get_table_names())
+    missing = [m for m in _MODELS if m.__tablename__ not in present]
+    if not missing:
+        print("The five attribute tables already exist — nothing to do.")
+        return []
+    with engine.begin() as conn:
+        for model in missing:
+            model.__table__.create(conn)
+    return [m.__tablename__ for m in missing]
+
+
+def _post_checks() -> None:
+    present = set(inspect(engine).get_table_names())
+    with engine.connect() as conn:
+        for model in _MODELS:
+            name = model.__tablename__
+            if name not in present:
+                raise SystemExit(f"Migration v2.22 aborted, post-check failed: {name} is missing.")
+            count = conn.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar()
+            if count != 0:
+                raise SystemExit(
+                    f"Migration v2.22 aborted, post-check failed: {name} holds {count} row(s), "
+                    "expected 0 — this migration creates zero rows."
+                )
+    print("Post-check: the five attribute tables exist and hold 0 rows.")
+
+
+def _converge_schema_meta() -> None:
+    with Session(engine) as session:
+        row = session.get(models.SchemaMeta, 1)
+        if row is None:
+            session.add(models.SchemaMeta(id=1, static_version=_THIS_VERSION))
+            print(f"Row: seeded schema_meta.id=1 at {_THIS_VERSION!r}")
+        elif _version_key(row.static_version) < _version_key(_THIS_VERSION):
+            previous = row.static_version
+            row.static_version = _THIS_VERSION
+            row.updated_at = datetime.now(UTC)
+            session.add(row)
+            print(f"Row: updated schema_meta.id=1: {previous!r} -> {_THIS_VERSION!r}")
+        else:
+            print(f"Row: schema_meta.id=1 already at {row.static_version!r} — nothing to do")
+        session.commit()
+
+
+def main() -> None:
+    print("Migration v2.22 — the state of the world")
+    _refuse_if_behind()
+    applied = _apply_ddl()
+    if applied:
+        print("Applied: " + ", ".join(applied) + ".")
+    else:
+        print("Migration v2.22 already fully applied — zero writes.")
+    _post_checks()
+    _converge_schema_meta()
+    print("\nMigration v2.22 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/attributes.py b/src/world_engine/attributes.py
new file mode 100644
index 0000000..62c12ba
--- /dev/null
+++ b/src/world_engine/attributes.py
@@ -0,0 +1,231 @@
+"""The state of the world, read (TICKET-0113, BRIEF-0113-A; decisions WA3,
+WB2, WC1, WE1 and WH1 of the conditions series).
+
+An attribute is either one of a world's definitions (`attribute_definition`,
+keyed by its id) or a SYSTEM attribute -- a state the canon already keeps,
+read where it lives and never copied (G3 of the series), keyed `sys:<name>`:
+`character.vital_status`, `entity.status`, `location.magic_status`. Both
+read the same way here:
+
+- `attribute_view(db, world_id, key)` : one attribute as an `AttributeView`
+  (its kind, its types, its choices, its default), or None.
+- `world_attributes(db, world_id)`    : the system attributes, then the
+  world's definitions by name.
+- `current_value(db, view, entity)`   : an entity's `StateValue` -- its own
+  value, or the default when it holds none (WC1: nothing is written on read).
+- `world_entity_types(db, world_id)`  : the entity types a definition may
+  name (WB2): the built-in four, then the world's active runtime types.
+
+The vocabularies of the system attributes are the creator forms'
+(`cockpit/crud/entities.py`: `ENTITY_STATUSES`, the character's
+`vital_status` select, the location's `magic_status` select), kept equal to
+them by `attributes.py` AA4. This module writes nothing; its writer is
+`writes/attributes.py`.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Optional, Union
+
+from sqlmodel import Session, select
+
+from .models import (
+    AttributeChoice,
+    AttributeDefinition,
+    AttributeDefinitionType,
+    AttributeValue,
+    Character,
+    Entity,
+    EntityType,
+    Location,
+)
+
+# The condition form that reads an attribute (TICKET-0113, WG1); its
+# evaluator lives in `condition_forms.py`.
+ATTRIBUTE_FORM = "attribute"
+
+# The built-in entity types -- `cockpit/crud/entities.py`'s
+# `ENTITY_TYPE_REGISTRY` keys, kept equal by AA4. A runtime type is named by
+# its `entity_type.slug`, which is its entities' `entity.type`.
+BUILTIN_ENTITY_TYPES: tuple[str, ...] = ("character", "location", "faction", "item")
+
+SYSTEM_PREFIX = "sys:"
+
+RawValue = Union[str, int, None]
+
+
+@dataclass(frozen=True)
+class SystemAttribute:
+    """A state the canon already keeps (WE1): a `choice` kind whose choices
+    are the column's values, each with its French label."""
+    key: str
+    name: str
+    entity_types: Optional[tuple[str, ...]]  # None: every entity
+    values: tuple[tuple[str, str], ...]      # (stored value, French label)
+    default: str
+
+
+SYSTEM_ATTRIBUTES: tuple[SystemAttribute, ...] = (
+    SystemAttribute("sys:vital_status", "État vital", ("character",),
+                    (("alive", "en vie"), ("dead", "mort"), ("missing", "disparu"), ("unknown", "d'état inconnu")),
+                    "alive"),
+    SystemAttribute("sys:status", "Statut", None,
+                    (("active", "actif"), ("inactive", "inactif"), ("destroyed", "détruit"),
+                     ("missing", "disparu")),
+                    "active"),
+    SystemAttribute("sys:magic_status", "Magie", ("location",),
+                    (("inert", "inerte"), ("sensitive", "sensible"), ("active", "active"), ("nexus", "nexus")),
+                    "inert"),
+)
+
+
+@dataclass(frozen=True)
+class AttributeView:
+    """One attribute as every reader sees it. `choices` are (key, label)
+    pairs in order -- a choice's id, or a system value; `default` is a
+    choice key, an integer, or None (an `entity` kind's default is empty).
+    `holder_types` None: every entity type."""
+    key: str
+    name: str
+    kind: str
+    system: bool
+    hidden: bool
+    status: str
+    holder_types: Optional[tuple[str, ...]]
+    value_types: tuple[str, ...]
+    choices: tuple[tuple[str, str], ...]
+    default: RawValue
+
+
+@dataclass(frozen=True)
+class StateValue:
+    """An entity's state for one attribute: the raw value (a choice key, an
+    integer, an entity id or None), its French label, and whether it is the
+    default because the entity holds no value of its own."""
+    raw: RawValue
+    label: str
+    is_default: bool
+
+
+def system_attribute(key: Optional[str]) -> Optional[SystemAttribute]:
+    return next((s for s in SYSTEM_ATTRIBUTES if s.key == key), None)
+
+
+def world_entity_types(db: Session, world_id: str) -> tuple[str, ...]:
+    """WB2: the built-in types, then the world's active runtime types by slug."""
+    slugs = db.exec(select(EntityType.slug).where(
+        EntityType.world_id == world_id, EntityType.status == "active",
+    )).all()
+    return BUILTIN_ENTITY_TYPES + tuple(sorted(s for s in slugs if s not in BUILTIN_ENTITY_TYPES))
+
+
+def _system_view(spec: SystemAttribute) -> AttributeView:
+    return AttributeView(
+        key=spec.key, name=spec.name, kind="choice", system=True, hidden=False, status="active",
+        holder_types=spec.entity_types, value_types=(), choices=spec.values, default=spec.default,
+    )
+
+
+def _types(db: Session, definition_id: str, side: str) -> tuple[str, ...]:
+    return tuple(db.exec(select(AttributeDefinitionType.entity_type).where(
+        AttributeDefinitionType.definition_id == definition_id, AttributeDefinitionType.side == side,
+    ).order_by(AttributeDefinitionType.entity_type)).all())
+
+
+def _definition_view(db: Session, definition: AttributeDefinition) -> AttributeView:
+    choices = db.exec(select(AttributeChoice).where(
+        AttributeChoice.definition_id == definition.id, AttributeChoice.status == "active",
+    ).order_by(AttributeChoice.position)).all()
+    default: RawValue = None
+    if definition.kind == "choice":
+        default = next((c.id for c in choices if c.is_default), None)
+    elif definition.kind == "integer":
+        default = definition.default_integer
+    return AttributeView(
+        key=definition.id, name=definition.name, kind=definition.kind, system=False,
+        hidden=definition.is_hidden, status=definition.status,
+        holder_types=_types(db, definition.id, "holder"), value_types=_types(db, definition.id, "value"),
+        choices=tuple((c.id, c.label) for c in choices), default=default,
+    )
+
+
+def attribute_view(db: Session, world_id: str, key: Optional[str]) -> Optional[AttributeView]:
+    """The attribute `key` names in `world_id` -- a system key or one of its
+    definitions, active or retired -- or None."""
+    spec = system_attribute(key)
+    if spec is not None:
+        return _system_view(spec)
+    definition = db.get(AttributeDefinition, key) if key else None
+    if definition is None or definition.world_id != world_id:
+        return None
+    return _definition_view(db, definition)
+
+
+def world_attributes(db: Session, world_id: str, include_retired: bool = False) -> tuple[AttributeView, ...]:
+    """Every attribute of the world: the system ones, then its definitions
+    by name (the retired ones only on request)."""
+    query = select(AttributeDefinition).where(AttributeDefinition.world_id == world_id)
+    if not include_retired:
+        query = query.where(AttributeDefinition.status == "active")
+    definitions = sorted(db.exec(query).all(), key=lambda d: d.name.casefold())
+    return tuple(_system_view(s) for s in SYSTEM_ATTRIBUTES) + tuple(_definition_view(db, d) for d in definitions)
+
+
+def applies_to(view: AttributeView, entity_type: str) -> bool:
+    return view.holder_types is None or entity_type in view.holder_types
+
+
+def value_label(db: Session, view: AttributeView, raw: RawValue) -> str:
+    """The French of one raw value of `view`: a choice's label (a retired one
+    included, for the history), an integer, an entity's name, or « (aucun) »."""
+    if raw is None:
+        return "(aucun)"
+    if view.kind == "integer":
+        return str(raw)
+    if view.kind == "entity":
+        entity = db.get(Entity, raw)
+        return entity.name if entity is not None else str(raw)
+    label = dict(view.choices).get(raw)
+    if label is None and not view.system:
+        choice = db.get(AttributeChoice, raw)
+        label = choice.label if choice is not None else None
+    return label if label is not None else str(raw)
+
+
+def _system_raw(db: Session, key: str, entity: Entity) -> RawValue:
+    if key == "sys:status":
+        return entity.status
+    if key == "sys:vital_status":
+        character = db.get(Character, entity.id)
+        return character.vital_status if character is not None else None
+    location = db.get(Location, entity.id)
+    return location.magic_status if location is not None else None
+
+
+def stored_value(db: Session, definition_id: str, entity_id: str) -> Optional[AttributeValue]:
+    return db.exec(select(AttributeValue).where(
+        AttributeValue.definition_id == definition_id, AttributeValue.entity_id == entity_id,
+    )).first()
+
+
+def raw_of(row: AttributeValue) -> RawValue:
+    if row.choice_id is not None:
+        return row.choice_id
+    if row.integer_value is not None:
+        return row.integer_value
+    return row.entity_value_id
+
+
+def current_value(db: Session, view: AttributeView, entity: Entity) -> StateValue:
+    """The entity's state for `view`: a system column read where it lives,
+    else its own value, else the default (WC1). The caller checks
+    `applies_to` first."""
+    if view.system:
+        raw = _system_raw(db, view.key, entity)
+        return StateValue(raw=raw, label=value_label(db, view, raw), is_default=False)
+    row = stored_value(db, view.key, entity.id)
+    if row is None:
+        return StateValue(raw=view.default, label=value_label(db, view, view.default), is_default=True)
+    raw = raw_of(row)
+    return StateValue(raw=raw, label=value_label(db, view, raw), is_default=False)
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index 48aeb40..1abdf68 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -17,6 +17,10 @@ Layout, by stratum:
                         knowledge anchor spine) added at BRIEF-0082-b.
                         FactDefault (scoped default knowledge level, G2a)
                         added at BRIEF-0082-c.
+    canon_attribute.py — the state of the world (AttributeDefinition,
+                        AttributeDefinitionType, AttributeChoice,
+                        AttributeValue, AttributeChange; TICKET-0113,
+                        schema v2.22), canon.
     config.py        — canon curated-config tables too new/small to justify
                         growing canon.py at its module_budget cap
                         (ConversationWindowConfig, TICKET-0050).
@@ -39,7 +43,8 @@ This module re-exports the ENTIRE former public surface of the flat
 `models.py` — every class, constant, and the two module functions
 (`_uuid`, `_created_ts`) — so every existing `from .models import X` /
 `from world_engine.models import X` in `src/` and `scripts/` resolves
-unchanged. Import order (canon, canon_faction, canon_knowledge, config,
+unchanged. Import order (canon, canon_faction, canon_knowledge,
+canon_attribute, config,
 ephemeral, pipeline, observation, quests) keeps table registration on
 `SQLModel.metadata` deterministic;
 cross-stratum foreign keys (string table-name references) resolve
@@ -86,6 +91,17 @@ from .canon_faction import (
     FactionRole,
 )
 from .canon_knowledge import Fact, FactDefault, FactParticipant, Knowledge, Relation
+from .canon_attribute import (
+    ATTRIBUTE_CHANGE_KINDS,
+    ATTRIBUTE_KINDS,
+    ATTRIBUTE_STATUSES,
+    ATTRIBUTE_TYPE_SIDES,
+    AttributeChange,
+    AttributeChoice,
+    AttributeDefinition,
+    AttributeDefinitionType,
+    AttributeValue,
+)
 from .config import (
     CONDITION_OPS,
     CONDITION_ROLES,
@@ -177,6 +193,15 @@ __all__ = [
     "Fact",
     "FactParticipant",
     "FactDefault",
+    "AttributeDefinition",
+    "AttributeDefinitionType",
+    "AttributeChoice",
+    "AttributeValue",
+    "AttributeChange",
+    "ATTRIBUTE_KINDS",
+    "ATTRIBUTE_TYPE_SIDES",
+    "ATTRIBUTE_STATUSES",
+    "ATTRIBUTE_CHANGE_KINDS",
     "NpcGoal",
     "GoalPrerequisite",
     "Ledger",
diff --git a/src/world_engine/models/canon_attribute.py b/src/world_engine/models/canon_attribute.py
new file mode 100644
index 0000000..cf858fd
--- /dev/null
+++ b/src/world_engine/models/canon_attribute.py
@@ -0,0 +1,141 @@
+"""Canon SQLModel table classes -- the state of the world (TICKET-0113,
+BRIEF-0113-A, schema v2.22; decisions WA3, WB2, WC1, WD1 and WH1 of the
+conditions series).
+
+A world defines its own attributes -- « Maudit », « Ouvert », « Niveau
+d'alerte », « Occupé par » -- and every entity of a type the definition
+names holds one value of it, its history kept row by row:
+
+- `attribute_definition`      : one attribute of one world -- its name, its
+  kind (a choice among labels, an integer, or another entity), its default
+  (WC1: an entity with no value reads the default, nothing is written on
+  read), whether it is hidden from the player (WH1), active or retired.
+- `attribute_definition_type` : the entity types it applies to
+  (`side = 'holder'`, WB2), and for an `entity` kind the types its value may
+  name (`side = 'value'`).
+- `attribute_choice`          : the labels of a `choice` kind, in order, one
+  of them the default; a label is retired, never deleted.
+- `attribute_value`           : one entity's current value -- a choice, an
+  integer, or an entity (none of the three: an `entity` kind left empty).
+- `attribute_change`          : the history (WD1), append-only: the value
+  before and after each write, `correction` or `changement`, by whom.
+
+The states the canon already keeps (`character.vital_status`,
+`entity.status`, `location.magic_status`) are read as SYSTEM attributes by
+`attributes.py`, never copied here (G3 of the series). `writes/attributes.py`
+is the one writer of all five tables. Same schema-fidelity conventions as
+`canon.py`.
+"""
+
+from __future__ import annotations
+
+from datetime import datetime
+from typing import Optional
+
+from sqlalchemy import CheckConstraint, Index, text
+from sqlmodel import Field, SQLModel
+
+from .canon import _created_ts, _uuid
+
+ATTRIBUTE_KINDS: tuple[str, ...] = ("choice", "integer", "entity")
+ATTRIBUTE_TYPE_SIDES: tuple[str, ...] = ("holder", "value")
+ATTRIBUTE_STATUSES: tuple[str, ...] = ("active", "retired")
+# The kind of a change -- `writes.facts.FACT_CHANGE_KINDS`, quoted by the
+# CHECK below (models never import `writes`; `attributes.py` AA1 keeps them
+# equal).
+ATTRIBUTE_CHANGE_KINDS: tuple[str, ...] = ("correction", "changement")
+
+
+class AttributeDefinition(SQLModel, table=True):
+    __tablename__ = "attribute_definition"
+    __table_args__ = (
+        CheckConstraint("kind IN ('choice','integer','entity')", name="ck_attribute_definition_kind"),
+        CheckConstraint("status IN ('active','retired')", name="ck_attribute_definition_status"),
+        CheckConstraint("kind = 'integer' OR default_integer IS NULL", name="ck_attribute_definition_default"),
+        Index("idx_attribute_definition_name", "world_id", text("name COLLATE NOCASE"), unique=True),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    name: str
+    kind: str
+    default_integer: Optional[int] = None
+    is_hidden: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
+    status: str = Field(default="active", sa_column_kwargs={"server_default": text("'active'")})
+    created_at: datetime = _created_ts()
+    updated_at: datetime = _created_ts()
+
+
+class AttributeDefinitionType(SQLModel, table=True):
+    __tablename__ = "attribute_definition_type"
+    __table_args__ = (
+        CheckConstraint("side IN ('holder','value')", name="ck_attribute_definition_type_side"),
+        Index("idx_attribute_definition_type_unique", "definition_id", "side", "entity_type", unique=True),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    definition_id: str = Field(foreign_key="attribute_definition.id", nullable=False)
+    side: str
+    entity_type: str
+
+
+class AttributeChoice(SQLModel, table=True):
+    __tablename__ = "attribute_choice"
+    __table_args__ = (
+        CheckConstraint("status IN ('active','retired')", name="ck_attribute_choice_status"),
+        CheckConstraint("is_default = 0 OR status = 'active'", name="ck_attribute_choice_default"),
+        Index("idx_attribute_choice_label", "definition_id", text("label COLLATE NOCASE"), unique=True),
+        Index("idx_attribute_choice_one_default", "definition_id", unique=True,
+              sqlite_where=text("is_default = 1")),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    definition_id: str = Field(foreign_key="attribute_definition.id", nullable=False)
+    label: str
+    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
+    is_default: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
+    status: str = Field(default="active", sa_column_kwargs={"server_default": text("'active'")})
+
+
+class AttributeValue(SQLModel, table=True):
+    __tablename__ = "attribute_value"
+    __table_args__ = (
+        CheckConstraint(
+            "(choice_id IS NOT NULL) + (integer_value IS NOT NULL) + (entity_value_id IS NOT NULL) <= 1",
+            name="ck_attribute_value_one",
+        ),
+        Index("idx_attribute_value_pair", "definition_id", "entity_id", unique=True),
+        Index("idx_attribute_value_entity", "entity_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    definition_id: str = Field(foreign_key="attribute_definition.id", nullable=False)
+    entity_id: str = Field(foreign_key="entity.id", nullable=False)
+    choice_id: Optional[str] = Field(default=None, foreign_key="attribute_choice.id")
+    integer_value: Optional[int] = None
+    entity_value_id: Optional[str] = Field(default=None, foreign_key="entity.id")
+    updated_at: datetime = _created_ts()
+
+
+class AttributeChange(SQLModel, table=True):
+    __tablename__ = "attribute_change"
+    __table_args__ = (
+        CheckConstraint("kind IN ('correction','changement')", name="ck_attribute_change_kind"),
+        Index("idx_attribute_change_value", "value_id", "changed_at"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    value_id: str = Field(foreign_key="attribute_value.id", nullable=False)
+    kind: str
+    changed_by: str
+    before_choice_id: Optional[str] = Field(default=None, foreign_key="attribute_choice.id")
+    before_integer: Optional[int] = None
+    before_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
+    after_choice_id: Optional[str] = Field(default=None, foreign_key="attribute_choice.id")
+    after_integer: Optional[int] = None
+    after_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
+    changed_at: datetime = _created_ts()
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index ea11411..46cdf6c 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.21"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.22"
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index 8d40198..a73467d 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -59,6 +59,12 @@ Layout, by canon domain:
                           `clean_condition`, `write_condition`,
                           `delete_offer_conditions` (TICKET-0111,
                           BRIEF-0111-C).
+    attributes.py       — the state of the world: `attribute_definition`,
+                          `attribute_definition_type`, `attribute_choice`,
+                          `attribute_value`, `attribute_change`:
+                          `clean_definition`, `write_attribute_definition`,
+                          `set_attribute_status`, `write_attribute_value`
+                          (TICKET-0113, BRIEF-0113-A).
     worlds.py           — `delete_world_cascade` (the sole delete-side
                           helper, wildcard-allowed in canon_write_policy.txt).
 
@@ -158,6 +164,14 @@ from .quests import (
     write_quest_offer,
 )
 from .conditions import clean_condition, clean_leaf, delete_offer_conditions, write_condition
+from .attributes import (
+    ChoiceSpec,
+    DefinitionSpec,
+    clean_definition,
+    set_attribute_status,
+    write_attribute_definition,
+    write_attribute_value,
+)
 from .pipeline import (
     BATCH_RESOLVED_STATUS,
     BATCH_STATUSES,
diff --git a/src/world_engine/writes/attributes.py b/src/world_engine/writes/attributes.py
new file mode 100644
index 0000000..5e468aa
--- /dev/null
+++ b/src/world_engine/writes/attributes.py
@@ -0,0 +1,375 @@
+"""The writer of the state of the world (TICKET-0113, BRIEF-0113-A;
+decisions WA3, WB2, WC1, WD1, WE1 and WJ2 of the conditions series): the
+one writer of `attribute_definition`, `attribute_definition_type`,
+`attribute_choice`, `attribute_value` and `attribute_change`.
+
+- `clean_definition(db, world_id, spec, definition_id=None)` : a definition
+  as it will be written, or `ValueError` -- the name is not a system
+  attribute's nor another definition's of the world (compared through
+  `lore_resolve.normalize_surface`), its types are the world's, a `choice`
+  kind has two labels or more and one of them is the default, an `integer`
+  kind has an integer default, an `entity` kind names the types its value
+  may take. On an existing definition, nothing in use is taken away (WJ2): its
+  kind, a holder type an entity holding a value has, a value type a value
+  names, a choice a value or a condition holds. Writes nothing -- the
+  interpreter validates a proposed definition through it (BRIEF-0113-E).
+- `write_attribute_definition(db, *, world_id, spec, definition_id=None)` :
+  create or save one definition after cleaning it; its types are replaced
+  whole (the full-replace shape of `write_offer_terms`), a choice dropped
+  from the list is retired, never deleted, and a retired label named again
+  comes back.
+- `set_attribute_status(db, *, world_id, definition_id, status)` : retire
+  or restore one definition; retiring is refused while a condition names it
+  (WJ2).
+- `write_attribute_value(db, *, world_id, definition_id, entity_id, value,
+  kind, changed_by)` : set one entity's value and append its
+  `attribute_change` row -- the value before (the default when it held
+  none) and after, `correction` or `changement` (WD1). An unchanged value
+  writes nothing and returns None.
+
+A system attribute (`attributes.SYSTEM_ATTRIBUTES`) is never written here:
+its column keeps its own writer. None of these functions commits.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from datetime import UTC, datetime
+from typing import Optional
+
+from sqlalchemy import text
+from sqlmodel import Session, select
+
+from ..attributes import (
+    ATTRIBUTE_FORM,
+    SYSTEM_ATTRIBUTES,
+    RawValue,
+    raw_of,
+    stored_value,
+    world_entity_types,
+)
+from ..lore_resolve import normalize_surface
+from ..models import (
+    ATTRIBUTE_CHANGE_KINDS,
+    ATTRIBUTE_KINDS,
+    ATTRIBUTE_STATUSES,
+    AttributeChange,
+    AttributeChoice,
+    AttributeDefinition,
+    AttributeDefinitionType,
+    AttributeValue,
+    ConditionNode,
+    Entity,
+)
+
+MAX_NAME_CHARS = 80
+
+
+@dataclass(frozen=True)
+class ChoiceSpec:
+    """One label of a `choice` kind; `id` names an existing choice."""
+    label: str
+    id: Optional[str] = None
+
+
+@dataclass(frozen=True)
+class DefinitionSpec:
+    """A definition as the creator (or the interpreter) states it. `default`
+    is a choice's label, an integer, or None for an `entity` kind."""
+    name: str
+    kind: str
+    holder_types: tuple[str, ...]
+    value_types: tuple[str, ...] = ()
+    choices: tuple[ChoiceSpec, ...] = ()
+    default: RawValue = None
+    is_hidden: bool = False
+
+
+# --- cleaning ------------------------------------------------------------------
+
+def _clean_name(db: Session, world_id: str, name: object, definition_id: Optional[str]) -> str:
+    if not isinstance(name, str) or not name.strip():
+        raise ValueError("an attribute needs a name")
+    clean = " ".join(name.split())
+    if len(clean) > MAX_NAME_CHARS:
+        raise ValueError(f"an attribute's name has at most {MAX_NAME_CHARS} characters")
+    key = normalize_surface(clean)
+    for system in SYSTEM_ATTRIBUTES:
+        if normalize_surface(system.name) == key:
+            raise ValueError(f"« {clean} » is a system attribute's name")
+    for other in db.exec(select(AttributeDefinition).where(AttributeDefinition.world_id == world_id)).all():
+        if other.id != definition_id and normalize_surface(other.name) == key:
+            raise ValueError(f"« {clean} » is already the name of « {other.name} »")
+    return clean
+
+
+def _clean_types(world_types: tuple[str, ...], raw: object, what: str) -> tuple[str, ...]:
+    if isinstance(raw, str) or not isinstance(raw, (list, tuple)):
+        raise ValueError(f"an attribute's {what} types are a list")
+    seen: list[str] = []
+    for entity_type in raw:
+        if entity_type not in world_types:
+            raise ValueError(f"unknown entity type {entity_type!r}")
+        if entity_type not in seen:
+            seen.append(entity_type)
+    return tuple(seen)
+
+
+def _clean_choices(kind: str, choices: tuple[ChoiceSpec, ...], default: RawValue) -> tuple[tuple[ChoiceSpec, ...], RawValue]:
+    if kind != "choice":
+        if choices:
+            raise ValueError(f"a {kind} attribute has no choices")
+        return (), default
+    labels: list[ChoiceSpec] = []
+    keys: set[str] = set()
+    for choice in choices:
+        label = " ".join(str(choice.label or "").split())
+        if not label:
+            raise ValueError("a choice needs a label")
+        if normalize_surface(label) in keys:
+            raise ValueError(f"the label « {label} » is given twice")
+        keys.add(normalize_surface(label))
+        labels.append(ChoiceSpec(label=label, id=choice.id))
+    if len(labels) < 2:
+        raise ValueError("a choice attribute has at least two labels")
+    if not isinstance(default, str) or normalize_surface(default) not in keys:
+        raise ValueError("a choice attribute's default is one of its labels")
+    chosen = next(c.label for c in labels if normalize_surface(c.label) == normalize_surface(default))
+    return tuple(labels), chosen
+
+
+def _clean_default(kind: str, default: RawValue) -> RawValue:
+    if kind == "integer":
+        if not isinstance(default, int) or isinstance(default, bool):
+            raise ValueError("an integer attribute's default is an integer")
+        return default
+    if kind == "entity" and default is not None:
+        raise ValueError("an entity attribute's default is empty")
+    return default
+
+
+def clean_definition(
+    db: Session, world_id: str, spec: DefinitionSpec, definition_id: Optional[str] = None,
+) -> DefinitionSpec:
+    """`spec` as it will be written; raises `ValueError` on any violation.
+    Writes nothing."""
+    if spec.kind not in ATTRIBUTE_KINDS:
+        raise ValueError(f"unknown attribute kind {spec.kind!r}")
+    world_types = world_entity_types(db, world_id)
+    holder_types = _clean_types(world_types, spec.holder_types, "holder")
+    if not holder_types:
+        raise ValueError("an attribute applies to one entity type or more")
+    value_types = _clean_types(world_types, spec.value_types, "value")
+    if (spec.kind == "entity") != bool(value_types):
+        raise ValueError("an entity attribute, and only it, names the types its value may take")
+    choices, default = _clean_choices(spec.kind, tuple(spec.choices), spec.default)
+    clean = DefinitionSpec(
+        name=_clean_name(db, world_id, spec.name, definition_id), kind=spec.kind,
+        holder_types=holder_types, value_types=value_types, choices=choices,
+        default=_clean_default(spec.kind, default), is_hidden=bool(spec.is_hidden),
+    )
+    if definition_id is not None:
+        _clean_update(db, world_id, definition_id, clean)
+    elif any(c.id for c in clean.choices):
+        raise ValueError("a new attribute's choices carry no id")
+    return clean
+
+
+# --- what an existing definition holds (WJ2) -----------------------------------
+
+def _leaves(db: Session, definition_id: str) -> list[ConditionNode]:
+    return list(db.exec(select(ConditionNode).where(
+        ConditionNode.form == ATTRIBUTE_FORM, ConditionNode.target_key == definition_id,
+    )).all())
+
+
+def _values(db: Session, definition_id: str) -> list[AttributeValue]:
+    return list(db.exec(select(AttributeValue).where(AttributeValue.definition_id == definition_id)).all())
+
+
+def _entity_type(db: Session, entity_id: Optional[str]) -> Optional[str]:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    return entity.type if entity is not None else None
+
+
+def _clean_update(db: Session, world_id: str, definition_id: str, clean: DefinitionSpec) -> None:
+    definition = db.get(AttributeDefinition, definition_id)
+    if definition is None or definition.world_id != world_id:
+        raise ValueError(f"unknown attribute {definition_id!r}")
+    values, leaves = _values(db, definition_id), _leaves(db, definition_id)
+    if clean.kind != definition.kind and (values or leaves):
+        raise ValueError(f"« {definition.name} » is in use: its kind cannot change")
+    held = {_entity_type(db, v.entity_id) for v in values} | {
+        _entity_type(db, n.subject_entity_id) for n in leaves if n.subject_entity_id}
+    for entity_type in sorted(t for t in held if t and t not in clean.holder_types):
+        raise ValueError(f"« {definition.name} » is in use on a {entity_type}: that type stays")
+    named = {_entity_type(db, v.entity_value_id) for v in values if v.entity_value_id} | {
+        _entity_type(db, n.target_entity_id) for n in leaves if n.target_entity_id}
+    for entity_type in sorted(t for t in named if t and t not in clean.value_types):
+        raise ValueError(f"« {definition.name} » names a {entity_type}: that value type stays")
+    kept = {c.id for c in clean.choices if c.id}
+    used = {v.choice_id for v in values if v.choice_id} | {n.value for n in leaves if n.value}
+    for choice in _choice_rows(db, definition_id):
+        if choice.status == "active" and choice.id not in kept and choice.id in used:
+            raise ValueError(f"the label « {choice.label} » is in use: it stays")
+    for choice in clean.choices:
+        if choice.id and choice.id not in {c.id for c in _choice_rows(db, definition_id)}:
+            raise ValueError(f"unknown choice {choice.id!r}")
+
+
+def _choice_rows(db: Session, definition_id: str) -> list[AttributeChoice]:
+    return list(db.exec(select(AttributeChoice).where(
+        AttributeChoice.definition_id == definition_id).order_by(AttributeChoice.position)).all())
+
+
+# --- writing a definition --------------------------------------------------------
+
+def _write_types(db: Session, world_id: str, definition_id: str, clean: DefinitionSpec) -> None:
+    db.execute(text("DELETE FROM attribute_definition_type WHERE definition_id = :did"), {"did": definition_id})
+    for side, types in (("holder", clean.holder_types), ("value", clean.value_types)):
+        for entity_type in types:
+            db.add(AttributeDefinitionType(world_id=world_id, definition_id=definition_id, side=side,
+                                           entity_type=entity_type))
+
+
+def _write_choices(db: Session, world_id: str, definition_id: str, clean: DefinitionSpec) -> None:
+    rows = _choice_rows(db, definition_id)
+    by_id = {c.id: c for c in rows}
+    by_label = {normalize_surface(c.label): c for c in rows}
+    kept: set[str] = set()
+    for row in rows:
+        row.is_default = False
+        db.add(row)
+    db.flush()
+    for position, spec in enumerate(clean.choices):
+        row = by_id.get(spec.id) if spec.id else by_label.get(normalize_surface(spec.label))
+        if row is None:
+            row = AttributeChoice(world_id=world_id, definition_id=definition_id, label=spec.label)
+        row.label, row.position, row.status = spec.label, position, "active"
+        row.is_default = normalize_surface(spec.label) == normalize_surface(str(clean.default))
+        db.add(row)
+        db.flush()
+        kept.add(row.id)
+    for row in rows:
+        if row.id not in kept:
+            row.status = "retired"
+            db.add(row)
+
+
+def write_attribute_definition(
+    db: Session, *, world_id: str, spec: DefinitionSpec, definition_id: Optional[str] = None,
+) -> AttributeDefinition:
+    """Create (`definition_id` None) or save one definition after
+    `clean_definition`. Returns its row, flushed."""
+    clean = clean_definition(db, world_id, spec, definition_id)
+    if definition_id is None:
+        definition = AttributeDefinition(world_id=world_id, name=clean.name, kind=clean.kind)
+    else:
+        definition = db.get(AttributeDefinition, definition_id)
+    definition.name, definition.kind, definition.is_hidden = clean.name, clean.kind, clean.is_hidden
+    definition.default_integer = clean.default if clean.kind == "integer" else None
+    definition.updated_at = datetime.now(UTC)
+    db.add(definition)
+    db.flush()
+    _write_types(db, world_id, definition.id, clean)
+    _write_choices(db, world_id, definition.id, clean)
+    db.flush()
+    return definition
+
+
+def set_attribute_status(db: Session, *, world_id: str, definition_id: str, status: str) -> AttributeDefinition:
+    """Retire or restore one definition. Retiring is refused while a
+    condition names it (WJ2)."""
+    if status not in ATTRIBUTE_STATUSES:
+        raise ValueError(f"unknown attribute status {status!r}")
+    definition = db.get(AttributeDefinition, definition_id)
+    if definition is None or definition.world_id != world_id:
+        raise ValueError(f"unknown attribute {definition_id!r}")
+    if status == "retired" and _leaves(db, definition_id):
+        raise ValueError(f"« {definition.name} » is named by a condition: it cannot be retired")
+    definition.status = status
+    definition.updated_at = datetime.now(UTC)
+    db.add(definition)
+    db.flush()
+    return definition
+
+
+# --- writing a value --------------------------------------------------------------
+
+def _clean_value(db: Session, world_id: str, definition: AttributeDefinition, value: RawValue) -> RawValue:
+    if definition.kind == "integer":
+        if not isinstance(value, int) or isinstance(value, bool):
+            raise ValueError(f"« {definition.name} » takes an integer")
+        return value
+    if definition.kind == "choice":
+        choice = db.get(AttributeChoice, value) if isinstance(value, str) else None
+        if choice is None or choice.definition_id != definition.id or choice.status != "active":
+            raise ValueError(f"« {definition.name} » takes one of its labels")
+        return value
+    if value is None:
+        return None
+    entity = db.get(Entity, value) if isinstance(value, str) else None
+    value_types = set(db.exec(select(AttributeDefinitionType.entity_type).where(
+        AttributeDefinitionType.definition_id == definition.id, AttributeDefinitionType.side == "value",
+    )).all())
+    if entity is None or entity.world_id != world_id or entity.type not in value_types:
+        raise ValueError(f"« {definition.name} » cannot name {value!r}")
+    return value
+
+
+def _default_raw(db: Session, definition: AttributeDefinition) -> RawValue:
+    if definition.kind == "integer":
+        return definition.default_integer
+    if definition.kind == "choice":
+        return db.exec(select(AttributeChoice.id).where(
+            AttributeChoice.definition_id == definition.id, AttributeChoice.is_default == True,  # noqa: E712
+        )).first()
+    return None
+
+
+def _columns(kind: str, raw: RawValue, prefix: str) -> dict:
+    return {
+        f"{prefix}choice_id": raw if kind == "choice" else None,
+        f"{prefix}integer": raw if kind == "integer" else None,
+        f"{prefix}entity_id": raw if kind == "entity" else None,
+    }
+
+
+def write_attribute_value(
+    db: Session, *, world_id: str, definition_id: str, entity_id: str, value: RawValue, kind: str,
+    changed_by: str,
+) -> Optional[AttributeChange]:
+    """Set one entity's value of one active definition (WD1): `kind` is
+    `correction` or `changement`. Returns the appended `attribute_change`, or
+    None when the value is unchanged (nothing written)."""
+    if kind not in ATTRIBUTE_CHANGE_KINDS:
+        raise ValueError(f"unknown change kind {kind!r}")
+    if not changed_by:
+        raise ValueError("a change names who made it")
+    definition = db.get(AttributeDefinition, definition_id)
+    if definition is None or definition.world_id != world_id or definition.status != "active":
+        raise ValueError(f"unknown attribute {definition_id!r}")
+    entity = db.get(Entity, entity_id)
+    holder_types = set(db.exec(select(AttributeDefinitionType.entity_type).where(
+        AttributeDefinitionType.definition_id == definition_id, AttributeDefinitionType.side == "holder",
+    )).all())
+    if entity is None or entity.world_id != world_id or entity.type not in holder_types:
+        raise ValueError(f"« {definition.name} » does not apply to {entity_id!r}")
+    after = _clean_value(db, world_id, definition, value)
+    row = stored_value(db, definition_id, entity_id)
+    before = raw_of(row) if row is not None else _default_raw(db, definition)
+    if before == after:
+        return None
+    if row is None:
+        row = AttributeValue(world_id=world_id, definition_id=definition_id, entity_id=entity_id)
+    row.choice_id, row.integer_value, row.entity_value_id = _columns(definition.kind, after, "").values()
+    row.updated_at = datetime.now(UTC)
+    db.add(row)
+    db.flush()
+    change = AttributeChange(
+        world_id=world_id, value_id=row.id, kind=kind, changed_by=changed_by,
+        **_columns(definition.kind, before, "before_"), **_columns(definition.kind, after, "after_"),
+    )
+    db.add(change)
+    db.flush()
+    return change
diff --git a/src/world_engine/writes/worlds.py b/src/world_engine/writes/worlds.py
index 3c93563..ed3a747 100644
--- a/src/world_engine/writes/worlds.py
+++ b/src/world_engine/writes/worlds.py
@@ -77,6 +77,8 @@ _DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
     "world_law", "quest", "quest_offer", "quest_offer_step",
     "item_holding", "quest_offer_term", "quest_term", "quest_economy",
     "debt", "debt_term",
+    "attribute_definition", "attribute_definition_type", "attribute_choice",
+    "attribute_value", "attribute_change",
 )
 
 # Refusing tables (root_table, label_column, guarded_children, message) —
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 5fa72d3..7a2fa4e 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19052,6 +19052,52 @@ D2 (compress only, everything in the root; reactivation: a session misses a
 local invariant), D3 (an imported file: loaded at launch anyway), H2 (a
 second full text of each invariant), H3 (cut without keeping the law).
 
+## THE STATE OF THE WORLD IS A WORLD'S OWN ATTRIBUTES (TICKET-0113) -- A DEFINITION PER IDEA, ONE VALUE PER ENTITY, ITS HISTORY ROW BY ROW (BRIEF-0113-a, schema v2.22)
+
+**B1, G1 of the conditions series.** What the canon could not say -- the
+door is open, the bridge destroyed, the throne occupied by Ysa -- is now an
+attribute the creator defines in her world, never a column, never a ticket.
+`attribute_definition` names it and its kind (WA3): `choice` (labels in
+`attribute_choice`, one the default), `integer`, or `entity` (another
+entity, of the types its `value` side names). `attribute_definition_type`
+lists the entity types it applies to (WB2: one « Maudit » for characters and
+items, not three). `attribute_value` holds one entity's value; an entity
+with none reads the default and nothing is written on read (WC1).
+`attribute_change` is its history, append-only -- the rows ARE the history
+-- each row the value before and after and `correction` or `changement`,
+the creator's choice at every write as for facts since TICKET-0105 (WD1).
+`is_hidden` (WH1, off by default) is read by the condition language
+(BRIEF-0113-B). `writes/attributes.py` is the one writer of the five tables.
+
+**WE1.** The states the canon already keeps -- `character.vital_status`,
+`entity.status`, `location.magic_status` -- are SYSTEM attributes
+(`attributes.SYSTEM_ATTRIBUTES`), read where they live and never copied
+(G3 rejected: one state in two places diverges). No definition takes a
+system attribute's name, nor another definition's of its world, compared
+through `lore_resolve.normalize_surface`.
+
+**WJ2.** Nothing in use is taken away: a definition's kind once a value or
+a condition holds it, a subject type an entity holding a value has, a
+value type a value names, a label a value or a condition holds. A label
+dropped is retired, never deleted (a history names it); a definition is
+retired, refused while a condition names it, and can be restored. The
+types are replaced whole (`_write_types`, the full-replace shape of
+`write_offer_terms`, named in `single_canon_write.py`).
+
+**v2.22 moves `schema_meta` to v2.22 only.** `migrate_v2_22_attributes.py`
+converges to its own version, not the code's: v2.23 (BRIEF-0113-B) converts
+condition leaves this one does not, and the boot guard keeps refusing until
+it has run.
+
+**Rejected.** WA1 (choice and integer only; reactivation: none -- « occupé
+par Ysa » needed the `entity` kind), WA2 (choice only), WB1 (one type per
+definition: the same idea defined three times), WB3 (every entity type),
+WC2 (a value written for every entity at definition), WC3 (no value reads
+unknown), WD2 (a JSON history: it is shown), WD3 (the history alone, the
+current value its last row), WE2 (the `vital_status` form kept beside the
+attribute form), WE3 (no system attribute: « détruit » defined twice), WJ1
+(retiring silently breaks conditions), WJ3 (a hard delete).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index f62b0ba..e18ed81 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -8,6 +8,7 @@ npc_schedule condition condition_node fact fact_participant fact_default
 skill_rank quest_offer quest_offer_step quest
 item_holding quest_offer_term quest_term quest_economy
 debt debt_term
+attribute_definition attribute_definition_type attribute_choice attribute_value attribute_change
 
 [ALLOWED_SITES]
 # path::function                                              tables
@@ -67,6 +68,12 @@ src/world_engine/writes/quest_settlement.py::finish_settlement  quest
 # TICKET-0110, BRIEF-0110-B: write_debt writes a debt and its owed terms, once (its fact, participants, knowledge and faction default go through create_fact, attach_participants, write_knowledge and create_fact_default, allow-listed above); _close closes it once -- status, closed_at, closed_note -- never deleted. Creator CRUD, a service, or a settlement on credit.
 src/world_engine/writes/debts.py::write_debt                    debt debt_term
 src/world_engine/writes/debts.py::_close                        debt
+# TICKET-0113, BRIEF-0113-A: the state of the world's one writer -- write_attribute_definition creates or saves a definition, _write_types replaces its types whole (the write_offer_terms full-replace shape), _write_choices adds, renames and retires its labels (never a DELETE), set_attribute_status retires or restores it, write_attribute_value sets one entity's value and appends its attribute_change row. Creator CRUD only (and, from BRIEF-0113-E, the offer save writing a definition the interpreter proposed).
+src/world_engine/writes/attributes.py::write_attribute_definition attribute_definition
+src/world_engine/writes/attributes.py::_write_types             attribute_definition_type
+src/world_engine/writes/attributes.py::_write_choices           attribute_choice
+src/world_engine/writes/attributes.py::set_attribute_status     attribute_definition
+src/world_engine/writes/attributes.py::write_attribute_value    attribute_value attribute_change
 # TICKET-0044, BRIEF-0044-c: create_entity_type is the 26th site — the governed
 # structural-write authority (D2), a NEW sanctioned site distinct from the two
 # canon-write paths (AI-proposal pipeline, creator CRUD). Its `CREATE TABLE
diff --git a/tooling/verify/checks/attributes.py b/tooling/verify/checks/attributes.py
new file mode 100644
index 0000000..25781d9
--- /dev/null
+++ b/tooling/verify/checks/attributes.py
@@ -0,0 +1,562 @@
+"""G1 check for TICKET-0113 -- the state of the world: a world's attributes, one value per entity, its history kept.
+
+The lot adds its pieces brief by brief; this check grows with it (the
+`conditions.py` precedent). Each brief adds its rules here in the same
+commit.
+
+AA1 -- storage (BRIEF-0113-A, import). The five attribute tables carry
+   exactly their contract's columns, CHECK names and index names; no column
+   of theirs is JSON; `ATTRIBUTE_KINDS`, `ATTRIBUTE_TYPE_SIDES`,
+   `ATTRIBUTE_STATUSES` and `ATTRIBUTE_CHANGE_KINDS` are the values their
+   CHECKs quote, in order, and `ATTRIBUTE_CHANGE_KINDS` is
+   `writes.facts.FACT_CHANGE_KINDS`; the code's schema version is v2.22 or
+   later.
+AA2 -- the definition writer (fixture). `write_attribute_definition` writes
+   a `choice`, an `integer` and an `entity` definition; `attribute_view`
+   reads each back with its types, its choices in order and its default;
+   `world_attributes` lists the three system attributes first, then the
+   definitions by name. Refused, each with no row written: an unknown kind,
+   an empty name, a system attribute's name (any case or accent), another
+   definition's name (« maudit » against « Maudit »), an unknown entity
+   type, no holder type, a choice kind with one label or a default that is
+   none of its labels, an integer kind with a non-integer default, an
+   entity kind with no value type, value types on a choice kind, an id on a
+   new definition's choice.
+AA3 -- values and history (fixture). `write_attribute_value` sets a choice,
+   an integer and an entity value, each appending one `attribute_change`
+   whose `before_*` is the default and `after_*` the value, with its kind;
+   a second write's `before_*` is the first value; an unchanged write
+   returns None and adds no row; `current_value` reads the default with
+   `is_default` before any write and the value after. Refused, each with no
+   row written: an unknown change kind, no `changed_by`, an entity of a
+   type the definition does not name, a label of another definition, an
+   entity value of a type the definition does not name, a non-integer for
+   an integer, a retired definition.
+AA4 -- vocabularies (fixture, import). `BUILTIN_ENTITY_TYPES` is
+   `ENTITY_TYPE_REGISTRY`'s keys; `sys:status` reads `ENTITY_STATUSES`,
+   `sys:vital_status` the character's `vital_status` options and
+   `sys:magic_status` the location's `magic_status` options, each in order;
+   `world_entity_types` adds an active runtime type's slug and never a
+   retired one; `current_value` reads each system attribute from its column.
+AA5 -- in use (WJ2, fixture). Once a value exists, the kind cannot change
+   and a holder type an entity holding a value has cannot be dropped; a
+   label a value holds cannot be dropped; an unused label dropped is
+   retired, its row kept; the same label named again comes back active;
+   renaming a definition writes no `attribute_change`; a definition with no
+   condition is retired and restored.
+AA6 -- migration `scripts/migrate_v2_22_attributes.py`, on a database
+   without the five tables: at v2.20 it refuses and creates nothing; at
+   v2.21 it creates the five tables with the models' columns, zero rows,
+   and sets `schema_meta` to v2.22 -- its own version; a second run says
+   nothing to do.
+AA7 -- the reader writes nothing (static, AST). `attributes.py` calls no
+   `add`, `commit`, `delete`, `execute` or `flush`.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import ast
+import os
+import pathlib
+import re
+import sqlite3
+import subprocess
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+MIGRATION_V2_22 = ROOT / "scripts" / "migrate_v2_22_attributes.py"
+
+FAILURES: list[str] = []
+
+TABLES: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
+    "attribute_definition": (
+        ("id", "world_id", "name", "kind", "default_integer", "is_hidden", "status", "created_at", "updated_at"),
+        ("ck_attribute_definition_kind", "ck_attribute_definition_status", "ck_attribute_definition_default"),
+        ("idx_attribute_definition_name",),
+    ),
+    "attribute_definition_type": (
+        ("id", "world_id", "definition_id", "side", "entity_type"),
+        ("ck_attribute_definition_type_side",),
+        ("idx_attribute_definition_type_unique",),
+    ),
+    "attribute_choice": (
+        ("id", "world_id", "definition_id", "label", "position", "is_default", "status"),
+        ("ck_attribute_choice_status", "ck_attribute_choice_default"),
+        ("idx_attribute_choice_label", "idx_attribute_choice_one_default"),
+    ),
+    "attribute_value": (
+        ("id", "world_id", "definition_id", "entity_id", "choice_id", "integer_value", "entity_value_id",
+         "updated_at"),
+        ("ck_attribute_value_one",),
+        ("idx_attribute_value_pair", "idx_attribute_value_entity"),
+    ),
+    "attribute_change": (
+        ("id", "world_id", "value_id", "kind", "changed_by", "before_choice_id", "before_integer",
+         "before_entity_id", "after_choice_id", "after_integer", "after_entity_id", "changed_at"),
+        ("ck_attribute_change_kind",),
+        ("idx_attribute_change_value",),
+    ),
+}
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> str:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+    return db_path
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+# --- AA1 -------------------------------------------------------------------------
+
+def _quoted(sql: str) -> tuple[str, ...]:
+    return tuple(re.findall(r"'([^']+)'", sql))
+
+
+def check_aa1() -> None:
+    from sqlalchemy import JSON, CheckConstraint
+    from sqlmodel import SQLModel
+
+    from world_engine import models
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+    from world_engine.writes.facts import FACT_CHANGE_KINDS
+
+    seen = 0
+    for name, (columns, checks, indexes) in TABLES.items():
+        table = SQLModel.metadata.tables.get(name)
+        if table is None:
+            fail(f"AA1: table {name} is not declared")
+            continue
+        seen += 1
+        if tuple(table.c.keys()) != columns:
+            fail(f"AA1: {name} columns are {tuple(table.c.keys())}")
+        found = tuple(sorted(c.name for c in table.constraints if isinstance(c, CheckConstraint)))
+        if found != tuple(sorted(checks)):
+            fail(f"AA1: {name} CHECKs are {found}")
+        if tuple(sorted(i.name for i in table.indexes)) != tuple(sorted(indexes)):
+            fail(f"AA1: {name} indexes are {sorted(i.name for i in table.indexes)}")
+        for column in table.c:
+            if isinstance(column.type, JSON):
+                fail(f"AA1: {name}.{column.name} is JSON")
+    if seen != len(TABLES):
+        fail(f"AA1: {seen} of {len(TABLES)} tables declared")
+    meta = SQLModel.metadata.tables
+
+    def check_text(table: str, ck: str) -> str:
+        return next(str(c.sqltext) for c in meta[table].constraints
+                    if isinstance(c, CheckConstraint) and c.name == ck)
+
+    pairs = (
+        (models.ATTRIBUTE_KINDS, check_text("attribute_definition", "ck_attribute_definition_kind")),
+        (models.ATTRIBUTE_STATUSES, check_text("attribute_definition", "ck_attribute_definition_status")),
+        (models.ATTRIBUTE_STATUSES, check_text("attribute_choice", "ck_attribute_choice_status")),
+        (models.ATTRIBUTE_TYPE_SIDES, check_text("attribute_definition_type", "ck_attribute_definition_type_side")),
+        (models.ATTRIBUTE_CHANGE_KINDS, check_text("attribute_change", "ck_attribute_change_kind")),
+    )
+    for values, sql in pairs:
+        if tuple(values) != _quoted(sql):
+            fail(f"AA1: {values} is not the CHECK's {_quoted(sql)}")
+    if tuple(models.ATTRIBUTE_CHANGE_KINDS) != tuple(FACT_CHANGE_KINDS):
+        fail(f"AA1: ATTRIBUTE_CHANGE_KINDS {models.ATTRIBUTE_CHANGE_KINDS} != FACT_CHANGE_KINDS")
+    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < (2, 22):
+        fail(f"AA1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")
+
+
+# --- fixture -----------------------------------------------------------------------
+
+def _fixture(engine) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.models import Character, Entity, EntityType, Item, Location, World
+
+    with Session(engine) as db:
+        world = World(name="Attributs", is_active=False)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind, name in (("ysa", "character", "Ysa"), ("garde", "character", "Garde"),
+                                ("trone", "item", "Trône"), ("crypte", "location", "Crypte"),
+                                ("guilde", "faction", "Guilde")):
+            entity = Entity(world_id=world.id, type=kind, name=name)
+            db.add(entity)
+            db.flush()
+            ids[key] = entity.id
+            if kind == "character":
+                db.add(Character(id=entity.id, world_id=world.id, character_type="npc"))
+            elif kind == "item":
+                db.add(Item(id=entity.id))
+            elif kind == "location":
+                db.add(Location(id=entity.id))
+        for slug, status in (("navire", "active"), ("epave", "retired")):
+            db.add(EntityType(world_id=world.id, name=slug, slug=slug, physical_table=f"ext_{slug}",
+                              status=status))
+        db.commit()
+    return ids
+
+
+def _count(db, model) -> int:
+    from sqlmodel import func, select
+
+    return db.exec(select(func.count()).select_from(model)).one()
+
+
+def _counts(db) -> tuple[int, ...]:
+    from world_engine import models
+
+    return tuple(_count(db, m) for m in (models.AttributeDefinition, models.AttributeDefinitionType,
+                                         models.AttributeChoice, models.AttributeValue,
+                                         models.AttributeChange))
+
+
+def _refused(db, label: str, rule: str, call) -> None:
+    before = _counts(db)
+    try:
+        call()
+    except ValueError:
+        db.rollback()
+        if _counts(db) != before:
+            fail(f"{rule}: {label} was refused after writing a row")
+        return
+    db.rollback()
+    fail(f"{rule}: {label} was accepted")
+
+
+def _spec(**fields):
+    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec
+
+    base = dict(name="Maudit", kind="choice", holder_types=("character", "item"),
+                choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non")
+    base.update(fields)
+    if "choices" in fields and fields["choices"] and isinstance(fields["choices"][0], str):
+        base["choices"] = tuple(ChoiceSpec(c) for c in fields["choices"])
+    return DefinitionSpec(**base)
+
+
+def _definitions(engine, ids) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.writes.attributes import write_attribute_definition
+
+    with Session(engine) as db:
+        made = {}
+        for key, spec in (
+            ("maudit", _spec()),
+            ("alerte", _spec(name="Niveau d'alerte", kind="integer", holder_types=("location",),
+                             choices=(), default=2)),
+            ("occupe", _spec(name="Occupé par", kind="entity", holder_types=("item",),
+                             value_types=("character",), choices=(), default=None)),
+        ):
+            made[key] = write_attribute_definition(db, world_id=ids["world"], spec=spec).id
+        db.commit()
+    return made
+
+
+def check_aa2(engine, ids: dict, defs: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.attributes import SYSTEM_ATTRIBUTES, attribute_view, world_attributes
+    from world_engine.writes.attributes import write_attribute_definition
+
+    with Session(engine) as db:
+        maudit = attribute_view(db, ids["world"], defs["maudit"])
+        if maudit is None or maudit.kind != "choice" or maudit.holder_types != ("character", "item") \
+                or [label for _key, label in maudit.choices] != ["non", "oui"] \
+                or maudit.default != maudit.choices[0][0] or maudit.hidden or maudit.system:
+            fail(f"AA2: the choice definition reads back as {maudit}")
+        alerte = attribute_view(db, ids["world"], defs["alerte"])
+        if alerte is None or alerte.kind != "integer" or alerte.default != 2 or alerte.choices:
+            fail(f"AA2: the integer definition reads back as {alerte}")
+        occupe = attribute_view(db, ids["world"], defs["occupe"])
+        if occupe is None or occupe.value_types != ("character",) or occupe.default is not None:
+            fail(f"AA2: the entity definition reads back as {occupe}")
+        listed = [v.key for v in world_attributes(db, ids["world"])]
+        want = [s.key for s in SYSTEM_ATTRIBUTES] + [defs["maudit"], defs["alerte"], defs["occupe"]]
+        if listed != want:
+            fail(f"AA2: world_attributes lists {listed}")
+        cases = {
+            "an unknown kind": _spec(name="A", kind="texte"),
+            "an empty name": _spec(name="  "),
+            "a system attribute's name": _spec(name="etat VITAL"),
+            "another definition's name": _spec(name="maudit"),
+            "an unknown entity type": _spec(name="B", holder_types=("dragon",)),
+            "no holder type": _spec(name="C", holder_types=()),
+            "a choice kind with one label": _spec(name="D", choices=("oui",), default="oui"),
+            "a default that is none of its labels": _spec(name="E", default="peut-être"),
+            "an integer default that is not one": _spec(name="F", kind="integer", choices=(), default="3"),
+            "an entity kind with no value type": _spec(name="G", kind="entity", choices=(), default=None),
+            "value types on a choice kind": _spec(name="H", value_types=("character",)),
+        }
+        for label, spec in cases.items():
+            _refused(db, label, "AA2", lambda spec=spec: write_attribute_definition(
+                db, world_id=ids["world"], spec=spec))
+        from world_engine.writes.attributes import ChoiceSpec
+        with_id = _spec(name="I", choices=(ChoiceSpec("a", id="x"), ChoiceSpec("b")), default="a")
+        _refused(db, "an id on a new definition's choice", "AA2", lambda: write_attribute_definition(
+            db, world_id=ids["world"], spec=with_id))
+
+
+def check_aa3(engine, ids: dict, defs: dict) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.attributes import attribute_view, current_value
+    from world_engine.models import AttributeChange, Entity
+    from world_engine.writes.attributes import set_attribute_status, write_attribute_definition, \
+        write_attribute_value
+
+    with Session(engine) as db:
+        world = ids["world"]
+        maudit = attribute_view(db, world, defs["maudit"])
+        non, oui = (key for key, _label in maudit.choices)
+        ysa = db.get(Entity, ids["ysa"])
+        before = current_value(db, maudit, ysa)
+        if before.raw != non or not before.is_default or before.label != "non":
+            fail(f"AA3: before any write, Ysa reads {before}")
+        first = write_attribute_value(db, world_id=world, definition_id=defs["maudit"], entity_id=ids["ysa"],
+                                      value=oui, kind="changement", changed_by="creator_crud")
+        second = write_attribute_value(db, world_id=world, definition_id=defs["maudit"], entity_id=ids["ysa"],
+                                       value=non, kind="correction", changed_by="creator_crud")
+        same = write_attribute_value(db, world_id=world, definition_id=defs["maudit"], entity_id=ids["ysa"],
+                                     value=non, kind="correction", changed_by="creator_crud")
+        db.commit()
+        if first is None or (first.before_choice_id, first.after_choice_id, first.kind) != (non, oui, "changement"):
+            fail(f"AA3: the first change is {first}")
+        if second is None or (second.before_choice_id, second.after_choice_id, second.kind) != (oui, non, "correction"):
+            fail(f"AA3: the second change is {second}")
+        if same is not None:
+            fail("AA3: an unchanged value appended a change")
+        after = current_value(db, maudit, ysa)
+        if after.raw != non or after.is_default:
+            fail(f"AA3: after the writes, Ysa reads {after}")
+        alerte = write_attribute_value(db, world_id=world, definition_id=defs["alerte"], entity_id=ids["crypte"],
+                                       value=-1, kind="changement", changed_by="creator_crud")
+        occupe = write_attribute_value(db, world_id=world, definition_id=defs["occupe"], entity_id=ids["trone"],
+                                       value=ids["ysa"], kind="changement", changed_by="creator_crud")
+        db.commit()
+        if alerte is None or (alerte.before_integer, alerte.after_integer) != (2, -1):
+            fail(f"AA3: the integer change is {alerte}")
+        if occupe is None or (occupe.before_entity_id, occupe.after_entity_id) != (None, ids["ysa"]):
+            fail(f"AA3: the entity change is {occupe}")
+        rows = db.exec(select(AttributeChange)).all()
+        if len(rows) != 4:
+            fail(f"AA3: {len(rows)} changes written, expected 4")
+        other = write_attribute_definition(db, world_id=world, spec=_spec(name="Ouvert", holder_types=("location",)))
+        db.commit()
+        foreign = attribute_view(db, world, other.id).choices[0][0]
+
+        def value(definition, entity, raw, kind="changement", by="creator_crud"):
+            return lambda: write_attribute_value(db, world_id=world, definition_id=defs[definition] if definition
+                                                 in defs else definition, entity_id=ids[entity], value=raw,
+                                                 kind=kind, changed_by=by)
+
+        cases = {
+            "an unknown change kind": value("maudit", "garde", oui, kind="oubli"),
+            "no changed_by": value("maudit", "garde", oui, by=""),
+            "an entity of a type it does not name": value("maudit", "crypte", oui),
+            "a label of another definition": value("maudit", "garde", foreign),
+            "an entity value of a type it does not name": value("occupe", "trone", ids["guilde"]),
+            "a non-integer for an integer": value("alerte", "crypte", "3"),
+        }
+        for label, call in cases.items():
+            _refused(db, label, "AA3", call)
+        set_attribute_status(db, world_id=world, definition_id=other.id, status="retired")
+        db.commit()
+        _refused(db, "a retired definition", "AA3", value(other.id, "crypte", foreign))
+
+
+def check_aa4(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.attributes import BUILTIN_ENTITY_TYPES, SYSTEM_ATTRIBUTES, attribute_view, \
+        current_value, world_entity_types
+    from world_engine.cockpit.crud.entities import ENTITY_STATUSES, ENTITY_TYPE_REGISTRY
+    from world_engine.models import Character, Entity, Location
+
+    if tuple(ENTITY_TYPE_REGISTRY) != BUILTIN_ENTITY_TYPES:
+        fail(f"AA4: BUILTIN_ENTITY_TYPES {BUILTIN_ENTITY_TYPES} != {tuple(ENTITY_TYPE_REGISTRY)}")
+
+    def options(entity_type: str, field: str) -> tuple:
+        spec = next(f for f in ENTITY_TYPE_REGISTRY[entity_type]["fields"] if f["name"] == field)
+        return tuple(spec["options"])
+
+    want = {"sys:status": tuple(ENTITY_STATUSES), "sys:vital_status": options("character", "vital_status"),
+            "sys:magic_status": options("location", "magic_status")}
+    got = {s.key: tuple(v for v, _label in s.values) for s in SYSTEM_ATTRIBUTES}
+    if got != want:
+        fail(f"AA4: the system vocabularies are {got}, expected {want}")
+    with Session(engine) as db:
+        types = world_entity_types(db, ids["world"])
+        if types != BUILTIN_ENTITY_TYPES + ("navire",):
+            fail(f"AA4: world_entity_types is {types}")
+        db.get(Character, ids["garde"]).vital_status = "dead"
+        db.get(Location, ids["crypte"]).magic_status = "nexus"
+        db.get(Entity, ids["trone"]).status = "destroyed"
+        db.commit()
+        reads = {
+            ("sys:vital_status", "garde"): "dead", ("sys:magic_status", "crypte"): "nexus",
+            ("sys:status", "trone"): "destroyed",
+        }
+        for (key, entity), raw in reads.items():
+            value = current_value(db, attribute_view(db, ids["world"], key), db.get(Entity, ids[entity]))
+            if value.raw != raw or value.is_default:
+                fail(f"AA4: {key} of {entity} reads {value}")
+
+
+def check_aa5(engine, ids: dict, defs: dict) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.attributes import attribute_view
+    from world_engine.models import AttributeChange, AttributeChoice, AttributeDefinition
+    from world_engine.writes.attributes import ChoiceSpec, set_attribute_status, write_attribute_definition
+
+    with Session(engine) as db:
+        world = ids["world"]
+        view = attribute_view(db, world, defs["maudit"])
+        (non_id, _), (oui_id, _) = view.choices
+        save = lambda spec: (lambda: write_attribute_definition(  # noqa: E731
+            db, world_id=world, spec=spec, definition_id=defs["maudit"]))
+        _refused(db, "a kind change once a value exists", "AA5", lambda: write_attribute_definition(
+            db, world_id=world, definition_id=defs["alerte"],
+            spec=_spec(name="Niveau d'alerte", holder_types=("location",))))
+        _refused(db, "dropping a holder type a value holds", "AA5", save(_spec(holder_types=("item",))))
+        _refused(db, "dropping a label a value holds", "AA5",
+                 save(_spec(choices=(ChoiceSpec("oui", id=oui_id), ChoiceSpec("peut-être")), default="oui")))
+        changes = len(db.exec(select(AttributeChange)).all())
+        write_attribute_definition(db, world_id=world, definition_id=defs["maudit"], spec=_spec(
+            name="Maudite", choices=(ChoiceSpec("non", id=non_id), ChoiceSpec("peut-être")), default="non"))
+        db.commit()
+        oui = db.get(AttributeChoice, oui_id)
+        if oui is None or oui.status != "retired":
+            fail(f"AA5: an unused label dropped is {oui and oui.status}")
+        if db.get(AttributeDefinition, defs["maudit"]).name != "Maudite":
+            fail("AA5: the definition was not renamed")
+        if len(db.exec(select(AttributeChange)).all()) != changes:
+            fail("AA5: saving a definition wrote an attribute_change")
+        write_attribute_definition(db, world_id=world, definition_id=defs["maudit"], spec=_spec(
+            name="Maudite", choices=(ChoiceSpec("non", id=non_id), ChoiceSpec("oui")), default="non"))
+        db.commit()
+        back = db.get(AttributeChoice, oui_id)
+        if back.status != "active" or [k for k, _l in attribute_view(db, world, defs["maudit"]).choices] \
+                != [non_id, oui_id]:
+            fail("AA5: a retired label named again did not come back")
+        retired = set_attribute_status(db, world_id=world, definition_id=defs["alerte"], status="retired")
+        restored = set_attribute_status(db, world_id=world, definition_id=defs["alerte"], status="active")
+        db.commit()
+        if retired.status != "active" or restored.status != "active":
+            fail("AA5: a definition with no condition was not retired then restored")
+
+
+# --- AA6 -------------------------------------------------------------------------
+
+def _run_migration(path: pathlib.Path, db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(path)], env=env, capture_output=True, text=True,
+                          cwd=str(ROOT), timeout=120)
+
+
+def _drop_attributes(db_path: str, version: str) -> None:
+    with sqlite3.connect(db_path) as conn:
+        for name in reversed(tuple(TABLES)):
+            conn.execute(f"DROP TABLE IF EXISTS {name}")
+        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))
+
+
+def _state(db_path: str) -> tuple[dict, str]:
+    with sqlite3.connect(db_path) as conn:
+        shapes = {}
+        for name in TABLES:
+            cols = tuple(r[1] for r in conn.execute(f"PRAGMA table_info({name})"))
+            count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] if cols else None
+            shapes[name] = (cols, count)
+        version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0]
+    return shapes, version
+
+
+def _migrated_db() -> str:
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, SQLModel
+
+    from world_engine.models import SchemaMeta
+
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "migrate.db")
+    eng = create_engine(f"sqlite:///{db_path}")
+    SQLModel.metadata.create_all(eng)
+    with Session(eng) as session:
+        session.add(SchemaMeta(id=1, static_version="v2.21"))
+        session.commit()
+    eng.dispose()
+    return db_path
+
+
+def check_aa6() -> None:
+    db_path = _migrated_db()
+    _drop_attributes(db_path, "v2.20")
+    result = _run_migration(MIGRATION_V2_22, db_path)
+    shapes, _version = _state(db_path)
+    if result.returncode == 0 or any(cols for cols, _count in shapes.values()):
+        fail(f"AA6: v2.20 was not refused (exit {result.returncode})")
+    _drop_attributes(db_path, "v2.21")
+    result = _run_migration(MIGRATION_V2_22, db_path)
+    shapes, version = _state(db_path)
+    want = {name: (cols, 0) for name, (cols, _checks, _indexes) in TABLES.items()}
+    if result.returncode != 0 or shapes != want or version != "v2.22":
+        fail(f"AA6: exit {result.returncode}, version {version}, shapes {shapes}: {result.stderr.strip()[-200:]}")
+    again = _run_migration(MIGRATION_V2_22, db_path)
+    if again.returncode != 0 or "nothing to do" not in again.stdout:
+        fail(f"AA6: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
+
+
+# --- AA7 -------------------------------------------------------------------------
+
+def check_aa7() -> None:
+    path = SRC / "attributes.py"
+    tree = ast.parse(path.read_text(encoding="utf-8"))
+    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
+    if not calls:
+        fail("AA7: attributes.py makes no attribute call at all")
+    for call in calls:
+        if call.func.attr in ("add", "commit", "delete", "execute", "flush"):
+            fail(f"AA7: attributes.py calls .{call.func.attr} on line {call.lineno}")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    ids = _fixture(engine)
+    defs = _definitions(engine, ids)
+    rules = (
+        ("AA1", check_aa1), ("AA2", lambda: check_aa2(engine, ids, defs)),
+        ("AA3", lambda: check_aa3(engine, ids, defs)), ("AA4", lambda: check_aa4(engine, ids)),
+        ("AA5", lambda: check_aa5(engine, ids, defs)), ("AA6", check_aa6), ("AA7", check_aa7),
+    )
+    for name, rule in rules:
+        try:
+            rule()
+        except Exception as exc:  # a crash is that rule's failure, never a pass
+            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: attributes -- v2.22 keeps a world's attributes, one value per entity of the types each "
+          "names, its history row by row; the system attributes read the canon's own columns; nothing in "
+          "use is taken away")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/single_canon_write.py b/tooling/verify/checks/single_canon_write.py
index 7fbc654..42cd5ab 100644
--- a/tooling/verify/checks/single_canon_write.py
+++ b/tooling/verify/checks/single_canon_write.py
@@ -81,11 +81,14 @@ single-row correction): `write_npc_prices`, `write_world_laws`,
 (TICKET-0108, BRIEF-0108-B: an offer's steps; its conditions through
 `delete_offer_conditions`, TICKET-0111, BRIEF-0111-C), `write_condition`
 (TICKET-0111: one owner's condition and its nodes) and
-`write_offer_terms` (TICKET-0109, BRIEF-0109-B: an offer's terms) each
+`write_offer_terms` (TICKET-0109, BRIEF-0109-B: an offer's terms) and
+`writes/attributes.py::_write_types` (TICKET-0113, BRIEF-0113-A: an
+attribute definition's entity types) each
 `DELETE FROM` their table(s) scoped to one parent (NPC / world / location /
-location / offer) then re-insert the submitted set, in one transaction —
-creator-CRUD and world-bootstrap only (`set_npc_prices`, `create_world`,
-`set_location_geometry`, `set_location_doors`, `save_offer`;
+location / offer / definition) then re-insert the submitted set, in one
+transaction — creator-CRUD and world-bootstrap only (`set_npc_prices`,
+`create_world`, `set_location_geometry`, `set_location_doors`,
+`save_offer`, the attribute definition routes;
 `location_subculture` and
 its writer were dropped in schema v2.06, TICKET-0091, BRIEF-0091-I), never
 reachable from any AI or play path. These
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index 654dfe0..79b9205 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -208,6 +208,16 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
               "fact_id": "fa-{w}"}),
     ("debt_term", {"id": "dt-{w}", "world_id": "{w}", "debt_id": "de-{w}", "term_order": 1,
                    "currency": "item", "item_id": "{w}-item", "amount": 2}),
+    # TICKET-0113 (BRIEF-0113-A): an attribute, its type, a choice, a value and its change.
+    ("attribute_definition", {"id": "ad-{w}", "world_id": "{w}", "name": "Maudit", "kind": "choice"}),
+    ("attribute_definition_type", {"id": "adt-{w}", "world_id": "{w}", "definition_id": "ad-{w}",
+                                   "side": "holder", "entity_type": "character"}),
+    ("attribute_choice", {"id": "ac-{w}", "world_id": "{w}", "definition_id": "ad-{w}", "label": "oui",
+                          "is_default": 1}),
+    ("attribute_value", {"id": "av-{w}", "world_id": "{w}", "definition_id": "ad-{w}",
+                         "entity_id": "{w}-char", "choice_id": "ac-{w}"}),
+    ("attribute_change", {"id": "ach-{w}", "world_id": "{w}", "value_id": "av-{w}", "kind": "changement",
+                          "changed_by": "creator_crud", "after_choice_id": "ac-{w}"}),
 )
 
 
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index f7c34b1..0e27a28 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,17 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.22** — TICKET-0113, BRIEF-0113-A: the state of the world.
+  `attribute_definition` (a world's attribute: its name, its kind --
+  `choice`, `integer` or `entity` --, its default, hidden or not, active or
+  retired), `attribute_definition_type` (the entity types it applies to, and
+  those an `entity` value may name), `attribute_choice` (a choice's labels,
+  one the default, retired never deleted), `attribute_value` (one entity's
+  value) and `attribute_change` (its history, append-only, each row a
+  `correction` or a `changement`) are added. The states the canon already
+  keeps are read in place as system attributes, never copied.
+  `migrate_v2_22_attributes.py` creates the five tables empty, refuses a
+  database older than v2.21 and moves `schema_meta` to v2.22 only.
 - **v2.21** — TICKET-0112, BRIEF-0112-B: the condition interpreter's
   journal. `condition_draft` (one row per proposal: the creator's
   instruction for one condition of an offer, what the model answered and
diff --git a/world-engine-schema.md b/world-engine-schema.md
index 0d2bd0d..6bf1446 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.21
+Current schema version: v2.22
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -2609,6 +2609,145 @@ CREATE INDEX idx_debt_term_debt ON debt_term(debt_id);
 
 -----
 
+### `attribute_definition`
+
+One attribute of a world -- the state of the world (v2.22, TICKET-0113,
+BRIEF-0113-A; WA3, WB2, WC1, WH1). « Maudit », « Ouvert », « Niveau
+d'alerte », « Occupé par »: the creator defines it, every entity of a type
+it names holds one value of it. `kind` is `choice` (one of its labels,
+`attribute_choice`), `integer` (`default_integer` its default) or `entity`
+(another entity of a type `attribute_definition_type` names on its `value`
+side; empty by default). WC1: an entity with no `attribute_value` row reads
+the default -- nothing is written on read. `is_hidden` (WH1): a condition on
+it never writes it out on a player surface. A definition is retired, never
+deleted; retiring is refused while a condition names it (WJ2). The states
+the canon already keeps -- `character.vital_status`, `entity.status`,
+`location.magic_status` -- are read in place as system attributes
+(`attributes.SYSTEM_ATTRIBUTES`), never rows here; no definition may take a
+system attribute's name, nor another definition's of its world (compared
+case- and accent-blind by the writer, case-blind by the index). Written
+only by `writes/attributes.py`.
+
+```sql
+CREATE TABLE attribute_definition (
+  id               TEXT PRIMARY KEY,
+  world_id         TEXT NOT NULL REFERENCES world(id),
+  name             TEXT NOT NULL,
+  kind             TEXT NOT NULL CHECK (kind IN ('choice','integer','entity')),
+  default_integer  INTEGER,
+  is_hidden        BOOLEAN NOT NULL DEFAULT 0,
+  status           TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','retired')),
+  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
+  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
+  CHECK (kind = 'integer' OR default_integer IS NULL)
+);
+CREATE UNIQUE INDEX idx_attribute_definition_name ON attribute_definition(world_id, name COLLATE NOCASE);
+```
+
+-----
+
+### `attribute_definition_type`
+
+The entity types a definition applies to (`side = 'holder'`, WB2: one
+« Maudit » for characters and items alike) and, for an `entity` kind, the
+types its value may name (`side = 'value'`). `entity_type` is a built-in
+type or a runtime type's slug (`entity.type`). Curated config: the writer
+replaces a definition's rows whole, refusing to drop a type an entity
+holding a value, or a condition, still uses.
+
+```sql
+CREATE TABLE attribute_definition_type (
+  id             TEXT PRIMARY KEY,
+  world_id       TEXT NOT NULL REFERENCES world(id),
+  definition_id  TEXT NOT NULL REFERENCES attribute_definition(id),
+  side           TEXT NOT NULL CHECK (side IN ('holder','value')),
+  entity_type    TEXT NOT NULL
+);
+CREATE UNIQUE INDEX idx_attribute_definition_type_unique
+  ON attribute_definition_type(definition_id, side, entity_type);
+```
+
+-----
+
+### `attribute_choice`
+
+The labels of a `choice` definition, in `position` order; exactly one
+active label is the default (`is_default`, the partial index). A label
+dropped from the list is retired, never deleted -- a value's history may
+name it -- and refused while a value or a condition holds it.
+
+```sql
+CREATE TABLE attribute_choice (
+  id             TEXT PRIMARY KEY,
+  world_id       TEXT NOT NULL REFERENCES world(id),
+  definition_id  TEXT NOT NULL REFERENCES attribute_definition(id),
+  label          TEXT NOT NULL,
+  position       INTEGER NOT NULL DEFAULT 0,
+  is_default     BOOLEAN NOT NULL DEFAULT 0,
+  status         TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','retired')),
+  CHECK (is_default = 0 OR status = 'active')
+);
+CREATE UNIQUE INDEX idx_attribute_choice_label ON attribute_choice(definition_id, label COLLATE NOCASE);
+CREATE UNIQUE INDEX idx_attribute_choice_one_default ON attribute_choice(definition_id) WHERE is_default = 1;
+```
+
+-----
+
+### `attribute_value`
+
+One entity's current value of one definition: a choice, an integer, or an
+entity -- none of the three only for an `entity` kind left empty. One row
+per (definition, entity), never deleted; each write appends an
+`attribute_change`.
+
+```sql
+CREATE TABLE attribute_value (
+  id               TEXT PRIMARY KEY,
+  world_id         TEXT NOT NULL REFERENCES world(id),
+  definition_id    TEXT NOT NULL REFERENCES attribute_definition(id),
+  entity_id        TEXT NOT NULL REFERENCES entity(id),
+  choice_id        TEXT REFERENCES attribute_choice(id),
+  integer_value    INTEGER,
+  entity_value_id  TEXT REFERENCES entity(id),
+  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
+  CHECK ((choice_id IS NOT NULL) + (integer_value IS NOT NULL) + (entity_value_id IS NOT NULL) <= 1)
+);
+CREATE UNIQUE INDEX idx_attribute_value_pair ON attribute_value(definition_id, entity_id);
+CREATE INDEX idx_attribute_value_entity ON attribute_value(entity_id);
+```
+
+-----
+
+### `attribute_change`
+
+The history of a value (WD1), append-only -- the rows ARE the history, no
+`change_history` column: the value before (the definition's default when
+the entity held none) and after, in the columns of its kind; `kind` is
+`correction` (it was always so) or `changement` (the world changed), the
+vocabulary of `writes.facts.FACT_CHANGE_KINDS`, chosen by the creator at
+each write; `changed_by` who made it. TICKET-0114's events will append here
+too.
+
+```sql
+CREATE TABLE attribute_change (
+  id                TEXT PRIMARY KEY,
+  world_id          TEXT NOT NULL REFERENCES world(id),
+  value_id          TEXT NOT NULL REFERENCES attribute_value(id),
+  kind              TEXT NOT NULL CHECK (kind IN ('correction','changement')),
+  changed_by        TEXT NOT NULL,
+  before_choice_id  TEXT REFERENCES attribute_choice(id),
+  before_integer    INTEGER,
+  before_entity_id  TEXT REFERENCES entity(id),
+  after_choice_id   TEXT REFERENCES attribute_choice(id),
+  after_integer     INTEGER,
+  after_entity_id   TEXT REFERENCES entity(id),
+  changed_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
+);
+CREATE INDEX idx_attribute_change_value ON attribute_change(value_id, changed_at);
+```
+
+-----
+
 ### `goal_agenda_link`
 
 Many-to-many tie between an `npc_goal` and the `agenda` intrigue(s) it
````

2. Regenerate: `python tooling/glue/gen_decisions_index.py`.
3. Regenerate: `python tooling/glue/gen_file_map.py`.
4. Commit as one commit: `BRIEF-0113-A: the state of the world -- attribute definitions, values and history (schema v2.22)`.

## Scope OUT

- Any condition form reading an attribute, `vital_status` untouched (BRIEF-0113-B).
- Any route or surface (BRIEF-0113-C); any assembler or prompt reading attributes (WL1 -- TICKET-0114's first point).
- Writing a system attribute: its column keeps its own writer (WE1, G3).
- `item.condition` (WF1).
- A hard delete of a definition, a choice or a history row (WJ2: retire, never delete).

## Invariants to defend

**Schema is authoritative** -- model, migration, doc, changelog and the code constant move together (`schema_version_agreement.py`, `schema_partition.py`). **History is sacred** -- `attribute_change` is INSERT-only; a label is retired, never deleted (INV-10's spirit, AA3, AA5). **Two sanctioned canon-write paths** -- the five tables are canon, written only by `writes/attributes.py`, each site allowed (INV-08, INV-12: no new hard delete). **World cascade** -- every table world-scoped and deleted with its world (`world_cascade.py`). **Nia's database is never touched by an executor** -- AA6 migrates a temporary copy.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain (R-21 aside).
- A named mutation does not turn its rule red.
- `single_canon_write.py` or `world_cascade.py` turns red for a reason the diff does not explain.
- The migration would need to alter an existing table.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- Another ticket added tables to `CANON_TABLES`, `_DIRECT_WORLD_SCOPED_DELETES` or `_FIXTURE` since `d9230a7`: keep theirs, add these five after them, report it.

REPORT-ONLY:
- Timing of the corpus run; a check that times out under load and passes when rerun alone (name it).
- `lore_usage.py` U12c red between 20:00 and 24:00 Toronto (`--since` from a local date against UTC rows, R-21): pre-existing on `main`; rerun after midnight or name it. Never fixed here.
- `schema_reconcile` listing the five tables among the static tables at boot.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/attributes.py` -> `PASS: attributes -- v2.22 keeps a world's attributes, one value per entity of the types each names, its history row by row; the system attributes read the canon's own columns; nothing in use is taken away`
- `single_canon_write.py`, `world_cascade.py`, `schema_version_agreement.py`, `schema_partition.py`, `knowledge_identity.py`, `json_ui_boundary.py`, `module_budget.py`, `function_length.py`, `file_map.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`attributes.py` exits 1 with the rule named):
  - in `src/world_engine/models/canon_attribute.py`, `ATTRIBUTE_CHANGE_KINDS: tuple[str, ...] = ("correction", "changement")` -> `ATTRIBUTE_CHANGE_KINDS: tuple[str, ...] = ("changement", "correction")` -> `AA1`
  - in `src/world_engine/writes/attributes.py`, `        if normalize_surface(system.name) == key:` -> `        if system.name == clean:` -> `AA2`
  - in `src/world_engine/writes/attributes.py`, `    before = raw_of(row) if row is not None else _default_raw(db, definition)` -> `    before = _default_raw(db, definition)` -> `AA3`
  - in `src/world_engine/attributes.py`, `        EntityType.world_id == world_id, EntityType.status == "active",` -> `        EntityType.world_id == world_id,` -> `AA4`
  - in `src/world_engine/writes/attributes.py`, `    if clean.kind != definition.kind and (values or leaves):` -> `    if clean.kind != definition.kind and leaves:` -> `AA5`
  - in `scripts/migrate_v2_22_attributes.py`, `_PREVIOUS_VERSION = "v2.21"` -> `_PREVIOUS_VERSION = "v2.20"` -> `AA6`
  - in `src/world_engine/attributes.py`, `    row = stored_value(db, view.key, entity.id)` -> `    row = stored_value(db, view.key, entity.id); db.flush()` -> `AA7`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 148/148 (outside 20:00-24:00 Toronto, R-21).
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Schema v2.22: `world-engine-schema.md` (header, five table sections) and `world-engine-schema-changelog.md` -- in the diff. Decision entry « THE STATE OF THE WORLD IS A WORLD'S OWN ATTRIBUTES (TICKET-0113) -- A DEFINITION PER IDEA, ONE VALUE PER ENTITY, ITS HISTORY ROW BY ROW (BRIEF-0113-a, schema v2.22) » -- in the diff. `FILE_MAP.md`, `DECISIONS_INDEX.md` regenerated.
