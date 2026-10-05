<!-- slug: capture-contacts -->
# BRIEF 0105-B — "Every placement and every encounter is a contact"

Lot: LOT-0105-fact-learning.md (authoritative on conflict)
Depends on: BRIEF-0105-A (the registries)
Commit header for decisions: `(BRIEF-0105-b, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0105`, on the tree the previous brief left (for A: cut from `main`), before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/models/ephemeral.py` declares `Passage` and `Rencontre.last_at` (BRIEF-0105-A).
- `src/world_engine/encounters.py:38` → `def record_encounter(`; `:57` → `    if _find_pair(db, lo_id, hi_id) is not None:` followed by `        return None`.
- `src/world_engine/db.py:157` → `def get_session():`, the module's last function; `db.py` imports nothing from `world_engine` at module level.
- `src/world_engine/writes/config.py:49` → `from ..encounters import record_encounter`; `:413` → `def write_npc_schedule(`; `:478` → the `DELETE FROM npc_schedule WHERE npc_id = :npc_id` line; `:491` → `    _record_schedule_encounters(db, world_id=world_id, npc_id=npc_id, clean=clean)`.
- `src/world_engine/writes/characters.py:48` → `    character.current_location_id = to_location_id`; `src/world_engine/cockpit/play_stream.py:471` → `    char.current_location_id = location_id`.
- `tooling/verify/checks/encounter_registry.py:3-5` → the docstring says « never updated, never deleted ».
- `CLAUDE.md:447` → `│   ├── gathering.py, encounters.py  # NPC clustering; rencontre's sole writer (non-canon)`.

## Facts carried

### R-01 — where a character's place is written [M]
Opened: enumeration E1; `src/world_engine/writes/characters.py:28-50`
(`write_character_location`); `src/world_engine/cockpit/play_stream.py:471`;
`src/world_engine/cockpit/routes/creator.py:680-686`;
`src/world_engine/cockpit/crud/entities.py:344-347` (`_PLACEMENT_FIELDS`),
`:642`, `:805`; `src/world_engine/models/canon.py:143-168` (`Character`:
`world_id`, `current_location_id`).
Finding: six paths write `current_location_id` — travel (direct
assignment), the tick's NPC move and zone promotion (through
`write_character_location`), PC creation (constructor keyword), and the
fiche and batch creators (`ext_model(**ext_kwargs)` and `setattr`). No raw
SQL writes it. `Character` carries its own `world_id`.
Consequence: one `before_flush` listener sees every one of them, including
the two no static scan can (P1); it reads the attribute history for the
place left.

### R-02 — the encounter registry [M]
Opened: `src/world_engine/models/ephemeral.py:156-183` (`Rencontre`,
`ENCOUNTER_SOURCES`); `src/world_engine/encounters.py:1-132`; enumeration
E2.
Finding: one row per unordered pair; `record_encounter` returns `None` and
writes nothing when the pair exists (`:57-58`); `first_at` is the earliest
encounter. Seven live sites call the three recorders: scene visit,
gathering creation and migration, conversation start, gathering join,
schedule co-presence, social relation birth (`writes/relations.py:222-230`).
Consequence: `last_at` is added; an existing pair's `last_at` moves forward
on every source but `relation` (L1). `record_encounter`'s return contract is
kept.

### R-03 — schedules name places without moving anyone [M]
Opened: `src/world_engine/models/schedule.py:32-60` (`NpcSchedule`);
`src/world_engine/writes/config.py:413-512` (`write_npc_schedule`: DELETE at
`:478`, `_record_schedule_encounters` at `:491`);
`src/world_engine/schedule_reads.py:116-161` (`where_is`, `who_is_at`:
position computed at read time).
Finding: a schedule never writes `current_location_id`; an NPC "at the forge
each evening" is never placed there. `write_npc_schedule` is at the
80-line ceiling, and `npc_schedule.py` requires its DELETE inside it;
`single_canon_write.py` allows `npc_schedule` writes only from it.
Consequence: the schedule's passages are recorded by a helper called before
the DELETE (old rows still readable), which also records the encounters;
read time treats schedule places and slot co-presence as a contact right
now.

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

### C-02 — passages
Produced by: BRIEF-0105-B   Consumed by: BRIEF-0105-D (through C-01), E
`passages.record_passage(db, *, world_id, entity_id, location_id, at=None)
-> Passage`: creates the pair's row or moves `last_at` forward to `at`
(default now, UTC), never back; finds a pending row of the same flush.
`passages.record_passages(db, *, world_id, entity_id, location_ids,
at=None) -> None`: each distinct place. `passages.listener_registered() ->
bool`. The `before_flush` listener on `sqlalchemy.orm.Session` records, for
every `Character` new with a place or whose `current_location_id` changed,
the place entered and the place left, at the flush's time; `db.py` imports
`passages` at module end. `write_npc_schedule` records the passages of every
place its old and new rows name. No function commits.
Error and empty cases: a character without place records nothing.

### C-03 — the last contact of an encounter
Produced by: BRIEF-0105-B   Consumed by: BRIEF-0105-D
`encounters.record_encounter(...)` unchanged signature and return (new row
or `None`). A new row has `last_at = first_at = at`. An existing pair's
`last_at` moves forward to `at` unless `source == "relation"`; never back.

## Context

The registries exist (A). This brief fills them from every contact Nia counted in L1: any placement write, through one `before_flush` listener (P1); every play encounter, which now moves the pair's `last_at`; and schedules, which name places without moving anyone. A relation is not a contact.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `src/world_engine/passages.py` (C-02): `record_passage`, `record_passages`, the `before_flush` listener on `sqlalchemy.orm.Session` and `listener_registered`; `db.py` imports it at module end;
   - in `encounters.py`, a new pair gets `last_at = first_at`; an existing pair's `last_at` moves forward unless the source is `relation` (C-03); module docstring updated; `models/ephemeral.py`'s `rencontre` comment says only `last_at` moves;
   - in `writes/config.py`, `write_npc_schedule` calls a new `_record_schedule_contacts` just before its DELETE (old rows still readable), which records the encounters (the existing `_record_schedule_encounters`) and the passages of every old and new place; the function keeps its length and its DELETE;
   - updates `encounter_registry.py`'s docstring; adds B1-B4 to `fact_learning.py`; one CLAUDE.md invariant line and the file-structure line;
   - appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): every placement and encounter records its last contact (BRIEF-0105-b)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 43d9a39..d62394e 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -372,6 +372,9 @@ Law only. Rationale, chantier history, and deferred alternatives live in
   `creation_container_sizing.py`.
 - Inside a `$effect` body, a `$state` binding assigned there must not be read afterwards in the
   same body — enforced by `effect_self_write.py`.
+- `passage` is written only by `passages.py`, whose `before_flush` listener records every
+  placement write; `rencontre.last_at` moves forward only, in `encounters.py` -- enforced by
+  `fact_learning.py`.
 - **The lore renderer receives rows, never a `Session`,** and only the `answered` verdict reaches
   a model — every empty verdict is rendered by code, so an absence is never explained by a model.
 - **The Lore usage journal (`lore_usage_event`) is written only through `lore_usage` and read only
@@ -444,7 +447,7 @@ WG-Nia/
 │   ├── context*.py          # NPC/MJ assembly + exclusions; context_window.py: sliding-window seam
 │   ├── knowledge_resolve.py, facet_reads.py, prose_*.py  # level resolution; facet reads; tokens
 │   ├── tick*.py             # world-tick: orchestrate/assemble/normalize; sites in world_tick.py
-│   ├── gathering.py, encounters.py  # NPC clustering; rencontre's sole writer (non-canon)
+│   ├── gathering.py, encounters.py, passages.py  # clustering; rencontre's, passage's writers
 │   ├── ollama_client.py     # local Ollama HTTP client; think-stripping; ping()
 │   ├── analyzer*.py         # conversation-bound wrapper + conversation-agnostic judging core
 │   ├── observation_*.py     # observed-lane socle/engine/runner/reads/writes; per-NPC window
diff --git a/src/world_engine/db.py b/src/world_engine/db.py
index ecfebf7..f447fd3 100644
--- a/src/world_engine/db.py
+++ b/src/world_engine/db.py
@@ -158,3 +158,9 @@ def get_session():
     """Yield a database session (FastAPI dependency-friendly)."""
     with Session(engine) as session:
         yield session
+
+
+# Every placement write records a `passage` (TICKET-0105, BRIEF-0105-B, P1):
+# the listener attaches to the Session class when this module is imported, so
+# no session that reaches the engine can write a location without it.
+from world_engine import passages as _passages  # noqa: E402,F401
diff --git a/src/world_engine/encounters.py b/src/world_engine/encounters.py
index 10c1371..ad82ac9 100644
--- a/src/world_engine/encounters.py
+++ b/src/world_engine/encounters.py
@@ -5,7 +5,10 @@
 encounter winning. It is non-canon bookkeeping, like `visit` and
 `gathering` — derived from play traces (visit, gathering membership,
 conversation) and authored state (NPC schedules, social relations), never
-edited by hand, never updated, never deleted.
+edited by hand, never deleted. `last_at` (TICKET-0105, BRIEF-0105-B, B5) is
+the pair's last contact: `first_at` on creation, then moved forward -- never
+back -- by every later encounter except a `relation` one, which is not a
+contact (L1). It is the only column ever updated.
 
 This module is the ONLY site that adds a `Rencontre` row
 (`tooling/verify/checks/encounter_registry.py`). No function here commits;
@@ -35,6 +38,20 @@ def _find_pair(db: Session, lo_id: str, hi_id: str) -> Optional[Rencontre]:
     ).first()
 
 
+def _utc(value: datetime) -> datetime:
+    return value.replace(tzinfo=UTC) if value.utcoffset() is None else value.astimezone(UTC)
+
+
+def _touch(db: Session, row: Rencontre, when: datetime, source: str) -> None:
+    """Move an existing pair's `last_at` forward to `when`; a `relation`
+    encounter is not a contact (L1) and moves nothing."""
+    if source == "relation":
+        return
+    if row.last_at is None or _utc(row.last_at) < _utc(when):
+        row.last_at = when
+        db.add(row)
+
+
 def record_encounter(
     db: Session,
     *,
@@ -47,22 +64,27 @@ def record_encounter(
 ) -> Optional[Rencontre]:
     """Record that `a_id` and `b_id` have met. Returns the new row, or
     `None` for a self pair or a pair already recorded (idempotent: read
-    guard before add). `source` outside `ENCOUNTER_SOURCES` raises
-    `ValueError`. `at` defaults to now (UTC)."""
+    guard before add); an already recorded pair has its `last_at` moved
+    forward to `at` unless `source` is `relation`. `source` outside
+    `ENCOUNTER_SOURCES` raises `ValueError`. `at` defaults to now (UTC)."""
     if source not in ENCOUNTER_SOURCES:
         raise ValueError(f"record_encounter: invalid source {source!r}")
     if a_id == b_id:
         return None
+    when = at or datetime.now(UTC)
     lo_id, hi_id = _ordered(a_id, b_id)
-    if _find_pair(db, lo_id, hi_id) is not None:
+    existing = _find_pair(db, lo_id, hi_id)
+    if existing is not None:
+        _touch(db, existing, when, source)
         return None
     row = Rencontre(
         world_id=world_id,
         entity_lo_id=lo_id,
         entity_hi_id=hi_id,
-        first_at=at or datetime.now(UTC),
+        first_at=when,
         source=source,
         source_ref=source_ref,
+        last_at=when,
     )
     db.add(row)
     db.flush()
diff --git a/src/world_engine/models/ephemeral.py b/src/world_engine/models/ephemeral.py
index 2b50481..6e5c643 100644
--- a/src/world_engine/models/ephemeral.py
+++ b/src/world_engine/models/ephemeral.py
@@ -159,7 +159,8 @@ class Visit(SQLModel, table=True):
 # contract C-06). One row per UNORDERED entity pair (`entity_lo_id` <
 # `entity_hi_id`, compared as strings); the earliest known encounter wins.
 # Derived from play traces and authored state, never edited by hand, never
-# updated, never deleted. NOT in canon_write_policy.txt's CANON_TABLES —
+# deleted; only `last_at` moves forward (TICKET-0105, BRIEF-0105-B). NOT in
+# canon_write_policy.txt's CANON_TABLES —
 # non-canon bookkeeping like visit/gathering, with its own writer
 # (`encounters.py`, BRIEF-0091-C). No JSON column.
 # -----------------------------------------------------------------------------
diff --git a/src/world_engine/passages.py b/src/world_engine/passages.py
new file mode 100644
index 0000000..01be287
--- /dev/null
+++ b/src/world_engine/passages.py
@@ -0,0 +1,117 @@
+"""Place registry writer (TICKET-0105, BRIEF-0105-B, C-02).
+
+`passage` records the last moment a character was at a location: one row
+per (character, location) pair, `last_at` moving forward only. It is
+non-canon bookkeeping, like `rencontre` and `visit`.
+
+Every placement write is captured in ONE place (P1): a `before_flush`
+listener on the SQLAlchemy `Session` class, registered when `db.py` is
+imported. Whatever path creates a character with a location or changes its
+`current_location_id` -- travel, the tick's NPC move, zone promotion, the
+fiche, PC creation, a batch -- the listener sees the old and the new value at
+flush time and records both: leaving a place is a contact with it as much as
+entering it. A schedule names places without moving anyone, so
+`write_npc_schedule` records its old and new places itself, through
+`record_passages`.
+
+This module is the ONLY site that adds a `Passage` row
+(`tooling/verify/checks/fact_learning.py`, B1), the v2.14 migration's
+backfill aside. No function here commits; the caller owns the transaction.
+"""
+from __future__ import annotations
+
+from datetime import UTC, datetime
+from typing import Iterable, Optional
+
+from sqlalchemy import event, inspect
+from sqlalchemy.orm import Session as OrmSession
+from sqlmodel import select
+
+from .models import Character, Passage
+
+
+def _utc(value: datetime) -> datetime:
+    return value.replace(tzinfo=UTC) if value.utcoffset() is None else value.astimezone(UTC)
+
+
+def _find(db: OrmSession, entity_id: str, location_id: str) -> Optional[Passage]:
+    for obj in db.new:
+        if isinstance(obj, Passage) and obj.entity_id == entity_id and obj.location_id == location_id:
+            return obj
+    with db.no_autoflush:
+        return db.execute(
+            select(Passage).where(Passage.entity_id == entity_id, Passage.location_id == location_id)
+        ).scalars().first()
+
+
+def record_passage(
+    db: OrmSession,
+    *,
+    world_id: str,
+    entity_id: str,
+    location_id: str,
+    at: Optional[datetime] = None,
+) -> Passage:
+    """Record that `entity_id` was at `location_id` at `at` (default: now,
+    UTC). Creates the pair's row, or moves its `last_at` forward -- never
+    back. Returns the row."""
+    when = _utc(at or datetime.now(UTC))
+    row = _find(db, entity_id, location_id)
+    if row is None:
+        row = Passage(world_id=world_id, entity_id=entity_id, location_id=location_id, last_at=when)
+        db.add(row)
+    elif _utc(row.last_at) < when:
+        row.last_at = when
+        db.add(row)
+    return row
+
+
+def record_passages(
+    db: OrmSession,
+    *,
+    world_id: str,
+    entity_id: str,
+    location_ids: Iterable[str],
+    at: Optional[datetime] = None,
+) -> None:
+    """`record_passage` for each distinct location of `location_ids`."""
+    when = at or datetime.now(UTC)
+    for location_id in sorted(set(location_ids)):
+        record_passage(db, world_id=world_id, entity_id=entity_id, location_id=location_id, at=when)
+
+
+def _moves(db: OrmSession) -> list[tuple[Character, list[str]]]:
+    """Each character of the pending flush whose location is set or changed,
+    with the places to record: the new one, and the one it left."""
+    out = []
+    for obj in db.new:
+        if isinstance(obj, Character) and obj.current_location_id:
+            out.append((obj, [obj.current_location_id]))
+    for obj in db.dirty:
+        if not isinstance(obj, Character):
+            continue
+        history = inspect(obj).attrs.current_location_id.history
+        if history.has_changes():
+            places = [p for p in list(history.added) + list(history.deleted) if p]
+            if places:
+                out.append((obj, places))
+    return out
+
+
+def _capture_placements(db: OrmSession, _flush_context, _instances) -> None:
+    """`before_flush`: one passage per place a character enters or leaves."""
+    moves = _moves(db)
+    if not moves:
+        return
+    now = datetime.now(UTC)
+    for character, places in moves:
+        record_passages(db, world_id=character.world_id, entity_id=character.id,
+                        location_ids=places, at=now)
+
+
+def listener_registered() -> bool:
+    """True when the placement listener is attached (read by the check)."""
+    return event.contains(OrmSession, "before_flush", _capture_placements)
+
+
+event.listen(OrmSession, "before_flush", _capture_placements)
diff --git a/src/world_engine/writes/config.py b/src/world_engine/writes/config.py
index d56f36a..92c6d8b 100644
--- a/src/world_engine/writes/config.py
+++ b/src/world_engine/writes/config.py
@@ -47,6 +47,7 @@ from sqlalchemy import text
 from sqlmodel import Session, select
 
 from ..encounters import record_encounter
+from ..passages import record_passages
 from ..models import (
     Character,
     ConversationWindowConfig,
@@ -475,6 +476,7 @@ def write_npc_schedule(
 
         clean.append((phase, location_id, standing_goal_id))
 
+    _record_schedule_contacts(db, world_id=world_id, npc_id=npc_id, clean=clean)
     db.execute(text("DELETE FROM npc_schedule WHERE npc_id = :npc_id"), {"npc_id": npc_id})
 
     new_rows: list[NpcSchedule] = []
@@ -488,10 +490,22 @@ def write_npc_schedule(
         )
         db.add(row)
         new_rows.append(row)
-    _record_schedule_encounters(db, world_id=world_id, npc_id=npc_id, clean=clean)
     return new_rows
 
 
+def _record_schedule_contacts(
+    db: Session, *, world_id: str, npc_id: str, clean: list[tuple[str, str, Optional[str]]]
+) -> None:
+    """Before the old rows go: the encounters the new schedule makes, and the
+    passages of every place the old or the new schedule names. A schedule
+    names places without moving anyone, so naming a place and dropping it
+    are both contacts of this moment (TICKET-0105, BRIEF-0105-B, L1)."""
+    previous = db.exec(select(NpcSchedule.location_id).where(NpcSchedule.npc_id == npc_id)).all()
+    _record_schedule_encounters(db, world_id=world_id, npc_id=npc_id, clean=clean)
+    record_passages(db, world_id=world_id, entity_id=npc_id,
+                    location_ids=list(previous) + [loc for _phase, loc, _goal in clean])
+
+
 def _record_schedule_encounters(
     db: Session, *, world_id: str, npc_id: str, clean: list[tuple[str, str, Optional[str]]]
 ) -> None:
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index da28999..7ab83e7 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17749,6 +17749,27 @@ acquaintance would forget them. B4, writing knowledge rows at each
 contact: rows by the thousand and the end of read-time resolution;
 reactivates if a reader needs a stored row where only a default exists.
 
+
+## EVERY PLACEMENT AND EVERY ENCOUNTER IS A CONTACT (TICKET-0105) -- ONE LISTENER, ONE WRITER (BRIEF-0105-b, no schema change)
+
+**P1.** `passages.py` is the sole writer of `passage`. Its `before_flush`
+listener, attached to the SQLAlchemy `Session` class when `db.py` is
+imported, sees every character created with a location or whose
+`current_location_id` changes, whatever the path (travel, the tick's NPC
+move, zone promotion, the fiche, PC creation, a batch), and records both
+the place entered and the place left: leaving is a contact too. A schedule
+names places without moving anyone, so `write_npc_schedule` records the
+passages of every place its old and new rows name, before the old rows go.
+
+**L1.** `record_encounter` moves an existing pair's `last_at` forward --
+never back -- for every source but `relation`: a social relation makes two
+entities acquaintances (Q5a) but is not a contact.
+
+**Rejected.** P2, routing every placement through
+`write_character_location` with an AST check: the fiche and batch creators
+place characters through `**ext_kwargs`, which no static scan can see.
+Reactivates if the listener proves incompatible with a write path.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/encounter_registry.py b/tooling/verify/checks/encounter_registry.py
index e937774..c1dd63d 100644
--- a/tooling/verify/checks/encounter_registry.py
+++ b/tooling/verify/checks/encounter_registry.py
@@ -1,8 +1,10 @@
 """G1 check: the encounter registry (TICKET-0091, BRIEF-0091-C, gate (e)).
 
 `rencontre` is non-canon bookkeeping with exactly one writer
-(`src/world_engine/encounters.py`), never updated, never deleted, fed by
-every live encounter site. Four rules:
+(`src/world_engine/encounters.py`), never deleted, fed by every live
+encounter site; its only moving column, `last_at` (TICKET-0105), is set by
+attribute in `encounters.py` and covered by `fact_learning.py` B4. Four
+rules:
 
 R1 (AST) -- no `Rencontre(` call anywhere under `src/` or `scripts/`
    outside `src/world_engine/encounters.py` and
diff --git a/tooling/verify/checks/fact_learning.py b/tooling/verify/checks/fact_learning.py
index e7fcf77..5d851cd 100644
--- a/tooling/verify/checks/fact_learning.py
+++ b/tooling/verify/checks/fact_learning.py
@@ -24,6 +24,24 @@ A2 -- migration `scripts/migrate_v2_14_passage.py`, on a v2.13-shaped
       `schema_meta` to the code's version;
    c. a second run exits zero and changes no row.
 
+B1 -- one writer (BRIEF-0105-B, AST). No `Passage(` call under `src/` or
+   `scripts/` outside `src/world_engine/passages.py` and
+   `scripts/migrate_v2_14_passage.py`; the text `UPDATE passage` /
+   `DELETE FROM passage` (case-insensitive) appears nowhere in `src/`.
+B2 -- the listener. `src/world_engine/db.py` imports `passages`, and
+   `passages.listener_registered()` is true once `world_engine.db` is
+   imported.
+B3 -- every placement is a passage (fixture): a character created at L1;
+   moved to L2 by `write_character_location`; moved to L3 by assigning
+   `current_location_id` (the travel path); each flush leaves exactly the
+   passages of the places entered and left, `last_at` never moving back;
+   recording one pair twice in one flush leaves one row; an NPC schedule
+   at L4, then replaced by one at L5, leaves passages at L4 and L5.
+B4 -- encounters move their last contact (fixture): a new pair has
+   `last_at == first_at`; a later `visit` encounter moves `last_at` and
+   keeps `first_at` and the row count; a later `relation` encounter and an
+   earlier `gathering` one move nothing.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that examines zero rows is a
 FAILURE.
@@ -206,16 +224,175 @@ def check_a2(db_path: str) -> None:
         fail(f"A2c: second run exit {again.returncode} or changed rows: {again.stdout.strip()[-200:]}")
 
 
+# --- B1-B4 ---------------------------------------------------------------------
+
+def check_b1() -> None:
+    import ast
+    import re
+
+    allowed = {"src/world_engine/passages.py", "scripts/migrate_v2_14_passage.py"}
+    seen = 0
+    for base in (ROOT / "src", ROOT / "scripts"):
+        for path in sorted(base.rglob("*.py")):
+            rel = path.relative_to(ROOT).as_posix()
+            text = path.read_text(encoding="utf-8")
+            seen += 1
+            for node in ast.walk(ast.parse(text)):
+                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
+                        and node.func.id == "Passage" and rel not in allowed):
+                    fail(f"B1: Passage( constructed in {rel}")
+            if rel.startswith("src/") and re.search(r"(UPDATE\s+passage|DELETE\s+FROM\s+passage)\b",
+                                                    text, re.IGNORECASE):
+                fail(f"B1: raw passage mutation in {rel}")
+    if seen == 0:
+        fail("B1: no file scanned")
+
+
+def check_b2() -> None:
+    db_text = (SRC / "db.py").read_text(encoding="utf-8")
+    if "from world_engine import passages" not in db_text:
+        fail("B2: db.py does not import passages")
+    import world_engine.db  # noqa: F401
+    from world_engine import passages
+    if not passages.listener_registered():
+        fail("B2: the placement listener is not registered")
+
+
+def _world(session, name: str) -> dict:
+    from world_engine.models import Entity, Location, World
+
+    world = World(name=name, is_active=False)
+    session.add(world)
+    session.flush()
+    ids = {"world": world.id}
+    for key in ("L1", "L2", "L3", "L4", "L5"):
+        row = Entity(world_id=world.id, type="location", name=f"{name} {key}")
+        session.add(row)
+        session.flush()
+        session.add(Location(id=row.id, parent_location_id=None))
+        ids[key] = row.id
+    for key in ("A", "B"):
+        row = Entity(world_id=world.id, type="character", name=f"{name} {key}")
+        session.add(row)
+        session.flush()
+        ids[key] = row.id
+    session.commit()
+    return ids
+
+
+def _passages_of(session, entity_id: str) -> dict:
+    from sqlmodel import select
+
+    from world_engine.models import Passage
+    rows = session.exec(select(Passage).where(Passage.entity_id == entity_id)).all()
+    return {r.location_id: r.last_at for r in rows}
+
+
+def check_b3(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.models import Character
+    from world_engine.passages import record_passage
+    from world_engine.writes import write_character_location, write_npc_schedule
+
+    with Session(engine) as session:
+        ids = _world(session, "B3")
+        session.add(Character(id=ids["A"], world_id=ids["world"], character_type="npc",
+                              current_location_id=ids["L1"]))
+        session.commit()
+        first = _passages_of(session, ids["A"])
+        if set(first) != {ids["L1"]}:
+            fail(f"B3: creation left passages {sorted(first)}")
+            return
+        write_character_location(session, entity_id=ids["A"], to_location_id=ids["L2"])
+        session.commit()
+        moved = _passages_of(session, ids["A"])
+        if set(moved) != {ids["L1"], ids["L2"]} or moved[ids["L1"]] < first[ids["L1"]]:
+            fail(f"B3: a move left passages {moved}")
+        char = session.get(Character, ids["A"])
+        char.current_location_id = ids["L3"]
+        session.add(char)
+        session.commit()
+        travelled = _passages_of(session, ids["A"])
+        if set(travelled) != {ids["L1"], ids["L2"], ids["L3"]} or travelled[ids["L2"]] < moved[ids["L2"]]:
+            fail(f"B3: an assignment left passages {travelled}")
+        record_passage(session, world_id=ids["world"], entity_id=ids["A"], location_id=ids["L4"])
+        record_passage(session, world_id=ids["world"], entity_id=ids["A"], location_id=ids["L4"])
+        session.commit()
+        if len(_passages_of(session, ids["A"])) != 4:
+            fail("B3: one pair recorded twice in one flush is not one row")
+        session.add(Character(id=ids["B"], world_id=ids["world"], character_type="npc"))
+        session.commit()
+        for place in ("L4", "L5"):
+            session.add_all(write_npc_schedule(
+                session, world_id=ids["world"], npc_id=ids["B"],
+                rows=[{"phase": "soir", "location_id": ids[place]}], changed_by="check"))
+            session.commit()
+        if set(_passages_of(session, ids["B"])) != {ids["L4"], ids["L5"]}:
+            fail(f"B3: schedules left passages {sorted(_passages_of(session, ids['B']))}")
+
+
+def check_b4(engine) -> None:
+    from datetime import UTC, datetime, timedelta
+
+    from sqlmodel import Session, select
+
+    from world_engine.encounters import record_encounter
+    from world_engine.models import Rencontre
+
+    with Session(engine) as session:
+        ids = _world(session, "B4")
+        t0 = datetime(2026, 1, 1, tzinfo=UTC)
+
+        def row():
+            rows = session.exec(select(Rencontre).where(Rencontre.world_id == ids["world"])).all()
+            return rows[0] if len(rows) == 1 else None
+
+        def stamp(value):
+            return value.replace(tzinfo=UTC) if value.utcoffset() is None else value
+
+        record_encounter(session, world_id=ids["world"], a_id=ids["A"], b_id=ids["B"],
+                         source="gathering", at=t0)
+        session.commit()
+        created = row()
+        if created is None or stamp(created.last_at) != stamp(created.first_at):
+            fail("B4: a new pair's last_at is not its first_at")
+            return
+        later = t0 + timedelta(days=3)
+        record_encounter(session, world_id=ids["world"], a_id=ids["B"], b_id=ids["A"],
+                         source="visit", at=later)
+        session.commit()
+        moved = row()
+        if moved is None or stamp(moved.last_at) != later or stamp(moved.first_at) != t0:
+            fail("B4: a later visit did not move last_at alone")
+            return
+        record_encounter(session, world_id=ids["world"], a_id=ids["A"], b_id=ids["B"],
+                         source="relation", at=later + timedelta(days=1))
+        record_encounter(session, world_id=ids["world"], a_id=ids["A"], b_id=ids["B"],
+                         source="gathering", at=t0)
+        session.commit()
+        kept = row()
+        if kept is None or stamp(kept.last_at) != later:
+            fail("B4: a relation or an earlier encounter moved last_at")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_a1()
     check_a2(db_path)
+    check_b1()
+    check_b2()
+    from world_engine.db import create_db_and_tables, engine
+    create_db_and_tables()
+    check_b3(engine)
+    check_b4(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print("PASS: fact_learning -- v2.14 declares passage and the encounter's last "
-          "contact, presets tenue to rencontre, and migrates from v2.13 only")
+          "contact, presets tenue to rencontre, and migrates from v2.13 only; every "
+          "placement and every encounter moves its last contact, through one writer each")
     return 0
 
 
````

## Scope OUT

- Reading the registries (D).
- Routing placements through `write_character_location` or adding an AST ban on other writes (P2, rejected).
- Recording a contact for the duration of a gathering (only its join counts; O1 covers the scene).
- Items' `location_id`: an item knows nothing.
- Moving `last_at` from a `relation` encounter.
- Every later brief of this lot.

## Invariants to defend

**Per-NPC uniqueness / gathering paths:** untouched — the listener adds `passage` rows only. **Creator-direct cores never commit:** neither does `passages.py`; the listener runs inside the caller's flush. **Commit before touching a canon-writing path:** the fiche CRUD and the tick's move now flush a listener; it writes no canon table. `rencontre` keeps one writer.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- The listener raises inside any existing check's flush (a placement path the RECON did not see).
- `function_length.py`, `npc_schedule.py` or `single_canon_write.py` fails on `writes/config.py`.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- Any check whose fixtures now carry `passage` rows (expected: cascaded with their world).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/fact_learning.py` → `PASS: fact_learning -- … every placement and every encounter moves its last contact, through one writer each`.
- `encounter_registry.py`, `npc_schedule.py`, `single_canon_write.py`, `function_length.py`, `import_cycle.py`, `claude_md_contract.py` → `PASS`.
- Mutation tests, each red then reverted: replace the module's last line `event.listen(OrmSession, "before_flush", _capture_placements)` with `pass` → `B2`, `B3`; delete the two lines `    if source == "relation":` / `        return` in `encounters._touch` → `B4`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 138/138.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

CLAUDE.md: one invariant (`passage` written only by `passages.py`'s listener; `rencontre.last_at` moves forward only) and the file-structure line — in the diff. Decision entry `EVERY PLACEMENT AND EVERY ENCOUNTER IS A CONTACT (TICKET-0105) -- ONE LISTENER, ONE WRITER (BRIEF-0105-b, no schema change)` — in the diff.
