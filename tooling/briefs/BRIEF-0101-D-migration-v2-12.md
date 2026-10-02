<!-- slug: migration-v2-12 -->
# BRIEF 0101-D — "Migration v2.12"

Lot: LOT-0101-zones.md (authoritative on conflict)
Depends on: A (C-01, C-02, C-03); C by choice (see the lot's dependency graph)
Commit header for decisions: `(BRIEF-0101-d, schema v2.12)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- BRIEFS 0101-A to -C are committed.
- `src/world_engine/schema_version.py:15` → `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.11"`
- `src/world_engine/models/canon_knowledge.py:38` → `            unique=True, sqlite_where=text("type NOT IN ('connects_to','controls')"),`
- `world-engine-schema.md:3` → `Current schema version: v2.11`; `:2468` → `  WHERE type NOT IN ('connects_to','controls');`; the NOTE ending `by the \`knowledge\` rows on the lien fact.` before the `### \`fact\`` section
- `world-engine-schema-changelog.md:16` → `- **v2.11** — TICKET-0098, BRIEF-0098-B: the lore writing path's source`
- `tooling/verify/checks/lore_write.py:205` → `    if result.returncode != 0 or counts != [0, 0] or version != "v2.11":`
- `scripts/migrate_v2_11_lore_entry.py:52` → `_PREVIOUS_VERSION = "v2.10"`
- `ls scripts/migrate_v2_12_zone_borde.py` → no such file

## Facts carried

### R-01 — `Relation` model [M]
Opened: `src/world_engine/models/canon_knowledge.py:23-61` (the model).
Finding: no status column; `type` a free `str`; `change_history` a non-null
JSON list. `idx_relation_oriented_social (entity_a_id, entity_b_id)`, unique,
`sqlite_where=text("type NOT IN ('connects_to','controls')")` (`:36-39`),
commented as a re-typing of `RELATION_GRAPH_EXCLUDED_TYPES`.
Consequence: a relation is retyped in place or hard-deleted, never closed
(N1). `borde` in the structural split is DDL on this index (D).

### R-14 — checks that read this vocabulary [M]
Opened: `tooling/verify/checks/relation_graph.py:83-120` (implementation);
`known_reachability.py:303-335` (`DOCUMENTED_MODULES`);
`knowledge_identity.py:31-35, 109-113` (`_SUBJECT_CENSUS`);
`lore_write.py:185-210` (W2); `migrate_v2_11_lore_entry.py:142-156`
(`_converge_schema_meta`).
Finding: `relation_graph.py` resolves the tuple by regex on a literal;
`known_reachability.py` fails on any new module spelling `"connects_to"`
until it is listed (and classified in `tooling/tickets/connects-to-readers-
TICKET-0082.md`); `knowledge_identity.py` pins every file's count of
`subject` references; `lore_write.py` W2b pinned `"v2.11"` as the version
the v2.11 migration converges to — the migration converges to the code
constant.
Consequence: the tuple stays a literal; `zone_rules.py` (A) and
`writes/zone_promotion.py` (C) are listed and classified; the latter's three
`discoverable_detail.subject` reads join the census; W2b compares to the
constant (D).

### R-16 — schema version and migrations [M]
Opened: `src/world_engine/schema_version.py:15`; `world-engine-schema.md:3,
562-585, 2462-2468`; `world-engine-schema-changelog.md:14-20`;
`scripts/migrate_v2_11_lore_entry.py` (whole); `migrate_v2_00_
connects_to_facts.py:1-35` (data-only migration bumped the version).
Finding: v2.11; migrations refuse an older `schema_meta`, are idempotent,
post-check before converging `schema_meta` to the constant.
Consequence: v2.12, same shape (D).

## Contracts

### C-01 — `zone_rules.py` (family)
Produced by: A   Consumed by: A, B, C, D, E, F
Pure reads, a session's pending rows included (autoflush).
| function | returns | rule |
|---|---|---|
| `active_child_ids(db, location_id, *, exclude_id=None)` | `list[str]` | ids of ACTIVE `location` entities whose `parent_location_id` is `location_id`, oldest first (`entity.created_at`, then id), `exclude_id` left out |
| `is_zone(db, location_id)` | `bool` | at least one active child; None → False |
| `zone_ids(db, world_id)` | `set[str]` | distinct non-null parents of the world's active locations |
| `geographic_link_type(db, a, b)` | `"borde"` \| `"connects_to"` | `borde` iff either end is a zone |
| `require_visitable(db, location_id, *, what)` | `None` | raises `ZoneRefusal(ValueError)` « {what} : « {name} » est une zone, on ne peut s'y trouver que dans l'un de ses lieux » when a zone; None passes |
Written before any member; re-read after `require_visitable` (B's use).

### C-02 — L1/V1 in `write_relation`
Produced by: A   Consumed by: every caller of `write_relation`
Judged on a NEW row and on a `mode="set"` row whose type changes, before
anything is mutated (`_require_map_shape`): a retype into or out of
`MAP_TOPOLOGY_TYPES` raises; a geographic row whose two ends are not both
`location` entities raises; a geographic type other than
`geographic_link_type(a, b)` raises — all `ValueError`. An existing row
whose type does not change is never judged. A new `borde` row births one
fact, `borde_fact_content(token_a, token_b)`, `facet='lien'`,
`default_level='knows'`; a `connects_to` ↔ `borde` change rewrites the fact
through `update_typed_fact_content`.

### C-03 — the vocabulary
Produced by: A   Consumed by: A, D, F
`RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str, str] = ("connects_to",
"borde", "controls")` (a literal); `MAP_TOPOLOGY_TYPES: tuple[str, str] =
("connects_to", "borde")`; `borde_fact_content(a, b) -> f"{a} borde {b}."`.

## Context

O1 puts `borde` in the social index's exclusion, which is DDL; N1 converts existing data in place; T1 reports, never moves. Nia's Aestia already has zones (the Secte du Phoenix) whose old `connects_to` rows would otherwise stay traversable into a place one cannot stand in. This brief is the `migration` danger class: live gate, no auto-merge, a manual backup first (`python scripts/backup.py`).

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `scripts/migrate_v2_12_zone_borde.py`;
   - `models/canon_knowledge.py`: the index predicate excludes `'borde'`;
   - `schema_version.py`: `v2.12`;
   - `world-engine-schema.md`: header, a NOTE on zones and `borde`, the index DDL; `world-engine-schema-changelog.md`: the v2.12 entry;
   - `lore_write.py`: W2b compares with `EXPECTED_STATIC_SCHEMA_VERSION` (R-14);
   - `tooling/verify/checks/zone_migration.py`;
   - the decision entry above the footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Named mutations, each run with `python tooling/verify/checks/zone_migration.py`, then restored:
   - in the migration, change `    for rel in touching:` to `    for rel in touching[:0]:` → the migration's own post-check aborts and the check prints `FAIL: (b) vacuous-proof …`;
   - replace `    rebuilt = _rebuild_index()` with `    rebuilt = False` → the same;
   - in `_report`, replace the two lines `    for line in lines:` / `        print(line)` with `    for char in session.exec(select(Character).where(Character.current_location_id.in_(zones))).all():` / `        char.current_location_id = None` / `    for line in lines:` / `        print(line)` → `FAIL: (c) the NPC was moved`.
4. Do NOT run the migration on `prod` in this session. The test database: `WORLD_ENGINE_ENV=test python scripts/migrate_v2_12_zone_borde.py` must print `Migration v2.12 applied.`; a second run prints `already fully applied — zero writes`.
5. Commit message: `feat(zones): migration v2.12 — borde in the social index, existing zones converted (BRIEF-0101-d)`.

````diff
diff --git a/scripts/migrate_v2_12_zone_borde.py b/scripts/migrate_v2_12_zone_borde.py
new file mode 100644
index 0000000..8faa558
--- /dev/null
+++ b/scripts/migrate_v2_12_zone_borde.py
@@ -0,0 +1,220 @@
+"""Migration v2.12 — `borde`, the geographic link that touches a zone
+(TICKET-0101, BRIEF-0101-D, decisions O1, N1, T1).
+
+1. Index (O1). `idx_relation_oriented_social` is rebuilt with the predicate
+   `type NOT IN ('connects_to','borde','controls')` — the same split as
+   `relation_orientation.RELATION_GRAPH_EXCLUDED_TYPES`. The new predicate
+   covers a subset of the old one's rows, so the rebuild cannot fail on
+   existing data.
+2. Conversion (N1). Every `connects_to` row touching a location that is
+   already a zone (`zone_rules.zone_ids`: at least one active child) is
+   retyped in place to `borde` through `writes.relations.write_relation
+   (mode="set")`: the row's previous state goes to its `change_history`,
+   its typed fact is rewritten (`borde_fact_content`) with the previous
+   content kept in the fact's `change_history`. No row is created or
+   deleted. Each conversion is printed.
+3. Report (T1). Characters, NPC schedule rows, items lying somewhere and
+   discoverable details that already sit in a zone are LISTED, never moved
+   — Nia corrects them through the fiche.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.11 (the migrations are sequential).
+
+Idempotent: the index is rebuilt only while its stored SQL lacks `'borde'`;
+a second run finds no `connects_to` touching a zone and writes nothing.
+
+Post-checks, before `schema_meta` converges: the stored index SQL names
+`'borde'`; zero `connects_to` rows touch a zone; the `relation` row count is
+unchanged.
+
+Run from the project root:
+
+    python scripts/migrate_v2_12_zone_borde.py
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
+        "migrate_v2_12_zone_borde.py refuses to run without WORLD_ENGINE_ENV "
+        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+from sqlalchemy import text  # noqa: E402
+from sqlmodel import Session, select  # noqa: E402
+
+from world_engine import models  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+from world_engine.models import (  # noqa: E402
+    Character, DiscoverableDetail, Entity, Item, NpcSchedule, Relation, World,
+)
+from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
+from world_engine.writes.relations import write_relation  # noqa: E402
+from world_engine.zone_rules import zone_ids  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.11"
+_INDEX = "idx_relation_oriented_social"
+_INDEX_DDL = (
+    f"CREATE UNIQUE INDEX {_INDEX} ON relation(entity_a_id, entity_b_id) "
+    "WHERE type NOT IN ('connects_to','borde','controls')"
+)
+_CHANGED_BY = "migrate_v2_12"
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
+            f"Migration v2.12 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _index_sql() -> str:
+    with engine.connect() as conn:
+        row = conn.execute(
+            text("SELECT sql FROM sqlite_master WHERE type = 'index' AND name = :name"), {"name": _INDEX}
+        ).first()
+    return row[0] if row is not None and row[0] else ""
+
+
+def _rebuild_index() -> bool:
+    if "'borde'" in _index_sql():
+        print(f"Index {_INDEX} already excludes 'borde' — nothing to do.")
+        return False
+    with engine.begin() as conn:
+        conn.execute(text(f"DROP INDEX IF EXISTS {_INDEX}"))
+        conn.execute(text(_INDEX_DDL))
+    print(f"Index {_INDEX} rebuilt: type NOT IN ('connects_to','borde','controls').")
+    return True
+
+
+def _zones_by_world(session: Session) -> dict[str, set[str]]:
+    return {w.id: zone_ids(session, w.id) for w in session.exec(select(World)).all()}
+
+
+def _names(session: Session, ids: set[str]) -> dict[str, str]:
+    if not ids:
+        return {}
+    return {e.id: e.name for e in session.exec(select(Entity).where(Entity.id.in_(ids))).all()}
+
+
+def _convert(session: Session, zones: set[str]) -> int:
+    rows = session.exec(select(Relation).where(Relation.type == "connects_to")).all()
+    touching = [r for r in rows if r.entity_a_id in zones or r.entity_b_id in zones]
+    names = _names(session, {r.entity_a_id for r in touching} | {r.entity_b_id for r in touching})
+    for rel in touching:
+        write_relation(
+            session, mode="set", relation_id=rel.id, type="borde", value=rel.intensity,
+            direction=rel.direction, visible_to_b=rel.visible_to_b, notes=rel.notes,
+            changed_by=_CHANGED_BY,
+        )
+        print(f"  borde: {names.get(rel.entity_a_id)} -- {names.get(rel.entity_b_id)} (relation {rel.id})")
+    return len(touching)
+
+
+def _report(session: Session, zones: set[str]) -> int:
+    """T1: what already sits in a zone, listed, never moved."""
+    if not zones:
+        return 0
+    names = _names(session, zones)
+    lines: list[str] = []
+    for char, ent in session.exec(
+        select(Character, Entity).join(Entity, Entity.id == Character.id)
+        .where(Character.current_location_id.in_(zones))
+    ).all():
+        lines.append(f"  personnage « {ent.name} » est dans la zone « {names[char.current_location_id]} »")
+    for row in session.exec(select(NpcSchedule).where(NpcSchedule.location_id.in_(zones))).all():
+        npc = session.get(Entity, row.npc_id)
+        lines.append(f"  horaire {row.phase} de « {npc.name if npc else row.npc_id} » vise la zone "
+                     f"« {names[row.location_id]} »")
+    for item, ent in session.exec(
+        select(Item, Entity).join(Entity, Entity.id == Item.id).where(Item.location_id.in_(zones))
+    ).all():
+        lines.append(f"  objet « {ent.name} » est posé dans la zone « {names[item.location_id]} »")
+    for detail in session.exec(select(DiscoverableDetail).where(DiscoverableDetail.location_id.in_(zones))).all():
+        lines.append(f"  détail « {detail.subject} » est dans la zone « {names[detail.location_id]} »")
+    for line in lines:
+        print(line)
+    return len(lines)
+
+
+def _post_checks(session: Session, relations_before: int) -> None:
+    if "'borde'" not in _index_sql():
+        raise SystemExit(f"Migration v2.12 aborted, post-check failed: {_INDEX} does not exclude 'borde'.")
+    zones = set().union(*_zones_by_world(session).values())
+    left = [
+        r.id for r in session.exec(select(Relation).where(Relation.type == "connects_to")).all()
+        if r.entity_a_id in zones or r.entity_b_id in zones
+    ]
+    if left:
+        raise SystemExit(f"Migration v2.12 aborted, post-check failed: connects_to still touches a zone: {left}")
+    after = session.exec(select(Relation)).all()
+    if len(after) != relations_before:
+        raise SystemExit(
+            f"Migration v2.12 aborted, post-check failed: relation rows {relations_before} -> {len(after)}."
+        )
+    print(f"Post-check: no connects_to touches a zone; relation rows unchanged ({relations_before}).")
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
+    print("Migration v2.12 — borde, the geographic link that touches a zone")
+    _refuse_if_behind()
+    rebuilt = _rebuild_index()
+    with Session(engine) as session:
+        relations_before = len(session.exec(select(Relation)).all())
+        converted = 0
+        reported = 0
+        for world_id, zones in _zones_by_world(session).items():
+            print(f"World {world_id}: {len(zones)} zone(s).")
+            converted += _convert(session, zones)
+            reported += _report(session, zones)
+        session.flush()
+        _post_checks(session, relations_before)
+        session.commit()
+    print(f"Converted {converted} connects_to -> borde; {reported} placement(s) in a zone reported "
+          "(not moved — correct them through the fiche).")
+    if not rebuilt and not converted:
+        print("Migration v2.12 already fully applied — zero writes.")
+    _converge_schema_meta()
+    print("\nMigration v2.12 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/models/canon_knowledge.py b/src/world_engine/models/canon_knowledge.py
index 87bf7a6..363f948 100644
--- a/src/world_engine/models/canon_knowledge.py
+++ b/src/world_engine/models/canon_knowledge.py
@@ -30,12 +30,13 @@ class Relation(SQLModel, table=True):
         Index("idx_relation_b", "entity_b_id"),
         Index("idx_relation_world", "world_id"),
         # At most one social row per oriented pair (TICKET-0090, schema
-        # v2.04). The predicate is the same social/structural split as
+        # v2.04; `borde` joined at v2.12, TICKET-0101). The predicate is the
+        # same social/structural split as
         # `relation_orientation.RELATION_GRAPH_EXCLUDED_TYPES`, re-typed here
         # only because SQLite index predicates cannot import Python.
         Index(
             "idx_relation_oriented_social", "entity_a_id", "entity_b_id",
-            unique=True, sqlite_where=text("type NOT IN ('connects_to','controls')"),
+            unique=True, sqlite_where=text("type NOT IN ('connects_to','borde','controls')"),
         ),
     )
 
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index c6c5f15..d68deab 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.11"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.12"
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index c917d88..a3df818 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17552,6 +17552,18 @@ deferring: the lot would ship a path that breaks B1.
 **Rejected.** S2, a client-only dialog: any other write path would promote
 silently.
 
+## MIGRATION v2.12 (TICKET-0101) -- `borde` IN THE INDEX, EXISTING ZONES CONVERTED (BRIEF-0101-d, schema v2.12)
+
+**O1, N1, T1.** `idx_relation_oriented_social` excludes `borde` like the
+other two structural types. `migrate_v2_12_zone_borde.py` rebuilds it,
+retypes in place every `connects_to` touching a location that already has
+an active child (row and fact history kept, each conversion printed), and
+lists what already sits in a zone (characters, schedules, items, details)
+without moving it. Refuses a database older than v2.11; idempotent.
+
+**Rejected.** O2, the tuple alone with the index left as it was: the
+schema would claim `borde` is social.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/lore_write.py b/tooling/verify/checks/lore_write.py
index 56ba09c..54c02b1 100644
--- a/tooling/verify/checks/lore_write.py
+++ b/tooling/verify/checks/lore_write.py
@@ -202,7 +202,11 @@ def check_w2(db_path: str) -> None:
         version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0]
         counts = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                   for t in ("lore_entry", "lore_entry_row")] if result.returncode == 0 else None
-    if result.returncode != 0 or counts != [0, 0] or version != "v2.11":
+    # The migration converges `schema_meta` to the code constant, which moves
+    # on with every later migration (v2.12, TICKET-0101) -- never a pinned literal.
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+
+    if result.returncode != 0 or counts != [0, 0] or version != EXPECTED_STATIC_SCHEMA_VERSION:
         fail(f"W2b: first run exit {result.returncode}, counts {counts}, version {version!r}: "
              f"{result.stderr.strip()[-200:]}")
     again = _run_migration(db_path)
diff --git a/tooling/verify/checks/zone_migration.py b/tooling/verify/checks/zone_migration.py
new file mode 100644
index 0000000..5ff8d60
--- /dev/null
+++ b/tooling/verify/checks/zone_migration.py
@@ -0,0 +1,231 @@
+"""G1 check for TICKET-0101 (BRIEF-0101-D) — migration v2.12.
+
+Self-contained: a fresh temp-file SQLite database is built from the models,
+then turned back into a v2.11-shaped one (the old
+`idx_relation_oriented_social` predicate, `schema_meta` at v2.11) holding
+the state the migration exists for: a location Z that has an active child C
+and still a `connects_to` to V (written before C existed, as on a real v2.11
+database), a `connects_to` V-W between two visitable locations, and an NPC
+standing in Z with its `matin` schedule at Z. The migration runs as a
+subprocess against that file (WORLD_ENGINE_DATABASE_URL), exactly as Nia runs
+it. Zero outcomes in any assertion is a FAIL.
+
+Four assertions:
+  a. On a database at v2.10 the script exits non-zero and changes nothing.
+  b. After a run at v2.11: the stored index SQL names `'borde'`;
+     `schema_meta.static_version` is the code constant; Z-V is the same
+     relation row, now `borde`, its `change_history` one longer, its fact
+     content `borde_fact_content(...)` with the old content in the fact's
+     `change_history`; V-W is untouched (`connects_to`, same history).
+  c. T1: the output names the NPC standing in Z and its schedule; the NPC
+     and its schedule row are still at Z (reported, never moved).
+  d. A second run prints the zero-writes line and changes no relation row.
+
+Named mutations: drop `_convert`'s `write_relation` call -> (b);
+skip `_rebuild_index` -> (b); make `_report` move the NPC -> (c).
+"""
+from __future__ import annotations
+
+import os
+import pathlib
+import subprocess
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src"
+MIGRATION = ROOT / "scripts" / "migrate_v2_12_zone_borde.py"
+OLD_INDEX = (
+    "CREATE UNIQUE INDEX idx_relation_oriented_social ON relation(entity_a_id, entity_b_id) "
+    "WHERE type NOT IN ('connects_to','controls')"
+)
+
+FAILURES: list[str] = []
+COUNTS: dict[str, int] = {}
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_engine():
+    tmp_dir = tempfile.mkdtemp()
+    db_path = pathlib.Path(tmp_dir) / "check.db"
+    url = f"sqlite:///{db_path}"
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = url
+    sys.path.insert(0, str(SRC))
+    for name in list(sys.modules):
+        if name == "world_engine" or name.startswith("world_engine."):
+            del sys.modules[name]
+
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    return engine, url
+
+
+def _set_version(engine, version: str) -> None:
+    from sqlalchemy import text
+
+    with engine.begin() as conn:
+        conn.execute(text("DELETE FROM schema_meta"))
+        conn.execute(text("INSERT INTO schema_meta (id, static_version, updated_at) "
+                          "VALUES (1, :v, CURRENT_TIMESTAMP)"), {"v": version})
+
+
+def _seed(engine) -> dict[str, str]:
+    from sqlalchemy import text
+    from sqlmodel import Session
+
+    from world_engine.models import Character, Entity, Location, NpcSchedule, World
+    from world_engine.writes.relations import write_relation
+
+    with engine.begin() as conn:
+        conn.execute(text("DROP INDEX IF EXISTS idx_relation_oriented_social"))
+        conn.execute(text(OLD_INDEX))
+    ids: dict[str, str] = {}
+    with Session(engine) as db:
+        world = World(name="Migration check", is_active=True)
+        db.add(world)
+        db.commit()
+        ids["world"] = world.id
+        for label in ("Z", "V", "W"):
+            entity = Entity(world_id=world.id, type="location", name=f"Lieu {label}")
+            db.add(entity)
+            db.flush()
+            db.add(Location(id=entity.id))
+            db.commit()
+            ids[label] = entity.id
+        for a, b in (("Z", "V"), ("V", "W")):
+            rel = write_relation(db, mode="set", world_id=world.id, entity_a_id=ids[a], entity_b_id=ids[b],
+                                 type="connects_to", value=50, direction="mutual")
+            db.commit()
+            ids[a + b] = rel.id
+        child = Entity(world_id=world.id, type="location", name="Lieu C")
+        db.add(child)
+        db.flush()
+        db.add(Location(id=child.id, parent_location_id=ids["Z"]))
+        npc = Entity(world_id=world.id, type="character", name="Sentinelle")
+        db.add(npc)
+        db.flush()
+        db.add(Character(id=npc.id, world_id=world.id, character_type="npc", current_location_id=ids["Z"]))
+        db.add(NpcSchedule(world_id=world.id, npc_id=npc.id, phase="matin", location_id=ids["Z"]))
+        db.commit()
+        ids["C"], ids["N"] = child.id, npc.id
+    return ids
+
+
+def _run(url: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=url)
+    env.pop("WORLD_ENGINE_ENV", None)
+    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True, text=True, cwd=ROOT)
+
+
+def _snapshot(engine, ids):
+    from sqlmodel import Session
+
+    from world_engine.models import Relation
+
+    with Session(engine) as db:
+        return {k: (db.get(Relation, ids[k]).type, len(db.get(Relation, ids[k]).change_history or []))
+                for k in ("ZV", "VW")}
+
+
+def _index_sql(engine) -> str:
+    from sqlalchemy import text
+
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT sql FROM sqlite_master WHERE name = 'idx_relation_oriented_social'")).first()
+    return row[0] if row else ""
+
+
+def check_a_refusal(engine, url, ids) -> None:
+    _set_version(engine, "v2.10")
+    before = _snapshot(engine, ids)
+    proc = _run(url)
+    COUNTS["a"] = 1 if proc.returncode != 0 else 0
+    if proc.returncode == 0:
+        fail("(a) the migration ran on a v2.10 database")
+    if _snapshot(engine, ids) != before or "'borde'" in _index_sql(engine):
+        fail("(a) the refused run changed the database")
+
+
+def check_b_c_run(engine, url, ids) -> str:
+    from sqlalchemy import text
+    from sqlmodel import Session, select
+
+    from world_engine.models import Character, NpcSchedule, Relation
+    from world_engine.prose_render import entity_token
+    from world_engine.relation_orientation import borde_fact_content
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+    from world_engine.writes.relations import lien_fact_of
+
+    _set_version(engine, "v2.11")
+    before = _snapshot(engine, ids)
+    proc = _run(url)
+    if proc.returncode != 0:
+        fail(f"(b) the migration failed: {proc.stderr[-400:]}")
+        return ""
+    n = 0
+    n += _ok("'borde'" in _index_sql(engine), "(b) the index predicate does not exclude 'borde'")
+    with engine.connect() as conn:
+        version = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).scalar()
+    n += _ok(version == EXPECTED_STATIC_SCHEMA_VERSION, f"(b) schema_meta at {version!r}")
+    after = _snapshot(engine, ids)
+    n += _ok(after["ZV"] == ("borde", before["ZV"][1] + 1), f"(b) Z-V after the run: {after['ZV']}")
+    n += _ok(after["VW"] == before["VW"], f"(b) V-W changed: {before['VW']} -> {after['VW']}")
+    with Session(engine) as db:
+        fact = lien_fact_of(db, db.get(Relation, ids["ZV"]))
+        expected = borde_fact_content(entity_token(ids["Z"], "Lieu Z"), entity_token(ids["V"], "Lieu V"))
+        n += _ok(fact is not None and fact.content_raw == expected and len(fact.change_history or []) == 1,
+                 "(b) Z-V fact not rewritten with its history")
+        COUNTS["b"] = n
+        m = _ok("Sentinelle" in proc.stdout and "horaire matin" in proc.stdout,
+                "(c) the report does not name the NPC and its schedule in the zone")
+        m += _ok(db.get(Character, ids["N"]).current_location_id == ids["Z"], "(c) the NPC was moved")
+        row = db.exec(select(NpcSchedule).where(NpcSchedule.npc_id == ids["N"])).one()
+        m += _ok(row.location_id == ids["Z"],
+                 "(c) the schedule was moved")
+        COUNTS["c"] = m
+    return proc.stdout
+
+
+def _ok(cond: bool, msg: str) -> int:
+    if not cond:
+        fail(msg)
+        return 0
+    return 1
+
+
+def check_d_rerun(engine, url, ids) -> None:
+    before = _snapshot(engine, ids)
+    proc = _run(url)
+    n = _ok(proc.returncode == 0 and "zero writes" in proc.stdout, f"(d) second run: {proc.stdout[-200:]}")
+    n += _ok(_snapshot(engine, ids) == before, "(d) the second run changed a relation")
+    COUNTS["d"] = n
+
+
+def main() -> int:
+    engine, url = _fresh_engine()
+    ids = _seed(engine)
+    check_a_refusal(engine, url, ids)
+    check_b_c_run(engine, url, ids)
+    check_d_rerun(engine, url, ids)
+
+    for key in ("a", "b", "c", "d"):
+        if not COUNTS.get(key):
+            fail(f"({key}) vacuous-proof: zero outcomes examined")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print(
+        "PASS: zone_migration — "
+        f"(a) refuses a v2.10 database [{COUNTS['a']}], (b) index + in-place borde [{COUNTS['b']}], "
+        f"(c) T1 reports, never moves [{COUNTS['c']}], (d) idempotent [{COUNTS['d']}]"
+    )
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 996762d..fecefea 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,13 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.12** — TICKET-0101, BRIEF-0101-D: `borde`, the geographic link that
+  touches a zone. `idx_relation_oriented_social` is rebuilt with the
+  predicate `type NOT IN ('connects_to','borde','controls')`;
+  `migrate_v2_12_zone_borde.py` retypes every `connects_to` touching a
+  location that already has an active child to `borde` in place (row and
+  fact history kept), reports what already sits in a zone without moving
+  it, and refuses a database older than v2.11. No table or column change.
 - **v2.11** — TICKET-0098, BRIEF-0098-B: the lore writing path's source
   record — `lore_entry` (the creator's statement, the clarification
   questions and her answers) and `lore_entry_row` (one row per canon row a
diff --git a/world-engine-schema.md b/world-engine-schema.md
index a34d582..919a408 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.11
+Current schema version: v2.12
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -581,6 +581,15 @@ CREATE TABLE relation (
 --       `default_level='unaware'`). `visible_to_b` is dead weight, kept for
 --       one ticket and read by no play path: who knows the feeling is carried
 --       by the `knowledge` rows on the lien fact.
+-- NOTE (schema v2.12, TICKET-0101): `borde` is the second location map
+--       topology type, structurally isolated like `connects_to`. A location
+--       with at least one active child is a ZONE (derived from
+--       `location.parent_location_id`, never stored). `connects_to` joins two
+--       visitable (childless) locations and is the only traversable link;
+--       `borde` is the link whenever a zone is an endpoint, never traversed.
+--       The type is derived from the endpoints at write time; a `borde` row
+--       carries one typed fact ("A borde B.", `default_level='knows'`). A
+--       zone that loses its last child keeps its `borde` rows.
 
 -----
 
@@ -2462,10 +2471,11 @@ CREATE INDEX idx_npc_goal_npc_status ON npc_goal(npc_id, status);
 CREATE INDEX idx_relation_a          ON relation(entity_a_id);
 CREATE INDEX idx_relation_b          ON relation(entity_b_id);
 CREATE INDEX idx_relation_world      ON relation(world_id);
--- at most one social row per oriented pair (schema v2.04, TICKET-0090)
+-- at most one social row per oriented pair (schema v2.04, TICKET-0090;
+-- `borde` excluded since v2.12, TICKET-0101)
 CREATE UNIQUE INDEX idx_relation_oriented_social
   ON relation(entity_a_id, entity_b_id)
-  WHERE type NOT IN ('connects_to','controls');
+  WHERE type NOT IN ('connects_to','borde','controls');
 
 -- character lookups by location and owning user
 CREATE INDEX idx_character_location  ON character(current_location_id);
````

## Scope OUT

- Moving anything the report lists (T1: Nia corrects through the fiche).
- Any new column or table (none is needed: the type is a free string, R-01).
- Converting a `borde` back to `connects_to` for a zone that lost its children (K: links stay).
- Running the migration on `prod` (Nia, at the live gate, after a backup).

## Invariants to defend

- **The app refuses to boot on a version mismatch** (CLAUDE.md): doc, constant and migration all say v2.12; `schema_version_agreement.py` holds it.
- **History is sacred**: conversions retype in place through `write_relation`; no row is created or deleted (post-check on the row count).
- **`schema_meta` is migration-only**: converged at the end, after the post-checks, as every migration does.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- A named mutation of Scope IN does not fail as stated.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- The migration fails on the test database, or its second run writes anything.
- `schema_version_agreement.py` fails.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- Any Svelte warning printed for a file this brief does not touch.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff plus `tooling/standards/DECISIONS_INDEX.md`.
- `zone_migration.py` → `PASS: zone_migration — (a) refuses a v2.10 database [1], (b) index + in-place borde [5], (c) T1 reports, never moves [3], (d) idempotent [2]`.
- `lore_write.py`, `schema_version_agreement.py`, `decisions_index.py` → `PASS`.
- The three named mutations failed as stated; item 4's two runs printed as stated.
- `corpus_gate.py` → 133/133.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Schema changelog entry v2.12, schema doc header, NOTE and index, decision entry `MIGRATION v2.12 (TICKET-0101) -- \`borde\` IN THE INDEX, EXISTING ZONES CONVERTED (BRIEF-0101-d, schema v2.12)` — in the diff.
