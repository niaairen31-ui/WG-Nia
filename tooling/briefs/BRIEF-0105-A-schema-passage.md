<!-- slug: schema-passage -->
# BRIEF 0105-A — "v2.14: passage, the encounter's last contact, the outfit's preset"

Lot: LOT-0105-fact-learning.md (authoritative on conflict)
Depends on: nothing in this lot
Commit header for decisions: `(BRIEF-0105-a, schema v2.14)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0105`, on the tree the previous brief left (for A: cut from `main`), before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/schema_version.py:15` → `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.13"`; `world-engine-schema.md:3` → `Current schema version: v2.13`.
- `src/world_engine/models/ephemeral.py:169` → `class Rencontre(SQLModel, table=True):`; `:182` → `    source_ref: Optional[str] = None  # id of the visit/gathering/conversation/relation row` (its last field).
- `src/world_engine/models/__init__.py` imports `Rencontre` from `.ephemeral` and lists `"Rencontre"` in `__all__`; no `Passage` exists anywhere under `src/`.
- `src/world_engine/facets.py:44` → `    FacetSpec("tenue", "identite", "bloc", "none", "Tenue",`.
- `src/world_engine/writes/worlds.py:75` → `    "npc_schedule", "observation_run", "obstacle", "rencontre",` (in `_DIRECT_WORLD_SCOPED_DELETES`).
- `src/world_engine/writes/facts.py:187` → `def create_fact_default(` (keyword-only `world_id, fact_id, scope_type, scope_id, level, created_by`).
- `tooling/verify/checks/fact_facets.py:74` → `    ("tenue", "identite", "bloc", "none", ()),`.
- `tooling/verify/checks/world_cascade.py:104` → the `rencontre` fixture row (no `last_at`).
- `scripts/migrate_v2_13_lore_usage.py` exists; no `scripts/migrate_v2_14_*.py` and no `tooling/verify/checks/fact_learning.py` exist.
- `world-engine-schema.md:1978` → `### \`rencontre\``; the changelog's newest entry is `- **v2.13**`.

## Facts carried

### R-04 — visits [M]
Opened: `src/world_engine/models/ephemeral.py:134-154` (`Visit`, plain
`DateTime` `entered_at`); `src/world_engine/cockpit/routes/scene.py:150-160`.
Finding: a `visit` row is written only when a player enters a scene; it is
append-only.
Consequence: the migration backfills a player's passage from the latest
`entered_at` per place; nothing else reads `visit` here.

### R-10 — the facet registry [M]
Opened: `src/world_engine/facets.py:26-60` (`FacetSpec`; `tenue` presets
`none`, `physique` presets `rencontre`); `src/world_engine/writes/facets.py:
60-70` (`_preset_scope`: `rencontre` scopes the entity itself), `:143`,
`:339` (preset level `knows`); `tooling/verify/checks/fact_facets.py:69-90`
(`EXPECTED_FACETS`, five fields compared).
Finding: an outfit is known by nobody by default. `FacetSpec` is a frozen
dataclass with defaulted trailing fields.
Consequence: V1 changes `tenue`'s preset and its row in `EXPECTED_FACETS`;
F adds `edit_kind` as a defaulted field, outside the compared five.

### R-14 — the date of facts created by the v2.06 migration [M]
Opened: enumeration E6; `src/world_engine/models/canon.py:54-59`
(`_created_ts`: default `datetime.now(UTC)`).
Finding: the v2.06 migration sets no `created_at`; the facts and defaults it
created carry the migration's date, later than many encounters.
Consequence: Q1 — existing encounters are dated with the v2.14 migration's
time, taken after its own new defaults.

### R-15 — datetimes [M]
Opened: `src/world_engine/models/canon.py:54-59` (plain `DateTime`
columns); the installed `sqlmodel/sql/sqltypes.py` (`UTCDateTime`, used for
fields annotated `datetime` without `sa_column`: refuses a naive value on
write, returns aware UTC); `requirements.txt` (`sqlmodel>=0.0.16`).
Finding: `first_at` (and the new `last_at` fields) are plain annotations,
so their type depends on the installed SQLModel; `created_at`,
`entered_at`, `updated_at` read back naive.
Consequence: every comparison goes through `fact_versions.utc` (a naive
value is UTC); writers and fixtures use aware datetimes.

### R-17 — the checks the lot passes [M]
Opened: `tooling/verify/checks/encounter_registry.py:1-60` (R1-R4);
`knowledge_resolution.py:74-166, 247-352` (tier 2b nearest; C-09 case 4:
the encounter is recorded before the defaults); `lore_write.py:300-400`
(C1c, `_REFUSALS`, the `__f3__` substitution); `world_cascade.py:1-40,
67-120` (W1 coverage, W3 fixture); `fact_facets.py:116-145`;
`function_length.py` (80 lines); `npc_schedule.py`;
`single_canon_write.py`; `claude_md_contract.py` (38 000 characters, 100
per line); `frontend_build_fresh.py`; `effect_self_write.py`.
Finding: C-09 case 4 and tier 2b encode the rules B5 and C1 replace;
`passage` is world-scoped and must be cascaded.
Consequence: D amends the two fixtures (named in its Scope IN); A adds
`passage` to the cascade and its fixture.

### R-18 — the migration pattern [M]
Opened: `scripts/migrate_v2_13_lore_usage.py` (env guard, refusal below the
previous version, idempotent DDL, post-checks, `schema_meta` convergence);
`scripts/migrate_v2_12_zone_borde.py:60-130` (data steps through
`writes/`); `tooling/verify/checks/lore_usage.py:240-300` (U2: a
previous-shaped database, refusal, shape equality, second run).
Consequence: `migrate_v2_14_passage.py` and A2 follow both, by name.

### R-19 — production measurement (Nia, 2026-10-05)
`fact_default` 540 rows (world 328, rencontre 167, location 43, faction 2);
79 of 1,660 facts with history; 647 knowledge rows, 42 without text;
`rencontre` 223 (relation 166, gathering 31, visit 21, schedule 3,
conversation 2); 32 visits; 157 characters placed; 13 schedule rows; one
`tenue`, no default.
Consequence: the 43 place defaults change meaning (kept after leaving); the
migration's backfill covers the 157 placements so nobody loses a fact.

## Contracts

### C-01 — the registries (schema v2.14)
Produced by: BRIEF-0105-A   Consumed by: BRIEF-0105-B, D
`passage(id TEXT PK, world_id FK world NOT NULL, entity_id FK entity NOT
NULL, location_id FK entity NOT NULL, last_at DATETIME NOT NULL)`, UNIQUE
`idx_passage_entity_location(entity_id, location_id)`, index
`idx_passage_location(location_id)`; model `Passage` in
`models/ephemeral.py`, exported by `models`. `rencontre.last_at DATETIME`
nullable in SQL, `Optional[datetime]` in the model. Both cascaded with the
world (`_DIRECT_WORLD_SCOPED_DELETES`).
Error and empty cases: the migration refuses below v2.13; leaves no NULL
`last_at`.

## Context

Nia locked B5: knowledge through a place or an encounter is decided at read time from the date of the last contact, kept in two registries. This brief creates them, empty of behaviour: `passage` and `rencontre.last_at`, plus the outfit's `rencontre` preset (V1). The migration dates every existing encounter with its own time (Q1) and fills `passage` (M1). Nothing writes the registries yet (B) and nothing reads them yet (D).

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - in `models/ephemeral.py`, adds `Rencontre.last_at: Optional[datetime] = None` and the `Passage` model (C-01); exports `Passage` from `models`;
   - in `facets.py`, `tenue` presets `rencontre`; `fact_facets.py`'s `EXPECTED_FACETS` row follows;
   - bumps `EXPECTED_STATIC_SCHEMA_VERSION` and the schema doc header to v2.14; documents `passage` and `rencontre.last_at` in `world-engine-schema.md` (table section, index section); adds the v2.14 changelog entry;
   - adds `passage` to `writes/worlds.py::_DIRECT_WORLD_SCOPED_DELETES` and to `world_cascade.py`'s fixture (with `last_at` on the `rencontre` fixture row);
   - creates `scripts/migrate_v2_14_passage.py` (the v2.13 migration's shape: env guard, refusal below v2.13, idempotent DDL, post-checks, `schema_meta` convergence; data steps through `writes.facts.create_fact_default`, as v2.12 goes through `writes/`): tenue defaults first, then the migration's time on every undated encounter, then the passage backfill while `passage` is empty;
   - creates `tooling/verify/checks/fact_learning.py` with A1-A2 (A2 follows `lore_usage.py` U2: a previous-shaped database, refusal, shape equality, second run);
   - appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): passage and the encounter's last contact, schema v2.14 (BRIEF-0105-a)`.

````diff
diff --git a/scripts/migrate_v2_14_passage.py b/scripts/migrate_v2_14_passage.py
new file mode 100644
index 0000000..23d36a8
--- /dev/null
+++ b/scripts/migrate_v2_14_passage.py
@@ -0,0 +1,249 @@
+"""Migration v2.14 — what a character keeps of a fact: `passage`, and the
+last contact of an encounter (TICKET-0105, BRIEF-0105-A, decisions B5, M1,
+Q1, V1).
+
+1. DDL. Creates `passage` (`id, world_id, entity_id, location_id, last_at`,
+   UNIQUE index `idx_passage_entity_location`, index `idx_passage_location`)
+   and adds the nullable column `rencontre.last_at`.
+2. Tenue (V1). Every `tenue` fact with no `fact_default` row and exactly one
+   participant receives the `rencontre` default its facet now presets: scope
+   = that participant, level `knows`, through `writes.facts.
+   create_fact_default`. A `tenue` fact with zero or several participants is
+   listed, never changed.
+3. Encounters (Q1). Every `rencontre` row whose `last_at` is NULL gets the
+   migration's own time: everyone who has met is taken to have seen the
+   other as they are today. Taken AFTER step 2, so the new tenue defaults
+   are not newer than the contact that reveals them.
+4. Passages (M1), only while `passage` is empty: one row per (character,
+   location) for every character's current location and every NPC schedule
+   row (the migration's time), and for every `visit` row (the latest
+   `entered_at` of that player at that place). A later run finds the table
+   filled and writes nothing.
+
+Change histories are not touched: an entry without a `kind` reads as a
+correction (M1), so nobody's knowledge is stale after this migration.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.13 (the migrations are sequential).
+
+Idempotent: the table and the column are created only when missing; steps 2
+and 3 find nothing left to do on a second run; step 4 runs only on an empty
+table.
+
+Post-checks, before `schema_meta` converges: `passage` exists, no
+`rencontre` row has a NULL `last_at`, and every one-participant `tenue` fact
+has a `fact_default` row.
+
+Run from the project root:
+
+    python scripts/migrate_v2_14_passage.py
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
+        "migrate_v2_14_passage.py refuses to run without WORLD_ENGINE_ENV "
+        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+from sqlalchemy import inspect, text  # noqa: E402
+from sqlmodel import Session, select  # noqa: E402
+
+from world_engine import models  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+from world_engine.models import (  # noqa: E402
+    Character, Entity, Fact, FactDefault, FactParticipant, NpcSchedule, Passage, Rencontre, Visit,
+)
+from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
+from world_engine.writes.facts import create_fact_default  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.13"
+_CREATED_BY = "migrate_v2_14"
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
+            f"Migration v2.14 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _apply_ddl() -> list[str]:
+    applied: list[str] = []
+    inspector = inspect(engine)
+    with engine.begin() as conn:
+        if "passage" not in set(inspector.get_table_names()):
+            conn.execute(text(
+                """
+CREATE TABLE passage (
+  id           TEXT PRIMARY KEY NOT NULL,
+  world_id     TEXT NOT NULL REFERENCES world(id),
+  entity_id    TEXT NOT NULL REFERENCES entity(id),
+  location_id  TEXT NOT NULL REFERENCES entity(id),
+  last_at      DATETIME NOT NULL
+)
+"""
+            ))
+            conn.execute(text(
+                "CREATE UNIQUE INDEX idx_passage_entity_location ON passage(entity_id, location_id)"
+            ))
+            conn.execute(text("CREATE INDEX idx_passage_location ON passage(location_id)"))
+            applied.append("passage table + idx_passage_entity_location + idx_passage_location")
+        if "last_at" not in {c["name"] for c in inspector.get_columns("rencontre")}:
+            conn.execute(text("ALTER TABLE rencontre ADD COLUMN last_at DATETIME"))
+            applied.append("rencontre.last_at")
+    return applied
+
+
+def _participants(session: Session, fact_id: str) -> list[str]:
+    return list(session.exec(
+        select(FactParticipant.entity_id).where(FactParticipant.fact_id == fact_id)
+    ).all())
+
+
+def _tenue_defaults(session: Session) -> int:
+    defaulted = set(session.exec(select(FactDefault.fact_id)).all())
+    added = 0
+    for fact in session.exec(select(Fact).where(Fact.facet == "tenue")).all():
+        if fact.id in defaulted:
+            continue
+        owners = _participants(session, fact.id)
+        if len(owners) != 1:
+            print(f"  tenue {fact.id} has {len(owners)} participant(s): left without a default.")
+            continue
+        create_fact_default(
+            session, world_id=fact.world_id, fact_id=fact.id, scope_type="rencontre",
+            scope_id=owners[0], level="knows", created_by=_CREATED_BY,
+        )
+        added += 1
+    session.flush()
+    return added
+
+
+def _encounters(session: Session, now: datetime) -> int:
+    rows = session.exec(select(Rencontre).where(Rencontre.last_at.is_(None))).all()
+    for row in rows:
+        row.last_at = now
+        session.add(row)
+    session.flush()
+    return len(rows)
+
+
+def _utc(value: datetime) -> datetime:
+    """`visit.entered_at` reads back naive (plain `DateTime`); it is UTC."""
+    return value.replace(tzinfo=UTC) if value.utcoffset() is None else value.astimezone(UTC)
+
+
+def _passages(session: Session, now: datetime) -> int:
+    if session.exec(select(Passage.id)).first() is not None:
+        print("Table passage already filled — no backfill.")
+        return 0
+    latest: dict[tuple[str, str], tuple[str, datetime]] = {}
+
+    def keep(world_id: str, entity_id: str, location_id: str, at: datetime) -> None:
+        key = (entity_id, location_id)
+        if key not in latest or latest[key][1] < at:
+            latest[key] = (world_id, at)
+
+    for char, entity in session.exec(
+        select(Character, Entity).join(Entity, Entity.id == Character.id)
+        .where(Character.current_location_id.is_not(None))
+    ).all():
+        keep(entity.world_id, char.id, char.current_location_id, now)
+    for row in session.exec(select(NpcSchedule)).all():
+        keep(row.world_id, row.npc_id, row.location_id, now)
+    for row in session.exec(select(Visit)).all():
+        keep(row.world_id, row.player_id, row.location_id, _utc(row.entered_at) if row.entered_at else now)
+    for (entity_id, location_id), (world_id, at) in latest.items():
+        session.add(Passage(world_id=world_id, entity_id=entity_id,
+                            location_id=location_id, last_at=at))
+    session.flush()
+    return len(latest)
+
+
+def _apply_data() -> None:
+    with Session(engine) as session:
+        tenues = _tenue_defaults(session)
+        now = datetime.now(UTC)
+        encounters = _encounters(session, now)
+        passages = _passages(session, now)
+        session.commit()
+    print(f"Tenue defaults added: {tenues}. Encounters dated: {encounters}. "
+          f"Passages filled: {passages}.")
+
+
+def _post_checks() -> None:
+    if "passage" not in set(inspect(engine).get_table_names()):
+        raise SystemExit("Migration v2.14 aborted, post-check failed: passage is missing.")
+    with Session(engine) as session:
+        undated = session.exec(select(Rencontre.id).where(Rencontre.last_at.is_(None))).all()
+        if undated:
+            raise SystemExit(
+                f"Migration v2.14 aborted, post-check failed: {len(undated)} rencontre row(s) "
+                "without last_at."
+            )
+        defaulted = set(session.exec(select(FactDefault.fact_id)).all())
+        bare = [
+            fact.id for fact in session.exec(select(Fact).where(Fact.facet == "tenue")).all()
+            if fact.id not in defaulted and len(_participants(session, fact.id)) == 1
+        ]
+        if bare:
+            raise SystemExit(
+                f"Migration v2.14 aborted, post-check failed: tenue fact(s) without a "
+                f"default: {bare}."
+            )
+    print("Post-check: passage exists; every rencontre row is dated; every tenue has a default.")
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
+    print("Migration v2.14 — passage, rencontre.last_at, tenue defaults")
+    _refuse_if_behind()
+    applied = _apply_ddl()
+    print("Applied: " + ", ".join(applied) + "." if applied else "DDL already applied.")
+    _apply_data()
+    _post_checks()
+    _converge_schema_meta()
+    print("\nMigration v2.14 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/facets.py b/src/world_engine/facets.py
index 240dd77..dbbfd84 100644
--- a/src/world_engine/facets.py
+++ b/src/world_engine/facets.py
@@ -41,7 +41,7 @@ _SPECS = (
               "Une position sociale, une charge ou un rang que l'entité occupe."),
     FacetSpec("physique", "identite", "bloc", "rencontre", "Physique",
               "Ce que l'on voit durablement de l'entité : corps, visage, allure."),
-    FacetSpec("tenue", "identite", "bloc", "none", "Tenue",
+    FacetSpec("tenue", "identite", "bloc", "rencontre", "Tenue",
               "Ce que l'entité porte en ce moment et qui peut changer."),
     FacetSpec("description", "identite", "bloc", "public_world", "Description",
               "La présentation générale de l'entité."),
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index dfd8654..8812f84 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -91,6 +91,7 @@ from .ephemeral import (
     LinkBatchRow,
     NpcBatch,
     NpcBatchRow,
+    Passage,
     Rencontre,
     Session,
     Visit,
@@ -178,6 +179,7 @@ __all__ = [
     "PromptVariable",
     "PromptVersion",
     "Visit",
+    "Passage",
     "Rencontre",
     "ENCOUNTER_SOURCES",
     "UnresolvedMention",
diff --git a/src/world_engine/models/ephemeral.py b/src/world_engine/models/ephemeral.py
index 1e3fd69..2b50481 100644
--- a/src/world_engine/models/ephemeral.py
+++ b/src/world_engine/models/ephemeral.py
@@ -180,6 +180,37 @@ class Rencontre(SQLModel, table=True):
     first_at: datetime
     source: str             # in ENCOUNTER_SOURCES
     source_ref: Optional[str] = None  # id of the visit/gathering/conversation/relation row
+    # Last contact between the pair (schema v2.14, TICKET-0105, B5). Set to
+    # `first_at` on creation and moved forward by every later encounter except
+    # a `relation` one (L1); the one column of `rencontre` that is ever
+    # updated, only by `encounters.py`. Nullable in SQL because SQLite cannot
+    # add a NOT NULL column without a constant default; the v2.14 migration
+    # fills every row and the writer always sets it.
+    last_at: Optional[datetime] = None
+
+
+# -----------------------------------------------------------------------------
+# passage  (last time a character was at a location — schema v2.14,
+# TICKET-0105, BRIEF-0105-A, B5). One row per (character, location) pair;
+# `last_at` is the last moment the character was there (entering, leaving,
+# or a schedule naming the place). Written ONLY by `passages.py`, from every
+# placement write (P1); never deleted except by the world cascade. NOT in
+# canon_write_policy.txt's CANON_TABLES -- non-canon bookkeeping like
+# `visit` and `rencontre`. Read by the `location` tier of
+# `knowledge_resolve.py`.
+# -----------------------------------------------------------------------------
+class Passage(SQLModel, table=True):
+    __tablename__ = "passage"
+    __table_args__ = (
+        Index("idx_passage_entity_location", "entity_id", "location_id", unique=True),
+        Index("idx_passage_location", "location_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    entity_id: str = Field(foreign_key="entity.id", nullable=False)
+    location_id: str = Field(foreign_key="entity.id", nullable=False)
+    last_at: datetime
 
 
 # -----------------------------------------------------------------------------
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index c69cf2e..35b9ccf 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.13"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.14"
diff --git a/src/world_engine/writes/worlds.py b/src/world_engine/writes/worlds.py
index 1084ed7..24059cf 100644
--- a/src/world_engine/writes/worlds.py
+++ b/src/world_engine/writes/worlds.py
@@ -72,7 +72,7 @@ _DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
     "day_rewrite", "door", "fact", "fact_default", "fact_participant",
     "faction_role", "goal_agenda_link", "goal_prerequisite",
     "location_type_catalog", "lore_entry", "npc_goal", "npc_price",
-    "npc_schedule", "observation_run", "obstacle", "rencontre",
+    "npc_schedule", "observation_run", "obstacle", "passage", "rencontre",
     "skill_resolution", "skill_system", "unresolved_mention", "visit",
     "world_law",
 )
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index d93c90b..da28999 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17722,6 +17722,33 @@ longer be written from the Lore tool. Reactivates if a production
 measurement shows no `rencontre` pair involving anything but two
 characters.
 
+
+## WHAT A CHARACTER KEEPS OF A FACT (TICKET-0105) -- PASSAGE AND THE ENCOUNTER'S LAST CONTACT (BRIEF-0105-a, schema v2.14)
+
+**B5.** Knowing a fact through a place or an encounter is decided at read
+time from the date of the last contact, never by writing knowledge rows.
+Two registries hold that date: `passage`, one row per (character,
+location) with `last_at`, and `rencontre.last_at`, the last contact of a
+pair. `last_at` is the one column of `rencontre` that is ever updated
+(only by `encounters.py`); it is nullable in SQL because SQLite adds no
+NOT NULL column without a constant default, and every writer sets it.
+
+**V1.** The `tenue` facet presets `rencontre`: an outfit is learned by
+meeting its wearer, like the physique. The migration gives the existing
+one-participant `tenue` facts that default.
+
+**M1, Q1.** The migration dates every existing encounter with its own time
+(everyone who has met has seen the other as they are today), fills
+`passage` from current locations, NPC schedules and visits, and leaves
+change histories alone: an entry without a `kind` reads as a correction,
+so nobody's knowledge is stale after it.
+
+**Rejected.** Q2, `last_at = first_at`: the physique facts the v2.06
+migration created carry that migration's date, so every older
+acquaintance would forget them. B4, writing knowledge rows at each
+contact: rows by the thousand and the end of read-time resolution;
+reactivates if a reader needs a stored row where only a default exists.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/fact_facets.py b/tooling/verify/checks/fact_facets.py
index 3ed6e50..f57a3bd 100644
--- a/tooling/verify/checks/fact_facets.py
+++ b/tooling/verify/checks/fact_facets.py
@@ -71,7 +71,7 @@ EXPECTED_FACETS = (
     ("appellation", "identite", "affirmation", "rencontre", ()),
     ("statut", "identite", "affirmation", "location", ()),
     ("physique", "identite", "bloc", "rencontre", ()),
-    ("tenue", "identite", "bloc", "none", ()),
+    ("tenue", "identite", "bloc", "rencontre", ()),
     ("description", "identite", "bloc", "public_world", ()),
     ("reputation", "identite", "affirmation", "location", ()),
     ("histoire", "interiorite", "affirmation", "none", ()),
diff --git a/tooling/verify/checks/fact_learning.py b/tooling/verify/checks/fact_learning.py
new file mode 100644
index 0000000..e7fcf77
--- /dev/null
+++ b/tooling/verify/checks/fact_learning.py
@@ -0,0 +1,223 @@
+"""G1 check for TICKET-0105 -- what a character keeps of a fact.
+
+The lot adds its pieces brief by brief; this check grows with it (the
+`lore_write.py` precedent, TICKET-0098). Each brief adds its rules here in
+the same commit.
+
+A1 -- schema (BRIEF-0105-A, v2.14). `passage` declares exactly the columns
+   `id, world_id, entity_id, location_id, last_at`, `last_at` NOT NULL, the
+   UNIQUE index `idx_passage_entity_location (entity_id, location_id)` and
+   the index `idx_passage_location (location_id)`; `rencontre` declares a
+   nullable `last_at`. The `tenue` facet presets `rencontre`.
+A2 -- migration `scripts/migrate_v2_14_passage.py`, on a v2.13-shaped
+   database (the current schema without `passage` and without
+   `rencontre.last_at`, `schema_meta` at v2.13), filled with: a character at
+   a place, an NPC with a schedule row at another place, a player with two
+   visits of a third place, an encounter dated 2020, a `tenue` fact with one
+   participant and no default, a `tenue` fact with two participants:
+   a. at v2.12 it refuses (non-zero exit) and creates nothing;
+   b. at v2.13 it creates `passage` and `rencontre.last_at` with the
+      model's shape, gives the one-participant `tenue` a `rencontre` default
+      on its participant at `knows` and leaves the other without one, dates
+      the encounter no earlier than that default, fills exactly the three
+      passages (the visit at its latest `entered_at`), and moves
+      `schema_meta` to the code's version;
+   c. a second run exits zero and changes no row.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that examines zero rows is a
+FAILURE.
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
+MIGRATION = ROOT / "scripts" / "migrate_v2_14_passage.py"
+
+FAILURES: list[str] = []
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
+# --- A1 ------------------------------------------------------------------------
+
+def check_a1() -> None:
+    from world_engine.facets import FACETS
+    from world_engine.models import Passage, Rencontre
+
+    table = Passage.__table__
+    columns = {c.name: c for c in table.columns}
+    if set(columns) != {"id", "world_id", "entity_id", "location_id", "last_at"}:
+        fail(f"A1: passage columns are {sorted(columns)}")
+    elif columns["last_at"].nullable:
+        fail("A1: passage.last_at is nullable")
+    indexes = {i.name: ([c.name for c in i.columns], bool(i.unique)) for i in table.indexes}
+    if indexes != {"idx_passage_entity_location": (["entity_id", "location_id"], True),
+                   "idx_passage_location": (["location_id"], False)}:
+        fail(f"A1: passage indexes are {indexes}")
+    last = Rencontre.__table__.columns.get("last_at")
+    if last is None or not last.nullable:
+        fail("A1: rencontre.last_at is missing or NOT NULL")
+    if FACETS["tenue"].preset != "rencontre":
+        fail(f"A1: the tenue facet presets {FACETS['tenue'].preset!r}")
+
+
+# --- A2 ------------------------------------------------------------------------
+
+def _run_migration(db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
+                          text=True, cwd=str(ROOT), timeout=120)
+
+
+def _shape(conn, table: str) -> list[tuple[str, int]]:
+    return [(r[1], r[3]) for r in conn.execute(f"PRAGMA table_info({table})")]
+
+
+def _seed(session) -> dict:
+    from datetime import UTC, datetime
+
+    from world_engine.models import (
+        Character, Entity, Location, NpcSchedule, Rencontre, SchemaMeta, Visit, World,
+    )
+    from world_engine.writes import attach_participants, create_fact
+
+    world = World(name="Learning A2", is_active=True)
+    session.add(world)
+    session.flush()
+    ids: dict = {"world": world.id}
+
+    def entity(etype: str, name: str) -> str:
+        row = Entity(world_id=world.id, type=etype, name=name)
+        session.add(row)
+        session.flush()
+        return row.id
+
+    for key in ("L1", "L2", "L3"):
+        ids[key] = entity("location", key)
+        session.add(Location(id=ids[key], parent_location_id=None))
+    for key, kind, place in (("C", "npc", "L1"), ("N", "npc", None), ("P", "player", None)):
+        ids[key] = entity("character", key)
+        session.add(Character(id=ids[key], world_id=world.id, character_type=kind,
+                              current_location_id=ids[place] if place else None))
+    session.flush()
+    session.add(NpcSchedule(world_id=world.id, npc_id=ids["N"], phase="soir",
+                            location_id=ids["L2"]))
+    ids["visit_last"] = datetime(2021, 3, 4, 5, 6, 7, tzinfo=UTC)
+    for at in (datetime(2020, 1, 1, tzinfo=UTC), ids["visit_last"]):
+        session.add(Visit(world_id=world.id, player_id=ids["P"], location_id=ids["L3"], entered_at=at))
+    lo, hi = sorted((ids["C"], ids["N"]))
+    session.add(Rencontre(world_id=world.id, entity_lo_id=lo, entity_hi_id=hi,
+                          first_at=datetime(2020, 1, 1, tzinfo=UTC), source="visit"))
+    for key, owners in (("T1", ["N"]), ("T2", ["N", "C"])):
+        fact = create_fact(session, world_id=world.id, content=key, created_by="check", facet="tenue")
+        session.flush()
+        attach_participants(session, fact=fact, entity_ids=[ids[o] for o in owners])
+        ids[key] = fact.id
+    if session.get(SchemaMeta, 1) is None:
+        session.add(SchemaMeta(id=1, static_version="v2.13"))
+    session.commit()
+    return ids
+
+
+def _to_v213(db_path: str, version: str) -> None:
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("DROP TABLE IF EXISTS passage")
+        if "last_at" in {r[1] for r in conn.execute("PRAGMA table_info(rencontre)")}:
+            conn.execute("ALTER TABLE rencontre DROP COLUMN last_at")
+        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))
+
+
+def _state(db_path: str) -> dict:
+    with sqlite3.connect(db_path) as conn:
+        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
+        state = {
+            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
+            "passage_shape": _shape(conn, "passage") if "passage" in tables else None,
+            "rencontre_shape": _shape(conn, "rencontre"),
+            "defaults": sorted(conn.execute(
+                "SELECT fact_id, scope_type, scope_id, level, created_at FROM fact_default").fetchall()),
+        }
+        state["passages"] = sorted(conn.execute(
+            "SELECT entity_id, location_id, last_at FROM passage").fetchall()) if "passage" in tables else None
+        has_last = "last_at" in {c for c, _ in state["rencontre_shape"]}
+        state["encounters"] = conn.execute(
+            "SELECT last_at FROM rencontre" if has_last else "SELECT NULL FROM rencontre").fetchall()
+    return state
+
+
+def check_a2(db_path: str) -> None:
+    from sqlmodel import Session
+
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    with Session(engine) as session:
+        ids = _seed(session)
+    engine.dispose()
+    with sqlite3.connect(db_path) as conn:
+        model_passage = _shape(conn, "passage")
+        model_rencontre = _shape(conn, "rencontre")
+    _to_v213(db_path, "v2.12")
+    result = _run_migration(db_path)
+    if result.returncode == 0 or _state(db_path)["passage_shape"] is not None:
+        fail(f"A2a: v2.12 was not refused (exit {result.returncode})")
+    _to_v213(db_path, "v2.13")
+    result = _run_migration(db_path)
+    after = _state(db_path)
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+    if result.returncode != 0 or after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
+        fail(f"A2b: exit {result.returncode}, version {after['version']!r}: "
+             f"{result.stderr.strip()[-300:]}")
+        return
+    if after["passage_shape"] != model_passage or after["rencontre_shape"] != model_rencontre:
+        fail(f"A2b: shapes {after['passage_shape']} / {after['rencontre_shape']} differ from the models")
+    tenue = [d for d in after["defaults"] if d[0] in (ids["T1"], ids["T2"])]
+    if [d[:4] for d in tenue] != [(ids["T1"], "rencontre", ids["N"], "knows")]:
+        fail(f"A2b: tenue defaults are {tenue}")
+    encounters = after["encounters"]
+    if len(encounters) != 1 or encounters[0][0] is None or (tenue and encounters[0][0] < tenue[0][4]):
+        fail(f"A2b: encounter dates {encounters} vs tenue default {tenue}")
+    passages = {(e, loc): at for e, loc, at in after["passages"] or []}
+    want = {(ids["C"], ids["L1"]), (ids["N"], ids["L2"]), (ids["P"], ids["L3"])}
+    if set(passages) != want:
+        fail(f"A2b: passages are {sorted(passages)}")
+    elif not str(passages[(ids["P"], ids["L3"])]).startswith("2021-03-04 05:06:07"):
+        fail(f"A2b: the visit passage is dated {passages[(ids['P'], ids['L3'])]}")
+    again = _run_migration(db_path)
+    if again.returncode != 0 or _state(db_path) != after:
+        fail(f"A2c: second run exit {again.returncode} or changed rows: {again.stdout.strip()[-200:]}")
+
+
+def main() -> int:
+    db_path = _fresh_db()
+    check_a1()
+    check_a2(db_path)
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: fact_learning -- v2.14 declares passage and the encounter's last "
+          "contact, presets tenue to rencontre, and migrates from v2.13 only")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index 5b7672c..26ae6fb 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -99,11 +99,13 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
     ("obstacle", {"id": "ob-{w}", "world_id": "{w}", "location_id": "{w}-loc"}),
     ("obstacle_vertex", {"id": "obv-{w}", "obstacle_id": "ob-{w}", "vertex_order": 0,
                          "x": 0.0, "y": 0.0}),
+    ("passage", {"id": "pas-{w}", "world_id": "{w}", "entity_id": "{w}-char",
+                 "location_id": "{w}-loc", "last_at": "2026-01-01 00:00:00"}),
     ("relation", {"id": "rel-{w}", "world_id": "{w}", "entity_a_id": "{w}-char",
                   "entity_b_id": "{w}-loc", "type": "knows"}),
     ("rencontre", {"id": "ren-{w}", "world_id": "{w}", "entity_lo_id": "{w}-char",
                    "entity_hi_id": "{w}-loc", "first_at": "2026-01-01 00:00:00",
-                   "source": "fixture"}),
+                   "last_at": "2026-01-01 00:00:00", "source": "fixture"}),
     ("session", {"id": "ses-{w}", "world_id": "{w}", "number": 1}),
     ("skill_system", {"id": "ss-{w}", "world_id": "{w}", "name": "s"}),
     ("visit", {"id": "vis-{w}", "world_id": "{w}", "player_id": "{w}-char",
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 5125032..eabcb3a 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,14 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.14** — TICKET-0105, BRIEF-0105-A: what a character keeps of a fact.
+  `passage` (one row per character and location, with the last time the
+  character was there) and `rencontre.last_at` (the last contact of a pair,
+  nullable in SQL). `migrate_v2_14_passage.py` gives every one-participant
+  `tenue` fact with no default the `rencontre` default its facet now
+  presets, dates every encounter with the migration's own time, fills
+  `passage` from current locations, NPC schedules and visits, and refuses a
+  database older than v2.13.
 - **v2.13** — TICKET-0103, BRIEF-0103-A: `lore_usage_event`, the Lore
   shell's usage journal (one row per writing or consultation step, with its
   payload and model exchanges, grouped by `attempt_id`). No `world_id` and no
diff --git a/world-engine-schema.md b/world-engine-schema.md
index 2d4c020..6a4a94a 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.13
+Current schema version: v2.14
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -1981,7 +1981,12 @@ Encounter registry (schema v2.05, TICKET-0091, BRIEF-0091-A): one row per
 UNORDERED entity pair that has met — `entity_lo_id` < `entity_hi_id`,
 compared as strings; the earliest known encounter wins. Derived from play
 traces (visit, gathering, conversation) and authored state (schedule,
-relation), never edited by hand, never updated, never deleted. NOT a canon
+relation), never edited by hand, never deleted. `last_at` (schema v2.14,
+TICKET-0105) is the pair's last contact: set to `first_at` on creation and
+moved forward by every later encounter except a `relation` one -- the only
+column ever updated, only by `encounters.py`. Nullable in SQL (SQLite adds
+no NOT NULL column without a constant default); the v2.14 migration dated
+every existing row with its own time. NOT a canon
 table (`canon_write_policy.txt`) — non-canon bookkeeping like `visit`, with
 one writer (`encounters.py`). Read by the `rencontre` scope of
 `fact_default`. `source` in `ENCOUNTER_SOURCES` (`models/ephemeral.py`):
@@ -1996,7 +2001,8 @@ CREATE TABLE rencontre (
   entity_hi_id      TEXT NOT NULL REFERENCES entity(id),
   first_at          DATETIME NOT NULL,
   source            TEXT NOT NULL,
-  source_ref        TEXT
+  source_ref        TEXT,
+  last_at           DATETIME          -- last contact (v2.14); filled by every writer
 );
 CREATE UNIQUE INDEX idx_rencontre_pair ON rencontre(entity_lo_id, entity_hi_id);
 CREATE INDEX idx_rencontre_hi ON rencontre(entity_hi_id);
@@ -2004,6 +2010,31 @@ CREATE INDEX idx_rencontre_hi ON rencontre(entity_hi_id);
 
 -----
 
+### `passage`
+
+Place registry (schema v2.14, TICKET-0105, BRIEF-0105-A): one row per
+(character, location) pair; `last_at` is the last moment the character was
+there -- entering it, leaving it, or a schedule naming it. Written only by
+`passages.py`, from every placement write, never deleted except by the world
+cascade. NOT a canon table -- non-canon bookkeeping like `visit` and
+`rencontre`. Read by the `location` tier of `knowledge_resolve.py`: a
+`location` default is known to whoever was in its place, or in a place
+inside it, after the default was written.
+
+```sql
+CREATE TABLE passage (
+  id                TEXT PRIMARY KEY,
+  world_id          TEXT NOT NULL REFERENCES world(id),
+  entity_id         TEXT NOT NULL REFERENCES entity(id),
+  location_id       TEXT NOT NULL REFERENCES entity(id),
+  last_at           DATETIME NOT NULL
+);
+CREATE UNIQUE INDEX idx_passage_entity_location ON passage(entity_id, location_id);
+CREATE INDEX idx_passage_location ON passage(location_id);
+```
+
+-----
+
 ### `unresolved_mention`
 
 Name-resolution worklist (schema v2.05, TICKET-0091, BRIEF-0091-A): a name
@@ -2584,6 +2615,10 @@ CREATE UNIQUE INDEX idx_rencontre_pair ON rencontre(entity_lo_id, entity_hi_id);
 CREATE INDEX idx_rencontre_hi ON rencontre(entity_hi_id);
 CREATE INDEX idx_unresolved_mention_world_open ON unresolved_mention(world_id, resolved_at);
 
+-- place registry: one row per (character, location) (schema v2.14, BRIEF-0105-A)
+CREATE UNIQUE INDEX idx_passage_entity_location ON passage(entity_id, location_id);
+CREATE INDEX idx_passage_location ON passage(location_id);
+
 -- agendas: by owner + status (schema v1.72, BRIEF-0018-a)
 CREATE INDEX idx_agenda_owner_status ON agenda(owner_entity_id, status);
 
````

## Scope OUT

- Writing `passage` or moving `last_at` from play (B).
- Any change to resolution (D) or to a reader (E).
- Defaults for a `tenue` with zero or several participants: listed by the migration, never guessed.
- Running the migration on Nia's database: that is the live gate, after a backup.
- Any `NOT NULL` rebuild of `rencontre` (SQLite cannot add one without a constant default).
- Every later brief of this lot.

## Invariants to defend

**History is sacred:** the migration only adds rows and dates a column that did not exist; it rewrites no history. **Schema is authoritative:** the model, the migration's DDL and the schema doc declare the same shape (A2b compares them). **The app refuses to boot on a version mismatch:** constant, doc header and `schema_meta` move together. `passage` is not canon: it stays out of `canon_write_policy.txt`.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `schema_version_agreement.py` or `schema_partition.py` fails after the bump.
- A2 finds the model's shape and the migrated shape different.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- The migration's printed counts on the check's fixture.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/fact_learning.py` → `PASS: fact_learning -- v2.14 declares passage and the encounter's last contact, presets tenue to rencontre, and migrates from v2.13 only`.
- `fact_facets.py`, `world_cascade.py`, `schema_version_agreement.py`, `schema_partition.py`, `env_guard.py` → `PASS`.
- Mutation test: in the migration's `_encounters`, `row.last_at = now` → `row.last_at = row.first_at` → `A2b`; revert.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 138/138.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Schema v2.14 in `world-engine-schema.md` (header, `rencontre`, `passage`, index section) and `world-engine-schema-changelog.md` — in the diff. Decision entry `WHAT A CHARACTER KEEPS OF A FACT (TICKET-0105) -- PASSAGE AND THE ENCOUNTER'S LAST CONTACT (BRIEF-0105-a, schema v2.14)` — in the diff.
