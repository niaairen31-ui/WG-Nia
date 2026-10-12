<!-- slug: type-effects -->
# BRIEF 0119-A — "What an event does to the state of the world is part of its type -- event_type_effect; a change keeps its event (schema v2.26)"

Lot: LOT-0119-event-producers.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved (on `main` at `b512f2d`).

- `src/world_engine/models/canon_event.py:143` -> `class EventParticipant(SQLModel, table=True):` (the module's last class; no `EventTypeEffect`)
- `src/world_engine/models/canon_attribute.py:141` -> `    changed_at: datetime = _created_ts()` (`AttributeChange`'s last column; no `event_id`)
- `src/world_engine/models/pipeline.py:326` -> `LORE_ENTRY_ROW_TABLES: tuple[str, ...] = (` naming seven tables
- `src/world_engine/writes/event_types.py:270` -> `def _write_scopes(db: Session, world_id: str, type_id: str, clean: EventTypeSpec, ids: dict[str, str]) -> None:`
- `src/world_engine/writes/attributes.py:280` -> `def set_attribute_status(` refusing a retirement only while a condition names the definition
- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.25"`
- No `scripts/migrate_v2_26_event_effects.py`, no `tooling/verify/checks/event_effects.py`.

## Facts carried

### R-01 — the event vocabulary and its writer [M]
Opened: `src/world_engine/models/canon_event.py` (the declaring file:
`EventType`, `EventTypeRole`, `EventTypeRoleType`, `EventTypeScope` :110,
`EventSorte`, `EventParticipant` :143; `EVENT_SCOPE_LEVELS` :53, quoted by
the CHECKs); `src/world_engine/writes/event_types.py` (`EventTypeSpec` :85 --
name, domain, roles, counts_quantity, in_chronicle, participants_secret,
scopes; `clean_event_type` :169; `_write_scopes` :270 deletes and
re-inserts a type's scopes; `write_event_type` :278; `ensure_domain_type`
:364); `src/world_engine/event_vocab.py` (`EventTypeView` :66, `_view`
:107, `type_view` :116).
Finding: a type has no effect; its scopes are the full-replace precedent.
Consequence: A adds `event_type_effect` beside the scopes, written whole by
`_write_effects`, read into `EventTypeView.effects`.

### R-02 — the state of the world and its writer [M]
Opened: `src/world_engine/models/canon_attribute.py` (`AttributeChange`
:123 -- value before and after, `kind`, `changed_by`, `changed_at` :141;
no `event_id`); `src/world_engine/attributes.py` (`SYSTEM_ATTRIBUTES` :83:
`sys:vital_status` -- characters, alive/dead/missing/unknown --,
`sys:status` -- every entity, active/inactive/destroyed/missing --,
`sys:magic_status` -- locations; `attribute_view` :167, `world_attributes`
:190, `current_value` :245); `src/world_engine/writes/attributes.py`
(`_clean_update` :195 keeps a choice a value or a condition holds;
`set_attribute_status` :280 refuses retiring while a condition names it;
`write_attribute_value` :338 -- `correction` or `changement`, an unchanged
value writes nothing; :30 « a system attribute is never written here »).
Consequence: A gives `attribute_change` its `event_id` and extends the
in-use guards to effects; system states need their own writer (R-03).

### R-09 — Lore's writing path [M]
Opened: `src/world_engine/lore_write_draft.py` (:124 `_values`, :248
`draft_proposal`); `src/world_engine/lore_write_apply.py` (:178 `validate`
refuses a proposal writing no fact, membership or control; :202 `_Writer`;
:323 `apply_proposal`); `src/world_engine/models/pipeline.py` (:326
`LORE_ENTRY_ROW_TABLES`, :350 its CHECK: seven tables); `src/world_engine/
lore_write_read.py:36` (`_label` maps the seven); `scripts/seed_pilot.py`
(:1910 / :1957 the proposal prompt, :1978 `LORE_WRITE_PROMPT_HEADS`, :1996
its variables); `tooling/verify/checks/lore_write.py:651` (F1b pins the
panel's calls); CLAUDE.md INV-57 (every row recorded).
Consequence: A widens `lore_entry_row`; G records every row an event wrote.

### R-10 — the lists this lot extends [M]
Opened: `tooling/verify/canon_write_policy.txt` (one line per writer);
`tooling/verify/checks/single_canon_write.py` (docstring: the named
full-replace deletes); `src/world_engine/writes/worlds.py:65`
(`_DIRECT_WORLD_SCOPED_DELETES`, :82 the event tables) and
`tooling/verify/checks/world_cascade.py` (W1/W3: every world table in the
list and the fixture); `tooling/verify/checks/attributes.py:123` (AA1/AA6 pin
`attribute_change`'s columns); `src/world_engine/schema_version.py:15`
(v2.25); `.claude/rules/gatherings.md` (INV-25).

## Contracts

### C-01 — v2.26
Produced by: BRIEF-0119-A   Consumed by: B-G
`event_type_effect` (`world_id`, `type_id`, `role_id`, `definition_id` XOR
`system_key`, `mode` in `EVENT_EFFECT_MODES = ("set", "add")`, exactly one of
`choice_id` / `system_value` / `integer_value` / `value_role_id`, `add` only
with `integer_value`, `position`; indexes `idx_event_type_effect_type`,
`idx_event_type_effect_definition`); `attribute_change.event_id` (FK
`event`, `idx_attribute_change_event`); `LORE_ENTRY_ROW_TABLES` gains
`event`, `event_participant`, `attribute_value`, `attribute_change`.

### C-02 — a type's effects (writer and reads)
Produced by: BRIEF-0119-A   Consumed by: B, C
`writes.event_types.EffectSpec(role, attribute, value, mode="set")` -- `role`
a role's NAME; `attribute` a definition id or a system key; `value` a choice
key, an integer, or (entity state) another role's NAME;
`EventTypeSpec.effects`; `EFFECT_SYSTEM_KEYS = ("sys:vital_status",
"sys:status")`; `MAX_EFFECTS = 8`. Refused (`ValueError`): an unknown or
retired state, a system state outside `EFFECT_SYSTEM_KEYS`, a role holding
no entity, a state applying to no entity type the role accepts, a value not
of the state's kind, `add` on a non-integer, an entity value naming the
same role or a role the state may not name, one role and state twice.
`event_vocab.EffectView(role_id, attribute, mode, value_kind ("choice" |
"integer" | "role"), value, position)`, `effect_view(row)`,
`EventTypeView.effects`. `write_attribute_value(..., event_id=None)` -- an
`event_id` only on a `changement`. A definition an effect names is not
retired, its kind does not change, its choice an effect names stays.

## Context

An event type says WHAT happened; this brief lets it also say what that does to the state of the world (M-c, C1): « Ouvrir : Cible -> Ouvert = oui ». An effect is data in the world's vocabulary -- a role, a state, a value of the state's kind (an integer set or added, D3; another role's entity; the vital state or the status, E1) -- that later briefs make concrete on an event's participants. `attribute_change` learns which event made a change, and `lore_entry_row` the tables an event Lore declares will write (G).

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `models/canon_event.py`: `EVENT_EFFECT_MODES`, `EventTypeEffect` (C-01); `models/canon_attribute.py`: `AttributeChange.event_id` and its index; `models/pipeline.py`: four more `LORE_ENTRY_ROW_TABLES` and the CHECK; `models/__init__.py` exports;
   - `writes/event_types.py`: `EffectSpec`, `EventTypeSpec.effects`, `EFFECT_SYSTEM_KEYS`, `MAX_EFFECTS`, `_clean_effects`, `_write_effects` (C-02); `event_vocab.py`: `EffectView`, `effect_view`, `EventTypeView.effects`;
   - `writes/attributes.py`: a definition an effect names is not retired, its kind stays, its named choice stays; `write_attribute_value(..., event_id=None)`, a `changement` only;
   - `writes/worlds.py` and `world_cascade.py`: `event_type_effect` in the cascade and its fixture; `canon_write_policy.txt` and the `single_canon_write.py` docstring: `_write_effects`, a full-replace;
   - `scripts/migrate_v2_26_event_effects.py`; `schema_version.py`, `world-engine-schema.md` (header, `event_type_effect`, `attribute_change`, `lore_entry_row`), the changelog;
   - `tooling/verify/checks/attributes.py`: `attribute_change`'s pinned shape gains `event_id`; creates check `event_effects.py` (EF1-EF5);
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - scripts/migrate_v2_26_event_effects.py
   - src/world_engine/event_vocab.py
   - src/world_engine/models/__init__.py
   - src/world_engine/models/canon_attribute.py
   - src/world_engine/models/canon_event.py
   - src/world_engine/models/pipeline.py
   - src/world_engine/schema_version.py
   - src/world_engine/writes/__init__.py
   - src/world_engine/writes/attributes.py
   - src/world_engine/writes/event_types.py
   - src/world_engine/writes/worlds.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/canon_write_policy.txt
   - tooling/verify/checks/attributes.py
   - tooling/verify/checks/event_effects.py
   - tooling/verify/checks/single_canon_write.py
   - tooling/verify/checks/world_cascade.py
   - world-engine-schema-changelog.md
   - world-engine-schema.md

````diff
diff --git a/scripts/migrate_v2_26_event_effects.py b/scripts/migrate_v2_26_event_effects.py
new file mode 100644
index 0000000..1707146
--- /dev/null
+++ b/scripts/migrate_v2_26_event_effects.py
@@ -0,0 +1,218 @@
+"""Migration v2.26 — what an event does to the state of the world
+(TICKET-0119, BRIEF-0119-A; decisions M-c, C1, D3, E1 and U1 of the
+conditions series).
+
+Schema, additive except one rebuild; no data is written:
+
+- creates `event_type_effect` (an event type's effects: the role whose
+  entity changes, the state, the value -- a choice, an integer set or
+  added, or the entity of another role), exactly as the model declares it;
+- adds `attribute_change.event_id` (the event that made a change, M-c) and
+  its index `idx_attribute_change_event`;
+- rebuilds `lore_entry_row` (its `row_table` CHECK gains `event`,
+  `event_participant`, `attribute_value` and `attribute_change`: an event
+  Lore declares is recorded with everything it wrote, U1), every row
+  copied.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.25. Idempotent: each step checks what is already there. One raw
+transaction (`foreign_keys` and `legacy_alter_table` set before it).
+
+Post-check, before `schema_meta` moves: `lore_entry_row` and
+`attribute_change` kept their row counts; the new table, column and CHECK
+are in place; `PRAGMA foreign_key_check` on the tables this migration
+writes is empty (a dangling row elsewhere is a note, never a failure --
+AMENDMENT-0107-01). `schema_meta` then moves to v2.26.
+
+Run from the project root:
+
+    python scripts/migrate_v2_26_event_effects.py
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
+        "migrate_v2_26_event_effects.py refuses to run without WORLD_ENGINE_ENV "
+        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+from sqlalchemy import inspect, text  # noqa: E402
+from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
+from sqlmodel import Session  # noqa: E402
+
+from world_engine import models  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.25"
+_THIS_VERSION = "v2.26"
+_LORE_ROW_COLUMNS = "id, entry_id, row_table, row_id, action"
+_EVENT_INDEX = "idx_attribute_change_event"
+# The tables this migration writes: the only ones its foreign-key post-check judges.
+_TOUCHED_TABLES = ("event_type_effect", "attribute_change", "lore_entry_row")
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+def _refuse() -> None:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
+    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
+        found = row[0] if row is not None else "no schema_meta row"
+        raise SystemExit(
+            f"Migration v2.26 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _table_sql(table: str) -> str:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:t"), {"t": table}).first()
+    return row[0] if row is not None else ""
+
+
+def _columns(table: str) -> set[str]:
+    return {column["name"] for column in inspect(engine).get_columns(table)}
+
+
+def _indexes(table: str) -> set[str]:
+    return {index["name"] for index in inspect(engine).get_indexes(table)}
+
+
+def _count(conn, table: str) -> int:
+    return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
+
+
+def _create_from_model(cursor, model) -> None:
+    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
+    for index in model.__table__.indexes:
+        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))
+
+
+def _rebuild(cursor, table: str, model, columns: str) -> None:
+    for (index_name,) in cursor.execute(
+        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (table,)
+    ).fetchall():
+        cursor.execute(f"DROP INDEX {index_name}")
+    cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
+    _create_from_model(cursor, model)
+    cursor.execute(f"INSERT INTO {table} ({columns}) SELECT {columns} FROM {table}_old")
+    cursor.execute(f"DROP TABLE {table}_old")
+
+
+def _plan() -> dict:
+    existing = set(inspect(engine).get_table_names())
+    return {
+        "effect": "event_type_effect" not in existing,
+        "event_id": "event_id" not in _columns("attribute_change"),
+        "event_index": _EVENT_INDEX not in _indexes("attribute_change"),
+        "lore_entry_row": "'attribute_change'" not in _table_sql("lore_entry_row"),
+    }
+
+
+def _apply(plan: dict) -> list[str]:
+    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
+    PRAGMAs must land before any transaction exists)."""
+    applied: list[str] = []
+    raw = engine.raw_connection()
+    try:
+        cursor = raw.cursor()
+        cursor.execute("PRAGMA foreign_keys=OFF")
+        cursor.execute("PRAGMA legacy_alter_table=ON")
+        cursor.execute("BEGIN")
+        if plan["effect"]:
+            _create_from_model(cursor, models.EventTypeEffect)
+            applied.append("event_type_effect created")
+        if plan["event_id"]:
+            cursor.execute("ALTER TABLE attribute_change ADD COLUMN event_id VARCHAR REFERENCES event (id)")
+            applied.append("attribute_change.event_id added")
+        if plan["event_index"]:
+            cursor.execute(f"CREATE INDEX {_EVENT_INDEX} ON attribute_change (event_id)")
+            applied.append(f"{_EVENT_INDEX} created")
+        if plan["lore_entry_row"]:
+            _rebuild(cursor, "lore_entry_row", models.LoreEntryRow, _LORE_ROW_COLUMNS)
+            applied.append("lore_entry_row rebuilt")
+        cursor.execute("COMMIT")
+        cursor.execute("PRAGMA legacy_alter_table=OFF")
+        cursor.execute("PRAGMA foreign_keys=ON")
+        cursor.close()
+    except Exception:
+        raw.rollback()
+        raise
+    finally:
+        raw.close()
+    return applied
+
+
+def _post_checks(before: dict[str, int]) -> None:
+    with engine.connect() as conn:
+        after = {t: _count(conn, t) for t in before}
+        dangling = [row for table in _TOUCHED_TABLES
+                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
+        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
+                     if row[0] not in _TOUCHED_TABLES]
+    problems = []
+    if after != before:
+        problems.append(f"row counts changed {before} -> {after}")
+    if "event_type_effect" not in set(inspect(engine).get_table_names()):
+        problems.append("event_type_effect was not created")
+    if "event_id" not in _columns("attribute_change") or _EVENT_INDEX not in _indexes("attribute_change"):
+        problems.append("attribute_change.event_id or its index is missing")
+    if "'attribute_change'" not in _table_sql("lore_entry_row"):
+        problems.append("lore_entry_row was not rebuilt")
+    if dangling:
+        problems.append(f"foreign_key_check {dangling}")
+    if problems:
+        raise SystemExit("Migration v2.26 aborted, post-check failed: " + "; ".join(problems) + ".")
+    for table, rowid, parent, _fk in elsewhere:
+        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
+    print(f"Post-check: event_type_effect, attribute_change.event_id and lore_entry_row in place; "
+          f"counts kept {after}.")
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
+    print("Migration v2.26 — what an event does to the state of the world")
+    _refuse()
+    with engine.connect() as conn:
+        before = {t: _count(conn, t) for t in ("lore_entry_row", "attribute_change")}
+    applied = _apply(_plan())
+    print("Applied: " + ", ".join(applied) + "." if applied else "Migration v2.26 already fully applied.")
+    _post_checks(before)
+    _converge_schema_meta()
+    print("\nMigration v2.26 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/event_vocab.py b/src/world_engine/event_vocab.py
index 491b131..5860158 100644
--- a/src/world_engine/event_vocab.py
+++ b/src/world_engine/event_vocab.py
@@ -2,7 +2,8 @@
 decisions B1, C1, D1, N1 and W1 of the conditions series).
 
 A world's event types -- each with its roles in order, the entity types a
-role accepts and whether a sorte may fill it, who learns an event of it --
+role accepts and whether a sorte may fill it, who learns an event of it,
+what it does to the state of the world (its effects, M-c, TICKET-0119) --
 and its sortes. Every surface that names an event type or a sorte reads
 them here: the Création « Vocabulaire du monde » tab, the journal's sheet,
 the `event` condition form, the interpreter, the play analyzer.
@@ -29,6 +30,7 @@ from .lore_resolve import near_ratio, near_score, normalize_surface
 from .models import (
     EventSorte,
     EventType,
+    EventTypeEffect,
     EventTypeRole,
     EventTypeRoleType,
     EventTypeScope,
@@ -62,6 +64,21 @@ class ScopeView:
     level: str
 
 
+@dataclass(frozen=True)
+class EffectView:
+    """One effect of a type (M-c, TICKET-0119): the entity in `role_id`
+    takes, for the state `attribute` (a definition's id, or a system key),
+    `value` -- a choice's key (a definition's choice id, or a system state's
+    stored value), an integer (set, or added when `mode` is `add`, D3), or
+    the id of the role whose entity it names (`value_kind` says which)."""
+    role_id: str
+    attribute: str
+    mode: str
+    value_kind: str  # "choice" | "integer" | "role"
+    value: object
+    position: int
+
+
 @dataclass(frozen=True)
 class EventTypeView:
     id: str
@@ -74,6 +91,7 @@ class EventTypeView:
     status: str
     roles: tuple[RoleView, ...]
     scopes: tuple[ScopeView, ...]
+    effects: tuple[EffectView, ...] = ()
 
     def role(self, role_id: Optional[str]) -> Optional[RoleView]:
         return next((r for r in self.roles if r.id == role_id), None)
@@ -104,17 +122,35 @@ def _scopes(db: Session, type_id: str) -> tuple[ScopeView, ...]:
     return tuple(ScopeView(row.scope_kind, row.role_id, row.level) for row in rows)
 
 
+def effect_view(row: EventTypeEffect) -> EffectView:
+    """One stored effect as every reader sees it."""
+    if row.value_role_id is not None:
+        kind, value = "role", row.value_role_id
+    elif row.integer_value is not None:
+        kind, value = "integer", row.integer_value
+    else:
+        kind, value = "choice", row.choice_id if row.choice_id is not None else row.system_value
+    return EffectView(role_id=row.role_id, attribute=row.definition_id or row.system_key, mode=row.mode,
+                      value_kind=kind, value=value, position=row.position)
+
+
+def _effects(db: Session, type_id: str) -> tuple[EffectView, ...]:
+    rows = db.exec(select(EventTypeEffect).where(EventTypeEffect.type_id == type_id)
+                   .order_by(EventTypeEffect.position, EventTypeEffect.id)).all()
+    return tuple(effect_view(row) for row in rows)
+
+
 def _view(db: Session, row: EventType) -> EventTypeView:
     return EventTypeView(
         id=row.id, world_id=row.world_id, name=row.name, domain=row.domain,
         counts_quantity=row.counts_quantity, in_chronicle=row.in_chronicle,
         participants_secret=row.participants_secret, status=row.status,
-        roles=_roles(db, row.id), scopes=_scopes(db, row.id),
+        roles=_roles(db, row.id), scopes=_scopes(db, row.id), effects=_effects(db, row.id),
     )
 
 
 def type_view(db: Session, type_id: Optional[str]) -> Optional[EventTypeView]:
-    """One event type, its roles and scopes; None when there is none."""
+    """One event type, its roles, scopes and effects; None when there is none."""
     row = db.get(EventType, type_id) if type_id else None
     return _view(db, row) if row is not None else None
 
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index 51ea637..3f4a8ce 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -24,7 +24,8 @@ Layout, by stratum:
     canon_event.py   — the event journal's vocabulary and participants
                         (EventType, EventTypeRole, EventTypeRoleType,
                         EventTypeScope, EventSorte, EventParticipant;
-                        TICKET-0114, schema v2.24), canon.
+                        TICKET-0114, schema v2.24; EventTypeEffect,
+                        TICKET-0119, schema v2.26), canon.
     config.py        — canon curated-config tables too new/small to justify
                         growing canon.py at its module_budget cap
                         (ConversationWindowConfig, TICKET-0050).
@@ -107,6 +108,7 @@ from .canon_attribute import (
 )
 from .canon_event import (
     EVENT_DOMAINS,
+    EVENT_EFFECT_MODES,
     EVENT_SCOPE_KINDS,
     EVENT_SCOPE_LEVELS,
     EVENT_VOCAB_STATUSES,
@@ -114,6 +116,7 @@ from .canon_event import (
     EventSorte,
     EventType,
     EventTypeRole,
+    EventTypeEffect,
     EventTypeRoleType,
     EventTypeScope,
 )
@@ -225,6 +228,8 @@ __all__ = [
     "EventTypeScope",
     "EventSorte",
     "EventParticipant",
+    "EventTypeEffect",
+    "EVENT_EFFECT_MODES",
     "EVENT_DOMAINS",
     "EVENT_SCOPE_KINDS",
     "EVENT_SCOPE_LEVELS",
diff --git a/src/world_engine/models/canon_attribute.py b/src/world_engine/models/canon_attribute.py
index cf858fd..cc41f85 100644
--- a/src/world_engine/models/canon_attribute.py
+++ b/src/world_engine/models/canon_attribute.py
@@ -18,7 +18,9 @@ names holds one value of it, its history kept row by row:
 - `attribute_value`           : one entity's current value -- a choice, an
   integer, or an entity (none of the three: an `entity` kind left empty).
 - `attribute_change`          : the history (WD1), append-only: the value
-  before and after each write, `correction` or `changement`, by whom.
+  before and after each write, `correction` or `changement`, by whom --
+  and, for a change an event made (M-c, TICKET-0119, v2.26), that event
+  (`event_id`).
 
 The states the canon already keeps (`character.vital_status`,
 `entity.status`, `location.magic_status`) are read as SYSTEM attributes by
@@ -125,6 +127,7 @@ class AttributeChange(SQLModel, table=True):
     __table_args__ = (
         CheckConstraint("kind IN ('correction','changement')", name="ck_attribute_change_kind"),
         Index("idx_attribute_change_value", "value_id", "changed_at"),
+        Index("idx_attribute_change_event", "event_id"),
     )
 
     id: str = Field(default_factory=_uuid, primary_key=True)
@@ -139,3 +142,6 @@ class AttributeChange(SQLModel, table=True):
     after_integer: Optional[int] = None
     after_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
     changed_at: datetime = _created_ts()
+    # v2.26 (TICKET-0119, M-c): the event that made this change, when one
+    # did; a creator's own edit has none.
+    event_id: Optional[str] = Field(default=None, foreign_key="event.id")
diff --git a/src/world_engine/models/canon_event.py b/src/world_engine/models/canon_event.py
index 2d2a0d4..4b344ad 100644
--- a/src/world_engine/models/canon_event.py
+++ b/src/world_engine/models/canon_event.py
@@ -22,6 +22,13 @@ and every `event` row is one happening of one of those types:
   « bandit » -- a role may be filled by one, with the event's quantity.
 - `event_participant`     : who took part in one event, in which role: an
   entity or a sorte, exactly one (V1; it replaces `event_entity`).
+- `event_type_effect`     : what an event of the type does to the state of
+  the world (M-c, TICKET-0119, schema v2.26) -- « Ouvrir : Cible -> Ouvert =
+  oui » --, in order: the role whose entity changes, the state (a world's
+  definition, or `État vital` / `Statut`, E1), and the value it takes -- a
+  choice, an integer set or ADDED (D3), or the entity of another role
+  (« Occupé par = l'Usurpateur »). It pre-fills the changes of an event's
+  proposal; the creator keeps, edits or drops each.
 
 `writes/event_types.py` is the one writer of the vocabulary tables,
 `writes/events.py` the one writer of `event_participant`. Same
@@ -53,6 +60,8 @@ EVENT_VOCAB_STATUSES: tuple[str, ...] = ("active", "retired")
 EVENT_SCOPE_LEVELS: tuple[str, ...] = (
     "unaware", "rumor", "suspicious", "partial", "knows", "fully_understands",
 )
+# D3 (TICKET-0119): an effect sets its value, or adds an integer to it.
+EVENT_EFFECT_MODES: tuple[str, ...] = ("set", "add")
 
 
 def _in(values: tuple[str, ...]) -> str:
@@ -161,3 +170,40 @@ class EventParticipant(SQLModel, table=True):
     entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
     sorte_id: Optional[str] = Field(default=None, foreign_key="event_sorte.id")
     position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
+
+
+class EventTypeEffect(SQLModel, table=True):
+    """One effect of a type (M-c, TICKET-0119): the entity in `role_id`
+    takes, for the state `definition_id` (a world's) or `system_key` (E1:
+    `sys:vital_status`, `sys:status`), exactly one value -- `choice_id` (a
+    definition's choice), `system_value` (a system state's stored value),
+    `integer_value` (set, or added when `mode` is `add`), or the entity of
+    the role `value_role_id`. Which one fits the state's kind is
+    `writes.event_types`'s rule; the table holds that exactly one is set."""
+    __tablename__ = "event_type_effect"
+    __table_args__ = (
+        CheckConstraint(f"mode IN ({_in(EVENT_EFFECT_MODES)})", name="ck_event_type_effect_mode"),
+        CheckConstraint(
+            "(definition_id IS NOT NULL) + (system_key IS NOT NULL) = 1", name="ck_event_type_effect_state",
+        ),
+        CheckConstraint(
+            "(choice_id IS NOT NULL) + (system_value IS NOT NULL) + (integer_value IS NOT NULL)"
+            " + (value_role_id IS NOT NULL) = 1", name="ck_event_type_effect_value",
+        ),
+        CheckConstraint("mode = 'set' OR integer_value IS NOT NULL", name="ck_event_type_effect_add"),
+        Index("idx_event_type_effect_type", "type_id", "position"),
+        Index("idx_event_type_effect_definition", "definition_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    type_id: str = Field(foreign_key="event_type.id", nullable=False)
+    role_id: str = Field(foreign_key="event_type_role.id", nullable=False)
+    definition_id: Optional[str] = Field(default=None, foreign_key="attribute_definition.id")
+    system_key: Optional[str] = None
+    mode: str = Field(default="set", sa_column_kwargs={"server_default": text("'set'")})
+    choice_id: Optional[str] = Field(default=None, foreign_key="attribute_choice.id")
+    system_value: Optional[str] = None
+    integer_value: Optional[int] = None
+    value_role_id: Optional[str] = Field(default=None, foreign_key="event_type_role.id")
+    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
diff --git a/src/world_engine/models/pipeline.py b/src/world_engine/models/pipeline.py
index aa81f5b..e791442 100644
--- a/src/world_engine/models/pipeline.py
+++ b/src/world_engine/models/pipeline.py
@@ -326,6 +326,9 @@ class DayMentionReview(SQLModel, table=True):
 LORE_ENTRY_ROW_TABLES: tuple[str, ...] = (
     "entity", "fact", "fact_participant", "fact_default", "knowledge",
     "relation", "faction_membership",
+    # v2.26 (TICKET-0119, U1): an event Lore declares, its participants, and
+    # the states it changes.
+    "event", "event_participant", "attribute_value", "attribute_change",
 )
 LORE_ENTRY_ROW_ACTIONS: tuple[str, ...] = ("created", "updated")
 
@@ -348,7 +351,8 @@ class LoreEntryRow(SQLModel, table=True):
         Index("idx_lore_entry_row_entry", "entry_id", "row_table", "row_id", unique=True),
         CheckConstraint(
             "row_table IN ('entity','fact','fact_participant','fact_default','knowledge',"
-            "'relation','faction_membership')",
+            "'relation','faction_membership','event','event_participant','attribute_value',"
+            "'attribute_change')",
             name="ck_lore_entry_row_table",
         ),
         CheckConstraint("action IN ('created','updated')", name="ck_lore_entry_row_action"),
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index cd1e07a..22d8d07 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.25"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.26"
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index f94e864..f1ce798 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -70,7 +70,8 @@ Layout, by canon domain:
                           (TICKET-0113, BRIEF-0113-A).
     event_types.py      — the event journal's vocabulary: `event_type`,
                           `event_type_role`, `event_type_role_type`,
-                          `event_type_scope`, `event_sorte`:
+                          `event_type_scope`, `event_type_effect`
+                          (TICKET-0119), `event_sorte`:
                           `clean_event_type`, `write_event_type`,
                           `set_event_type_status`, `write_sorte`,
                           `set_sorte_status`, `ensure_domain_type`
diff --git a/src/world_engine/writes/attributes.py b/src/world_engine/writes/attributes.py
index 5e468aa..e986249 100644
--- a/src/world_engine/writes/attributes.py
+++ b/src/world_engine/writes/attributes.py
@@ -11,7 +11,8 @@ one writer of `attribute_definition`, `attribute_definition_type`,
   kind has an integer default, an `entity` kind names the types its value
   may take. On an existing definition, nothing in use is taken away (WJ2): its
   kind, a holder type an entity holding a value has, a value type a value
-  names, a choice a value or a condition holds. Writes nothing -- the
+  names, a choice a value, a condition or an event type's effect holds;
+  its kind while an effect names it (TICKET-0119). Writes nothing -- the
   interpreter validates a proposed definition through it (BRIEF-0113-E).
 - `write_attribute_definition(db, *, world_id, spec, definition_id=None)` :
   create or save one definition after cleaning it; its types are replaced
@@ -19,13 +20,14 @@ one writer of `attribute_definition`, `attribute_definition_type`,
   from the list is retired, never deleted, and a retired label named again
   comes back.
 - `set_attribute_status(db, *, world_id, definition_id, status)` : retire
-  or restore one definition; retiring is refused while a condition names it
-  (WJ2).
+  or restore one definition; retiring is refused while a condition or an
+  event type's effect names it (WJ2, TICKET-0119).
 - `write_attribute_value(db, *, world_id, definition_id, entity_id, value,
-  kind, changed_by)` : set one entity's value and append its
+  kind, changed_by, event_id=None)` : set one entity's value and append its
   `attribute_change` row -- the value before (the default when it held
-  none) and after, `correction` or `changement` (WD1). An unchanged value
-  writes nothing and returns None.
+  none) and after, `correction` or `changement` (WD1), and the event that
+  made it, when one did (M-c, TICKET-0119). An unchanged value writes
+  nothing and returns None.
 
 A system attribute (`attributes.SYSTEM_ATTRIBUTES`) is never written here:
 its column keeps its own writer. None of these functions commits.
@@ -58,6 +60,7 @@ from ..models import (
     AttributeDefinition,
     AttributeDefinitionType,
     AttributeValue,
+    EventTypeEffect,
     ConditionNode,
     Entity,
 )
@@ -183,6 +186,10 @@ def _leaves(db: Session, definition_id: str) -> list[ConditionNode]:
     )).all())
 
 
+def _effects(db: Session, definition_id: str) -> list[EventTypeEffect]:
+    return list(db.exec(select(EventTypeEffect).where(EventTypeEffect.definition_id == definition_id)).all())
+
+
 def _values(db: Session, definition_id: str) -> list[AttributeValue]:
     return list(db.exec(select(AttributeValue).where(AttributeValue.definition_id == definition_id)).all())
 
@@ -197,7 +204,8 @@ def _clean_update(db: Session, world_id: str, definition_id: str, clean: Definit
     if definition is None or definition.world_id != world_id:
         raise ValueError(f"unknown attribute {definition_id!r}")
     values, leaves = _values(db, definition_id), _leaves(db, definition_id)
-    if clean.kind != definition.kind and (values or leaves):
+    effects = _effects(db, definition_id)
+    if clean.kind != definition.kind and (values or leaves or effects):
         raise ValueError(f"« {definition.name} » is in use: its kind cannot change")
     held = {_entity_type(db, v.entity_id) for v in values} | {
         _entity_type(db, n.subject_entity_id) for n in leaves if n.subject_entity_id}
@@ -208,7 +216,8 @@ def _clean_update(db: Session, world_id: str, definition_id: str, clean: Definit
     for entity_type in sorted(t for t in named if t and t not in clean.value_types):
         raise ValueError(f"« {definition.name} » names a {entity_type}: that value type stays")
     kept = {c.id for c in clean.choices if c.id}
-    used = {v.choice_id for v in values if v.choice_id} | {n.value for n in leaves if n.value}
+    used = {v.choice_id for v in values if v.choice_id} | {n.value for n in leaves if n.value} | {
+        e.choice_id for e in effects if e.choice_id}
     for choice in _choice_rows(db, definition_id):
         if choice.status == "active" and choice.id not in kept and choice.id in used:
             raise ValueError(f"the label « {choice.label} » is in use: it stays")
@@ -287,6 +296,8 @@ def set_attribute_status(db: Session, *, world_id: str, definition_id: str, stat
         raise ValueError(f"unknown attribute {definition_id!r}")
     if status == "retired" and _leaves(db, definition_id):
         raise ValueError(f"« {definition.name} » is named by a condition: it cannot be retired")
+    if status == "retired" and _effects(db, definition_id):
+        raise ValueError(f"« {definition.name} » is changed by an event type: it cannot be retired")
     definition.status = status
     definition.updated_at = datetime.now(UTC)
     db.add(definition)
@@ -337,15 +348,18 @@ def _columns(kind: str, raw: RawValue, prefix: str) -> dict:
 
 def write_attribute_value(
     db: Session, *, world_id: str, definition_id: str, entity_id: str, value: RawValue, kind: str,
-    changed_by: str,
+    changed_by: str, event_id: Optional[str] = None,
 ) -> Optional[AttributeChange]:
     """Set one entity's value of one active definition (WD1): `kind` is
-    `correction` or `changement`. Returns the appended `attribute_change`, or
-    None when the value is unchanged (nothing written)."""
+    `correction` or `changement`; `event_id` the event that made it (M-c),
+    a `changement` only. Returns the appended `attribute_change`, or None
+    when the value is unchanged (nothing written)."""
     if kind not in ATTRIBUTE_CHANGE_KINDS:
         raise ValueError(f"unknown change kind {kind!r}")
     if not changed_by:
         raise ValueError("a change names who made it")
+    if event_id is not None and kind != "changement":
+        raise ValueError("an event changes the world: its change is a `changement`")
     definition = db.get(AttributeDefinition, definition_id)
     if definition is None or definition.world_id != world_id or definition.status != "active":
         raise ValueError(f"unknown attribute {definition_id!r}")
@@ -367,7 +381,7 @@ def write_attribute_value(
     db.add(row)
     db.flush()
     change = AttributeChange(
-        world_id=world_id, value_id=row.id, kind=kind, changed_by=changed_by,
+        world_id=world_id, value_id=row.id, kind=kind, changed_by=changed_by, event_id=event_id,
         **_columns(definition.kind, before, "before_"), **_columns(definition.kind, after, "after_"),
     )
     db.add(change)
diff --git a/src/world_engine/writes/event_types.py b/src/world_engine/writes/event_types.py
index 6659a08..8816d75 100644
--- a/src/world_engine/writes/event_types.py
+++ b/src/world_engine/writes/event_types.py
@@ -1,7 +1,7 @@
 """The writer of the event journal's vocabulary (TICKET-0114, BRIEF-0114-A;
 decisions B1, C1, D1, N1 and W1 of the conditions series): the one writer of
-`event_type`, `event_type_role`, `event_type_role_type`, `event_type_scope`
-and `event_sorte`.
+`event_type`, `event_type_role`, `event_type_role_type`, `event_type_scope`,
+`event_type_effect` (TICKET-0119) and `event_sorte`.
 
 - `clean_event_type(db, world_id, spec, type_id=None)` : a type as it will
   be written, or `ValueError` -- its name is no other type's of the world
@@ -9,14 +9,21 @@ and `event_sorte`.
   `EVENT_DOMAINS`, one role or more with distinct names, each accepting one
   of the world's entity types or a sorte; a scope on `rencontre` names a
   role that accepts an entity, on `faction` a role that accepts a faction.
-  On an existing type, nothing in use is taken away: a role an event or a
+  An effect (M-c, TICKET-0119, `EFFECT_SYSTEM_KEYS` for E1) names one of
+  its roles that holds an entity, a state of the world -- one of the world's
+  active definitions, or `État vital` / `Statut` -- that applies to an
+  entity type the role accepts, and a value of that state's kind: one of its
+  choices, an integer (`add` only for an integer, D3), or another role whose
+  entity the state may name; never the same role and state twice. On an
+  existing type, nothing in use is taken away: a role an event or a
   condition names, an entity type a participant has, a sorte a participant
   is, a quantity an event carries. Writes nothing -- the interpreter and the
   analyzer validate a proposed type through it.
 - `write_event_type(db, *, world_id, spec, type_id=None)` : create or save
   one type after cleaning it. Roles are matched by id, else by name; a role
   dropped from the list is retired, never deleted, and comes back when named
-  again. A role's entity types and the type's scopes are replaced whole.
+  again. A role's entity types, the type's scopes and its effects are
+  replaced whole (an effect only pre-fills a proposal: nothing holds it).
 - `set_event_type_status(db, *, world_id, type_id, status)` : retire or
   restore a type; retiring is refused while a condition names it.
 - `clean_sorte_name` / `write_sorte(db, *, world_id, name, sorte_id=None)` /
@@ -39,11 +46,12 @@ from typing import Optional
 from sqlalchemy import text
 from sqlmodel import Session, select
 
-from ..attributes import world_entity_types
+from ..attributes import AttributeView, attribute_view, world_entity_types
 from ..event_vocab import DOMAIN_LABELS_FR, DOMAIN_ROLE_FR, EVENT_FORM
 from ..lore_resolve import normalize_surface
 from ..models import (
     EVENT_DOMAINS,
+    EVENT_EFFECT_MODES,
     EVENT_SCOPE_KINDS,
     EVENT_SCOPE_LEVELS,
     EVENT_VOCAB_STATUSES,
@@ -54,6 +62,7 @@ from ..models import (
     EventParticipant,
     EventSorte,
     EventType,
+    EventTypeEffect,
     EventTypeRole,
     EventTypeRoleType,
     EventTypeScope,
@@ -61,6 +70,10 @@ from ..models import (
 
 MAX_NAME_CHARS = 80
 MAX_ROLES = 8
+MAX_EFFECTS = 8
+# E1 (TICKET-0119): the system states an effect may change. `Magie` stays
+# the creator's alone.
+EFFECT_SYSTEM_KEYS: tuple[str, ...] = ("sys:vital_status", "sys:status")
 
 
 @dataclass(frozen=True)
@@ -81,6 +94,18 @@ class ScopeSpec:
     level: str = "knows"
 
 
+@dataclass(frozen=True)
+class EffectSpec:
+    """One effect as the creator states it (M-c): `role` and, for an
+    `entity` state, `value` are role NAMES of the type; `attribute` is a
+    definition id or a system key; `value` is otherwise a choice key or an
+    integer. `mode` is `set` or, for an integer, `add` (D3)."""
+    role: str
+    attribute: str
+    value: object
+    mode: str = "set"
+
+
 @dataclass(frozen=True)
 class EventTypeSpec:
     name: str
@@ -90,6 +115,7 @@ class EventTypeSpec:
     in_chronicle: bool = True
     participants_secret: bool = False
     scopes: tuple[ScopeSpec, ...] = ()
+    effects: tuple[EffectSpec, ...] = ()
 
 
 # --- cleaning ------------------------------------------------------------------
@@ -166,6 +192,59 @@ def _clean_scopes(roles: tuple[RoleSpec, ...], scopes: tuple[ScopeSpec, ...]) ->
     return tuple(seen)
 
 
+def _effect_state(db: Session, world_id: str, key: object) -> AttributeView:
+    view = attribute_view(db, world_id, key) if isinstance(key, str) else None
+    if view is None or view.status != "active":
+        raise ValueError(f"unknown state {key!r}")
+    if view.system and view.key not in EFFECT_SYSTEM_KEYS:
+        raise ValueError(f"« {view.name} » is the creator's alone: no event changes it")
+    return view
+
+
+def _effect_value(view: AttributeView, effect: EffectSpec, by_key: dict, role: RoleSpec) -> object:
+    if effect.mode not in EVENT_EFFECT_MODES:
+        raise ValueError(f"unknown effect mode {effect.mode!r}")
+    if effect.mode == "add" and view.kind != "integer":
+        raise ValueError(f"« {view.name} » is not a number: an effect sets it")
+    if view.kind == "integer":
+        if not isinstance(effect.value, int) or isinstance(effect.value, bool):
+            raise ValueError(f"« {view.name} » takes an integer")
+        return effect.value
+    if view.kind == "choice":
+        if effect.value not in dict(view.choices):
+            raise ValueError(f"{effect.value!r} is no value of « {view.name} »")
+        return effect.value
+    other = by_key.get(normalize_surface(str(effect.value or "")))
+    if other is None or other is role:
+        raise ValueError(f"« {view.name} » names the entity of another role of the type")
+    if not set(other.entity_types) & set(view.value_types):
+        raise ValueError(f"the role « {other.name} » holds no entity « {view.name} » may name")
+    return other.name
+
+
+def _clean_effects(db: Session, world_id: str, roles: tuple[RoleSpec, ...],
+                   effects: tuple[EffectSpec, ...]) -> tuple[EffectSpec, ...]:
+    by_key = {normalize_surface(role.name): role for role in roles}
+    if len(effects) > MAX_EFFECTS:
+        raise ValueError(f"an event type has at most {MAX_EFFECTS} effects")
+    seen: list[EffectSpec] = []
+    for effect in effects:
+        role = by_key.get(normalize_surface(str(effect.role or "")))
+        if role is None:
+            raise ValueError("an effect names one of the type's roles")
+        if not role.entity_types:
+            raise ValueError(f"the role « {role.name} » holds no entity: no state to change")
+        view = _effect_state(db, world_id, effect.attribute)
+        if view.holder_types is not None and not set(role.entity_types) & set(view.holder_types):
+            raise ValueError(f"« {view.name} » applies to no entity the role « {role.name} » holds")
+        clean = EffectSpec(role=role.name, attribute=view.key, value=_effect_value(view, effect, by_key, role),
+                           mode=effect.mode)
+        if any(s.role == clean.role and s.attribute == clean.attribute for s in seen):
+            raise ValueError(f"the role « {role.name} » changes « {view.name} » twice")
+        seen.append(clean)
+    return tuple(seen)
+
+
 def clean_event_type(db: Session, world_id: str, spec: EventTypeSpec, type_id: Optional[str] = None) -> EventTypeSpec:
     """`spec` as it will be written; raises `ValueError` on any violation.
     Writes nothing."""
@@ -176,6 +255,7 @@ def clean_event_type(db: Session, world_id: str, spec: EventTypeSpec, type_id: O
         name=_clean_type_name(db, world_id, spec.name, type_id), domain=spec.domain, roles=roles,
         counts_quantity=bool(spec.counts_quantity), in_chronicle=bool(spec.in_chronicle),
         participants_secret=bool(spec.participants_secret), scopes=_clean_scopes(roles, tuple(spec.scopes)),
+        effects=_clean_effects(db, world_id, roles, tuple(spec.effects)),
     )
     if type_id is not None:
         _clean_update(db, world_id, type_id, clean)
@@ -275,6 +355,29 @@ def _write_scopes(db: Session, world_id: str, type_id: str, clean: EventTypeSpec
                               level=scope.level))
 
 
+def _write_effects(db: Session, world_id: str, type_id: str, clean: EventTypeSpec, ids: dict[str, str]) -> None:
+    """The type's effects replaced whole: an effect pre-fills a proposal,
+    nothing holds it."""
+    db.execute(text("DELETE FROM event_type_effect WHERE type_id = :tid"), {"tid": type_id})
+    for position, effect in enumerate(clean.effects):
+        row = EventTypeEffect(world_id=world_id, type_id=type_id, role_id=ids[normalize_surface(effect.role)],
+                              mode=effect.mode, position=position)
+        if effect.attribute.startswith("sys:"):
+            row.system_key = effect.attribute
+        else:
+            row.definition_id = effect.attribute
+        kind = attribute_view(db, world_id, effect.attribute).kind
+        if kind == "integer":
+            row.integer_value = effect.value
+        elif kind == "entity":
+            row.value_role_id = ids[normalize_surface(effect.value)]
+        elif row.system_key is not None:
+            row.system_value = effect.value
+        else:
+            row.choice_id = effect.value
+        db.add(row)
+
+
 def write_event_type(
     db: Session, *, world_id: str, spec: EventTypeSpec, type_id: Optional[str] = None,
 ) -> EventType:
@@ -293,6 +396,7 @@ def write_event_type(
     db.flush()
     ids = _write_roles(db, world_id, row.id, clean)
     _write_scopes(db, world_id, row.id, clean, ids)
+    _write_effects(db, world_id, row.id, clean, ids)
     db.flush()
     return row
 
diff --git a/src/world_engine/writes/worlds.py b/src/world_engine/writes/worlds.py
index f89d065..195528d 100644
--- a/src/world_engine/writes/worlds.py
+++ b/src/world_engine/writes/worlds.py
@@ -80,6 +80,7 @@ _DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
     "attribute_value", "attribute_change",
     "event_type", "event_type_role", "event_type_role_type", "event_type_scope",
     "event_sorte", "event_participant", "condition_node_filter",
+    "event_type_effect",
 )
 
 # Refusing tables (root_table, label_column, guarded_children, message) —
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index fc41b64..cad8eed 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19481,6 +19481,38 @@ typed shape, an EVENT_CREATION RUBRIC, the two lists in the message),
 delivered by `apply_ticket_0114_analysis_prompt.py`, fragment by fragment:
 the creator's edits are kept.
 
+## WHAT AN EVENT DOES TO THE STATE OF THE WORLD IS PART OF ITS TYPE (TICKET-0119) -- `event_type_effect`, AND A CHANGE KEEPS ITS EVENT (BRIEF-0119-a, schema v2.26)
+
+**M-c, C1.** An event type declares its effects as data: « Ouvrir : Cible
+-> Ouvert = oui », « Usurper : Trône -> Occupé par = l'Usurpateur ». An
+effect names a role of the type that holds an entity, a state -- one of
+the world's definitions, or a system state -- that applies to an entity
+type the role accepts, and one value of the state's kind: a choice, an
+integer, or the entity of another role. An effect only PRE-FILLS the
+changes of an event's proposal (TICKET-0119's later briefs); the creator
+keeps, edits or drops each, so nothing holds an effect and a type's effects
+are replaced whole.
+
+**D3.** An integer effect sets its value or ADDS to it (« Alerte + 1 »).
+A count of events stays the journal's: an integer state is for what is not
+a number of events.
+
+**E1.** An effect may change `État vital` and `Statut`, the two system
+states play may move (`EFFECT_SYSTEM_KEYS`); `Magie` stays the creator's.
+Their columns keep their own writers and no history table; the reason of a
+change is the event and its fact.
+
+**What an effect holds.** A definition an effect names is not retired, its
+kind does not change, and a choice it names stays (the WJ2 rule, extended).
+
+**A change keeps its event.** `attribute_change.event_id` names the event
+that made a `changement`; a creator's own correction names none, and an
+event never makes a `correction`.
+
+**Lore records an event (U1).** `lore_entry_row` may name `event`,
+`event_participant`, `attribute_value` and `attribute_change`, so an event
+Lore declares (BRIEF-0119-G) is recorded with every row it wrote.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index e7b545e..f88c348 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -10,6 +10,7 @@ item_holding quest_offer_term quest_term quest_economy
 debt debt_term
 attribute_definition attribute_definition_type attribute_choice attribute_value attribute_change
 event_type event_type_role event_type_role_type event_type_scope event_sorte event_participant condition_node_filter
+event_type_effect
 
 [ALLOWED_SITES]
 # path::function                                              tables
@@ -79,6 +80,8 @@ src/world_engine/writes/attributes.py::write_attribute_value    attribute_value
 src/world_engine/writes/event_types.py::write_event_type       event_type
 src/world_engine/writes/event_types.py::_write_roles           event_type_role event_type_role_type
 src/world_engine/writes/event_types.py::_write_scopes          event_type_scope
+# TICKET-0119, BRIEF-0119-A: _write_effects replaces a type's effects whole (an effect only pre-fills a proposal; nothing holds it). Same callers as write_event_type.
+src/world_engine/writes/event_types.py::_write_effects         event_type_effect
 src/world_engine/writes/event_types.py::set_event_type_status  event_type
 src/world_engine/writes/event_types.py::write_sorte            event_sorte
 src/world_engine/writes/event_types.py::set_sorte_status       event_sorte
diff --git a/tooling/verify/checks/attributes.py b/tooling/verify/checks/attributes.py
index 4140b37..3341f1e 100644
--- a/tooling/verify/checks/attributes.py
+++ b/tooling/verify/checks/attributes.py
@@ -120,11 +120,13 @@ TABLES: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
         ("ck_attribute_value_one",),
         ("idx_attribute_value_pair", "idx_attribute_value_entity"),
     ),
+    # `event_id` and its index: v2.26 (TICKET-0119, BRIEF-0119-A), the event
+    # that made a change.
     "attribute_change": (
         ("id", "world_id", "value_id", "kind", "changed_by", "before_choice_id", "before_integer",
-         "before_entity_id", "after_choice_id", "after_integer", "after_entity_id", "changed_at"),
+         "before_entity_id", "after_choice_id", "after_integer", "after_entity_id", "changed_at", "event_id"),
         ("ck_attribute_change_kind",),
-        ("idx_attribute_change_value",),
+        ("idx_attribute_change_value", "idx_attribute_change_event"),
     ),
 }
 
diff --git a/tooling/verify/checks/event_effects.py b/tooling/verify/checks/event_effects.py
new file mode 100644
index 0000000..e349307
--- /dev/null
+++ b/tooling/verify/checks/event_effects.py
@@ -0,0 +1,461 @@
+"""G1 check for TICKET-0119 -- what an event type does to the state of the world: its effects, written and read.
+
+BRIEF-0119-A's rules (M-c, C1, D3 and E1 of the conditions series). An effect
+only pre-fills an event's proposal; what an approved event writes is
+`event_changes.py`'s.
+
+EF1 -- storage (import). `event_type_effect` carries exactly its contract's
+   columns, CHECK names and index names, none of them JSON;
+   `EVENT_EFFECT_MODES` is its mode CHECK's values; `attribute_change` has
+   `event_id` and `idx_attribute_change_event`; `EFFECT_SYSTEM_KEYS` are
+   system attributes (`attributes.SYSTEM_ATTRIBUTES`) and are exactly
+   `sys:vital_status` and `sys:status`; the code's schema version is v2.26
+   or later.
+EF2 -- the writer (fixture). `write_event_type` writes « Ouvrir » (Cible ->
+   Ouvert = oui, a choice), « Usurper » (Trône -> Occupé par = the
+   Usurpateur's entity, a role), « Alerter » (Garnison -> Alerte = 3 set and
+   « Être repéré » Garnison -> Alerte + 1 added) and « Tuer » (Victime ->
+   État vital = mort, a system state); `type_view` reads each effect back
+   with its role, state, mode, kind and value, in order. Refused, each with
+   no row written: an unknown state, `Magie` (a system state no event
+   changes), a role that holds only sortes, a state that applies to no
+   entity type the role accepts, a value that is not one of the state's
+   choices, `add` on a choice, a text for an integer, an entity state naming
+   the same role, an unknown role or a role whose entities the state may
+   not name, one role and state twice, nine effects.
+EF3 -- replaced whole, and what an effect holds (fixture). « Ouvrir » saved
+   with no effect keeps no `event_type_effect` row. While an effect names
+   « Ouvert », retiring it, changing its kind, or dropping its choice
+   « oui » is refused; once the effect is gone, retiring works.
+EF4 -- a change names its event (fixture). `write_attribute_value` with an
+   `event_id` and the kind `correction` is refused, nothing written; with
+   `changement` it stores the event on its `attribute_change` row.
+EF5 -- migration `scripts/migrate_v2_26_event_effects.py`, on a v2.25
+   database (`attribute_change` and `lore_entry_row` in their v2.25 DDL,
+   frozen below, one row each; no `event_type_effect`): at v2.24 it refuses
+   and changes nothing; at v2.25 it creates the table, adds the column and
+   index, rebuilds `lore_entry_row` (its CHECK naming `event`), keeps both
+   rows, and sets `schema_meta` to v2.26; a second run writes nothing.
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import os
+import pathlib
+import sqlite3
+import subprocess
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+MIGRATION = ROOT / "scripts" / "migrate_v2_26_event_effects.py"
+
+FAILURES: list[str] = []
+
+COLUMNS = ("id", "world_id", "type_id", "role_id", "definition_id", "system_key", "mode", "choice_id",
+           "system_value", "integer_value", "value_role_id", "position")
+CHECKS = ("ck_event_type_effect_add", "ck_event_type_effect_mode", "ck_event_type_effect_state",
+          "ck_event_type_effect_value")
+INDEXES = ("idx_event_type_effect_definition", "idx_event_type_effect_type")
+
+# The two tables v2.26 changes, as v2.25 declared them (frozen: EF5 builds
+# the database the migration was written for).
+V2_25_DDL: tuple[str, ...] = (
+    "CREATE TABLE attribute_change (id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, value_id VARCHAR NOT NULL, "
+    "kind VARCHAR NOT NULL, changed_by VARCHAR NOT NULL, before_choice_id VARCHAR, before_integer INTEGER, "
+    "before_entity_id VARCHAR, after_choice_id VARCHAR, after_integer INTEGER, after_entity_id VARCHAR, "
+    "changed_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (id), "
+    "CONSTRAINT ck_attribute_change_kind CHECK (kind IN ('correction','changement')), "
+    "FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(value_id) REFERENCES attribute_value (id), "
+    "FOREIGN KEY(before_choice_id) REFERENCES attribute_choice (id), "
+    "FOREIGN KEY(before_entity_id) REFERENCES entity (id), "
+    "FOREIGN KEY(after_choice_id) REFERENCES attribute_choice (id), "
+    "FOREIGN KEY(after_entity_id) REFERENCES entity (id))",
+    "CREATE INDEX idx_attribute_change_value ON attribute_change (value_id, changed_at)",
+    "CREATE TABLE lore_entry_row (id VARCHAR NOT NULL, entry_id VARCHAR NOT NULL, row_table VARCHAR NOT NULL, "
+    "row_id VARCHAR NOT NULL, action VARCHAR NOT NULL, PRIMARY KEY (id), "
+    "CONSTRAINT ck_lore_entry_row_table CHECK (row_table IN ('entity','fact','fact_participant','fact_default',"
+    "'knowledge','relation','faction_membership')), "
+    "CONSTRAINT ck_lore_entry_row_action CHECK (action IN ('created','updated')), "
+    "FOREIGN KEY(entry_id) REFERENCES lore_entry (id))",
+    "CREATE UNIQUE INDEX idx_lore_entry_row_entry ON lore_entry_row (entry_id, row_table, row_id)",
+)
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
+# --- EF1 -------------------------------------------------------------------------
+
+def check_ef1() -> None:
+    import re
+
+    from sqlalchemy import JSON, CheckConstraint
+    from sqlmodel import SQLModel
+
+    from world_engine import models
+    from world_engine.attributes import SYSTEM_ATTRIBUTES
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+    from world_engine.writes.event_types import EFFECT_SYSTEM_KEYS
+
+    table = SQLModel.metadata.tables.get("event_type_effect")
+    if table is None:
+        fail("EF1: event_type_effect is not declared")
+        return
+    if tuple(table.c.keys()) != COLUMNS:
+        fail(f"EF1: event_type_effect columns are {tuple(table.c.keys())}")
+    checks = {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
+    if tuple(sorted(checks)) != CHECKS:
+        fail(f"EF1: event_type_effect CHECKs are {sorted(checks)}")
+    if tuple(sorted(i.name for i in table.indexes)) != INDEXES:
+        fail(f"EF1: event_type_effect indexes are {sorted(i.name for i in table.indexes)}")
+    if any(isinstance(c.type, JSON) for c in table.c):
+        fail("EF1: event_type_effect has a JSON column")
+    modes = tuple(re.findall(r"'([^']+)'", checks.get("ck_event_type_effect_mode", "")))
+    if modes != tuple(models.EVENT_EFFECT_MODES) or modes != ("set", "add"):
+        fail(f"EF1: the mode CHECK names {modes}, EVENT_EFFECT_MODES {models.EVENT_EFFECT_MODES}")
+    change = SQLModel.metadata.tables["attribute_change"]
+    if "event_id" not in change.c or "idx_attribute_change_event" not in {i.name for i in change.indexes}:
+        fail("EF1: attribute_change has no event_id or no idx_attribute_change_event")
+    system = {s.key for s in SYSTEM_ATTRIBUTES}
+    if tuple(EFFECT_SYSTEM_KEYS) != ("sys:vital_status", "sys:status") or not set(EFFECT_SYSTEM_KEYS) <= system:
+        fail(f"EF1: EFFECT_SYSTEM_KEYS is {EFFECT_SYSTEM_KEYS}")
+    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < (2, 26):
+        fail(f"EF1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")
+
+
+# --- fixture -----------------------------------------------------------------------
+
+def _fixture(engine) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.models import Character, Entity, Faction, Location, World
+    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition
+
+    with Session(engine) as db:
+        world = World(name="Effets", is_active=False)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind, name in (("brakk", "character", "Brakk"), ("ysa", "character", "Ysa"),
+                                ("porte", "location", "Porte"), ("guilde", "faction", "Guilde")):
+            entity = Entity(world_id=world.id, type=kind, name=name)
+            db.add(entity)
+            db.flush()
+            ids[key] = entity.id
+            if kind == "character":
+                db.add(Character(id=entity.id, world_id=world.id, character_type="npc"))
+            elif kind == "location":
+                db.add(Location(id=entity.id))
+            else:
+                db.add(Faction(id=entity.id))
+        ouvert = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
+            name="Ouvert", kind="choice", holder_types=("location", "item"),
+            choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non"))
+        occupe = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
+            name="Occupé par", kind="entity", holder_types=("item", "location"), value_types=("character",)))
+        alerte = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
+            name="Alerte", kind="integer", holder_types=("faction",), default=0))
+        db.commit()
+        from world_engine.attributes import attribute_view
+
+        ids.update(ouvert=ouvert.id, occupe=occupe.id, alerte=alerte.id,
+                   oui=dict((label, key) for key, label in attribute_view(db, world.id, ouvert.id).choices)["oui"],
+                   non=dict((label, key) for key, label in attribute_view(db, world.id, ouvert.id).choices)["non"])
+    return ids
+
+
+def _counts(db) -> tuple[int, ...]:
+    from sqlmodel import func, select
+
+    from world_engine import models
+
+    return tuple(db.exec(select(func.count()).select_from(m)).one() for m in (
+        models.EventType, models.EventTypeRole, models.EventTypeEffect))
+
+
+def _refused(db, label: str, rule: str, call) -> None:
+    before = _counts(db)
+    try:
+        call()
+    except ValueError:
+        db.rollback()
+        if _counts(db) != before:
+            fail(f"{rule}: {label} was refused but wrote rows")
+        return
+    db.rollback()
+    fail(f"{rule}: {label} was not refused")
+
+
+def _role(name, types=("character",), sorte=False):
+    from world_engine.writes.event_types import RoleSpec
+
+    return RoleSpec(name=name, entity_types=types, accepts_sorte=sorte)
+
+
+def _effect(role, attribute, value, mode="set"):
+    from world_engine.writes.event_types import EffectSpec
+
+    return EffectSpec(role=role, attribute=attribute, value=value, mode=mode)
+
+
+def _type(name, roles, effects):
+    from world_engine.writes.event_types import EventTypeSpec
+
+    return EventTypeSpec(name=name, roles=tuple(roles), effects=tuple(effects))
+
+
+def check_ef2(engine, ids: dict) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.event_vocab import type_view
+    from world_engine.writes.event_types import write_event_type
+
+    w = ids["world"]
+    specs = {
+        "ouvrir": _type("Ouvrir", [_role("Ouvreur"), _role("Cible", ("location", "item"))],
+                        [_effect("Cible", ids["ouvert"], ids["oui"])]),
+        "usurper": _type("Usurper", [_role("Usurpateur"), _role("Trône", ("item", "location"))],
+                         [_effect("Trône", ids["occupe"], "Usurpateur")]),
+        "alerter": _type("Alerter", [_role("Garnison", ("faction",))],
+                         [_effect("Garnison", ids["alerte"], 3)]),
+        "reperer": _type("Être repéré", [_role("Intrus"), _role("Garnison", ("faction",))],
+                         [_effect("Garnison", ids["alerte"], 1, "add")]),
+        "tuer": _type("Tuer", [_role("Tueur"), _role("Victime", ("character",), sorte=True)],
+                      [_effect("Victime", "sys:vital_status", "dead")]),
+    }
+    made: dict[str, str] = {}
+    with Session(engine) as db:
+        for key, spec in specs.items():
+            made[key] = write_event_type(db, world_id=w, spec=spec).id
+        db.commit()
+        got = {}
+        for key, type_id in made.items():
+            view = type_view(db, type_id)
+            names = {r.id: r.name for r in view.roles}
+            got[key] = [(names[e.role_id], e.attribute, e.mode, e.value_kind,
+                         names.get(e.value, e.value) if e.value_kind == "role" else e.value) for e in view.effects]
+    want = {
+        "ouvrir": [("Cible", ids["ouvert"], "set", "choice", ids["oui"])],
+        "usurper": [("Trône", ids["occupe"], "set", "role", "Usurpateur")],
+        "alerter": [("Garnison", ids["alerte"], "set", "integer", 3)],
+        "reperer": [("Garnison", ids["alerte"], "add", "integer", 1)],
+        "tuer": [("Victime", "sys:vital_status", "set", "choice", "dead")],
+    }
+    if got != want:
+        fail(f"EF2: the effects read back are {got}")
+    cible = [_role("Ouvreur"), _role("Cible", ("location", "item"))]
+    refused = (
+        ("an unknown state", _type("X1", cible, [_effect("Cible", "nope", "oui")])),
+        ("Magie", _type("X2", cible, [_effect("Cible", "sys:magic_status", "active")])),
+        ("a sorte-only role", _type("X3", [_role("Proie", (), sorte=True)],
+                                    [_effect("Proie", "sys:vital_status", "dead")])),
+        ("a state for no type of the role", _type("X4", [_role("Qui")], [_effect("Qui", ids["ouvert"], ids["oui"])])),
+        ("a value not a choice", _type("X5", cible, [_effect("Cible", ids["ouvert"], "peut-être")])),
+        ("add on a choice", _type("X6", cible, [_effect("Cible", ids["ouvert"], ids["oui"], "add")])),
+        ("a text for an integer", _type("X7", [_role("G", ("faction",))], [_effect("G", ids["alerte"], "3")])),
+        ("the same role as value", _type("X8", [_role("U"), _role("T", ("item",))], [_effect("T", ids["occupe"], "T")])),
+        ("an unknown value role", _type("X9", [_role("U"), _role("T", ("item",))],
+                                        [_effect("T", ids["occupe"], "Personne")])),
+        ("a value role the state may not name", _type("X10", [_role("U", ("faction",)), _role("T", ("item",))],
+                                                      [_effect("T", ids["occupe"], "U")])),
+        ("one role and state twice", _type("X11", cible, [_effect("Cible", ids["ouvert"], ids["oui"]),
+                                                          _effect("Cible", ids["ouvert"], ids["non"])])),
+        ("nine effects", _type("X12", [_role(f"R{i}", ("location",)) for i in range(8)] + [_role("R8", ("location",))],
+                               [_effect(f"R{i}", ids["ouvert"], ids["oui"]) for i in range(9)])),
+    )
+    with Session(engine) as db:
+        for label, spec in refused:
+            _refused(db, label, "EF2", lambda spec=spec: write_event_type(db, world_id=w, spec=spec))
+    return made
+
+
+def check_ef3(engine, ids: dict, made: dict) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.models import EventTypeEffect
+    from world_engine.writes.attributes import (
+        ChoiceSpec,
+        DefinitionSpec,
+        set_attribute_status,
+        write_attribute_definition,
+    )
+    from world_engine.writes.event_types import write_event_type
+
+    w = ids["world"]
+    with Session(engine) as db:
+        _refused(db, "retiring a state an effect names", "EF3",
+                 lambda: set_attribute_status(db, world_id=w, definition_id=ids["ouvert"], status="retired"))
+        _refused(db, "changing its kind", "EF3", lambda: write_attribute_definition(
+            db, world_id=w, definition_id=ids["ouvert"], spec=DefinitionSpec(
+                name="Ouvert", kind="integer", holder_types=("location", "item"), default=0)))
+        _refused(db, "dropping the choice an effect names", "EF3", lambda: write_attribute_definition(
+            db, world_id=w, definition_id=ids["ouvert"], spec=DefinitionSpec(
+                name="Ouvert", kind="choice", holder_types=("location", "item"),
+                choices=(ChoiceSpec("non", ids["non"]), ChoiceSpec("fermé")), default="non")))
+        write_event_type(db, world_id=w, type_id=made["ouvrir"], spec=_type(
+            "Ouvrir", [_role("Ouvreur"), _role("Cible", ("location", "item"))], []))
+        db.commit()
+        left = db.exec(select(EventTypeEffect).where(EventTypeEffect.type_id == made["ouvrir"])).all()
+        if left:
+            fail(f"EF3: « Ouvrir » saved with no effect keeps {len(left)} effect row(s)")
+        try:
+            set_attribute_status(db, world_id=w, definition_id=ids["ouvert"], status="retired")
+            db.commit()
+        except ValueError as exc:
+            db.rollback()
+            fail(f"EF3: once no effect names « Ouvert », retiring it is refused: {exc}")
+
+
+def check_ef4(engine, ids: dict) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.models import AttributeChange, Event
+    from world_engine.writes.attributes import set_attribute_status, write_attribute_value
+    from world_engine.writes.event_types import ensure_domain_type
+
+    w = ids["world"]
+    with Session(engine) as db:
+        set_attribute_status(db, world_id=w, definition_id=ids["ouvert"], status="active")
+        event = Event(world_id=w, type_id=ensure_domain_type(db, world_id=w, domain="other").id, title="t")
+        db.add(event)
+        db.commit()
+        before = len(db.exec(select(AttributeChange)).all())
+        try:
+            write_attribute_value(db, world_id=w, definition_id=ids["ouvert"], entity_id=ids["porte"],
+                                  value=ids["oui"], kind="correction", changed_by="check", event_id=event.id)
+            fail("EF4: a correction naming an event was not refused")
+        except ValueError:
+            db.rollback()
+        if len(db.exec(select(AttributeChange)).all()) != before:
+            fail("EF4: the refused correction wrote a change")
+        change = write_attribute_value(db, world_id=w, definition_id=ids["ouvert"], entity_id=ids["porte"],
+                                       value=ids["oui"], kind="changement", changed_by="check", event_id=event.id)
+        db.commit()
+        if change is None or db.get(AttributeChange, change.id).event_id != event.id:
+            fail("EF4: a changement does not keep its event")
+
+
+# --- EF5 -------------------------------------------------------------------------
+
+def _v2_25_db() -> str:
+    """A database the migration was written for: every table of the code
+    but `event_type_effect` and the two it changes, those in v2.25 DDL."""
+    from sqlalchemy import create_engine
+    from sqlmodel import SQLModel
+
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "migrate.db")
+    eng = create_engine(f"sqlite:///{db_path}")
+    skipped = {"event_type_effect", "attribute_change", "lore_entry_row"}
+    SQLModel.metadata.create_all(eng, tables=[t for n, t in SQLModel.metadata.tables.items() if n not in skipped])
+    eng.dispose()
+    with sqlite3.connect(db_path) as conn:
+        for statement in V2_25_DDL:
+            conn.execute(statement)
+        conn.executescript("""
+            INSERT INTO schema_meta (id, static_version, updated_at) VALUES (1, 'v2.24', '2026-10-01');
+            INSERT INTO world (id, name, is_active, created_at, updated_at) VALUES ('w', 'W', 0, '2026-10-01', '2026-10-01');
+            INSERT INTO entity (id, world_id, type, name, status, created_at, updated_at)
+              VALUES ('a', 'w', 'location', 'A', 'active', '2026-10-01', '2026-10-01');
+            INSERT INTO attribute_definition (id, world_id, name, kind, is_hidden, status, created_at, updated_at)
+              VALUES ('d', 'w', 'Ouvert', 'integer', 0, 'active', '2026-10-01', '2026-10-01');
+            INSERT INTO attribute_value (id, world_id, definition_id, entity_id, integer_value, updated_at)
+              VALUES ('v', 'w', 'd', 'a', 1, '2026-10-01');
+            INSERT INTO attribute_change (id, world_id, value_id, kind, changed_by, after_integer, changed_at)
+              VALUES ('c', 'w', 'v', 'correction', 'creator', 1, '2026-10-01');
+            INSERT INTO lore_entry (id, world_id, statement, created_at) VALUES ('le', 'w', 's', '2026-10-01');
+            INSERT INTO lore_entry_row (id, entry_id, row_table, row_id, action)
+              VALUES ('r', 'le', 'entity', 'a', 'created');
+        """)
+    return db_path
+
+
+def _run_migration(db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True, text=True,
+                          cwd=str(ROOT), timeout=120)
+
+
+def _snapshot(db_path: str) -> dict:
+    with sqlite3.connect(db_path) as conn:
+        def sql(name: str) -> str:
+            row = conn.execute("SELECT sql FROM sqlite_master WHERE name = ?", (name,)).fetchone()
+            return row[0] if row else ""
+        return {
+            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
+            "effect": bool(sql("event_type_effect")),
+            "event_id": "event_id" in [r[1] for r in conn.execute("PRAGMA table_info(attribute_change)")],
+            "index": bool(sql("idx_attribute_change_event")),
+            "lore_check": "'event'" in sql("lore_entry_row"),
+            "rows": (conn.execute("SELECT id, after_integer FROM attribute_change").fetchall(),
+                     conn.execute("SELECT id, row_table FROM lore_entry_row").fetchall()),
+        }
+
+
+def check_ef5() -> None:
+    db_path = _v2_25_db()
+    before = _snapshot(db_path)
+    refused = _run_migration(db_path)
+    if refused.returncode == 0 or _snapshot(db_path) != before:
+        fail(f"EF5: v2.24 was not refused untouched (exit {refused.returncode})")
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.25' WHERE id = 1")
+    result = _run_migration(db_path)
+    after = _snapshot(db_path)
+    want = {"version": "v2.26", "effect": True, "event_id": True, "index": True, "lore_check": True,
+            "rows": ([("c", 1)], [("r", "entity")])}
+    if result.returncode != 0 or after != want:
+        fail(f"EF5: exit {result.returncode}, state {after}: {result.stderr.strip()[-300:]}")
+    again = _run_migration(db_path)
+    if again.returncode != 0 or "already fully applied" not in again.stdout or _snapshot(db_path) != after:
+        fail(f"EF5: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    ids = _fixture(engine)
+    state: dict = {}
+
+    def ef2() -> None:
+        state["made"] = check_ef2(engine, ids)
+
+    rules = (
+        ("EF1", check_ef1), ("EF2", ef2), ("EF3", lambda: check_ef3(engine, ids, state["made"])),
+        ("EF4", lambda: check_ef4(engine, ids)), ("EF5", check_ef5),
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
+    print("PASS: event_effects -- v2.26 keeps what an event type does to the state of the world: the role whose "
+          "entity changes, the state, and a value of its kind; a state an effect names is never taken away, and "
+          "a change keeps the event that made it")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/single_canon_write.py b/tooling/verify/checks/single_canon_write.py
index 7b46125..889e78c 100644
--- a/tooling/verify/checks/single_canon_write.py
+++ b/tooling/verify/checks/single_canon_write.py
@@ -86,6 +86,8 @@ single-row correction): `write_npc_prices`, `write_world_laws`,
 attribute definition's entity types) and `writes/event_types.py::_write_roles`
 / `_write_scopes` (TICKET-0114, BRIEF-0114-A: a role's entity types, an
 event type's scopes -- never a role itself, retired instead) and
+`writes/event_types.py::_write_effects` (TICKET-0119, BRIEF-0119-A: an
+event type's effects, which only pre-fill a proposal) and
 `writes/events.py::_write_scopes` (TICKET-0114, BRIEF-0114-C: an event's
 fact's scopes, from the journal or an approved proposal) each
 `DELETE FROM` their table(s) scoped to one parent (NPC / world / location /
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index cb0023d..bf09242 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -131,6 +131,9 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
     ("event_type_role_type", {"id": "etrt-{w}", "world_id": "{w}", "role_id": "etr-{w}",
                               "entity_type": "character"}),
     ("event_type_scope", {"id": "ets-{w}", "world_id": "{w}", "type_id": "et-{w}", "scope_kind": "world"}),
+    # TICKET-0119 (BRIEF-0119-A): an effect of the type -- the role's entity destroyed.
+    ("event_type_effect", {"id": "ete-{w}", "world_id": "{w}", "type_id": "et-{w}", "role_id": "etr-{w}",
+                           "system_key": "sys:status", "system_value": "destroyed"}),
     ("event", {"id": "ev-{w}", "world_id": "{w}", "title": "t", "type_id": "et-{w}"}),
     ("event_sorte", {"id": "eso-{w}", "world_id": "{w}", "name": "loup"}),
     ("event_participant", {"id": "ep-{w}", "world_id": "{w}", "event_id": "ev-{w}", "role_id": "etr-{w}",
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index b164cfe..e71497f 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,16 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.26** — TICKET-0119, BRIEF-0119-A: what an event does to the state of
+  the world. `event_type_effect` (an event type's effects: the role whose
+  entity changes, the state -- a world's definition, or `État vital` /
+  `Statut` --, and the value it takes: a choice, an integer set or added, or
+  the entity of another role; they pre-fill an event's proposal).
+  `attribute_change` gains `event_id` (the event that made a change) and
+  `idx_attribute_change_event`. `lore_entry_row` is rebuilt, its
+  `row_table` CHECK gaining `event`, `event_participant`, `attribute_value`
+  and `attribute_change`. `migrate_v2_26_event_effects.py` writes no data,
+  refuses a database older than v2.25, and moves `schema_meta` to v2.26.
 - **v2.25** — TICKET-0114, BRIEF-0114-D: the journal drops what it no
   longer reads. `event` is rebuilt without `type` (a type's `domain` now),
   `knowledge_status` (who knows an event is its fact's knowledge and
diff --git a/world-engine-schema.md b/world-engine-schema.md
index 401171a..b496a05 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.25
+Current schema version: v2.26
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -1183,7 +1183,8 @@ CREATE INDEX idx_lore_entry_world ON lore_entry(world_id, created_at);
 One row per canon row a `lore_entry` commit created or updated (schema v2.11,
 TICKET-0098, BRIEF-0098-B, M1), so a story can be reread with everything it
 produced. `row_id` carries no FK: it points into the table `row_table` names.
-`updated` marks a `bloc` fact rewritten in place. Append-only; the bulk undo
+`updated` marks a `bloc` fact rewritten in place, or a state an event Lore
+declared changed (`attribute_value`, v2.26, TICKET-0119). Append-only; the bulk undo
 of an entry is a later ticket (M2).
 
 ```sql
@@ -1191,7 +1192,8 @@ CREATE TABLE lore_entry_row (
   id         TEXT PRIMARY KEY,
   entry_id   TEXT NOT NULL REFERENCES lore_entry(id),
   row_table  TEXT NOT NULL CHECK (row_table IN ('entity','fact','fact_participant',
-               'fact_default','knowledge','relation','faction_membership')),
+               'fact_default','knowledge','relation','faction_membership','event',
+               'event_participant','attribute_value','attribute_change')),
   row_id     TEXT NOT NULL,
   action     TEXT NOT NULL CHECK (action IN ('created','updated'))
 );
@@ -1790,6 +1792,46 @@ CREATE UNIQUE INDEX idx_event_participant_unique_sorte
 
 -----
 
+### `event_type_effect`
+
+What an event of the type does to the state of the world (M-c, schema
+v2.26, TICKET-0119): the entity in `role_id` takes, for the state
+`definition_id` (one of the world's) or `system_key` (`sys:vital_status`,
+`sys:status` -- E1; `Magie` stays the creator's), exactly one value:
+`choice_id` (a definition's choice), `system_value` (a system state's stored
+value), `integer_value` (set, or added when `mode` is `add`, D3), or the
+entity of the role `value_role_id` (« Occupé par = l'Usurpateur »). Which
+value fits the state's kind is `writes/event_types.py`'s rule. An effect only
+PRE-FILLS the changes of an event's proposal, which the creator keeps, edits
+or drops; nothing holds it, so a type's effects are replaced whole. A
+definition an effect names is not retired, its kind does not change, and a
+choice it names stays (`writes/attributes.py`).
+
+```sql
+CREATE TABLE event_type_effect (
+  id             TEXT PRIMARY KEY,
+  world_id       TEXT NOT NULL REFERENCES world(id),
+  type_id        TEXT NOT NULL REFERENCES event_type(id),
+  role_id        TEXT NOT NULL REFERENCES event_type_role(id),
+  definition_id  TEXT REFERENCES attribute_definition(id),
+  system_key     TEXT,
+  mode           TEXT NOT NULL DEFAULT 'set' CHECK (mode IN ('set','add')),
+  choice_id      TEXT REFERENCES attribute_choice(id),
+  system_value   TEXT,
+  integer_value  INTEGER,
+  value_role_id  TEXT REFERENCES event_type_role(id),
+  position       INTEGER NOT NULL DEFAULT 0,
+  CHECK ((definition_id IS NOT NULL) + (system_key IS NOT NULL) = 1),
+  CHECK ((choice_id IS NOT NULL) + (system_value IS NOT NULL) + (integer_value IS NOT NULL)
+         + (value_role_id IS NOT NULL) = 1),
+  CHECK (mode = 'set' OR integer_value IS NOT NULL)
+);
+CREATE INDEX idx_event_type_effect_type ON event_type_effect(type_id, position);
+CREATE INDEX idx_event_type_effect_definition ON event_type_effect(definition_id);
+```
+
+-----
+
 ### `artifact`
 
 Magical or historically significant objects.
@@ -2890,8 +2932,8 @@ The history of a value (WD1), append-only -- the rows ARE the history, no
 the entity held none) and after, in the columns of its kind; `kind` is
 `correction` (it was always so) or `changement` (the world changed), the
 vocabulary of `writes.facts.FACT_CHANGE_KINDS`, chosen by the creator at
-each write; `changed_by` who made it. TICKET-0114's events will append here
-too.
+each write; `changed_by` who made it; `event_id` the event that made a
+`changement` (M-c, v2.26, TICKET-0119), NULL for the creator's own edit.
 
 ```sql
 CREATE TABLE attribute_change (
@@ -2906,9 +2948,11 @@ CREATE TABLE attribute_change (
   after_choice_id   TEXT REFERENCES attribute_choice(id),
   after_integer     INTEGER,
   after_entity_id   TEXT REFERENCES entity(id),
-  changed_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
+  changed_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
+  event_id          TEXT REFERENCES event(id)
 );
 CREATE INDEX idx_attribute_change_value ON attribute_change(value_id, changed_at);
+CREATE INDEX idx_attribute_change_event ON attribute_change(event_id);
 ```
 
 -----
````

2. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
3. Run the checks below, then the full corpus.

## Scope OUT

- Making an effect concrete on an event, writing a change, the vital state's writer -- BRIEF-0119-C.
- Editing effects in « Vocabulaire du monde », the routes' `effects` and `states` -- BRIEF-0119-B.
- An effect on a sorte (a sorte-only role takes none): carried forward in the ticket.
- A history table for the vital state and the status (E): carried forward.
- Every later brief of this lot: BRIEF-0119-B, C, D, E, F, G.

## Invariants to defend

INV-20: `event_type_effect` is relational; no column is JSON (EF1). INV-08/INV-12: `_write_effects` writes through `writes/` and its full-replace delete is named in `single_canon_write.py`'s list. INV-60: the code's version, the doc header and the migration's `schema_meta` move together to v2.26 (`schema_version_agreement.py`). INV-10: `attribute_change` stays append-only; `event_id` is set once, at insert.

## Decision rights

STOP:
- The migration's post-check fails on a database: it aborts before `schema_meta` moves -- report its message, never edit the migration to pass.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- Log lines a check prints before its verdict (`[skip] …`, a Starlette deprecation warning).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`.
- `python tooling/verify/checks/event_effects.py` -> `PASS`.
- `python tooling/verify/checks/attributes.py` -> `PASS`.
- `python tooling/verify/checks/world_cascade.py` -> `PASS`.
- `python tooling/verify/checks/single_canon_write.py` -> `PASS`.
- `python tooling/verify/checks/lore_write.py` -> `PASS`.
- `python tooling/verify/checks/event_journal.py` -> `PASS`.
- `python tooling/verify/checks/schema_version_agreement.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (157 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EF1** -- `models/canon_event.py`: `EVENT_EFFECT_MODES: tuple[str, ...] = ("set", "add")` -> `EVENT_EFFECT_MODES: tuple[str, ...] = ("set",)`
  - **EF2** -- `writes/event_types.py _effect_state`: `if view.system and view.key not in EFFECT_SYSTEM_KEYS:` -> `if False:`
  - **EF3** -- `writes/attributes.py set_attribute_status`: `if status == "retired" and _effects(db, definition_id):` -> `if False:`
  - **EF4** -- `writes/attributes.py write_attribute_value`: `if event_id is not None and kind != "changement":` -> `if False:`
  - **EF5** -- `scripts/migrate_v2_26_event_effects.py _plan`: `"lore_entry_row": "'attribute_change'" not in _table_sql("lore_entry_row"),` -> `"lore_entry_row": False,`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

Schema v2.26: `world-engine-schema.md` header and tables, the changelog entry, `schema_version.py` (in the diff); ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
