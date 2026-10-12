<!-- slug: journal-readers -->
# BRIEF 0114-D — "The models read the journal by what is known, and the MJ sees the states a player may see -- v2.25 drops what nobody reads"

Lot: LOT-0114-event-journal.md (authoritative on conflict)
Depends on: BRIEF-0114-C (C-05)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0114-C's commit).

- `src/world_engine/context.py` -> `def _mj_context_public_events(world_id: str | None, location_id: str, db: Session) -> list[dict]:`
- `src/world_engine/cockpit/play_physical.py` -> `def _compute_return_delta(`
- `src/world_engine/tick_context.py:622` and `:725` -> `Event.knowledge_status.in_(("public", "confirmed")),`
- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.24"`
- `scripts/migrate_v2_24_event_journal.py` -> `def _backfill(cursor)`
- No `src/world_engine/event_reads.py`, no `scripts/migrate_v2_25_event_columns.py`.

## Facts carried

### R-01 — `event` and `event_entity` [M]
Opened: `src/world_engine/models/canon.py:479` (`Event`: `session_id`,
`batch_id`, `title`, `description`, `type` free text, `knowledge_status`
default `'secret'`, `location_id`, `has_magic_impact`, `consequences`
JSON, `occurred_at`, `recorded_at`; one index `idx_event_world`), `:510`
(`EventEntity`: `event_id`, `entity_id`, unique `idx_event_entity_unique`).
Consequence: A adds `type_id` and `quantity` (nullable at v2.24, so the
migration can fill them); D rebuilds `event` without `type`,
`knowledge_status`, `has_magic_impact`, `consequences`, `occurred_at`,
`type_id` NOT NULL, and drops `event_entity` once every link has its
`event_participant` twin.

### R-02 — production holds four events, none with a fact [M]
Measured by Nia on her database (2026-10-11): four events -- `military`,
`other`, `political` with `knowledge_status = 'secret'`, `social` with
`'public'` --; each carries `consequences` = the JSON `null` (never SQL
NULL), no `has_magic_impact`, no `occurred_at`; zero `fact` rows with an
`event_id`.
Consequence: N1 (the type required) types them by their category, which
the migration makes as « Militaire », « Autre », « Politique »,
« Social », each with one role « Impliqué »; O1: the public one gets a
`world` scope at `knows`, the secret ones none. Nothing in the dropped
columns is lost (L1).

### R-05 — facts, their defaults and who knows them
Opened: `src/world_engine/models/canon_knowledge.py:87` (`Fact`, `:107`
`event_id`, at most one owner, `idx_fact_event`), `:164` (`FactDefault`:
`scope_type IN ('world','faction','location','rencontre')`, `scope_id`
NULL for `world`), `:199` (`Knowledge`); `src/world_engine/facets.py:79`
(facet `evenement`, monde, typed); `src/world_engine/writes/facts.py:75`
(`create_fact`), `:163` (`update_typed_fact_content`, kind `correction`),
`:204` (`create_fact_default`); `src/world_engine/knowledge_resolve.py:253`
(`resolve_known_for_entity`, 0105: own rows, then scopes in contact);
`src/world_engine/writes/knowledge.py:72` (`KNOWLEDGE_LEVEL_LADDER`).
Consequence: an event's fact is facet `evenement`, its text « title —
description »; a type's scopes are written as `fact_default` rows; the
models read through `resolve_known_for_entity` (Q1); a scope's level is
on the ladder, never `unaware`.

### R-06 — who reads `knowledge_status` [M]
Opened: `src/world_engine/context.py:701` (`_mj_context_public_events`,
`:709` filters `public`/`confirmed`), `src/world_engine/tick_context.py:622`
and `:725` (location and faction briefings),
`src/world_engine/cockpit/play_physical.py:601` (`_compute_return_delta`,
its filter at `:661`); `tooling/verify/checks/visit_delta.py` (its rule 2
pins the return delta's query).
Consequence: D replaces each with `event_reads` (C-07) and retargets
`visit_delta.py` rule 2; ED4 forbids any reader of the dropped columns.
The tick still WRITES the untyped shape (`tick_normalize.py:447-481`,
`knowledge_status` in its payload): C-06 reads it; its typed producer is
TICKET-0119.

### R-14 — fifteen seconds per check [M]
Opened: `tooling/verify/checks/corpus_gate.py` (per-check subprocess,
timeout a failure), `.claude/rules/verify-checks.md`.
Consequence: six checks, each measured on the replay: `event_journal.py`
4.8 s, `event_writes.py` 1.9 s, `event_contexts.py` 6.3 s,
`event_conditions.py` 1.4 s, `event_interpreter.py` 4.1 s,
`event_analyzer.py` 6.7 s.

## Contracts

### C-05 — `writes.events` (the journal's one writer)
Produced by: BRIEF-0114-C   Consumed by: D, E, H
`ParticipantSpec(role_id, entity_id=None, sorte_id=None, secret=None)`,
`EventScopeSpec(scope_type, scope_id, level)`, `EventSpec(type_id, title,
description=None, location_id=None, quantity=None, participants=(),
scopes=None (the type's), session_id=None, batch_id=None)`;
`event_fact_text(title, description) -> str` (« title — description »);
`clean_event(db, world_id, spec, event=None)`; `write_event(db, *,
world_id, spec, created_by) -> Event` (the event, its participants, ONE
fact `evenement`, the scopes, each participant entity's knowledge at
`knows`, secret as said, never for a player character); `event_fact(db,
event_id)`; `write_event_update(db, *, event, spec, changed_by)` (type
and participants kept; participants added; text rewritten as a
`correction`; scopes replaced whole).

### C-07 — `event_reads` and WL1
Produced by: BRIEF-0114-D   Consumed by: E
`known_chronicle_events(db, knower_id, world_id, *, location_id=None,
since=None) -> list[Event]` (newest first, `in_chronicle` types only,
through `resolve_known_for_entity`); `public_chronicle_events(db,
world_id, *, location_id=None, participant_id=None, limit=None)` (a
`world` scope on the fact); `attributes.perceived_states(db, world_id,
entity) -> str` (« Ouvert : oui · … », non-hidden, non-system).

## Context

Q1: who knows an event is its fact's knowledge and scopes, so the models read the journal by what is KNOWN -- Play's MJ the chronicle events the player knows (0105's resolver), the tick what everyone knows; only an `in_chronicle` type is told to a model. WL1 (0113's carried point): the MJ reads the states a player may see. Then v2.25 drops the five columns and `event_entity` (L1, V1), after typing anything left untyped exactly as v2.24 does.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `event_reads.py` (new, C-07); `context.py` (`_mj_context_public_events(world_id, location_id, player_id, db)`, the location's `states`, « États : … » in `format_mj_context`), `context_describe.py` (each co-present's `states`), `cockpit/play_physical.py` `_compute_return_delta`, `tick_context.py` (location and faction briefings) read through it;
   - `attributes.perceived_states` (C-07): visible, non-system, none when blindfolded;
   - `models/canon.py`: `Event` without the five columns, `type_id` required, `ck_event_quantity`, `idx_event_type`; `EventEntity` removed everywhere -- `models/__init__.py`, the `cockpit/crud/*.py` and `cockpit/routes/mutations.py` imports, the world cascade (`writes/worlds.py`, `checks/world_cascade.py`);
   - `scripts/migrate_v2_25_event_columns.py` (new): imports v2.24's `_backfill`, refuses below v2.24 or when a link has no participant twin, rebuilds `event`, drops `event_entity`, post-checks, `schema_meta` -> v2.25; `schema_version.py`, the schema doc and changelog;
   - `checks/json_ui_boundary.py` allowlist (`event.consequences` gone), `checks/visit_delta.py` rule 2, `checks/event_tab.py`, the `checks/fact_facets.py` fixture follow; creates check `event_contexts.py` (ED1-ED4);
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - scripts/migrate_v2_25_event_columns.py
   - src/world_engine/attributes.py
   - src/world_engine/cockpit/crud/agendas.py
   - src/world_engine/cockpit/crud/entities.py
   - src/world_engine/cockpit/crud/factions.py
   - src/world_engine/cockpit/crud/goals.py
   - src/world_engine/cockpit/crud/knowledge.py
   - src/world_engine/cockpit/crud/ledger.py
   - src/world_engine/cockpit/crud/locations.py
   - src/world_engine/cockpit/crud/prompts.py
   - src/world_engine/cockpit/crud/relations.py
   - src/world_engine/cockpit/crud/skills.py
   - src/world_engine/cockpit/play_physical.py
   - src/world_engine/cockpit/routes/mutations.py
   - src/world_engine/context.py
   - src/world_engine/context_describe.py
   - src/world_engine/event_reads.py
   - src/world_engine/models/__init__.py
   - src/world_engine/models/canon.py
   - src/world_engine/schema_version.py
   - src/world_engine/tick_context.py
   - src/world_engine/writes/worlds.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/event_contexts.py
   - tooling/verify/checks/event_tab.py
   - tooling/verify/checks/fact_facets.py
   - tooling/verify/checks/json_ui_boundary.py
   - tooling/verify/checks/visit_delta.py
   - tooling/verify/checks/world_cascade.py
   - world-engine-schema-changelog.md
   - world-engine-schema.md

````diff
diff --git a/scripts/migrate_v2_25_event_columns.py b/scripts/migrate_v2_25_event_columns.py
new file mode 100644
index 0000000..1774248
--- /dev/null
+++ b/scripts/migrate_v2_25_event_columns.py
@@ -0,0 +1,205 @@
+"""Migration v2.25 — the journal drops what it no longer reads (TICKET-0114,
+BRIEF-0114-D; decisions L1, N1, O1 and V1 of the conditions series).
+
+Rebuilds `event` without `type` (a type's `domain` now), `knowledge_status`
+(who knows an event is its fact's knowledge and scopes since v2.24),
+`has_magic_impact`, `consequences` and `occurred_at` (no reader, no value:
+the four production events carry the JSON `null` in `consequences`, never
+a magic impact nor an `occurred_at`), with `type_id` required and a
+`quantity` CHECK (1 or more); every row copied. Drops `event_entity`, whose
+rows v2.24 copied into `event_participant`.
+
+Before anything, the v2.24 data step is made complete: an event written
+between v2.24 and this code is typed, given its participants and its fact
+exactly as v2.24 did (`migrate_v2_24_event_journal._backfill`, imported,
+never copied), so no event loses what the dropped columns said.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.24, or when an `event_entity` row has no `event_participant`
+twin. Idempotent: a database already at the new shape is left as it is.
+One raw transaction (`foreign_keys` and `legacy_alter_table` set before it).
+
+Post-check, before `schema_meta` moves: `event` holds as many rows as
+before, none without a type; `event_entity` is gone; the dropped columns
+are gone; `PRAGMA foreign_key_check` on `event`, `event_participant` and
+`fact` is empty (a dangling row elsewhere is a note, AMENDMENT-0107-01).
+
+Run from the project root:
+
+    python scripts/migrate_v2_25_event_columns.py
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
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
+    print(
+        "migrate_v2_25_event_columns.py refuses to run without WORLD_ENGINE_ENV "
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
+from migrate_v2_24_event_journal import _backfill  # noqa: E402
+from world_engine import models  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.24"
+_KEPT_COLUMNS = "id, world_id, session_id, batch_id, type_id, title, description, location_id, quantity, recorded_at"
+_DROPPED = ("type", "knowledge_status", "has_magic_impact", "consequences", "occurred_at")
+_TOUCHED_TABLES = ("event", "event_participant", "fact", "fact_default", "event_type", "event_type_role",
+                   "event_type_role_type")
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+def _tables() -> set[str]:
+    return set(inspect(engine).get_table_names())
+
+
+def _columns(table: str) -> set[str]:
+    return {column["name"] for column in inspect(engine).get_columns(table)}
+
+
+def _refuse() -> None:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
+        if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
+            found = row[0] if row is not None else "no schema_meta row"
+            raise SystemExit(
+                f"Migration v2.25 refused: the database is at {found!r}; run the migrations "
+                f"up to {_PREVIOUS_VERSION} first."
+            )
+        if "event_entity" in _tables():
+            orphans = conn.execute(text(
+                "SELECT COUNT(*) FROM event_entity l JOIN event e ON e.id = l.event_id WHERE e.type_id IS NOT NULL "
+                "AND NOT EXISTS (SELECT 1 FROM event_participant p WHERE p.event_id = l.event_id "
+                "AND p.entity_id = l.entity_id)")).scalar_one()
+            if orphans:
+                raise SystemExit(
+                    f"Migration v2.25 refused: {orphans} event_entity row(s) have no event_participant twin; "
+                    "dropping them would lose who took part."
+                )
+
+
+def _create_from_model(cursor, model) -> None:
+    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
+    for index in model.__table__.indexes:
+        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))
+
+
+def _apply() -> list[str]:
+    needed = bool(set(_DROPPED) & _columns("event")) or "event_entity" in _tables()
+    if not needed:
+        return []
+    applied: list[str] = []
+    raw = engine.raw_connection()
+    try:
+        cursor = raw.cursor()
+        cursor.execute("PRAGMA foreign_keys=OFF")
+        cursor.execute("PRAGMA legacy_alter_table=ON")
+        cursor.execute("BEGIN")
+        typed = _backfill(cursor)
+        if typed:
+            applied.append(f"{len(typed)} event(s) typed first, as v2.24 does")
+        if set(_DROPPED) & _columns("event"):
+            for (index_name,) in cursor.execute(
+                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='event' AND sql IS NOT NULL"
+            ).fetchall():
+                cursor.execute(f"DROP INDEX {index_name}")
+            cursor.execute("ALTER TABLE event RENAME TO event_old")
+            _create_from_model(cursor, models.Event)
+            cursor.execute(f"INSERT INTO event ({_KEPT_COLUMNS}) SELECT {_KEPT_COLUMNS} FROM event_old")
+            cursor.execute("DROP TABLE event_old")
+            applied.append("event rebuilt without " + ", ".join(_DROPPED))
+        if "event_entity" in _tables():
+            cursor.execute("DROP TABLE event_entity")
+            applied.append("event_entity dropped")
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
+def _post_checks(before: int) -> None:
+    problems = []
+    with engine.connect() as conn:
+        after = conn.execute(text("SELECT COUNT(*) FROM event")).scalar_one()
+        untyped = conn.execute(text("SELECT COUNT(*) FROM event WHERE type_id IS NULL")).scalar_one()
+        dangling = [row for table in _TOUCHED_TABLES
+                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
+        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
+                     if row[0] not in _TOUCHED_TABLES]
+    if after != before:
+        problems.append(f"event holds {after} row(s), {before} before")
+    if untyped:
+        problems.append(f"{untyped} event(s) without a type")
+    if "event_entity" in _tables():
+        problems.append("event_entity is still there")
+    left = sorted(set(_DROPPED) & _columns("event"))
+    if left:
+        problems.append(f"event still has {left}")
+    if dangling:
+        problems.append(f"foreign_key_check {dangling}")
+    if problems:
+        raise SystemExit("Migration v2.25 aborted, post-check failed: " + "; ".join(problems) + ".")
+    for table, rowid, parent, _fk in elsewhere:
+        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
+    print(f"Post-check: {after} event(s) kept, each typed; the dropped columns and event_entity are gone.")
+
+
+def _converge_schema_meta() -> None:
+    with Session(engine) as session:
+        row = session.get(models.SchemaMeta, 1)
+        if row is None:
+            session.add(models.SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
+            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
+        elif _version_key(row.static_version) < _version_key(EXPECTED_STATIC_SCHEMA_VERSION):
+            previous = row.static_version
+            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
+            row.updated_at = datetime.now(UTC)
+            session.add(row)
+            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
+        else:
+            print(f"Row: schema_meta.id=1 already at {row.static_version!r} — nothing to do")
+        session.commit()
+
+
+def main() -> None:
+    print("Migration v2.25 — the journal drops what it no longer reads")
+    _refuse()
+    with engine.connect() as conn:
+        before = conn.execute(text("SELECT COUNT(*) FROM event")).scalar_one()
+    applied = _apply()
+    print("Applied: " + ", ".join(applied) + "." if applied else "Migration v2.25 already fully applied.")
+    _post_checks(before)
+    _converge_schema_meta()
+    print("\nMigration v2.25 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/attributes.py b/src/world_engine/attributes.py
index 507d05c..e01aa3a 100644
--- a/src/world_engine/attributes.py
+++ b/src/world_engine/attributes.py
@@ -324,3 +324,18 @@ def _history(db: Session, view: AttributeView, entity_id: str) -> list[dict]:
 def _change_raw(change: AttributeChange, side: str, kind: str) -> RawValue:
     column = {"choice": "choice_id", "integer": "integer", "entity": "entity_id"}[kind]
     return getattr(change, f"{side}_{column}")
+
+
+def perceived_states(db: Session, world_id: str, entity: Entity) -> str:
+    """WL1 (TICKET-0114, BRIEF-0114-D): the states of `entity` a player may
+    see, as the MJ reads them -- « Ouvert : oui · Occupé par : Ysa » -- every
+    active definition of the world that applies to it and is NOT hidden
+    (WH1), its current value or its default. A system attribute is left
+    out: its column already reaches the MJ (or never does) through its own
+    reader. Empty when there is none."""
+    parts = []
+    for view in world_attributes(db, world_id):
+        if view.system or view.hidden or not applies_to(view, entity.type):
+            continue
+        parts.append(f"{view.name} : {current_value(db, view, entity).label}")
+    return " · ".join(parts)
diff --git a/src/world_engine/cockpit/crud/agendas.py b/src/world_engine/cockpit/crud/agendas.py
index c575e12..1357ce5 100644
--- a/src/world_engine/cockpit/crud/agendas.py
+++ b/src/world_engine/cockpit/crud/agendas.py
@@ -28,7 +28,6 @@ from ...models import (
     DiscoverableDetail,
     Entity,
     Event,
-    EventEntity,
     Faction,
     FactionMembership,
     FactionRole,
diff --git a/src/world_engine/cockpit/crud/entities.py b/src/world_engine/cockpit/crud/entities.py
index 2d6ed7c..5f7e23b 100644
--- a/src/world_engine/cockpit/crud/entities.py
+++ b/src/world_engine/cockpit/crud/entities.py
@@ -35,7 +35,6 @@ from ...models import (
     EntityTrait,
     EntityType,
     Event,
-    EventEntity,
     Faction,
     FactionMembership,
     FactionRole,
diff --git a/src/world_engine/cockpit/crud/factions.py b/src/world_engine/cockpit/crud/factions.py
index 7505c3b..29dab6e 100644
--- a/src/world_engine/cockpit/crud/factions.py
+++ b/src/world_engine/cockpit/crud/factions.py
@@ -28,7 +28,6 @@ from ...models import (
     DiscoverableDetail,
     Entity,
     Event,
-    EventEntity,
     Faction,
     FactionMembership,
     FactionRole,
diff --git a/src/world_engine/cockpit/crud/goals.py b/src/world_engine/cockpit/crud/goals.py
index 17211c7..dc4e1ca 100644
--- a/src/world_engine/cockpit/crud/goals.py
+++ b/src/world_engine/cockpit/crud/goals.py
@@ -29,7 +29,6 @@ from ...models import (
     DiscoverableDetail,
     Entity,
     Event,
-    EventEntity,
     Faction,
     FactionMembership,
     FactionRole,
diff --git a/src/world_engine/cockpit/crud/knowledge.py b/src/world_engine/cockpit/crud/knowledge.py
index bdb6159..dd0ee66 100644
--- a/src/world_engine/cockpit/crud/knowledge.py
+++ b/src/world_engine/cockpit/crud/knowledge.py
@@ -29,7 +29,6 @@ from ...models import (
     DiscoverableDetail,
     Entity,
     Event,
-    EventEntity,
     Fact,
     FactDefault,
     FactParticipant,
diff --git a/src/world_engine/cockpit/crud/ledger.py b/src/world_engine/cockpit/crud/ledger.py
index 04bdb90..656549a 100644
--- a/src/world_engine/cockpit/crud/ledger.py
+++ b/src/world_engine/cockpit/crud/ledger.py
@@ -31,7 +31,6 @@ from ...models import (
     DiscoverableDetail,
     Entity,
     Event,
-    EventEntity,
     Faction,
     FactionMembership,
     FactionRole,
diff --git a/src/world_engine/cockpit/crud/locations.py b/src/world_engine/cockpit/crud/locations.py
index c72b619..e12245e 100644
--- a/src/world_engine/cockpit/crud/locations.py
+++ b/src/world_engine/cockpit/crud/locations.py
@@ -29,7 +29,6 @@ from ...models import (
     DiscoverableDetail,
     Entity,
     Event,
-    EventEntity,
     Faction,
     FactionMembership,
     FactionRole,
diff --git a/src/world_engine/cockpit/crud/prompts.py b/src/world_engine/cockpit/crud/prompts.py
index c05fc5e..6925659 100644
--- a/src/world_engine/cockpit/crud/prompts.py
+++ b/src/world_engine/cockpit/crud/prompts.py
@@ -30,7 +30,6 @@ from ...models import (
     DiscoverableDetail,
     Entity,
     Event,
-    EventEntity,
     Faction,
     FactionMembership,
     FactionRole,
diff --git a/src/world_engine/cockpit/crud/relations.py b/src/world_engine/cockpit/crud/relations.py
index 532a268..cc0aa96 100644
--- a/src/world_engine/cockpit/crud/relations.py
+++ b/src/world_engine/cockpit/crud/relations.py
@@ -30,7 +30,6 @@ from ...models import (
     DiscoverableDetail,
     Entity,
     Event,
-    EventEntity,
     Fact,
     FactDefault,
     Faction,
diff --git a/src/world_engine/cockpit/crud/skills.py b/src/world_engine/cockpit/crud/skills.py
index efbb2fa..364f8a8 100644
--- a/src/world_engine/cockpit/crud/skills.py
+++ b/src/world_engine/cockpit/crud/skills.py
@@ -30,7 +30,6 @@ from ...models import (
     DiscoverableDetail,
     Entity,
     Event,
-    EventEntity,
     Faction,
     FactionMembership,
     FactionRole,
diff --git a/src/world_engine/cockpit/play_physical.py b/src/world_engine/cockpit/play_physical.py
index d461306..cd0830b 100644
--- a/src/world_engine/cockpit/play_physical.py
+++ b/src/world_engine/cockpit/play_physical.py
@@ -21,6 +21,7 @@ from ..context import (
     assemble_npc_context,
 )
 from ..db import engine
+from ..event_reads import known_chronicle_events
 from ..facet_reads import facts_of, joined
 from ..facets import FACETS
 from ..models import (
@@ -30,7 +31,6 @@ from ..models import (
     ConversationMessage,
     DiscoverableDetail,
     Entity,
-    Event,
     Gathering,
     Location,
     PromptTemplate,
@@ -609,8 +609,8 @@ def _compute_return_delta(
     uses the tick's location-scope predicate VERBATIM (public, alive, active
     NPCs). Departed names resolve from `Entity` WITHOUT the alive/active
     filter (RECON-0016 F5) — the player saw them, their absence is public.
-    The event leg applies the SAME structural exclusion as the only other
-    Event reader (context.py) — secret events can never surface here.
+    The event leg reads what the player knows (`event_reads.known_chronicle_
+    events`, TICKET-0114), the same structural exclusion as the MJ context.
     """
     previous = db.exec(
         select(Visit)
@@ -653,17 +653,11 @@ def _compute_return_delta(
     if arrived_names:
         lines.append(f"- Arrivé·e·s : {', '.join(arrived_names)}")
 
-    events = db.exec(
-        select(Event)
-        .where(
-            Event.world_id == world_id,
-            Event.location_id == location_id,
-            Event.knowledge_status.in_(("public", "confirmed")),
-            Event.recorded_at > previous.entered_at,
-        )
-        .order_by(Event.recorded_at)
-    ).all()
-    for e in events:
+    # TICKET-0114 (BRIEF-0114-D, Q1): the chronicle events at this place the
+    # player knows -- entering it is a contact with its scope (0105).
+    events = known_chronicle_events(db, player_id, world_id, location_id=location_id,
+                                    since=previous.entered_at)
+    for e in reversed(events):
         line = f"- Événement : {e.title}"
         if e.description:
             first_sentence = e.description.split(".")[0].strip()
diff --git a/src/world_engine/cockpit/routes/mutations.py b/src/world_engine/cockpit/routes/mutations.py
index d360246..4ae3c97 100644
--- a/src/world_engine/cockpit/routes/mutations.py
+++ b/src/world_engine/cockpit/routes/mutations.py
@@ -63,7 +63,6 @@ from ...models import (
     DiscoverableDetail,
     Entity,
     Event,
-    EventEntity,
     Faction,
     FactionMembership,
     Gathering,
diff --git a/src/world_engine/context.py b/src/world_engine/context.py
index 265adf7..ed0631d 100644
--- a/src/world_engine/context.py
+++ b/src/world_engine/context.py
@@ -33,7 +33,6 @@ from .models import (
     Agenda,
     Character,
     Entity,
-    Event,
     Fact,
     FactionMembership,
     Gathering,
@@ -47,6 +46,8 @@ from .models import (
     SkillDefinition,
     World,
 )
+from .attributes import perceived_states
+from .event_reads import known_chronicle_events
 from .facet_reads import facts_of, joined, known_fact_texts, known_facts_of
 from .facets import FACETS
 from .knowledge_resolve import resolve_default_rows
@@ -675,6 +676,10 @@ def _mj_context_location(location_id: str, blindfolded: bool, db: Session) -> tu
         "description": None if blindfolded else joined(
             facts_of(db, entity_id=location_id, facets=("description",)), sep=" "),
         "subculture": subculture,
+        # The place's states the player may see (TICKET-0114, BRIEF-0114-D,
+        # WL1): never a hidden one; visual, so none when blindfolded.
+        "states": None if blindfolded or loc_entity is None else (
+            perceived_states(db, loc_entity.world_id, loc_entity) or None),
     }
     return location_block, loc_entity
 
@@ -698,33 +703,20 @@ def _mj_context_player_knowledge(player_character_id: str, db: Session) -> list[
     ]
 
 
-def _mj_context_public_events(world_id: str | None, location_id: str, db: Session) -> list[dict]:
-    """Public/confirmed only, location-matched first, capped at _MJ_EVENT_CAP."""
+def _mj_context_public_events(world_id: str | None, location_id: str, player_character_id: str,
+                              db: Session) -> list[dict]:
+    """The chronicle events the player knows (TICKET-0114, BRIEF-0114-D, Q1:
+    `event_reads.known_chronicle_events`), location-matched first, capped at
+    _MJ_EVENT_CAP."""
     if not world_id:
         return []
-    events = db.exec(
-        select(Event)
-        .where(
-            Event.world_id == world_id,
-            Event.knowledge_status.in_(("public", "confirmed")),
-        )
-        # `occurred_at` is written by nobody (in-fiction time, dormant
-        # column) — order by `recorded_at`, aligning with tick.py and
-        # app.py's return-visit delta (TICKET-0022, RECON finding 7).
-        .order_by(Event.recorded_at.desc())
-    ).all()
+    events = known_chronicle_events(db, player_character_id, world_id)
     local = [e for e in events if e.location_id == location_id]
     other = [e for e in events if e.location_id != location_id]
-    public_events: list[dict] = []
-    for e in (local + other)[:_MJ_EVENT_CAP]:
-        public_events.append({
-            "title": e.title,
-            "description": e.description,
-            "type": e.type,
-            "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
-            "location_id": e.location_id,
-        })
-    return public_events
+    return [
+        {"title": e.title, "description": e.description, "location_id": e.location_id}
+        for e in (local + other)[:_MJ_EVENT_CAP]
+    ]
 
 
 def _mj_context_custom_skills(world_id: str | None, db: Session) -> list[str]:
@@ -761,17 +753,21 @@ def assemble_mj_context(
 
     - `location` (static): the current location's `entity.name` + its
       `description` facts, plus the allow-listed (`FACETS["coutume"].aspects`)
-      `coutume` facts notorious at the location — ambiance is perceptible.
+      `coutume` facts notorious at the location — ambiance is perceptible —
+      and its states the player may see (TICKET-0114, WL1:
+      `attributes.perceived_states`, never a hidden one).
       `location.magic_status` is deliberately excluded (not directly
       perceivable).
     - `player_knowledge` (static): all `knowledge` rows belonging to the
       player character (fact text, level, content) — these are the player's
       own, so no further filtering is applied (a player's own `is_secret`
       row is something they already know, not a leak).
-    - `public_events` (static): `event` rows with `knowledge_status IN
-      ('public', 'confirmed')` for this world, ordered by `occurred_at DESC`,
+    - `public_events` (static): the chronicle events the player knows
+      (TICKET-0114, BRIEF-0114-D, Q1) -- an event whose type enters the
+      chronicle and whose fact the player resolves above `unaware`, by his
+      own knowledge or a scope he is in contact with -- newest first,
       capped at `_MJ_EVENT_CAP`; events whose `location_id` matches
-      `location_id` are preferred (listed first within the cap).
+      `location_id` are listed first within the cap.
     - `co_presents` (dynamic): public name + `description` facts of NPCs
       currently present, plus the `physique` facts the player resolves
       above `unaware` (the encounter registry: met -> seen, R-c), read fresh from the gathering roster
@@ -782,9 +778,9 @@ def assemble_mj_context(
     Structural exclusions (by query construction, never by instruction): no
     NPC `knowledge` row (only the player's own are read), no
     `character.secrets`, no `entity.internal_name`, no non-public entities,
-    no `event` rows with `knowledge_status = 'secret'`. (An event either
-    happened or did not; uncertainty about it lives on `knowledge.level =
-    'rumor'`, never on `event.knowledge_status` — TICKET-0022, R1.)
+    no event the player does not know (TICKET-0114: who knows an event is
+    its fact's knowledge and scopes; an event either happened or did not,
+    uncertainty about it lives on the knower's level).
 
     `blindfolded` (BRIEF-12): when True, visual information is structurally
     excluded — `location.description` is set to None and `co_presents` entries
@@ -805,7 +801,7 @@ def assemble_mj_context(
     world_id = loc_entity.world_id if loc_entity else None
 
     player_knowledge = _mj_context_player_knowledge(player_character_id, db)
-    public_events = _mj_context_public_events(world_id, location_id, db)
+    public_events = _mj_context_public_events(world_id, location_id, player_character_id, db)
     co_presents = _mj_context_co_presents(gathering_id, player_character_id, blindfolded, db)
     custom_skills = _mj_context_custom_skills(world_id, db)
 
@@ -837,6 +833,8 @@ def format_mj_context(mj_context: dict) -> str:
         ambiance = " ".join(str(v) for v in subculture.values() if v)
         if ambiance:
             loc_lines.append(f"Ambiance : {ambiance}")
+        if location.get("states"):
+            loc_lines.append(f"États : {location['states']}")
         blocks.append(_section(H_MJ_LOCATION, " ".join(loc_lines)))
 
     co_presents = mj_context.get("co_presents") or []
@@ -845,6 +843,7 @@ def format_mj_context(mj_context: dict) -> str:
             f"- {c['name']} : {c.get('description') or '(pas de description)'}"
             + (f" {c['physique']}" if c.get("physique") else "")
             + (f" Tenue : {c['tenue']}" if c.get("tenue") else "")
+            + (f" États : {c['states']}" if c.get("states") else "")
             for c in co_presents
         )
         blocks.append(_section(H_MJ_PRESENT, body))
diff --git a/src/world_engine/context_describe.py b/src/world_engine/context_describe.py
index 4f11bef..109bb61 100644
--- a/src/world_engine/context_describe.py
+++ b/src/world_engine/context_describe.py
@@ -13,6 +13,7 @@ from __future__ import annotations
 
 from sqlmodel import Session, select
 
+from .attributes import perceived_states
 from .facet_reads import facts_of, joined, known_facts_of
 from .models import (
     Character,
@@ -127,5 +128,8 @@ def _mj_context_co_presents(
                 db, perceiver_id=player_character_id, entity_id=co_entity.id,
                 facets=("tenue",),
             ), sep=" "),
+            # The states the player may see (TICKET-0114, BRIEF-0114-D, WL1):
+            # never a hidden one; visual, so none when blindfolded.
+            "states": None if blindfolded else (perceived_states(db, co_entity.world_id, co_entity) or None),
         })
     return co_presents
diff --git a/src/world_engine/event_reads.py b/src/world_engine/event_reads.py
new file mode 100644
index 0000000..48bc109
--- /dev/null
+++ b/src/world_engine/event_reads.py
@@ -0,0 +1,67 @@
+"""The journal as the models read it (TICKET-0114, BRIEF-0114-D; decisions
+K-a and Q1 of the conditions series). It replaces the former
+`event.knowledge_status IN ('public', 'confirmed')` filter of every reader.
+
+Only an event whose type enters the chronicle (`event_type.in_chronicle`)
+is ever told to a model: an event that only counts -- « un loup tué » --
+serves the conditions and is known as a fact, never as news.
+
+- `known_chronicle_events(db, knower_id, ...)` : what one character knows
+  of the chronicle -- the events whose fact he resolves above `unaware`
+  (`knowledge_resolve.resolve_known_for_entity`: his own knowledge rows,
+  then the scopes he is in contact with, 0105). The MJ of Play reads the
+  player's (`context.py`, `cockpit/play_physical.py`). His own rows are
+  never secret (INV-07); an NPC's secret row is never read here, nor
+  anywhere a model is briefed (INV-01).
+- `public_chronicle_events(db, world_id, ...)` : what everyone knows -- the
+  events whose fact has a `world` scope; the world tick reads these
+  (`tick_context.py`), its briefing governed by no one character.
+
+Both answer the newest first. This module writes nothing.
+"""
+
+from __future__ import annotations
+
+from datetime import datetime
+from typing import Optional
+
+from sqlmodel import Session, select
+
+from .knowledge_resolve import resolve_known_for_entity
+from .models import Event, EventParticipant, EventType, Fact, FactDefault
+
+
+def _chronicle(db: Session, world_id: str, location_id: Optional[str], since: Optional[datetime]):
+    query = (select(Event, Fact.id)
+             .join(EventType, EventType.id == Event.type_id)
+             .join(Fact, Fact.event_id == Event.id)
+             .where(Event.world_id == world_id, EventType.in_chronicle == True))  # noqa: E712
+    if location_id is not None:
+        query = query.where(Event.location_id == location_id)
+    if since is not None:
+        query = query.where(Event.recorded_at > since)
+    return query.order_by(Event.recorded_at.desc(), Event.id)
+
+
+def known_chronicle_events(db: Session, knower_id: str, world_id: str, *, location_id: Optional[str] = None,
+                           since: Optional[datetime] = None) -> list[Event]:
+    """The chronicle events `knower_id` knows, newest first."""
+    known = resolve_known_for_entity(db, knower_id)
+    if not known:
+        return []
+    rows = db.exec(_chronicle(db, world_id, location_id, since)).all()
+    return [event for event, fact_id in rows if fact_id in known]
+
+
+def public_chronicle_events(db: Session, world_id: str, *, location_id: Optional[str] = None,
+                            participant_id: Optional[str] = None, limit: Optional[int] = None) -> list[Event]:
+    """The chronicle events everyone knows (a `world` scope on their fact),
+    newest first; at one place, or with one participant, when asked."""
+    query = _chronicle(db, world_id, location_id, None).where(
+        Fact.id.in_(select(FactDefault.fact_id).where(FactDefault.scope_type == "world")))
+    if participant_id is not None:
+        query = query.where(Event.id.in_(select(EventParticipant.event_id).where(
+            EventParticipant.entity_id == participant_id)))
+    if limit is not None:
+        query = query.limit(limit)
+    return [event for event, _fact_id in db.exec(query).all()]
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index 16c5714..51ea637 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -4,7 +4,7 @@ package by schema stratum).
 
 Layout, by stratum:
     canon.py         — every table in canon_write_policy.txt's
-                        [CANON_TABLES], plus GoalPrerequisite/EventEntity
+                        [CANON_TABLES], plus GoalPrerequisite
                         (canon-domain writes, absent from [CANON_TABLES] by
                         a known governance gap — Nia's stratum escalation,
                         2026-07-15).
@@ -69,7 +69,6 @@ from .canon import (
     EntityType,
     EntityTypeHistory,
     Event,
-    EventEntity,
     GoalAgendaLink,
     GoalPrerequisite,
     Item,
@@ -254,7 +253,6 @@ __all__ = [
     "ConversationMessage",
     "ProposedMutation",
     "Event",
-    "EventEntity",
     "Artifact",
     "Item",
     "ItemHolding",
diff --git a/src/world_engine/models/canon.py b/src/world_engine/models/canon.py
index d2733ed..1c42c33 100644
--- a/src/world_engine/models/canon.py
+++ b/src/world_engine/models/canon.py
@@ -474,52 +474,32 @@ class Ledger(SQLModel, table=True):
 
 
 # -----------------------------------------------------------------------------
-# event  (facts that occur in the world)
+# event  (what happens in the world -- the journal, TICKET-0114)
+#
+# One happening of one of the world's event types (`models/canon_event.py`):
+# its participants by role are `event_participant`, who knows it is its
+# fact's knowledge and scopes (`fact.event_id`). v2.25 (BRIEF-0114-D) dropped
+# `knowledge_status`, `type` (a type's `domain` now), `has_magic_impact`,
+# `consequences`, `occurred_at` and `event_entity`; `type_id` is required.
 # -----------------------------------------------------------------------------
 class Event(SQLModel, table=True):
     __tablename__ = "event"
-    __table_args__ = (Index("idx_event_world", "world_id"),)
+    __table_args__ = (
+        CheckConstraint("quantity IS NULL OR quantity >= 1", name="ck_event_quantity"),
+        Index("idx_event_world", "world_id"),
+        Index("idx_event_type", "type_id"),
+    )
 
     id: str = Field(default_factory=_uuid, primary_key=True)
     world_id: str = Field(foreign_key="world.id", nullable=False)
     session_id: Optional[str] = Field(default=None, foreign_key="session.id")
     batch_id: Optional[str] = Field(default=None, foreign_key="batch.id")
+    type_id: str = Field(foreign_key="event_type.id", nullable=False)
     title: str
     description: Optional[str] = None
-    type: Optional[str] = None
-    knowledge_status: str = Field(
-        default="secret",
-        sa_column_kwargs={"server_default": text("'secret'")},
-    )
     location_id: Optional[str] = Field(default=None, foreign_key="entity.id")
-    has_magic_impact: bool = Field(
-        default=False, sa_column_kwargs={"server_default": text("0")}
-    )
-    consequences: Optional[Any] = Field(default=None, sa_column=Column(JSON))
-    occurred_at: Optional[datetime] = None
-    recorded_at: datetime = _created_ts()
-    # v2.24 (TICKET-0114, BRIEF-0114-A, N1): the world's type it is one of
-    # (`models/canon_event.py`), and how many, when its type counts (D1).
-    type_id: Optional[str] = Field(default=None, foreign_key="event_type.id")
     quantity: Optional[int] = None
-
-
-# -----------------------------------------------------------------------------
-# event_entity  (event <-> entity link, schema v1.79, TICKET-0025,
-# BRIEF-0025-c — replaces the FK-less event.involved_entities JSON id array)
-#
-# Membership queries become joins/EXISTS instead of a Python `in` over a
-# JSON list of ids. No change_history (link table, not a fact-bearing row).
-# -----------------------------------------------------------------------------
-class EventEntity(SQLModel, table=True):
-    __tablename__ = "event_entity"
-    __table_args__ = (
-        Index("idx_event_entity_unique", "event_id", "entity_id", unique=True),
-    )
-
-    id: str = Field(default_factory=_uuid, primary_key=True)
-    event_id: str = Field(foreign_key="event.id", nullable=False)
-    entity_id: str = Field(foreign_key="entity.id", nullable=False)
+    recorded_at: datetime = _created_ts()
 
 
 # -----------------------------------------------------------------------------
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index 198cae8..cd1e07a 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.24"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.25"
diff --git a/src/world_engine/tick_context.py b/src/world_engine/tick_context.py
index 445f5c1..ec01676 100644
--- a/src/world_engine/tick_context.py
+++ b/src/world_engine/tick_context.py
@@ -36,6 +36,7 @@ from .knowledge_resolve import (
     resolve_levels_for_entity,
     resolve_public_levels,
 )
+from .event_reads import public_chronicle_events
 from .facet_reads import facts_of, joined, known_fact_texts
 from .fact_refs import CodedRefs, code_facts
 from .prose_render import knowledge_texts
@@ -45,8 +46,6 @@ from .models import (
     AgendaStep,
     Character,
     Entity,
-    Event,
-    EventEntity,
     Fact,
     Faction,
     FactionMembership,
@@ -615,15 +614,9 @@ def assemble_location_event_context(
         else "(aucun lieu connecté)"
     )
 
-    recent = session.exec(
-        select(Event)
-        .where(
-            Event.location_id == location_id,
-            Event.knowledge_status.in_(("public", "confirmed")),
-        )
-        .order_by(Event.recorded_at.desc())
-        .limit(5)
-    ).all()
+    # TICKET-0114 (BRIEF-0114-D, Q1): the chronicle everyone knows, here.
+    place = session.get(Entity, location_id)
+    recent = public_chronicle_events(session, place.world_id, location_id=location_id, limit=5) if place else []
     recent_body = (
         "\n".join(f"- {e.title}" for e in recent)
         if recent
@@ -715,18 +708,10 @@ def _tick_faction_members_block(faction_id: str, session: Session) -> str:
 
 
 def _tick_faction_recent_events_block(faction_id: str, faction_entity: Entity | None, session: Session) -> str:
-    """Faction event filter is a join/EXISTS on event_entity (TICKET-0025,
-    BRIEF-0025-c) — was a Python `in` over event.involved_entities JSON."""
-    recent = session.exec(
-        select(Event)
-        .join(EventEntity, EventEntity.event_id == Event.id)
-        .where(
-            Event.world_id == (faction_entity.world_id if faction_entity else None),
-            Event.knowledge_status.in_(("public", "confirmed")),
-            EventEntity.entity_id == faction_id,
-        )
-        .order_by(Event.recorded_at.desc())
-    ).all()[:5]
+    """The chronicle everyone knows with the faction taking part
+    (TICKET-0114, BRIEF-0114-D: `event_reads.public_chronicle_events`)."""
+    recent = public_chronicle_events(session, faction_entity.world_id, participant_id=faction_id,
+                                     limit=5) if faction_entity else []
     return "\n".join(f"- {e.title}" for e in recent) if recent else "(aucun événement public récent)"
 
 
diff --git a/src/world_engine/writes/worlds.py b/src/world_engine/writes/worlds.py
index 19b55c0..f89d065 100644
--- a/src/world_engine/writes/worlds.py
+++ b/src/world_engine/writes/worlds.py
@@ -48,7 +48,6 @@ _SUBQUERY_SCOPED_DELETES: tuple[tuple[str, str, str], ...] = (
     ("artifact", "id", "entity"),
     ("item", "id", "entity"),
     ("agenda_step", "agenda_id", "agenda"),
-    ("event_entity", "event_id", "event"),
     ("obstacle_vertex", "obstacle_id", "obstacle"),
     ("observation_beat", "run_id", "observation_run"),
     ("observation_intent", "run_id", "observation_run"),
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 15235ae..def2460 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19344,6 +19344,37 @@ TICKET-0119 makes the tick propose typed events.
 mutation's conversation or declared action): the calendar of TICKET-0120
 will place every event on it without guessing.
 
+## THE MODELS READ THE JOURNAL BY WHAT IS KNOWN, AND THE MJ SEES THE STATES A PLAYER MAY SEE (TICKET-0114) -- `knowledge_status` RETIRED, v2.25 DROPS WHAT NOBODY READS (BRIEF-0114-d, schema v2.25)
+
+**Q1.** Who knows an event is its fact's knowledge and scopes; no reader
+filters a status any more (`event_reads.py`). The MJ of Play reads the
+chronicle events the player knows (`known_chronicle_events`: his own rows,
+then the scopes he is in contact with, the 0105 resolver) -- the MJ
+context's `public_events` and the return-visit delta. The world tick reads
+what everyone knows (`public_chronicle_events`: a `world` scope) at a
+place, or with a faction taking part. Only a type that enters the
+chronicle (`in_chronicle`) is told to a model: an event that only counts --
+« un loup tué » -- is known as a fact, never told as news. An event the
+player knows also reaches the MJ as his knowledge, as every fact he holds.
+
+**WL1.** The MJ reads the states a player may see
+(`attributes.perceived_states`): the place's and each co-present's, every
+active world definition that applies and is not hidden (WH1), its value or
+its default, written « États : Ouvert : oui ». Visual, so none blindfolded
+(BRIEF-12). A system attribute is left out: its column reaches the MJ, or
+never does, through its own reader.
+
+**L1, v2.25.** `event` loses `type`, `knowledge_status`,
+`has_magic_impact`, `consequences` and `occurred_at` (the four production
+events carried none of them for real: `consequences` was the JSON `null`);
+`type_id` is required; `event_entity` is dropped. The migration first types
+what was left untyped, exactly as v2.24 does (its `_backfill`, imported),
+and refuses when a link has no participant twin.
+
+**Rejected.** Q2 (the strict equivalent everywhere -- `world` scope only:
+the MJ would not remember that the player killed the wolf), L2 (keep the
+columns dormant).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/event_contexts.py b/tooling/verify/checks/event_contexts.py
new file mode 100644
index 0000000..e9ed163
--- /dev/null
+++ b/tooling/verify/checks/event_contexts.py
@@ -0,0 +1,373 @@
+"""G1 check for TICKET-0114 -- the models read the journal by what is known, and the MJ reads the states a player may see.
+
+BRIEF-0114-D's rules.
+
+ED1 -- who reads what (fixture). In a world where the PC Mira stands in the
+   Forêt, six chronicle events: one Mira took part in, one with a `world`
+   scope, one with a `location` scope on the Forêt, one with a `location`
+   scope on the Ville, one an NPC keeps secret with no scope, and one Mira
+   took part in whose type is not in the chronicle.
+   `event_reads.known_chronicle_events` for Mira lists exactly the first
+   three, newest first; `assemble_mj_context`'s `public_events` lists the
+   same three titles, the Forêt's first; `public_chronicle_events` lists
+   only the `world` one, and with the faction as participant only the
+   faction's; the tick's location briefing for the Forêt names the `world`
+   one held there and not the `location` one; the faction briefing names
+   the faction's; the return-visit delta at the Forêt, after a visit
+   recorded before the events, names the two known there.
+ED2 -- WL1 (fixture). `attributes.perceived_states` of the Forêt reads
+   « Ouvert : oui » from a visible attribute and never names a hidden one;
+   `assemble_mj_context`'s location carries it and `format_mj_context`
+   writes « États : Ouvert : oui »; blindfolded, the location carries no
+   states. `context_describe._mj_context_co_presents` gives each co-present
+   its `states` through `perceived_states`, none when blindfolded (static).
+ED3 -- migration `scripts/migrate_v2_25_event_columns.py`, on a v2.24
+   database (`event` and `event_entity` in their v2.24 DDL, frozen below):
+   at v2.23 it refuses and changes nothing; with an `event_entity` row of a
+   typed event that no participant twins, it refuses and changes nothing;
+   at v2.24 it first types an event left untyped (its link becomes a
+   participant, its fact is written), rebuilds `event` without the five
+   columns, `type_id` required, every row kept, drops `event_entity` and
+   sets `schema_meta` to the code's version; a second run writes nothing.
+ED4 -- nothing reads what was dropped (static, AST). No module under `src/`
+   names the attribute `knowledge_status`, `occurred_at`,
+   `has_magic_impact` or `consequences` on anything, nor `EventEntity`;
+   `event` declares none of the five columns; `context.py`,
+   `cockpit/play_physical.py` and `tick_context.py` each call
+   `event_reads`.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import ast
+import os
+import pathlib
+import sqlite3
+import subprocess
+import sys
+import tempfile
+from datetime import UTC, datetime, timedelta
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+MIGRATION_V2_25 = ROOT / "scripts" / "migrate_v2_25_event_columns.py"
+
+FAILURES: list[str] = []
+
+V2_24_EVENT = (
+    "CREATE TABLE event (id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, session_id VARCHAR, batch_id VARCHAR, "
+    "title VARCHAR NOT NULL, description VARCHAR, type VARCHAR, knowledge_status VARCHAR DEFAULT 'secret' NOT NULL, "
+    "location_id VARCHAR, has_magic_impact BOOLEAN DEFAULT 0 NOT NULL, consequences JSON, occurred_at DATETIME, "
+    "recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, type_id VARCHAR, quantity INTEGER, PRIMARY KEY (id), "
+    "FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(session_id) REFERENCES session (id), "
+    "FOREIGN KEY(batch_id) REFERENCES batch (id), FOREIGN KEY(location_id) REFERENCES entity (id), "
+    "FOREIGN KEY(type_id) REFERENCES event_type (id))",
+    "CREATE INDEX idx_event_world ON event (world_id)",
+    "CREATE TABLE event_entity (id VARCHAR NOT NULL, event_id VARCHAR NOT NULL, entity_id VARCHAR NOT NULL, "
+    "PRIMARY KEY (id), FOREIGN KEY(event_id) REFERENCES event (id), FOREIGN KEY(entity_id) REFERENCES entity (id))",
+    "CREATE UNIQUE INDEX idx_event_entity_unique ON event_entity (event_id, entity_id)",
+)
+DROPPED = ("knowledge_status", "occurred_at", "has_magic_impact", "consequences")
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> None:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+
+
+def _fixture(engine) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.models import Character, Entity, Faction, Location, Visit, World
+    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type
+
+    with Session(engine) as db:
+        world = World(name="Contextes", is_active=True)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind, name in (("foret", "location", "Forêt"), ("ville", "location", "Ville"),
+                                ("mira", "character", "Mira"), ("brakk", "character", "Brakk"),
+                                ("guilde", "faction", "Guilde")):
+            entity = Entity(world_id=world.id, type=kind, name=name)
+            db.add(entity)
+            db.flush()
+            ids[key] = entity.id
+            if kind == "location":
+                db.add(Location(id=entity.id))
+            elif kind == "faction":
+                db.add(Faction(id=entity.id))
+        db.flush()
+        for key in ("mira", "brakk"):
+            db.add(Character(id=ids[key], world_id=world.id, character_type="player" if key == "mira" else "npc",
+                             current_location_id=ids["foret"]))
+        db.add(Visit(world_id=world.id, player_id=ids["mira"], location_id=ids["foret"],
+                     entered_at=datetime.now(UTC) - timedelta(days=1), present_npc_ids=[]))
+        roles = (RoleSpec("qui", ("character", "faction")),)
+        ids["fait"] = write_event_type(db, world_id=world.id, spec=EventTypeSpec(name="Fait", roles=roles)).id
+        ids["compte"] = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
+            name="Compte", roles=roles, in_chronicle=False)).id
+        db.commit()
+    return ids
+
+
+def _events(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.event_vocab import type_view
+    from world_engine.models import Event
+    from world_engine.writes.events import EventScopeSpec, EventSpec, ParticipantSpec, write_event
+
+    with Session(engine) as db:
+        qui = type_view(db, ids["fait"]).roles[0].id
+        quic = type_view(db, ids["compte"]).roles[0].id
+        rows = (
+            ("Mira y était", ids["fait"], (ParticipantSpec(qui, entity_id=ids["mira"]),), (), ids["ville"]),
+            ("Tout le monde le sait", ids["fait"], (ParticipantSpec(qui, entity_id=ids["guilde"]),),
+             (EventScopeSpec("world", None, "knows"),), ids["foret"]),
+            ("On le sait à la Forêt", ids["fait"], (), (EventScopeSpec("location", ids["foret"], "knows"),),
+             ids["foret"]),
+            ("On le sait à la Ville", ids["fait"], (), (EventScopeSpec("location", ids["ville"], "knows"),),
+             ids["ville"]),
+            ("Le secret de Brakk", ids["fait"], (ParticipantSpec(qui, entity_id=ids["brakk"], secret=True),), (),
+             ids["foret"]),
+            ("Mira compte un loup", ids["compte"], (ParticipantSpec(quic, entity_id=ids["mira"]),), (), ids["foret"]),
+        )
+        for k, (title, type_id, participants, scopes, place) in enumerate(rows):
+            event = write_event(db, world_id=ids["world"], created_by="check", spec=EventSpec(
+                type_id=type_id, title=title, participants=participants, scopes=scopes, location_id=place))
+            event.recorded_at = datetime.now(UTC) - timedelta(hours=10 - k)
+            db.add(event)
+        db.commit()
+        assert db.get(Event, event.id) is not None
+
+
+def check_ed1(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.cockpit.play_physical import _compute_return_delta
+    from world_engine.context import assemble_mj_context
+    from world_engine.event_reads import known_chronicle_events, public_chronicle_events
+    from world_engine.tick_context import _tick_faction_recent_events_block
+    from world_engine.models import Entity
+
+    known_want = ["On le sait à la Forêt", "Tout le monde le sait", "Mira y était"]
+    with Session(engine) as db:
+        known = [e.title for e in known_chronicle_events(db, ids["mira"], ids["world"])]
+        if known != known_want:
+            fail(f"ED1: Mira knows {known}")
+        mj = assemble_mj_context(db, ids["mira"], ids["foret"])
+        titles = [e["title"] for e in mj["public_events"]]
+        if titles != ["On le sait à la Forêt", "Tout le monde le sait", "Mira y était"]:
+            fail(f"ED1: the MJ's public_events are {titles}")
+        public = [e.title for e in public_chronicle_events(db, ids["world"])]
+        guild = [e.title for e in public_chronicle_events(db, ids["world"], participant_id=ids["guilde"])]
+        if public != ["Tout le monde le sait"] or guild != ["Tout le monde le sait"]:
+            fail(f"ED1: public_chronicle_events gives {public}, with the guild {guild}")
+        block = _tick_faction_recent_events_block(ids["guilde"], db.get(Entity, ids["guilde"]), db)
+        if "Tout le monde le sait" not in block:
+            fail(f"ED1: the faction briefing reads {block!r}")
+        lines, _ = _compute_return_delta(db, ids["world"], ids["mira"], ids["foret"])
+        named = [line for line in (lines or []) if line.startswith("- Événement")]
+        if len(named) != 2 or "Tout le monde le sait" not in named[0] or "On le sait à la Forêt" not in named[1]:
+            fail(f"ED1: the return delta names {named}")
+    src = (SRC / "tick_context.py").read_text(encoding="utf-8")
+    if "public_chronicle_events(session, place.world_id, location_id=location_id" not in src:
+        fail("ED1: the tick's location briefing does not read public_chronicle_events at its place")
+
+
+def check_ed2(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.attributes import perceived_states
+    from world_engine.context import assemble_mj_context, format_mj_context
+    from sqlmodel import select
+
+    from world_engine.models import AttributeChoice, Entity
+    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition, \
+        write_attribute_value
+
+    with Session(engine) as db:
+        for name, hidden in (("Ouvert", False), ("Maudit", True)):
+            definition = write_attribute_definition(db, world_id=ids["world"], spec=DefinitionSpec(
+                name=name, kind="choice", holder_types=("location",), choices=(ChoiceSpec("non"), ChoiceSpec("oui")),
+                default="non", is_hidden=hidden))
+            oui = next(c for c in db.exec(select(AttributeChoice).where(
+                AttributeChoice.definition_id == definition.id)).all() if c.label == "oui")
+            write_attribute_value(db, world_id=ids["world"], definition_id=definition.id, entity_id=ids["foret"],
+                                  value=oui.id, kind="changement", changed_by="check")
+        db.commit()
+        states = perceived_states(db, ids["world"], db.get(Entity, ids["foret"]))
+        if states != "Ouvert : oui":
+            fail(f"ED2: the Forêt's perceived states are {states!r}")
+        mj = assemble_mj_context(db, ids["mira"], ids["foret"])
+        if mj["location"].get("states") != "Ouvert : oui" or "États : Ouvert : oui" not in format_mj_context(mj) \
+                or "Maudit" in format_mj_context(mj):
+            fail(f"ED2: the MJ's location reads {mj['location']}")
+        if assemble_mj_context(db, ids["mira"], ids["foret"], blindfolded=True)["location"].get("states"):
+            fail("ED2: blindfolded, the location still carries states")
+    describe = (SRC / "context_describe.py").read_text(encoding="utf-8")
+    if '"states": None if blindfolded else (perceived_states(db, co_entity.world_id, co_entity) or None)' \
+            not in describe:
+        fail("ED2: context_describe does not give each co-present its perceived states")
+
+
+# --- ED3 -------------------------------------------------------------------------
+
+def _run_migration(db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(MIGRATION_V2_25)], env=env, capture_output=True, text=True,
+                          cwd=str(ROOT), timeout=120)
+
+
+def _v2_24_db(orphan: bool) -> str:
+    from sqlalchemy import create_engine
+    from sqlmodel import SQLModel
+
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "migrate.db")
+    eng = create_engine(f"sqlite:///{db_path}")
+    SQLModel.metadata.create_all(eng, tables=[t for n, t in SQLModel.metadata.tables.items() if n != "event"])
+    eng.dispose()
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("PRAGMA foreign_keys=OFF")
+        conn.execute("DROP TABLE event_participant")
+        for statement in V2_24_EVENT:
+            conn.execute(statement)
+        conn.executescript("""
+            INSERT INTO schema_meta (id, static_version, updated_at) VALUES (1, 'v2.23', '2026-10-01');
+            INSERT INTO world (id, name, is_active, created_at, updated_at) VALUES ('w', 'W', 0, '2026-10-01', '2026-10-01');
+            INSERT INTO entity (id, world_id, type, name, status, created_at, updated_at)
+              VALUES ('a', 'w', 'character', 'A', 'active', '2026-10-01', '2026-10-01');
+            INSERT INTO event_type (id, world_id, name, domain, counts_quantity, in_chronicle, participants_secret,
+              status, created_at, updated_at) VALUES ('t', 'w', 'Social', 'social', 0, 1, 0, 'active', '2026-10-01', '2026-10-01');
+            INSERT INTO event_type_role (id, world_id, type_id, name, position, accepts_sorte, status)
+              VALUES ('r', 'w', 't', 'Impliqué', 0, 0, 'active');
+            INSERT INTO event_type_role_type (id, world_id, role_id, entity_type) VALUES ('rt', 'w', 'r', 'character');
+            INSERT INTO event (id, world_id, title, type, knowledge_status, recorded_at, type_id)
+              VALUES ('e1', 'w', 'Typé', 'social', 'secret', '2026-10-01', 't'),
+                     ('e2', 'w', 'Après', 'social', 'public', '2026-10-02', NULL);
+            INSERT INTO event_entity (id, event_id, entity_id) VALUES ('l1', 'e1', 'a'), ('l2', 'e2', 'a');
+            INSERT INTO fact (id, world_id, event_id, content, facet, default_level, created_at, created_by, change_history)
+              VALUES ('f1', 'w', 'e1', 'Typé', 'evenement', 'unaware', '2026-10-01', 'x', '[]');
+        """)
+        conn.execute(str(_participant_ddl()))
+        if not orphan:
+            conn.execute("INSERT INTO event_participant (id, world_id, event_id, role_id, entity_id, position) "
+                         "VALUES ('p1', 'w', 'e1', 'r', 'a', 0)")
+    return db_path
+
+
+def _participant_ddl() -> str:
+    from sqlalchemy.dialects import sqlite
+    from sqlalchemy.schema import CreateTable
+    from sqlmodel import SQLModel
+
+    return str(CreateTable(SQLModel.metadata.tables["event_participant"]).compile(dialect=sqlite.dialect()))
+
+
+def _state(db_path: str) -> dict:
+    with sqlite3.connect(db_path) as conn:
+        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
+        return {
+            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
+            "columns": [r[1] for r in conn.execute("PRAGMA table_info(event)")],
+            "events": sorted(conn.execute("SELECT id, type_id FROM event").fetchall()),
+            "participants": sorted(conn.execute("SELECT event_id, entity_id FROM event_participant").fetchall()),
+            "facts": sorted(conn.execute("SELECT event_id FROM fact WHERE event_id IS NOT NULL").fetchall()),
+            "event_entity": "event_entity" in tables,
+        }
+
+
+def check_ed3() -> None:
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+
+    db_path = _v2_24_db(orphan=False)
+    before = _state(db_path)
+    if _run_migration(db_path).returncode == 0 or _state(db_path) != before:
+        fail("ED3: v2.23 was not refused untouched")
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.24' WHERE id = 1")
+    orphan_path = _v2_24_db(orphan=True)
+    with sqlite3.connect(orphan_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.24' WHERE id = 1")
+    orphan_before = _state(orphan_path)
+    refused = _run_migration(orphan_path)
+    if refused.returncode == 0 or _state(orphan_path) != orphan_before:
+        fail(f"ED3: an untwinned event_entity row was not refused untouched ({refused.returncode})")
+    result = _run_migration(db_path)
+    after = _state(db_path)
+    want = {
+        "version": EXPECTED_STATIC_SCHEMA_VERSION,
+        "columns": ["id", "world_id", "session_id", "batch_id", "type_id", "title", "description", "location_id",
+                    "quantity", "recorded_at"],
+        "events": [("e1", "t"), ("e2", "t")],
+        "participants": [("e1", "a"), ("e2", "a")],
+        "facts": [("e1",), ("e2",)],
+        "event_entity": False,
+    }
+    if result.returncode != 0 or after != want:
+        fail(f"ED3: exit {result.returncode}, state {after}: {result.stderr.strip()[-300:]}")
+    again = _run_migration(db_path)
+    if again.returncode != 0 or "already fully applied" not in again.stdout or _state(db_path) != after:
+        fail(f"ED3: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
+
+
+# --- ED4 -------------------------------------------------------------------------
+
+def check_ed4() -> None:
+    from sqlmodel import SQLModel
+
+    scanned = 0
+    for path in sorted(SRC.rglob("*.py")):
+        tree = ast.parse(path.read_text(encoding="utf-8"))
+        scanned += 1
+        rel = path.relative_to(ROOT).as_posix()
+        for node in ast.walk(tree):
+            if isinstance(node, ast.Attribute) and node.attr in DROPPED:
+                fail(f"ED4: {rel}:{node.lineno} reads .{node.attr}")
+            if isinstance(node, ast.Name) and node.id == "EventEntity":
+                fail(f"ED4: {rel}:{node.lineno} names EventEntity")
+    if scanned < 100:
+        fail(f"ED4: only {scanned} modules scanned")
+    columns = set(SQLModel.metadata.tables["event"].c.keys())
+    if columns & set(DROPPED + ("type",)) or SQLModel.metadata.tables["event"].c["type_id"].nullable:
+        fail(f"ED4: event declares {sorted(columns)}")
+    for name in ("context.py", "cockpit/play_physical.py", "tick_context.py"):
+        text = (SRC / name).read_text(encoding="utf-8")
+        if "from .event_reads import" not in text and "from ..event_reads import" not in text:
+            fail(f"ED4: {name} does not read event_reads")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    ids = _fixture(engine)
+    _events(engine, ids)
+    rules = (("ED1", lambda: check_ed1(engine, ids)), ("ED2", lambda: check_ed2(engine, ids)), ("ED3", check_ed3),
+             ("ED4", check_ed4))
+    for name, rule in rules:
+        try:
+            rule()
+        except Exception as exc:  # a crash is that rule's failure, never a pass
+            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: event_contexts -- the MJ reads the chronicle the player knows, the tick what everyone knows; the "
+          "MJ reads the states a player may see, never a hidden one; v2.25 drops the columns nobody reads")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/event_tab.py b/tooling/verify/checks/event_tab.py
index b15c8d5..efa88d6 100644
--- a/tooling/verify/checks/event_tab.py
+++ b/tooling/verify/checks/event_tab.py
@@ -10,8 +10,8 @@ Asserts:
 1. No `event` delete surface exists anywhere: no `DELETE /api/events` (or
    `/api/events/{id}`) route in the cockpit app, and no client-side call to
    an `/api/events` path anywhere under frontend/src/creation uses DELETE
-   (C3 — `event` is history; retraction is `knowledge_status = 'secret'`,
-   never a delete). Vacuous-proof: at least one non-DELETE `/api/events`
+   (C3 — `event` is history; a retraction empties its fact's scopes since
+   TICKET-0114, never a delete). Vacuous-proof: at least one non-DELETE `/api/events`
    call must be found under frontend/src/creation, or the check fails --
    an empty scan proves nothing.
 2. `Event.occurred_at` appears in no `order_by(...)` anywhere in `src/`
diff --git a/tooling/verify/checks/fact_facets.py b/tooling/verify/checks/fact_facets.py
index f57a3bd..e5d3b50 100644
--- a/tooling/verify/checks/fact_facets.py
+++ b/tooling/verify/checks/fact_facets.py
@@ -196,7 +196,7 @@ def check_call_sites() -> None:
 def check_case_table(engine) -> None:
     from sqlmodel import Session as DbSession
 
-    from world_engine.models import Entity, Event, Fact, Relation, World, WorldLaw
+    from world_engine.models import Entity, Event, EventType, Fact, Relation, World, WorldLaw
     from world_engine.writes.facts import create_fact
 
     with DbSession(engine) as session:
@@ -209,7 +209,11 @@ def check_case_table(engine) -> None:
         session.add_all([a, b])
         session.commit()
         rel = Relation(world_id=wid, entity_a_id=a.id, entity_b_id=b.id, type="controls")
-        event = Event(world_id=wid, title="an event")
+        # TICKET-0114 (BRIEF-0114-D): an event is one of its world's types.
+        etype = EventType(world_id=wid, name="Fait")
+        session.add(etype)
+        session.flush()
+        event = Event(world_id=wid, title="an event", type_id=etype.id)
         law = WorldLaw(world_id=wid, text_="a law")
         session.add_all([rel, event, law])
         session.commit()
diff --git a/tooling/verify/checks/json_ui_boundary.py b/tooling/verify/checks/json_ui_boundary.py
index 133814d..de4d8da 100644
--- a/tooling/verify/checks/json_ui_boundary.py
+++ b/tooling/verify/checks/json_ui_boundary.py
@@ -66,7 +66,6 @@ JSON_COLUMN_ALLOWLIST = {
     "Visit.present_npc_ids",
     # No UI consumer today. The FIRST UI consumer of any of these
     # MUST migrate it to relational storage in the same brief.
-    "Event.consequences",
     "Artifact.known_properties",
     "Artifact.actual_behavior",
     # NPC link agent staging (TICKET-0036, BRIEF-0036-a) — ephemeral
diff --git a/tooling/verify/checks/visit_delta.py b/tooling/verify/checks/visit_delta.py
index f2ef715..c14dc2a 100644
--- a/tooling/verify/checks/visit_delta.py
+++ b/tooling/verify/checks/visit_delta.py
@@ -8,9 +8,10 @@ never touched again (same mechanical philosophy as `single_canon_write.py`
 and `world_tick.py`'s call-site allowlist).
 
 Rule 2 (structural exclusion): `_compute_return_delta` (cockpit/app.py) —
-the function housing the delta's `select(Event)` call — references
-`knowledge_status` somewhere in its body (same spirit as the
-secret-exclusion checks on the assemblers).
+the function housing the delta's event leg — calls
+`event_reads.known_chronicle_events` (since TICKET-0114, BRIEF-0114-D: the
+player reads only the events he knows; it referenced `knowledge_status`
+before), same spirit as the secret-exclusion checks on the assemblers.
 
 No DB, stdlib `ast` only.
 """
@@ -126,11 +127,12 @@ def check_event_structural_exclusion() -> None:
         fail(f"{rel}: _compute_return_delta not found")
         return
 
-    has_knowledge_status = any(
-        isinstance(n, ast.Attribute) and n.attr == "knowledge_status" for n in ast.walk(func)
+    reads_known = any(
+        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "known_chronicle_events"
+        for n in ast.walk(func)
     )
-    if not has_knowledge_status:
-        fail(f"{rel}: _compute_return_delta does not reference knowledge_status — structural exclusion missing")
+    if not reads_known:
+        fail(f"{rel}: _compute_return_delta does not call known_chronicle_events — structural exclusion missing")
 
 
 def main() -> None:
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index 8100aa6..cb0023d 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -124,8 +124,6 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
     ("batch", {"id": "bat-{w}", "session_id": "ses-{w}"}),
     ("door", {"id": "door-{w}", "world_id": "{w}", "location_id": "{w}-loc",
               "target_location_id": "{w}-loc", "x": 0.0, "y": 0.0}),
-    ("event", {"id": "ev-{w}", "world_id": "{w}", "title": "t"}),
-    ("event_entity", {"id": "eve-{w}", "event_id": "ev-{w}", "entity_id": "{w}-char"}),
     # TICKET-0114 (BRIEF-0114-A): a type, its role and scope, a sorte, a
     # participant, and a filter on the condition leaf above.
     ("event_type", {"id": "et-{w}", "world_id": "{w}", "name": "Tuer"}),
@@ -133,6 +131,7 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
     ("event_type_role_type", {"id": "etrt-{w}", "world_id": "{w}", "role_id": "etr-{w}",
                               "entity_type": "character"}),
     ("event_type_scope", {"id": "ets-{w}", "world_id": "{w}", "type_id": "et-{w}", "scope_kind": "world"}),
+    ("event", {"id": "ev-{w}", "world_id": "{w}", "title": "t", "type_id": "et-{w}"}),
     ("event_sorte", {"id": "eso-{w}", "world_id": "{w}", "name": "loup"}),
     ("event_participant", {"id": "ep-{w}", "world_id": "{w}", "event_id": "ev-{w}", "role_id": "etr-{w}",
                            "entity_id": "{w}-char"}),
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 26fc791..b164cfe 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,16 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.25** — TICKET-0114, BRIEF-0114-D: the journal drops what it no
+  longer reads. `event` is rebuilt without `type` (a type's `domain` now),
+  `knowledge_status` (who knows an event is its fact's knowledge and
+  scopes), `has_magic_impact`, `consequences` and `occurred_at` (no reader,
+  no value); `type_id` is required and `quantity` checked (1 or more);
+  `idx_event_type` is added. `event_entity` is dropped (its rows became
+  `event_participant` at v2.24). `migrate_v2_25_event_columns.py` first
+  types any event left untyped exactly as v2.24 does, refuses a database
+  older than v2.24 or an `event_entity` row no participant twins, and moves
+  `schema_meta` to v2.25.
 - **v2.24** — TICKET-0114, BRIEF-0114-A: the event journal's vocabulary.
   `event_type` (a world's type of event: its name, its domain -- one of the
   seven former categories --, whether it counts a quantity, enters the
diff --git a/world-engine-schema.md b/world-engine-schema.md
index f3f01df..401171a 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.24
+Current schema version: v2.25
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -1600,75 +1600,46 @@ read side rather than normalized).
 
 ### `event`
 
-Facts that occur in the world, arising from sessions or generated.
+What happens in the world -- the event journal (TICKET-0114). One happening
+of one of the world's event types (`event_type`, required since v2.25): its
+title and description, its place, how many when its type counts (`quantity`,
+1 or more), the session and day it was proposed in (`session_id`,
+`batch_id`, E1: the calendar of TICKET-0120 places it from them). Its
+participants by role are `event_participant`; who knows it is its fact's
+knowledge and scopes (`fact.event_id`, facet `evenement`, its title then its
+description): each character taking part holds a `knowledge` row at
+`knows`, secret or not as said (X1), and the fact's `fact_default` rows are
+its type's scopes made concrete unless the event says its own (W1).
+
+Written only by `writes/events.py` -- from the creator's journal
+(`cockpit/crud/events.py`) and from `_apply_mutation`'s `event_creation`, a
+model's proposal the creator approved (`event_payloads.py` reads its
+payload, typed or not). Never deleted (C3): a retraction empties its scopes.
+A model reads only an event whose type enters the chronicle: the MJ of Play
+the ones the player knows, the world tick the ones everyone knows (a
+`world` scope) -- `event_reads.py`.
+
+v2.25 (BRIEF-0114-D) dropped `type` (a type's `domain` now),
+`knowledge_status` (the fact's knowledge and scopes say it, v2.24 converted
+it), `has_magic_impact`, `consequences` and `occurred_at` (no reader, no
+value), and the table `event_entity` (its rows became `event_participant`
+at v2.24).
 
 ```sql
 CREATE TABLE event (
-  id                    TEXT PRIMARY KEY,
-  world_id              TEXT NOT NULL REFERENCES world(id),
-  session_id            TEXT REFERENCES session(id),
-  batch_id              TEXT REFERENCES batch(id),
-  title                 TEXT NOT NULL,
-  description           TEXT,
-  type                  TEXT,
-                        -- political | magical | criminal | military |
-                        -- social | mystery | other
-  knowledge_status      TEXT DEFAULT 'secret',
-                        -- secret | rumor | confirmed | public
-  location_id           TEXT REFERENCES entity(id),
-  has_magic_impact      BOOLEAN DEFAULT FALSE,
-  consequences          JSON,     -- changes applied to the world
-  occurred_at           DATETIME,
-  recorded_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
-  type_id               TEXT REFERENCES event_type(id),   -- v2.24
-  quantity              INTEGER                           -- v2.24
-);
-```
-
-`type_id` / `quantity` (v2.24, TICKET-0114, BRIEF-0114-A; F1, N1, D1): the
-world's event type this event is one of (`event_type`), and how many when
-its type counts (« 3 loups »). The v2.24 migration typed every earlier event
-by its former category -- the world's type named after that domain, one
-role « Impliqué » -- moved its `event_entity` rows into `event_participant`,
-and gave it its fact (`fact.event_id`, facet `evenement`): a `public` or
-`confirmed` event a `world` default at `knows`, a `secret` one none (O1).
-
-Two producers write this table (TICKET-0017/BRIEF-0017-a, no schema
-change), both through `_apply_mutation`'s `event_creation` branch ->
-`write_event` (the single canon-write site): a scope-level `world_tick`
-call for location/faction-scoped invocations (closed payload shape
-`{title, description, type, knowledge_status, involved_entities,
-location_id}`, quota-bounded), and the analyzer's conversation-sourced
-channel (minimal shape `{title, description, type, involved_entities}` —
-no `knowledge_status`/`location_id`, so this column's `DEFAULT 'secret'`
-applies). The model may propose `secret`/`public` only; `confirmed` is
-creator-reserved, accepted only at apply time. Duplicate guard is
-canon-existence (normalized title + `location_id`, same world), never
-tick_id/conversation-id equality, and applies to both producers alike.
-`session_id`/`batch_id` stay NULL for tick-sourced rows — the sibling
-`proposed_mutation` row's `tick_id`/`conversation_id` is the provenance
-anchor. Read by `context.py`'s MJ context assembler and the return-visit
-delta (TICKET-0016), both filtering `knowledge_status IN
-('public','confirmed')` at query construction. `involved_entities` (the
-payload key both producers still emit) is relationalized on write into
-`event_entity` — see below.
-
------
-
-### `event_entity`
-
-`event` <-> entity link (schema v1.79, TICKET-0025, BRIEF-0025-c —
-replaces the FK-less `event.involved_entities` JSON id array). Real FK
-integrity for the first time; membership queries are joins/EXISTS instead
-of a Python `in` over a JSON list.
-
-```sql
-CREATE TABLE event_entity (
-  id        TEXT PRIMARY KEY,
-  event_id  TEXT NOT NULL REFERENCES event(id),
-  entity_id TEXT NOT NULL REFERENCES entity(id)
+  id           TEXT PRIMARY KEY,
+  world_id     TEXT NOT NULL REFERENCES world(id),
+  session_id   TEXT REFERENCES session(id),
+  batch_id     TEXT REFERENCES batch(id),
+  type_id      TEXT NOT NULL REFERENCES event_type(id),
+  title        TEXT NOT NULL,
+  description  TEXT,
+  location_id  TEXT REFERENCES entity(id),
+  quantity     INTEGER CHECK (quantity IS NULL OR quantity >= 1),
+  recorded_at  DATETIME DEFAULT CURRENT_TIMESTAMP
 );
-CREATE UNIQUE INDEX idx_event_entity_unique ON event_entity(event_id, entity_id);
+CREATE INDEX idx_event_world ON event(world_id);
+CREATE INDEX idx_event_type ON event(type_id);
 ```
 
 -----
@@ -1794,7 +1765,8 @@ CREATE UNIQUE INDEX idx_event_sorte_name ON event_sorte(world_id, name COLLATE N
 ### `event_participant`
 
 Who took part in one event, in which role (V1): an entity or a sorte,
-exactly one. It replaces `event_entity` (dropped at v2.25). Written only by
+exactly one. It replaced `event_entity` (v1.79-v2.24, dropped at v2.25).
+Written only by
 `writes/events.py`.
 
 ```sql
````

2. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
3. Run the checks below, then the full corpus.

## Scope OUT

- The tick's typed producer -- the tick still emits the untyped shape, read by C-06 (TICKET-0119).
- Any condition reading events (E).
- A calendar to replace `occurred_at` -- TICKET-0120.
- Every later brief of this lot: BRIEF-0114-E, BRIEF-0114-F, BRIEF-0114-G, BRIEF-0114-H.

## Invariants to defend

INV-01 and INV-02: an event reaches the MJ only through the player's own knowledge -- a secret participant's fact never enters his context, by query construction (`known_chronicle_events`, ED1). INV-60: the boot guard moves to v2.25. A hidden attribute never reaches the MJ (WH1, ED2).

## Decision rights

STOP:
- The v2.25 migration's post-check fails on a copy of a v2.24 database.
- A reader of a dropped column remains that the diff does not rewrite (ED4 names it).
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- Log lines a check prints before its verdict (`[skip] …`, `[overhearing] …`): the analyzer's own logging.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`.
- `python tooling/verify/checks/event_contexts.py` -> `PASS`.
- `python tooling/verify/checks/event_writes.py` -> `PASS`.
- `python tooling/verify/checks/event_journal.py` -> `PASS`.
- `python tooling/verify/checks/visit_delta.py` -> `PASS`.
- `python tooling/verify/checks/json_ui_boundary.py` -> `PASS`.
- `python tooling/verify/checks/schema_version_agreement.py` -> `PASS`.
- `python tooling/verify/checks/world_tick.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (153 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **ED1** -- `event_reads.py` `_chronicle`: drop `, EventType.in_chronicle == True` from its `.where`
  - **ED2** -- `attributes.py` `perceived_states`: `if view.system or view.hidden or not applies_to(…)` -> `if view.system or not applies_to(…)`
  - **ED3** -- `migrate_v2_25_event_columns.py` `_refuse`: `if orphans:` -> `if False:`
  - **ED4** -- `event_reads.py`: add `def _dropped(e): return e.consequences` above `known_chronicle_events`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

Schema changelog v2.25 and `world-engine-schema.md` (in the diff); ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
