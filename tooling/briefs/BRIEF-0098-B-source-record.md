<!-- slug: source-record -->
# BRIEF 0098-B — "The source record: lore_entry, lore_entry_row, v2.11"

Lot: LOT-0098-lore-writing.md (authoritative on conflict)
Depends on: BRIEF-0098-A (textual: `lore_write.py`, the decision registry)
Commit header for decisions: `(BRIEF-0098-b, schema v2.11)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0098`, on the tree the previous brief left, before applying anything. Halt if one has moved.

- `src/world_engine/schema_version.py:15` → `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.10"`; `world-engine-schema.md:3` → `Current schema version: v2.10`
- `src/world_engine/writes/worlds.py:58` → `    ("day_mention_choice_evidence", "choice_id", "day_mention_choice"),` then `)`
- `src/world_engine/writes/worlds.py:73` → `    "location_type_catalog", "npc_goal", "npc_price",`
- `tooling/verify/checks/world_cascade.py:86` → `    ("location_type_catalog", {"id": "ltc-{w}", "world_id": "{w}", "name": "t"}),`
- `src/world_engine/models/pipeline.py:315` → `# skill_resolution  (one row per arbiter classification — the action`
- `tooling/verify/checks/lore_write.py:44` → `_LORE_WRITE_FILES: frozenset[str] = frozenset()` (A's census)
- `scripts/migrate_v2_11_lore_entry.py` → does not exist

## Facts carried

### R-03 — schema version plumbing [M]
Opened: `src/world_engine/schema_version.py:15` (`"v2.10"`),
`world-engine-schema.md:3`, `world-engine-schema-changelog.md` (newest entry
first), `scripts/migrate_v2_07_day_mention_choice.py` (whole file: env
guard, per-object idempotence, post-checks, `schema_meta` convergence).
Finding: the constant, the doc header and the newest changelog entry move
together (`schema_version_agreement.py`).
Consequence: B bumps all three to v2.11 and copies the v2.07 script's
structure; it adds a refusal below v2.10.

### R-04 — the world cascade [M]
Opened: `src/world_engine/writes/worlds.py:39-78` (the two table lists);
`tooling/verify/checks/world_cascade.py:1-35` (W1-W6), `:60-110` (`_FIXTURE`).
Finding: every world-reaching table must be named in
`_DIRECT_WORLD_SCOPED_DELETES` or as a child in `_SUBQUERY_SCOPED_DELETES`,
and once in `_FIXTURE` (W1, W3).
Consequence: B adds `lore_entry` (direct) and `("lore_entry_row",
"entry_id", "lore_entry")` (subquery), and two fixture rows.

### R-05 — where non-canon tables live [M]
Opened: `src/world_engine/models/pipeline.py:1-15` (module docstring),
`:200-315`; `tooling/verify/canon_write_policy.txt` `[CANON_TABLES]`.
Finding: `pipeline.py` holds the non-canon record tables (`day_mention_*`,
`skill_resolution`); none is in `[CANON_TABLES]`. `json_ui_boundary.py`
forbids UI-visible data in JSON.
Consequence: `LoreEntry` / `LoreEntryRow` go in `pipeline.py`, before
`skill_resolution`; questions and answers are plain TEXT, not JSON.

## Contracts

### C-04 — the source record
Produced by: B (tables), C (writer)   Consumed by: C, E (`lore_write_read`)
- `lore_entry(id, world_id FK, statement NOT NULL, questions, answers,
  created_at)`, index `idx_lore_entry_world(world_id, created_at)`.
- `lore_entry_row(id, entry_id FK, row_table CHECK in
  LORE_ENTRY_ROW_TABLES, row_id, action CHECK in created|updated)`, UNIQUE
  `idx_lore_entry_row_entry(entry_id, row_table, row_id)`.
- `writes/lore_entries.py`: `write_lore_entry(db, *, world_id, statement,
  questions=None, answers=None)` (empty statement -> ValueError, blanks ->
  NULL); `record_entry_row(db, *, entry_id, row_table, row_id,
  action="created")` (values outside the CHECK lists -> ValueError).
- `migrate_v2_11_lore_entry.py`: refuses below v2.10; creates both tables;
  idempotent; zero rows; converges `schema_meta` to v2.11.

## Context

The lot keeps every committed story and what it produced (B2 + M1). This brief adds the two record tables and their migration, with no writer yet (C writes them).

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: adds `LORE_ENTRY_ROW_TABLES`, `LORE_ENTRY_ROW_ACTIONS`, `LoreEntry`, `LoreEntryRow` to `models/pipeline.py` (before `skill_resolution`) and exports both classes from `models/__init__.py`; bumps `schema_version.py`, the schema doc header and DDL (two sections before `skill_resolution`), and the changelog to v2.11; creates `scripts/migrate_v2_11_lore_entry.py` (C-04); adds both tables to `writes/worlds.py` and two rows to `world_cascade.py`'s `_FIXTURE`; adds W1-W2 to `lore_write.py`; appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(schema): v2.11 lore_entry and lore_entry_row, the lore source record (BRIEF-0098-b)`.

````diff
diff --git a/scripts/migrate_v2_11_lore_entry.py b/scripts/migrate_v2_11_lore_entry.py
new file mode 100644
index 0000000..7e2e3c6
--- /dev/null
+++ b/scripts/migrate_v2_11_lore_entry.py
@@ -0,0 +1,173 @@
+"""Migration v2.11 — `lore_entry` and `lore_entry_row`, the lore writing
+path's source record (TICKET-0098, BRIEF-0098-B, decisions B2 + M1).
+
+Creates `lore_entry` (`id, world_id, statement, questions, answers,
+created_at`, index `idx_lore_entry_world`) and `lore_entry_row` (`id,
+entry_id, row_table, row_id, action`, CHECKs on `row_table` and `action`,
+UNIQUE index `idx_lore_entry_row_entry` on `(entry_id, row_table, row_id)`).
+
+Purely additive, zero rows created: both tables start empty and are filled
+only by commits from the Lore shell's writing panel going forward.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.10 (the migrations are sequential).
+
+Idempotent, per object independently (`migrate_v2_01_skill_system.py` rule):
+each table's existence is checked before creating it.
+
+Post-check, before commit: both tables exist and hold zero rows.
+
+Run from the project root:
+
+    python scripts/migrate_v2_11_lore_entry.py
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
+        "migrate_v2_11_lore_entry.py refuses to run without WORLD_ENGINE_ENV "
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
+from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.10"
+_TABLES = ("lore_entry", "lore_entry_row")
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
+            f"Migration v2.11 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _create_lore_entry() -> None:
+    with engine.begin() as conn:
+        conn.execute(text(
+            """
+CREATE TABLE lore_entry (
+  id          TEXT PRIMARY KEY,
+  world_id    TEXT NOT NULL REFERENCES world(id),
+  statement   TEXT NOT NULL,
+  questions   TEXT,
+  answers     TEXT,
+  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
+)
+"""
+        ))
+        conn.execute(text(
+            "CREATE INDEX idx_lore_entry_world ON lore_entry(world_id, created_at)"
+        ))
+
+
+def _create_lore_entry_row() -> None:
+    with engine.begin() as conn:
+        conn.execute(text(
+            """
+CREATE TABLE lore_entry_row (
+  id         TEXT PRIMARY KEY,
+  entry_id   TEXT NOT NULL REFERENCES lore_entry(id),
+  row_table  TEXT NOT NULL CHECK (row_table IN ('entity','fact','fact_participant',
+               'fact_default','knowledge','relation','faction_membership')),
+  row_id     TEXT NOT NULL,
+  action     TEXT NOT NULL CHECK (action IN ('created','updated'))
+)
+"""
+        ))
+        conn.execute(text(
+            "CREATE UNIQUE INDEX idx_lore_entry_row_entry "
+            "ON lore_entry_row(entry_id, row_table, row_id)"
+        ))
+
+
+def _apply_ddl() -> list[str]:
+    existing = set(inspect(engine).get_table_names())
+    applied: list[str] = []
+    if "lore_entry" not in existing:
+        _create_lore_entry()
+        applied.append("lore_entry table + idx_lore_entry_world")
+    else:
+        print("Table 'lore_entry' already exists — nothing to do.")
+    if "lore_entry_row" not in existing:
+        _create_lore_entry_row()
+        applied.append("lore_entry_row table + idx_lore_entry_row_entry")
+    else:
+        print("Table 'lore_entry_row' already exists — nothing to do.")
+    return applied
+
+
+def _post_checks() -> None:
+    missing = [t for t in _TABLES if t not in set(inspect(engine).get_table_names())]
+    if missing:
+        raise SystemExit(f"Migration v2.11 aborted, post-check failed: missing {missing}.")
+    with engine.connect() as conn:
+        for table in _TABLES:
+            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
+            if count != 0:
+                raise SystemExit(
+                    f"Migration v2.11 aborted, post-check failed: {table} holds {count} "
+                    "row(s), expected 0 — this migration creates zero rows."
+                )
+            print(f"Post-check: {table} row count = 0 (expected 0).")
+
+
+def _converge_schema_meta() -> None:
+    with Session(engine) as session:
+        row = session.get(models.SchemaMeta, 1)
+        if row is None:
+            session.add(models.SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
+            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
+        elif row.static_version != EXPECTED_STATIC_SCHEMA_VERSION:
+            previous = row.static_version
+            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
+            row.updated_at = datetime.now(UTC)
+            session.add(row)
+            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
+        else:
+            print(f"Row: schema_meta.id=1 already at {EXPECTED_STATIC_SCHEMA_VERSION!r} — nothing to do")
+        session.commit()
+
+
+def main() -> None:
+    print("Migration v2.11 — lore_entry, lore_entry_row")
+    _refuse_if_behind()
+    applied = _apply_ddl()
+    if applied:
+        print("Applied: " + ", ".join(applied) + ".")
+    else:
+        print("Migration v2.11 already fully applied — zero writes.")
+    _post_checks()
+    _converge_schema_meta()
+    print("\nMigration v2.11 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index 2671aa7..f9f7182 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -103,6 +103,8 @@ from .pipeline import (
     DayMentionResolution,
     DayMentionReview,
     DayRewrite,
+    LoreEntry,
+    LoreEntryRow,
     PassPlay,
     ProposedMutation,
     PromptTemplate,
@@ -147,6 +149,8 @@ __all__ = [
     "Batch",
     "PassPlay",
     "DayRewrite",
+    "LoreEntry",
+    "LoreEntryRow",
     "DayMentionResolution",
     "SkillResolution",
     "Gathering",
diff --git a/src/world_engine/models/pipeline.py b/src/world_engine/models/pipeline.py
index 998ee93..cfb3c3a 100644
--- a/src/world_engine/models/pipeline.py
+++ b/src/world_engine/models/pipeline.py
@@ -311,6 +311,56 @@ class DayMentionReview(SQLModel, table=True):
     created_at: datetime = _created_ts()
 
 
+# -----------------------------------------------------------------------------
+# lore_entry / lore_entry_row  (the lore writing path's source record, schema
+# v2.11, TICKET-0098, BRIEF-0098-B, decisions B2 + M1)
+#
+# One `lore_entry` per statement the creator committed from the Lore shell:
+# her text as she wrote it, the model's clarification questions and her
+# answers (plain text, NULL when the round was skipped). One `lore_entry_row`
+# per canon row that commit created or updated, so a story can be reread with
+# everything it produced. `row_id` carries no FK: it points into one of
+# several tables, named by `row_table`. Append-only, both (no UPDATE, no
+# DELETE outside the world cascade). Non-canon.
+# -----------------------------------------------------------------------------
+LORE_ENTRY_ROW_TABLES: tuple[str, ...] = (
+    "entity", "fact", "fact_participant", "fact_default", "knowledge",
+    "relation", "faction_membership",
+)
+LORE_ENTRY_ROW_ACTIONS: tuple[str, ...] = ("created", "updated")
+
+
+class LoreEntry(SQLModel, table=True):
+    __tablename__ = "lore_entry"
+    __table_args__ = (Index("idx_lore_entry_world", "world_id", "created_at"),)
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    statement: str
+    questions: Optional[str] = None
+    answers: Optional[str] = None
+    created_at: datetime = _created_ts()
+
+
+class LoreEntryRow(SQLModel, table=True):
+    __tablename__ = "lore_entry_row"
+    __table_args__ = (
+        Index("idx_lore_entry_row_entry", "entry_id", "row_table", "row_id", unique=True),
+        CheckConstraint(
+            "row_table IN ('entity','fact','fact_participant','fact_default','knowledge',"
+            "'relation','faction_membership')",
+            name="ck_lore_entry_row_table",
+        ),
+        CheckConstraint("action IN ('created','updated')", name="ck_lore_entry_row_action"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    entry_id: str = Field(foreign_key="lore_entry.id", nullable=False)
+    row_table: str
+    row_id: str
+    action: str
+
+
 # -------------------------------------------------------------------------
 # skill_resolution  (one row per arbiter classification — the action
 # lexicon's audit trail; schema v2.02, TICKET-0084)
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index d878993..c6c5f15 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.10"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.11"
diff --git a/src/world_engine/writes/worlds.py b/src/world_engine/writes/worlds.py
index 2f88ffb..1084ed7 100644
--- a/src/world_engine/writes/worlds.py
+++ b/src/world_engine/writes/worlds.py
@@ -56,6 +56,7 @@ _SUBQUERY_SCOPED_DELETES: tuple[tuple[str, str, str], ...] = (
     ("observation_run_template", "run_id", "observation_run"),
     ("day_mention_choice_candidate", "choice_id", "day_mention_choice"),
     ("day_mention_choice_evidence", "choice_id", "day_mention_choice"),
+    ("lore_entry_row", "entry_id", "lore_entry"),
 )
 
 # Direct world_id-scoped deletes — order free under the FK deferral.
@@ -70,7 +71,7 @@ _DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
     "day_mention_choice", "day_mention_resolution", "day_mention_review",
     "day_rewrite", "door", "fact", "fact_default", "fact_participant",
     "faction_role", "goal_agenda_link", "goal_prerequisite",
-    "location_type_catalog", "npc_goal", "npc_price",
+    "location_type_catalog", "lore_entry", "npc_goal", "npc_price",
     "npc_schedule", "observation_run", "obstacle", "rencontre",
     "skill_resolution", "skill_system", "unresolved_mention", "visit",
     "world_law",
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 01635d2..91cdd4c 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17239,6 +17239,23 @@ the cockpit ever listens beyond loopback, or another local tool must call
 the API. I3 (nothing now, authentication later): the writing route would
 ship open.
 
+## THE LORE WRITING PATH KEEPS ITS SOURCE (TICKET-0098) -- LORE_ENTRY AND LORE_ENTRY_ROW (BRIEF-0098-b, schema v2.11)
+
+**B2 + M1.** Every statement committed from the Lore shell is kept as a
+`lore_entry` (the text, the model's clarification questions, the creator's
+answers, as plain text), and every canon row the commit created or rewrote
+gets a `lore_entry_row` (`row_table`, `row_id`, `created|updated`), so a
+story can be reread with what it produced. `row_id` carries no FK because it
+points into several tables. Both tables are world-scoped, non-canon and
+append-only; they join the world cascade. v2.11 refuses a database older
+than v2.10.
+
+**Rejected.** M2 (bulk undo in this ticket): an undo must decide what to do
+with entities completed since, or facts learned in play; reactivates at the
+first injection the creator wants to take back. B3 (typed links between
+facts): reactivates if the day chain (A2) must follow a "why" from fact to
+fact.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/lore_write.py b/tooling/verify/checks/lore_write.py
index e439675..809f25c 100644
--- a/tooling/verify/checks/lore_write.py
+++ b/tooling/verify/checks/lore_write.py
@@ -8,6 +8,17 @@ L0 -- census. The files of the lore writing path that exist under
    `src/world_engine` (the glob `_CENSUS_GLOBS`) equal `_LORE_WRITE_FILES`
    exactly: a new module is red until a brief names it, a named module that
    is missing is red.
+W1 -- schema (BRIEF-0098-B, v2.11). `lore_entry` declares `world_id` (FK to
+   `world`) and the index `idx_lore_entry_world (world_id, created_at)`;
+   `lore_entry_row` declares `entry_id` (FK to `lore_entry`), the UNIQUE
+   index `idx_lore_entry_row_entry (entry_id, row_table, row_id)`, and CHECKs
+   whose literals equal `LORE_ENTRY_ROW_TABLES` and `LORE_ENTRY_ROW_ACTIONS`.
+W2 -- migration `scripts/migrate_v2_11_lore_entry.py`, on a v2.10-shaped
+   database (the current schema minus both tables, `schema_meta` at v2.10):
+   a. at v2.09 it refuses (non-zero exit) and creates nothing;
+   b. at v2.10 it creates both tables, empty, and moves `schema_meta` to
+      v2.11;
+   c. a second run changes nothing and exits zero.
 
 Fresh temp-file SQLite database for any fixture rule
 (`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
@@ -15,11 +26,17 @@ Nia's DB.
 """
 from __future__ import annotations
 
+import os
 import pathlib
+import re
+import sqlite3
+import subprocess
 import sys
+import tempfile
 
 ROOT = pathlib.Path(__file__).resolve().parents[3]
 SRC = ROOT / "src" / "world_engine"
+MIGRATION = ROOT / "scripts" / "migrate_v2_11_lore_entry.py"
 
 FAILURES: list[str] = []
 
@@ -42,13 +59,102 @@ def check_l0() -> None:
         fail(f"L0: {missing} is named in _LORE_WRITE_FILES but does not exist")
 
 
+def _check_literals(table, name: str, expected: tuple[str, ...]) -> None:
+    sql = next((str(c.sqltext) for c in table.constraints if getattr(c, "name", None) == name), None)
+    if sql is None:
+        fail(f"W1: {table.name} has no CHECK {name}")
+        return
+    got = tuple(re.findall(r"'([a-z_]+)'", sql))
+    if got != expected:
+        fail(f"W1: {name} lists {got}, expected {expected}")
+
+
+def _index(table, name: str):
+    return next((i for i in table.indexes if i.name == name), None)
+
+
+def check_w1() -> None:
+    from world_engine.models import LoreEntry, LoreEntryRow
+    from world_engine.models.pipeline import LORE_ENTRY_ROW_ACTIONS, LORE_ENTRY_ROW_TABLES
+
+    entry, row = LoreEntry.__table__, LoreEntryRow.__table__
+    if {fk.target_fullname for fk in entry.c.world_id.foreign_keys} != {"world.id"}:
+        fail("W1: lore_entry.world_id is not a FK to world.id")
+    idx = _index(entry, "idx_lore_entry_world")
+    if idx is None or [c.name for c in idx.columns] != ["world_id", "created_at"]:
+        fail("W1: idx_lore_entry_world is not (world_id, created_at)")
+    if {fk.target_fullname for fk in row.c.entry_id.foreign_keys} != {"lore_entry.id"}:
+        fail("W1: lore_entry_row.entry_id is not a FK to lore_entry.id")
+    idx = _index(row, "idx_lore_entry_row_entry")
+    if idx is None or not idx.unique or [c.name for c in idx.columns] != ["entry_id", "row_table", "row_id"]:
+        fail("W1: idx_lore_entry_row_entry is not UNIQUE (entry_id, row_table, row_id)")
+    _check_literals(row, "ck_lore_entry_row_table", LORE_ENTRY_ROW_TABLES)
+    _check_literals(row, "ck_lore_entry_row_action", LORE_ENTRY_ROW_ACTIONS)
+
+
+def _run_migration(db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
+                          text=True, cwd=str(ROOT), timeout=120)
+
+
+def _tables(db_path: str) -> set[str]:
+    with sqlite3.connect(db_path) as conn:
+        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
+
+
+def _set_version(db_path: str, version: str) -> None:
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("DROP TABLE IF EXISTS lore_entry_row")
+        conn.execute("DROP TABLE IF EXISTS lore_entry")
+        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))
+
+
+def check_w2(db_path: str) -> None:
+    from sqlmodel import Session
+
+    from world_engine.db import create_db_and_tables, engine
+    from world_engine.models import SchemaMeta
+
+    create_db_and_tables()
+    with Session(engine) as session:
+        if session.get(SchemaMeta, 1) is None:
+            session.add(SchemaMeta(id=1, static_version="v2.10"))
+            session.commit()
+    engine.dispose()
+    _set_version(db_path, "v2.09")
+    result = _run_migration(db_path)
+    if result.returncode == 0 or {"lore_entry", "lore_entry_row"} & _tables(db_path):
+        fail(f"W2a: v2.09 was not refused (exit {result.returncode})")
+    _set_version(db_path, "v2.10")
+    result = _run_migration(db_path)
+    with sqlite3.connect(db_path) as conn:
+        version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0]
+        counts = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
+                  for t in ("lore_entry", "lore_entry_row")] if result.returncode == 0 else None
+    if result.returncode != 0 or counts != [0, 0] or version != "v2.11":
+        fail(f"W2b: first run exit {result.returncode}, counts {counts}, version {version!r}: "
+             f"{result.stderr.strip()[-200:]}")
+    again = _run_migration(db_path)
+    if again.returncode != 0 or "nothing to do" not in again.stdout:
+        fail(f"W2c: second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
+
+
 def main() -> int:
+    tmp = tempfile.mkdtemp(prefix="lore_write_")
+    db_path = f"{tmp}/w.db"
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
     check_l0()
+    check_w1()
+    check_w2(db_path)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
-    print(f"PASS: lore_write -- census of {len(_LORE_WRITE_FILES)} module(s) holds")
+    print(f"PASS: lore_write -- census of {len(_LORE_WRITE_FILES)} module(s) holds; "
+          "v2.11 declares the source record and migrates from v2.10 only")
     return 0
 
 
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index f2fa539..5b7672c 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -84,6 +84,9 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
     ("link_batch_row", {"id": "lbr-{w}", "batch_id": "lb-{w}", "pair_a_id": "{w}-char",
                         "pair_b_id": "{w}-loc", "kind": "no_links", "payload": "{{}}"}),
     ("location_type_catalog", {"id": "ltc-{w}", "world_id": "{w}", "name": "t"}),
+    ("lore_entry", {"id": "le-{w}", "world_id": "{w}", "statement": "s"}),
+    ("lore_entry_row", {"id": "ler-{w}", "entry_id": "le-{w}", "row_table": "entity",
+                        "row_id": "{w}-char", "action": "created"}),
     ("npc_batch", {"id": "nb-{w}", "world_id": "{w}", "scope": "{{}}"}),
     ("npc_batch_row", {"id": "nbr-{w}", "batch_id": "nb-{w}", "line_index": 0,
                        "kind": "draft", "payload": "{{}}"}),
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 2f2e461..996762d 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,11 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.11** — TICKET-0098, BRIEF-0098-B: the lore writing path's source
+  record — `lore_entry` (the creator's statement, the clarification
+  questions and her answers) and `lore_entry_row` (one row per canon row a
+  commit created or updated). Additive, zero rows;
+  `migrate_v2_11_lore_entry.py` refuses a database older than v2.10.
 - **v2.10** — TICKET-0097, BRIEF-0097-G: `knowledge.subject` and
   `idx_knowledge_subject` dropped. `migrate_v2_10_drop_knowledge_subject.py`
   refuses to run before v2.09, and while a row's subject is neither
diff --git a/world-engine-schema.md b/world-engine-schema.md
index 44b260e..a34d582 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.10
+Current schema version: v2.11
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -1142,6 +1142,53 @@ CREATE INDEX idx_day_mention_review_choice ON day_mention_review(choice_id);
 
 -----
 
+### `lore_entry`
+
+The lore writing path's source record (schema v2.11, TICKET-0098,
+BRIEF-0098-B, decisions B2 + M1): one row per statement the creator committed
+from the Lore shell's writing panel — her text as written (`statement`), the
+model's clarification questions (`questions`, one per line) and her free-text
+answers (`answers`); both NULL when the clarification round was skipped.
+Append-only. Non-canon: it records where canon rows came from, it is never
+read as world truth.
+
+```sql
+CREATE TABLE lore_entry (
+  id          TEXT PRIMARY KEY,
+  world_id    TEXT NOT NULL REFERENCES world(id),
+  statement   TEXT NOT NULL,
+  questions   TEXT,
+  answers     TEXT,
+  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
+);
+CREATE INDEX idx_lore_entry_world ON lore_entry(world_id, created_at);
+```
+
+-----
+
+### `lore_entry_row`
+
+One row per canon row a `lore_entry` commit created or updated (schema v2.11,
+TICKET-0098, BRIEF-0098-B, M1), so a story can be reread with everything it
+produced. `row_id` carries no FK: it points into the table `row_table` names.
+`updated` marks a `bloc` fact rewritten in place. Append-only; the bulk undo
+of an entry is a later ticket (M2).
+
+```sql
+CREATE TABLE lore_entry_row (
+  id         TEXT PRIMARY KEY,
+  entry_id   TEXT NOT NULL REFERENCES lore_entry(id),
+  row_table  TEXT NOT NULL CHECK (row_table IN ('entity','fact','fact_participant',
+               'fact_default','knowledge','relation','faction_membership')),
+  row_id     TEXT NOT NULL,
+  action     TEXT NOT NULL CHECK (action IN ('created','updated'))
+);
+CREATE UNIQUE INDEX idx_lore_entry_row_entry
+  ON lore_entry_row(entry_id, row_table, row_id);
+```
+
+-----
+
 ### `skill_resolution`
 
 ```sql
````

## Scope OUT

- Any writer of the two tables (C).
- Running the migration on any database Nia uses: she runs it at the live gate.
- An FK on `lore_entry_row.row_id` (it points into several tables).
- JSON columns for the questions or answers (`json_ui_boundary.py`).
- Bulk undo (M2).
- Every later brief of the lot: BRIEF-0098-C, BRIEF-0098-D, BRIEF-0098-E, BRIEF-0098-F.

## Invariants to defend

**History is sacred:** both tables are append-only; nothing here updates or deletes them outside the world cascade. **The app refuses to boot on a schema mismatch:** the constant, the doc header and the changelog move together, and the migration converges `schema_meta` only after its post-checks.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `migrate_v2_11_lore_entry.py` run on a v2.10 test database does not end with `Migration v2.11 applied.`

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- Any Starlette/httpx deprecation warning printed by a check.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/lore_write.py` → `PASS` (W2 builds its own v2.10-shaped database).
- On a temp DB built from `main` before this lot (`init_db.py`, `seed_pilot.py` at v2.10): `migrate_v2_11_lore_entry.py` twice; the first run prints `Applied: lore_entry table + idx_lore_entry_world, lore_entry_row table + idx_lore_entry_row_entry.` and `'v2.10' -> 'v2.11'`; the second prints `nothing to do`.
- `world_cascade.py`, `schema_version_agreement.py`, `json_ui_boundary.py` → `PASS`.
- `corpus_gate.py` → 128/128.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

This brief carries its docs: schema doc v2.11 (two table sections), changelog v2.11, decision entry `THE LORE WRITING PATH KEEPS ITS SOURCE (TICKET-0098) … (BRIEF-0098-b, schema v2.11)`.
