# AMENDMENT-0107-01 — the v2.16 post-check judges only the tables it writes

Ticket: TICKET-0107 "NPCs have skill sheets; a skill may require a master, and cannot be rolled until taught"   Lot: LOT-0107-npc-skills-masters.md
Brief in flight: none — found at the live gate (branch `ticket/0107`, PR #138)
Decision: post-check scope, Nia's live gate, 2026-10-06

## What deviated

C-01's post-check ran `PRAGMA foreign_key_check` on the whole database. On
prod it reported `('session', 2, 'world', 0)`: a `session` row whose world
no longer exists. The migration writes `skill`, `skill_definition` and
`character` only; that row predates it. The check aborted AFTER the DDL and
the 128 carrures had committed and BEFORE `schema_meta` converged, leaving
a v2.16-shaped database marked v2.15 (the cockpit refuses to boot), and a
second run aborts the same way.

## Amended contract (verbatim; the lot header carries the same text)

**C-01**, post-check: `PRAGMA foreign_key_check(<table>)` is empty for
`skill`, `skill_definition` and `character`; a dangling row elsewhere is
printed (« Note: <table> rowid <n> points to a missing <parent> row (not
written by this migration). ») and never stops the migration. A second run
on a half-migrated database (columns added, `physical_tier` dropped,
`schema_meta` still v2.15) converts nothing, passes the post-check and
converges `schema_meta`.

## Touched files

- `scripts/migrate_v2_16_npc_skills.py` — `_TOUCHED_TABLES`, the scoped
  check, the note, the docstring.
- `tooling/verify/checks/npc_skills.py` — A2's v2.15-shaped database holds a
  `session` row pointing to a missing world; A2b judges the three tables and
  requires the note on stdout.

No other brief changes: A2 is the only rule that runs the migration.

## Apply

On `ticket/0107`, save the block below to a file, `git apply --check`, then
`git apply`. Commit message:
`fix(skills): v2.16 post-check judges only its own tables (AMENDMENT-0107-01)`.

````diff
diff --git a/scripts/migrate_v2_16_npc_skills.py b/scripts/migrate_v2_16_npc_skills.py
index 710340d..211db63 100644
--- a/scripts/migrate_v2_16_npc_skills.py
+++ b/scripts/migrate_v2_16_npc_skills.py
@@ -22,7 +22,10 @@ while `character.physical_tier` exists.
 
 Post-checks, before `schema_meta` converges: both new columns exist,
 `character.physical_tier` is gone, every converted NPC holds its `physical`
-row at the mapped rank, and `PRAGMA foreign_key_check` is empty.
+row at the mapped rank, and `PRAGMA foreign_key_check` is empty on the three
+tables this migration changes (`skill`, `skill_definition`, `character`).
+A dangling reference elsewhere in the database predates it: it is listed,
+never a reason to stop (AMENDMENT-0107-01).
 
 Run from the project root:
 
@@ -61,6 +64,8 @@ from world_engine.skill_ranks import TIER_TO_RANK  # noqa: E402
 from world_engine.writes import write_skill_row  # noqa: E402
 
 _PREVIOUS_VERSION = "v2.15"
+# The tables this migration writes: the only ones its foreign-key post-check judges.
+_TOUCHED_TABLES = ("skill", "skill_definition", "character")
 
 
 def _version_key(version: str) -> tuple[int, int]:
@@ -144,9 +149,14 @@ def _post_checks(converted: dict[str, int]) -> None:
             if row is None or row.rank != rank:
                 raise SystemExit(f"Migration v2.16 aborted, post-check failed: NPC {npc_id} physical row {row}.")
     with engine.connect() as conn:
-        dangling = conn.execute(text("PRAGMA foreign_key_check")).fetchall()
+        dangling = [row for table in _TOUCHED_TABLES
+                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
+        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
+                     if row[0] not in _TOUCHED_TABLES]
     if dangling:
         raise SystemExit(f"Migration v2.16 aborted, post-check failed: foreign_key_check {dangling}.")
+    for table, rowid, parent, _fk in elsewhere:
+        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
     print(f"Post-check: columns in place; physical_tier dropped; {len(converted)} carrure(s) converted.")
 
 
diff --git a/tooling/verify/checks/npc_skills.py b/tooling/verify/checks/npc_skills.py
index 4d4138d..5e67942 100644
--- a/tooling/verify/checks/npc_skills.py
+++ b/tooling/verify/checks/npc_skills.py
@@ -22,7 +22,10 @@ A2 -- migration `scripts/migrate_v2_16_npc_skills.py`, on a v2.15-shaped
       NPC that held a row keeps it at rank 4, alone; `physical_tier` is
       gone, both new columns exist (the definition's `requires_master` 0),
       the three tables have the models' columns, `PRAGMA
-      foreign_key_check` is empty and `schema_meta` is the code's version;
+      foreign_key_check` is empty on those three tables, and `schema_meta`
+      is the code's version -- with a `session` row pointing to a missing
+      world in the database, which the migration lists and does not stop on
+      (AMENDMENT-0107-01);
    c. a second run exits zero and changes no row.
 A3 -- the rows a roll reads (fixture, D1). For the player:
    `skill_access.player_skill` on a base domain reads the base row; on a
@@ -207,6 +210,8 @@ def _seed_v215(db_path: str) -> dict:
                      (ids["world"],))
         conn.execute("INSERT INTO skill (id, character_id, domain, rank) VALUES ('held-phys', ?, 'physical', 4)",
                      (ids["held"],))
+        # A dangling reference this migration never wrote (AMENDMENT-0107-01).
+        conn.execute("INSERT INTO session (id, world_id, number) VALUES ('orphan-session', 'gone-world', 9)")
     return ids
 
 
@@ -222,7 +227,8 @@ def _state(db_path: str) -> dict:
             "shapes": {t: _shape(conn, t) for t in ("skill", "skill_definition", "character")},
             "skills": sorted(conn.execute("SELECT character_id, domain, rank, skill_definition_id FROM skill").fetchall()),
             "definitions": conn.execute("SELECT * FROM skill_definition").fetchall(),
-            "fk": conn.execute("PRAGMA foreign_key_check").fetchall(),
+            "fk": [r for t in ("skill", "skill_definition", "character")
+                   for r in conn.execute(f"PRAGMA foreign_key_check({t})").fetchall()],
         }
 
 
@@ -242,6 +248,8 @@ def check_a2(db_path: str) -> None:
     _set(db_path, "UPDATE character SET physical_tier = 0 WHERE id = ?", (ids["z"],))
     result = _run_migration(db_path)
     after = _state(db_path)
+    if result.returncode == 0 and "session rowid" not in result.stdout:
+        fail("A2b: the dangling session row was not listed")
     from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
     if result.returncode != 0 or after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
         fail(f"A2b: exit {result.returncode}, version {after['version']!r}: {result.stderr.strip()[-400:]}")
````

## Gate checks re-run

- `WORLD_ENGINE_ENV=test python tooling/verify/checks/npc_skills.py` -> PASS.
- Named mutation: the global `PRAGMA foreign_key_check` restored in the
  migration -> `A2b` red; reverted.
- A seeded v2.15 database, migrated by the unamended script, then marked
  v2.15 again with a dangling `session` row (Nia's state): the amended
  script prints the note, converts 0 carrures, converges to v2.16.
- `corpus_gate.py` -> 140/140.

## For the prod database

Nothing to restore: run the amended script again. It reports `0 carrure(s)
converted` (the 128 are already in), lists the `session` row, and moves
`schema_meta` to v2.16. To look at that row afterwards:

```sql
SELECT s.rowid, s.id, s.world_id, s.number FROM session s
LEFT JOIN world w ON w.id = s.world_id WHERE w.id IS NULL;
```
