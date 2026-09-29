<!-- slug: drop-subject -->
# BRIEF 0097-G — "Drop knowledge.subject, v2.10"

Lot: LOT-0097-knowledge-identity.md (authoritative on conflict)
Depends on: F
Commit header for decisions: `(BRIEF-0097-g, schema v2.10)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0097` before applying anything. Halt if one has moved.

- `src/world_engine/models/canon_knowledge.py` → `Knowledge` still declares `subject: str` and `Index("idx_knowledge_subject", "subject")`
- `src/world_engine/schema_version.py` → `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.09"` (brief A)
- `tooling/verify/checks/knowledge_identity.py` `_SUBJECT_CENSUS` → 22 references (brief F)
- `scripts/migrate_v2_10_drop_knowledge_subject.py` → does not exist

## Facts carried

### R-01 — `knowledge` (model)
Opened: `src/world_engine/models/canon_knowledge.py:198-235` (declares the table).
Finding: columns `id, entity_id, fact_id (NOT NULL, FK fact), subject (str,
NOT NULL), level, content (SQL name, attr `content_raw`), source,
is_incorrect, is_secret, share_threshold, acquired_at, updated_at,
session_id, change_history`. Indexes: `idx_knowledge_entity(entity_id)`,
`idx_knowledge_subject(subject)` (line 206), `idx_knowledge_fact(fact_id)`
(line 207). No unique index on `(entity_id, fact_id)`.
Consequence: A adds `idx_knowledge_entity_fact` UNIQUE; G drops the subject
index then the column (SQLite refuses `DROP COLUMN` on an indexed column).

### R-03 — prod data (Nia's machine, 2026-09-28, read-only `mode=ro`)
Opened: Nia's run of `q1b_measure.py` on `~/.world_engine/world_engine.db`.
Finding (verbatim excerpts):
```
== M0 schema version == [(1, 'v2.08', '2026-09-27 21:35:07.202136')]
== M2 subjects split over >1 fact, per world ==
'Nestia': split_subjects=1 rows=20 facts_involved=20
'Verkhaal': split_subjects=1 rows=5 facts_involved=5
'La Dichotomie': split_subjects=1 rows=4 facts_involved=4
'le château de Valdur': split_subjects=1 rows=2 facts_involved=2
  (all four: 'creator_meta')
== M3 facts carrying >1 distinct subject == count: 0
== M4 same entity holds the same subject on >1 row == count: 3
  ('6974bf4a-…', 'Lily', 2) ('ce441cec-…', 'npc:ffd887a6-…', 2) ('fee5dd2f-…', 'Lily', 2)
same entity + same fact on >1 row: 3
== M5 == content == subject 607 ; content != subject 34 (all 'creator_meta')
facet of facts referenced by knowledge: [(None, 291), ('histoire', 34), ('lien', 39)]
== M7 == npc:% subjects: 269 ; creator_meta subjects: 34 ; 'unknown' subjects: 0
== M8 == details: (5, 5) ; detail subjects present as a knowledge subject: 0
== M9 == [('knowledge_change','approved',1), ('new_knowledge','applied',16),
          ('new_knowledge','proposed',5), ('new_knowledge','rejected',2)]
```
Consequence: E1 (a guard, no merge), F1 (three absorptions), G (269 rows'
facts get their participant), H1 (nothing to backfill), N1 (the one approved
`knowledge_change` stays visible, refused at apply).

### R-15 — pre-existing breakage, left as is
Opened: `scripts/seed_test.py`, `scripts/test_context.py`, run on `main`.
Finding: `seed_test.py` fails with `NOT NULL constraint failed:
knowledge.fact_id` on `main` already; `test_context.py` depends on it.
`scripts/apply_ticket_0087_subject_participants.py` imports `subject_resolve`.
Consequence: named deferrals; nothing in the corpus runs them.

## Contracts

### C-09 — migrations
Produced by: A (v2.09), G (v2.10)   Consumed by: `knowledge_identity.py`
- `migrate_v2_09_knowledge_identity.migrate(cursor) -> dict` with keys
  `absorbed` (list of `(entity_id, fact_id, rows_deleted)`), `index_created`,
  `npc_facts` (`{"token","participant","untouched"}` lists of fact ids),
  `detail_column_added`, `gates_rekeyed`, `gates_untouched`; raises `Abort`.
- `migrate_v2_10_drop_knowledge_subject.migrate(cursor) -> bool` (True when
  dropped, False when already gone); raises `Abort`.

## Context

K3 shows no reader of `knowledge.subject` left. v2.10 drops its index, then the column, and refuses to run if a legacy label would be lost; `write_knowledge` loses the parameter.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below to a file and run `git apply --check <file>` then `git apply <file>` from the
repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: removes `subject` and `idx_knowledge_subject` from `Knowledge`; bumps the version, schema doc and changelog to v2.10; creates `scripts/migrate_v2_10_drop_knowledge_subject.py` (C-09); removes `subject` from `write_knowledge`, `apply_knowledge_patch`, `upsert_knowledge_row` (the seed names a legacy fact's content with `fact_content`) and the discovery payload; updates CLAUDE.md's creator-note wording; removes `subject` from the fixtures of eight checks and `world_cascade.py`; extends K2's fixture to the v2.08 shape and adds K9.
2. Regenerate the index.
3. Message: `feat(knowledge): drop knowledge.subject, v2.10 (BRIEF-0097-g)`.

```diff
diff --git a/CLAUDE.md b/CLAUDE.md
index cc4f39a..726fb0b 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -147,7 +147,7 @@ Law only. Rationale, chantier history, and deferred alternatives live in
   names a fact only by a code from a `fact_refs.code_facts` list; code resolves it.
 - **Secrets are structurally excluded** from every assembled context — never
   "guarded by instruction". The creator's note on an entity (a `histoire`
-  fact whose entity holds a `creator_meta` `is_secret` row) is excluded from
+  fact whose entity holds an `unaware` `is_secret` row on it) is excluded from
   `facet_reads` by query construction; only the Lore dossier opts in, plus the
   `creator` regime of `name_index` for name resolution (Lore question, names
   panel). Token posing never indexes a creator-only or unscoped appellation.
diff --git a/scripts/migrate_v2_10_drop_knowledge_subject.py b/scripts/migrate_v2_10_drop_knowledge_subject.py
new file mode 100644
index 0000000..e601aaf
--- /dev/null
+++ b/scripts/migrate_v2_10_drop_knowledge_subject.py
@@ -0,0 +1,150 @@
+"""Migration v2.10 — drop `knowledge.subject` (TICKET-0097, BRIEF-0097-G, B3).
+
+Since v2.09 a `knowledge` row is identified by the fact it knows, and no
+code reads `subject` any more (`knowledge_identity.py` K3). One transaction:
+
+- S1 guard: v2.09 ran — `idx_knowledge_entity_fact` exists. Otherwise abort,
+  writing nothing: the identity must stand before its old key goes.
+- S2 guard: every legacy label is still readable elsewhere — for every
+  `knowledge` row whose `subject` is neither `creator_meta` nor its fact's
+  content (the only other shape v2.09 leaves is an `npc:<id>` subject whose
+  fact was tokenized), the fact has a participant. Otherwise abort and list
+  the rows.
+- S3 `DROP INDEX idx_knowledge_subject` (SQLite refuses to drop an indexed
+  column).
+- S4 `ALTER TABLE knowledge DROP COLUMN subject`.
+- S5 post-check: the column and its index are gone; the row count is
+  unchanged.
+- then `schema_meta` converges to v2.10.
+
+Idempotent: a second run finds no `subject` column, skips S2-S4 and only
+converges `schema_meta`.
+
+Run from the project root, right after `migrate_v2_09_knowledge_identity.py`
+(after `python scripts/backup.py`), before starting the cockpit:
+
+    python scripts/migrate_v2_10_drop_knowledge_subject.py
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
+        "migrate_v2_10_drop_knowledge_subject.py refuses to run without WORLD_ENGINE_ENV "
+        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+from sqlmodel import Session  # noqa: E402
+
+from world_engine import models  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+
+TARGET_VERSION = "v2.10"
+CREATOR_META = "creator_meta"
+
+
+class Abort(Exception):
+    """A pre- or post-check failed; the transaction is rolled back."""
+
+
+def _has_column(cursor) -> bool:
+    return "subject" in [row[1] for row in cursor.execute("PRAGMA table_info(knowledge)")]
+
+
+def _has_index(cursor, name: str) -> bool:
+    return cursor.execute(
+        "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)
+    ).fetchone() is not None
+
+
+def orphan_labels(cursor) -> list[tuple]:
+    """S2: (knowledge id, subject) of rows whose label would be lost."""
+    return cursor.execute(
+        "SELECT k.id, k.subject FROM knowledge k JOIN fact f ON f.id = k.fact_id "
+        "WHERE k.subject <> ? AND k.subject IS NOT f.content "
+        "AND NOT EXISTS (SELECT 1 FROM fact_participant p WHERE p.fact_id = k.fact_id) "
+        "ORDER BY k.id",
+        (CREATOR_META,),
+    ).fetchall()
+
+
+def migrate(cursor) -> bool:
+    """S1-S5 on an open transaction. True when the column was dropped, False
+    when it was already gone. Raises `Abort` on any failed check."""
+    if not _has_index(cursor, "idx_knowledge_entity_fact"):
+        raise Abort("idx_knowledge_entity_fact is missing — run migrate_v2_09_knowledge_identity.py first")
+    if not _has_column(cursor):
+        return False
+    orphans = orphan_labels(cursor)
+    if orphans:
+        raise Abort(f"{len(orphans)} knowledge row(s) would lose their only label: {orphans[:10]!r}")
+    rows_before = cursor.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
+    if _has_index(cursor, "idx_knowledge_subject"):
+        cursor.execute("DROP INDEX idx_knowledge_subject")
+    cursor.execute("ALTER TABLE knowledge DROP COLUMN subject")
+    if _has_column(cursor) or _has_index(cursor, "idx_knowledge_subject"):
+        raise Abort("post-check: knowledge.subject or its index is still present")
+    rows_after = cursor.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
+    if rows_after != rows_before:
+        raise Abort(f"post-check: knowledge holds {rows_after} row(s), expected {rows_before}")
+    return True
+
+
+def _apply() -> None:
+    raw = engine.raw_connection()
+    try:
+        cursor = raw.cursor()
+        cursor.execute("BEGIN")
+        try:
+            dropped = migrate(cursor)
+        except Abort as exc:
+            cursor.execute("ROLLBACK")
+            raise SystemExit(f"Migration {TARGET_VERSION} aborted, rolled back. {exc}") from None
+        cursor.execute("COMMIT")
+        cursor.close()
+        print("knowledge.subject dropped." if dropped else "knowledge.subject already gone — nothing to do.")
+    except Exception:
+        raw.rollback()
+        raise
+    finally:
+        raw.close()
+
+
+def _converge_schema_meta() -> None:
+    with Session(engine) as session:
+        row = session.get(models.SchemaMeta, 1)
+        if row is None:
+            session.add(models.SchemaMeta(id=1, static_version=TARGET_VERSION))
+            print(f"Row: seeded schema_meta.id=1 at {TARGET_VERSION!r}")
+        elif row.static_version != TARGET_VERSION:
+            previous = row.static_version
+            row.static_version = TARGET_VERSION
+            row.updated_at = datetime.now(UTC)
+            session.add(row)
+            print(f"Row: updated schema_meta.id=1: {previous!r} -> {TARGET_VERSION!r}")
+        else:
+            print(f"Row: schema_meta.id=1 already at {TARGET_VERSION!r} — nothing to do")
+        session.commit()
+
+
+def main() -> None:
+    print(f"Migration {TARGET_VERSION} — drop knowledge.subject")
+    _apply()
+    _converge_schema_meta()
+    print(f"\nMigration {TARGET_VERSION} applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index 230d792..ed17ecc 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -110,9 +110,9 @@ def upsert_knowledge(session: Session, id: str, **fields):
 
     The create-or-converge logic lives in
     `writes/knowledge.py::upsert_knowledge_row` (TICKET-0091,
-    AMENDMENT-0091-05): the stored text is read raw only in `writes/`. The
-    `fact_id` fallback (`content = subject`) is unchanged; seed text is never
-    tokenized.
+    AMENDMENT-0091-05): the stored text is read raw only in `writes/`. A row
+    seeded on its own fact names that fact's content with `fact_content`
+    (TICKET-0097: the legacy slug label, C1); seed text is never tokenized.
     """
     status = upsert_knowledge_row(session, id=id, created_by="seed_pilot", **fields)
     {"created": _created, "updated": _updated, "existing": _existing}[status].append(
@@ -3338,7 +3338,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-maelis-tavern-daily",
         entity_id="npc-maelis",
-        subject="tavern_daily",
+        fact_content="tavern_daily",
         level="knows",
         content=(
             "Tient Le Dernier Verre au quotidien : ce qu'elle sert à boire et à "
@@ -3353,7 +3353,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-maelis-tavern-clientele",
         entity_id="npc-maelis",
-        subject="tavern_clientele",
+        fact_content="tavern_clientele",
         level="knows",
         content=(
             "Connaît les habitués et les voyageurs des deux nations qui passent "
@@ -3367,7 +3367,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-maelis-verkhaal-city",
         entity_id="npc-maelis",
-        subject="verkhaal_city",
+        fact_content="verkhaal_city",
         level="knows",
         content=(
             "Savoir public d'habitante : Verkhaal est la ville-forteresse qui "
@@ -3384,7 +3384,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-maelis-incidents",
         entity_id="npc-maelis",
-        subject="local_magic_incidents",
+        fact_content="local_magic_incidents",
         level="partial",
         content=(
             "Connaît les micro-phénomènes discrets du Dernier Verre (chaleur, "
@@ -3401,7 +3401,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-maelis-unnamed",
         entity_id="npc-maelis",
-        subject="the_unnamed",
+        fact_content="the_unnamed",
         level="partial",
         content="Sait servir le réseau, le nie en public.",
         source="appartenance",
@@ -3416,7 +3416,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-reike-existence",
         entity_id="npc-reike",
-        subject="magic_existence",
+        fact_content="magic_existence",
         level="suspicious",
         content=(
             "Ne croit plus à la version « technique » des incidents, mais ne "
@@ -3429,7 +3429,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-reike-awakening",
         entity_id="npc-reike",
-        subject="magic_awakening",
+        fact_content="magic_awakening",
         level="rumor",
         content="Sent la fréquence des incidents augmenter.",
         source="scènes de terrain",
@@ -3443,7 +3443,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         "kn-senna-existence",
         entity_id="npc-senna",
         fact_id=_fact_of(session, "kn-reike-existence"),
-        subject="magic_existence",
+        fact_content="magic_existence",
         level="knows",
         content="Savoir de base des Marcheurs : la magie est réelle, elle a dormi.",
         source="savoir oral des Marcheurs",
@@ -3454,7 +3454,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         "kn-senna-awakening",
         entity_id="npc-senna",
         fact_id=_fact_of(session, "kn-reike-awakening"),
-        subject="magic_awakening",
+        fact_content="magic_awakening",
         level="knows",
         content=(
             "Sait que la magie endormie se réveille ; inquiète, n'en parle "
@@ -3467,7 +3467,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-senna-nexus",
         entity_id="npc-senna",
-        subject="verkhaal_nexus",
+        fact_content="verkhaal_nexus",
         level="partial",
         content="Soupçonne un lien entre la taverne et le nœud.",
         source="savoir oral des Marcheurs",
@@ -3479,7 +3479,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-player-tavern",
         entity_id="char-player",
-        subject="le_dernier_verre",
+        fact_content="le_dernier_verre",
         level="knows",
         content="Connaît l'existence et l'emplacement du Dernier Verre.",
         source="habitué du lieu",
@@ -3489,7 +3489,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-player-maelis",
         entity_id="char-player",
-        subject="maelis",
+        fact_content="maelis",
         level="partial",
         content="Connaît Maelis de vue comme la patronne du Dernier Verre.",
         source="fréquentation du lieu",
@@ -3499,7 +3499,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-player-incident",
         entity_id="char-player",
-        subject="personal_magic_incident",
+        fact_content="personal_magic_incident",
         level="partial",
         content="A vécu un incident magique inexpliqué qu'il n'a dit à personne.",
         source="vécu personnel",
@@ -3836,7 +3836,7 @@ def main() -> None:
             for k in rows:
                 flag = "SECRET   " if k.is_secret else "shareable"
                 print(
-                    f"    - [{flag}] {k.subject} "
+                    f"    - [{flag}] {k.id} "
                     f"(level={k.level}, threshold={k.share_threshold})"
                 )
 
diff --git a/src/world_engine/cockpit/play_discovery.py b/src/world_engine/cockpit/play_discovery.py
index 0269dc9..5efce9a 100644
--- a/src/world_engine/cockpit/play_discovery.py
+++ b/src/world_engine/cockpit/play_discovery.py
@@ -33,7 +33,6 @@ def _propose_engine_discovery(
         target_id=conv.player_id,
         payload={
             "entity_id": conv.player_id,
-            "subject": detail.subject,
             "level": "knows",
             "content": detail.content,
             "source": "discovery",
diff --git a/src/world_engine/models/canon_knowledge.py b/src/world_engine/models/canon_knowledge.py
index fe69670..87bf7a6 100644
--- a/src/world_engine/models/canon_knowledge.py
+++ b/src/world_engine/models/canon_knowledge.py
@@ -203,7 +203,6 @@ class Knowledge(SQLModel, table=True):
             name="ck_knowledge_share_threshold",
         ),
         Index("idx_knowledge_entity", "entity_id"),
-        Index("idx_knowledge_subject", "subject"),
         Index("idx_knowledge_fact", "fact_id"),
         # TICKET-0097 (BRIEF-0097-A, schema v2.09): what an entity knows is
         # identified by the fact it knows -- one row per (entity, fact).
@@ -213,7 +212,6 @@ class Knowledge(SQLModel, table=True):
     id: str = Field(default_factory=_uuid, primary_key=True)
     entity_id: str = Field(foreign_key="entity.id", nullable=False)
     fact_id: str = Field(foreign_key="fact.id", nullable=False)
-    subject: str
     level: str
     # SQL column `content`; rendered through `prose_render.knowledge_text`.
     content_raw: Optional[str] = Field(
diff --git a/src/world_engine/models/config.py b/src/world_engine/models/config.py
index 72069c0..a6794f6 100644
--- a/src/world_engine/models/config.py
+++ b/src/world_engine/models/config.py
@@ -106,7 +106,7 @@ class AgendaStep(SQLModel, table=True):
 # TICKET-0075, BRIEF-0075-b). `goal_prerequisite` shape precedent (same
 # id/world_id/type/target_entity_id/threshold spine), widened to a closed
 # four-form vocabulary and a `target_key` column for the two forms that gate
-# on a string (knowledge subject, resource tag) rather than an entity.
+# on a string (knowledge fact id since TICKET-0097, resource tag) rather than an entity.
 #
 # The per-type shape CHECK is the structural guarantee that an ill-formed row
 # cannot exist: `relation_gte`/`location_reachable` require target_entity_id
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index 025a93f..d878993 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.09"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.10"
diff --git a/src/world_engine/writes/knowledge.py b/src/world_engine/writes/knowledge.py
index e224404..9fb83b6 100644
--- a/src/world_engine/writes/knowledge.py
+++ b/src/world_engine/writes/knowledge.py
@@ -9,7 +9,7 @@ decomposed from `writes.py`).
   `knowledge_change` branch. Narrower than the default update: only
   `level`, `source` and `updated_at` change (the previous state is still
   appended to `change_history` first) — `content`, `is_incorrect`,
-  `is_secret`, `share_threshold` and `subject` on the existing row are left
+  `is_secret` and `share_threshold` on the existing row are left
   untouched, unlike a default-mode update.
 
 `_build_knowledge_level_change`/`_build_knowledge_update` are pure builds
@@ -25,9 +25,9 @@ fallback lives here rather than being duplicated at each caller — an
 explicit `fact_id` attaches to that existing fact; omitting it auto-creates
 a free-standing one (`writes/facts.py::create_fact`) whose content is the
 row's own stored text (TICKET-0097, M1: a fact born here carries the
-sentence, not a slug) -- the given `subject` only when the row has no text.
-`subject` is optional and derived: absent, the column takes the fact's
-stored content (v2.10 drops the column; nothing reads it as a key).
+sentence, not a slug). A row with neither text nor `fact_id` is refused. A
+knowledge row is identified by its fact (`idx_knowledge_entity_fact`); it
+has no label of its own since v2.10.
 
 `subject_entity_ids` (TICKET-0087, BRIEF-0087-a) attaches participants to
 the row's fact on create only, with no `role`; a participant IS the
@@ -179,7 +179,7 @@ def _tokenized_content(
 
 def _build_knowledge_update(
     db: Session, *, knowledge_id: Optional[str], entity_id: Optional[str],
-    subject: Optional[str], level: Optional[str], content: Optional[Any],
+    level: Optional[str], content: Optional[Any],
     source: Optional[Any], is_incorrect: bool, is_secret: bool,
     share_threshold: int, session_id: Optional[str], changed_by: str,
     fact_id: Optional[str] = None,
@@ -204,8 +204,6 @@ def _build_knowledge_update(
         if k is None:
             raise ValueError(f"write_knowledge: knowledge {knowledge_id!r} not found")
         _append_knowledge_history(k, changed_by=changed_by)
-        if subject is not None:
-            k.subject = subject
         k.level = norm_level
         k.content_raw, pending = _tokenized_content(db, k.entity_id, content, previous=k.content_raw)
         k.source = source
@@ -222,9 +220,10 @@ def _build_knowledge_update(
         entity = db.get(Entity, entity_id)
         if entity is None:
             raise ValueError(f"write_knowledge: entity {entity_id!r} not found")
-        text = stored if isinstance(stored, str) and stored.strip() else (subject or "unknown")
+        if not isinstance(stored, str) or not stored.strip():
+            raise ValueError("write_knowledge: a new fact needs the row's content")
         fact = create_fact(
-            db, world_id=entity.world_id, content=text, created_by=changed_by,
+            db, world_id=entity.world_id, content=stored, created_by=changed_by,
             facet="information",
         )
     else:
@@ -233,7 +232,7 @@ def _build_knowledge_update(
             raise ValueError(f"write_knowledge: fact {fact_id!r} not found")
     _attach_subject_participants(db, fact=fact, subject_entity_ids=subject_entity_ids)
     return Knowledge(
-        entity_id=entity_id, fact_id=fact.id, subject=subject or fact.content_raw, level=norm_level,
+        entity_id=entity_id, fact_id=fact.id, level=norm_level,
         content_raw=stored, source=source, is_incorrect=bool(is_incorrect),
         is_secret=bool(is_secret), share_threshold=threshold, session_id=session_id,
     ), pending
@@ -245,7 +244,6 @@ def write_knowledge(
     mode: str = "update",
     knowledge_id: Optional[str] = None,
     entity_id: Optional[str] = None,
-    subject: Optional[str] = None,
     level: Optional[str] = None,
     content: Optional[Any] = None,
     source: Optional[Any] = None,
@@ -279,7 +277,7 @@ def write_knowledge(
         )
     else:
         k, pending = _build_knowledge_update(
-            db, knowledge_id=knowledge_id, entity_id=entity_id, subject=subject,
+            db, knowledge_id=knowledge_id, entity_id=entity_id,
             level=level, content=content, source=source, is_incorrect=is_incorrect,
             is_secret=is_secret, share_threshold=share_threshold, session_id=session_id,
             changed_by=changed_by, fact_id=fact_id, subject_entity_ids=subject_entity_ids,
@@ -307,7 +305,7 @@ def apply_knowledge_patch(db: Session, *, knowledge: Knowledge, patch: dict, cha
     merged.update(patch)
     return write_knowledge(
         db, mode="update", knowledge_id=knowledge.id, entity_id=knowledge.entity_id,
-        subject=knowledge.subject, level=merged["level"], content=merged["content"],
+        level=merged["level"], content=merged["content"],
         source=merged["source"], is_incorrect=merged["is_incorrect"],
         is_secret=merged["is_secret"], share_threshold=merged["share_threshold"],
         session_id=knowledge.session_id, changed_by=changed_by,
@@ -321,8 +319,10 @@ def upsert_knowledge_row(db: Session, *, id: str, created_by: str, **fields) ->
     The `content` key maps to `content_raw`; the text is stored as given,
     never tokenized (seed text is a reproducible dataset, like migrated text).
     On create, absent a `fact_id`, a free-standing fact is created with
-    `content = subject` (the `write_knowledge` fallback); an existing row's
-    `fact_id` is never touched. Returns "created", "updated" or "existing"."""
+    `content = fact_content` (the seed's legacy fact label, C1); an existing
+    row's `fact_id` is never touched, and `fact_content` then goes unused.
+    Returns "created", "updated" or "existing"."""
+    fact_content = fields.pop("fact_content", None)
     if "content" in fields:
         fields = {("content_raw" if key == "content" else key): value for key, value in fields.items()}
     obj = db.get(Knowledge, id)
@@ -331,7 +331,7 @@ def upsert_knowledge_row(db: Session, *, id: str, created_by: str, **fields) ->
             entity = db.get(Entity, fields["entity_id"])
             fact = create_fact(
                 db, world_id=entity.world_id,
-                content=fields.get("subject") or "unknown", created_by=created_by,
+                content=fact_content or fields.get("content_raw") or "unknown", created_by=created_by,
                 facet="information",
             )
             fields = {**fields, "fact_id": fact.id}
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index c4f149c..2e4e66b 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17199,6 +17199,29 @@ card shows the fact's text, its first knower's version (by name), how many
 know it, then the candidates or near names. Binding is one participant
 POST, since a card is one fact.
 
+## KNOWLEDGE.SUBJECT IS DROPPED (TICKET-0097) -- THE FACT IS THE ONLY IDENTITY (BRIEF-0097-g, schema v2.10)
+
+**B3, last step.** `knowledge_identity.py` K3 showed no reader left; v2.10
+drops `idx_knowledge_subject` (SQLite refuses to drop an indexed column),
+then the column. `write_knowledge` loses its `subject` parameter and refuses
+a new row with neither text nor `fact_id`; the seed names a legacy fact's
+content with `fact_content` (C1: the old slug stays the fact's text).
+
+**The migration refuses to lose a label.** v2.10 aborts before v2.09 has
+run, and while any row's subject is neither `creator_meta`, nor its fact's
+content, nor backed by a participant. Measured on prod: the only rows whose
+subject differs from their fact's content are the 34 `creator_meta` notes.
+
+**What remains in the census.** `discoverable_detail.subject` is a detail's
+own short label, not a knowledge key, and stays; the window analysis still
+reads a model's `subject` field as a hint of who learned something, never as
+an identity.
+
+**Named deferrals.** `scripts/seed_test.py` and `scripts/test_context.py`
+already fail on `main` (no `fact_id`, since 0082) and are left as they are;
+`apply_ticket_0087_subject_participants.py` imports the deleted
+`subject_resolve` -- a one-shot that ran in 0087, kept as history.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/analyzer_seam.py b/tooling/verify/checks/analyzer_seam.py
index d344249..75ea141 100644
--- a/tooling/verify/checks/analyzer_seam.py
+++ b/tooling/verify/checks/analyzer_seam.py
@@ -376,7 +376,7 @@ def _seed_fixture(engine):
 
         from world_engine.writes import write_knowledge
         write_knowledge(
-            session, entity_id=npc_id, subject="a_subject", level="knows",
+            session, entity_id=npc_id, level="knows",
             content="Fixture fact.", is_secret=False, share_threshold=50, changed_by="check",
         )
         session.commit()
diff --git a/tooling/verify/checks/context_disclosure_floor.py b/tooling/verify/checks/context_disclosure_floor.py
index 90c535f..b488660 100644
--- a/tooling/verify/checks/context_disclosure_floor.py
+++ b/tooling/verify/checks/context_disclosure_floor.py
@@ -112,7 +112,7 @@ def _seed_fixture(engine):
         session.commit()
 
         write_knowledge(
-            session, entity_id=a_id, subject="the plan", level="knows",
+            session, entity_id=a_id, level="knows",
             content="Le plan se met en place demain.",
             is_secret=False, share_threshold=50, changed_by="check",
         )
diff --git a/tooling/verify/checks/day_choice.py b/tooling/verify/checks/day_choice.py
index 0ca40fc..0d0c1a4 100644
--- a/tooling/verify/checks/day_choice.py
+++ b/tooling/verify/checks/day_choice.py
@@ -425,7 +425,7 @@ def check_requests(engine) -> int:
         known = fact("Elle a perdu une bague.", ScopeChoice("world"))
         unknown = fact("Elle cache un poignard.", ScopeChoice("none"))
         secret = fact("Secret de créatrice.", ScopeChoice("world"))
-        write_knowledge(session, entity_id=maelis.id, fact_id=secret.id, subject="creator_meta",
+        write_knowledge(session, entity_id=maelis.id, fact_id=secret.id,
                         level="unaware", is_secret=True, changed_by="check")
         session.flush()
         pc = SimpleNamespace(id=mini.id, world_id=world.id)
diff --git a/tooling/verify/checks/fact_spine.py b/tooling/verify/checks/fact_spine.py
index a51dce2..a241cc3 100644
--- a/tooling/verify/checks/fact_spine.py
+++ b/tooling/verify/checks/fact_spine.py
@@ -143,8 +143,8 @@ def check_db_fixture(engine) -> None:
         attach_participants(session, fact=free_fact, entity_ids=[a, b, c], role="conspirator")
         session.commit()
 
-        write_knowledge(session, entity_id=d, subject="a shared secret", level="rumor", fact_id=free_fact.id)
-        write_knowledge(session, entity_id=d, subject="unrelated gossip", level="knows")
+        write_knowledge(session, entity_id=d, level="rumor", fact_id=free_fact.id)
+        gossip_id = write_knowledge(session, entity_id=d, content="unrelated gossip", level="knows").id
         session.commit()
 
         # ── Positive: no participant on a typed fact, no NULL fact_id, every level valid ──
@@ -188,9 +188,7 @@ def check_db_fixture(engine) -> None:
 
         # ── Negative: an out-of-vocabulary knowledge.level (no DB CHECK guards
         #    this column) -> FAILs naming it, then heals ────────────────────────
-        gossip = session.exec(
-            select(Knowledge).where(Knowledge.entity_id == d, Knowledge.subject == "unrelated gossip")
-        ).first()
+        gossip = session.get(Knowledge, gossip_id)
         gossip.level = "omniscient"
         session.add(gossip)
         session.commit()
diff --git a/tooling/verify/checks/knowledge_identity.py b/tooling/verify/checks/knowledge_identity.py
index 8d6f430..b02a3da 100644
--- a/tooling/verify/checks/knowledge_identity.py
+++ b/tooling/verify/checks/knowledge_identity.py
@@ -21,6 +21,13 @@ K2 -- migration v2.09 (`scripts/migrate_v2_09_knowledge_identity.py`), run
    f. a knowledge gate keyed by a subject is rekeyed to that subject's
       fact id; a gate keyed by an unknown string is untouched;
    g. a second run changes nothing.
+K9 -- migration v2.10 (`scripts/migrate_v2_10_drop_knowledge_subject.py`),
+   run on the K2 database after v2.09:
+   a. a row whose subject is neither `creator_meta`, nor its fact's content,
+      nor backed by a participant aborts the run;
+   b. otherwise `knowledge.subject` and `idx_knowledge_subject` are gone and
+      the row count is unchanged;
+   c. a second run reports the column already gone.
 K3 -- census. The `subject` references of `src/world_engine` (an attribute
    `.subject`, a string constant `"subject"`, a `subject=` keyword or a
    `subject` parameter), counted per file, equal `_SUBJECT_CENSUS` exactly.
@@ -95,15 +102,14 @@ import tempfile
 ROOT = pathlib.Path(__file__).resolve().parents[3]
 SRC = ROOT / "src"
 MIGRATION_V2_09 = ROOT / "scripts" / "migrate_v2_09_knowledge_identity.py"
+MIGRATION_V2_10 = ROOT / "scripts" / "migrate_v2_10_drop_knowledge_subject.py"
 
 FAILURES: list[str] = []
 
 _SUBJECT_CENSUS: dict[str, int] = {
     "src/world_engine/analyzer_transcript.py": 3,
     "src/world_engine/cockpit/crud/locations.py": 7,
-    "src/world_engine/cockpit/play_discovery.py": 3,
-    "src/world_engine/models/canon_knowledge.py": 1,
-    "src/world_engine/writes/knowledge.py": 8,
+    "src/world_engine/cockpit/play_discovery.py": 1,
 }
 
 A = "11111111-1111-1111-1111-111111111111"
@@ -204,7 +210,8 @@ def _insert(cursor, rows) -> None:
 
 def _v2_08_database() -> sqlite3.Connection:
     """A second database, built from the current metadata, then taken back
-    to the v2.08 shape of the two objects v2.09 creates."""
+    to the v2.08 shape: without the two objects v2.09 creates, and with the
+    `knowledge.subject` column and index v2.10 drops."""
     from sqlalchemy import create_engine
     from sqlmodel import SQLModel
 
@@ -212,14 +219,16 @@ def _v2_08_database() -> sqlite3.Connection:
     SQLModel.metadata.create_all(create_engine(f"sqlite:///{db_path}"))
     conn = sqlite3.connect(db_path, isolation_level=None)
     conn.execute("DROP INDEX idx_knowledge_entity_fact")
+    conn.execute("ALTER TABLE knowledge ADD COLUMN subject TEXT NOT NULL DEFAULT ''")
+    conn.execute("CREATE INDEX idx_knowledge_subject ON knowledge(subject)")
     conn.execute("DROP TABLE discoverable_detail")
     conn.execute(_V2_08_DETAIL)
     _insert(conn.cursor(), _ROWS)
     return conn
 
 
-def _load_migration():
-    spec = importlib.util.spec_from_file_location("migrate_v2_09_check", MIGRATION_V2_09)
+def _load_migration(path: pathlib.Path = MIGRATION_V2_09):
+    spec = importlib.util.spec_from_file_location(f"{path.stem}_check", path)
     module = importlib.util.module_from_spec(spec)
     spec.loader.exec_module(module)
     return module
@@ -298,6 +307,43 @@ def rule_k2() -> None:
     if report["absorbed"] or report["index_created"] or report["npc_facts"]["token"] \
             or report["detail_column_added"] or report["gates_rekeyed"] or _snapshot(conn) != before:
         fail(f"K2g the second run changed something: {report!r}")
+    _k9(conn)
+
+
+def _k9(conn) -> None:
+    """K9 on the migrated K2 database."""
+    drop = _load_migration(MIGRATION_V2_10)
+    cursor = conn.cursor()
+    count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
+    conn.execute("INSERT INTO fact (id, world_id, content, created_by, change_history) "
+                 "VALUES ('f-lone', 'w1', 'lone', 'check', '[]')")
+    conn.execute("INSERT INTO knowledge (id, entity_id, fact_id, subject, level, change_history, "
+                 "updated_at) VALUES ('k-lone', ?, 'f-lone', 'other label', 'rumor', '[]', "
+                 "'2026-01-01 00:00:00')", (P,))
+    for expect_abort in (True, False):
+        cursor.execute("BEGIN")
+        try:
+            dropped = drop.migrate(cursor)
+            cursor.execute("COMMIT")
+            if expect_abort:
+                fail("K9a a label with no fact content and no participant did not abort v2.10")
+        except drop.Abort:
+            cursor.execute("ROLLBACK")
+            if not expect_abort:
+                fail("K9b v2.10 aborted on a clean database")
+                return
+        conn.execute("DELETE FROM knowledge WHERE id = 'k-lone'")
+        conn.execute("DELETE FROM fact WHERE id = 'f-lone'")
+    columns = [row[1] for row in conn.execute("PRAGMA table_info(knowledge)")]
+    if not dropped or "subject" in columns or conn.execute(
+            "SELECT 1 FROM sqlite_master WHERE name = 'idx_knowledge_subject'").fetchone():
+        fail(f"K9b knowledge.subject or its index survived v2.10: {columns!r}")
+    if conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0] != count:
+        fail("K9b v2.10 changed the knowledge row count")
+    cursor.execute("BEGIN")
+    if drop.migrate(cursor) is not False:
+        fail("K9c a second v2.10 run did not report the column already gone")
+    cursor.execute("COMMIT")
 
 
 _KEY_CASES: tuple[tuple[dict, tuple[str, str]], ...] = (
diff --git a/tooling/verify/checks/knowledge_resolution.py b/tooling/verify/checks/knowledge_resolution.py
index 4670f6a..968e662 100644
--- a/tooling/verify/checks/knowledge_resolution.py
+++ b/tooling/verify/checks/knowledge_resolution.py
@@ -127,7 +127,7 @@ def _build_fixture(session):
     # Tier 1 — stored row beats everything, including a faction default.
     fact_stored = _fact("tier1: stored beats faction default")
     create_fact_default(session, world_id=world_id, fact_id=fact_stored, scope_type="faction", scope_id=faction_a_id, level="knows", created_by="check")
-    write_knowledge(session, entity_id=alice_id, fact_id=fact_stored, subject="tier1", level="partial")
+    write_knowledge(session, entity_id=alice_id, fact_id=fact_stored, level="partial")
     session.commit()
 
     # Tier 2 — location beats world.
@@ -310,7 +310,7 @@ def _build_c09_fixture(session):
         ("rencontre", friend_id), ("location", here_id), ("faction", faction_id), ("world", None),
     ):
         _default(f1, scope_type, scope_id, "knows")
-    write_knowledge(session, entity_id=perceiver_id, fact_id=f1, subject="c09 1", level="unaware")
+    write_knowledge(session, entity_id=perceiver_id, fact_id=f1, level="unaware")
     session.commit()
     cases[1] = (f1, "unaware")
 
diff --git a/tooling/verify/checks/name_index.py b/tooling/verify/checks/name_index.py
index f9167b9..6ae6c53 100644
--- a/tooling/verify/checks/name_index.py
+++ b/tooling/verify/checks/name_index.py
@@ -250,7 +250,7 @@ def _appellation(session, owner, content, scope=None):
 def _make_creator_only(session, owner, fact) -> None:
     from world_engine.writes.knowledge import write_knowledge
 
-    write_knowledge(session, entity_id=owner.id, fact_id=fact.id, subject="creator_meta",
+    write_knowledge(session, entity_id=owner.id, fact_id=fact.id,
                     level="unaware", is_secret=True, changed_by="check")
     session.flush()
 
diff --git a/tooling/verify/checks/observation_runner.py b/tooling/verify/checks/observation_runner.py
index 2a64f04..5a883f1 100644
--- a/tooling/verify/checks/observation_runner.py
+++ b/tooling/verify/checks/observation_runner.py
@@ -294,7 +294,7 @@ def check_rules_5_6_7(fixture, engine) -> None:
     window_items = [{
         "mutation_type": "new_knowledge",
         "payload": {
-            "entity_id": npc_ids[1], "subject": "observed_test_subject",
+            "entity_id": npc_ids[1],
             "level": "rumor", "content": "un fait observé", "source": "conversation",
         },
     }]
diff --git a/tooling/verify/checks/subject_resolution.py b/tooling/verify/checks/subject_resolution.py
index 1660ccd..ae716b3 100644
--- a/tooling/verify/checks/subject_resolution.py
+++ b/tooling/verify/checks/subject_resolution.py
@@ -182,7 +182,7 @@ def check_behavioural(engine) -> None:
         # ── A3, negative: a subject_entity_id from a DIFFERENT world is refused,
         #    nothing written ─────────────────────────────────────────────────
         payload_cross_world = {
-            "entity_id": learner, "subject": "s", "content": "c",
+            "entity_id": learner, "content": "c",
             "subject_entity_id": subject_other_world,
         }
         err = _mutation_apply_new_knowledge(mut, payload_cross_world, session)
@@ -198,7 +198,7 @@ def check_behavioural(engine) -> None:
 
         # ── A3, heal: an in-world id applies, one participant, role NULL ────────
         payload_in_world = {
-            "entity_id": learner, "subject": "s", "content": "c",
+            "entity_id": learner, "content": "c",
             "subject_entity_id": subject_in_world,
         }
         err2 = _mutation_apply_new_knowledge(mut, payload_in_world, session)
@@ -220,7 +220,7 @@ def check_behavioural(engine) -> None:
         fact_id = fps[0].fact_id
         second_learner = _npc(world_a.id, "Second Learner")
         write_knowledge(
-            session, entity_id=second_learner, subject="s", fact_id=fact_id,
+            session, entity_id=second_learner, fact_id=fact_id,
             subject_entity_ids=[subject_in_world],
         )
         session.commit()
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index 039ef04..f2fa539 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -134,7 +134,7 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
                            "type": "relation_gte", "target_entity_id": "{w}-loc",
                            "threshold": 50}),
     ("knowledge", {"id": "kn-{w}", "entity_id": "{w}-char", "fact_id": "fa-{w}",
-                   "subject": "s", "level": "knows"}),
+                   "level": "knows"}),
     ("observation_run", {"id": "or-{w}", "world_id": "{w}", "location_id": "{w}-loc",
                          "max_beats": 1, "quiescence_limit": 1, "cooldown_beats": 1,
                          "debt_weight": 1.0, "propensity_mode": "flat", "model": "m"}),
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 3a38ae1..2f2e461 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,10 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.10** — TICKET-0097, BRIEF-0097-G: `knowledge.subject` and
+  `idx_knowledge_subject` dropped. `migrate_v2_10_drop_knowledge_subject.py`
+  refuses to run before v2.09, and while a row's subject is neither
+  `creator_meta`, nor its fact's content, nor backed by a participant.
 - **v2.09** — TICKET-0097, BRIEF-0097-A: knowledge identity by fact —
   `idx_knowledge_entity_fact`, a UNIQUE index on `knowledge(entity_id,
   fact_id)`, and `discoverable_detail.fact_id` (nullable FK to `fact`).
diff --git a/world-engine-schema.md b/world-engine-schema.md
index bd1b56f..44b260e 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.09
+Current schema version: v2.10
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -698,20 +698,17 @@ CREATE INDEX idx_fact_default_fact ON fact_default(fact_id);
 
 What each entity knows — structured and injectable into prompts.
 `fact_id` (schema v1.98, TICKET-0082, BRIEF-0082-b) anchors each row to the
-fact it is knowledge OF; `subject` is unchanged and still the identity key
-for the ten call sites enumerated in BRIEF-0082-b (cutover deferred to a
-successor ticket). From v2.09 (TICKET-0097, BRIEF-0097-A) a row is unique
-per `(entity_id, fact_id)`: what an entity knows is identified by the fact
-it knows (`idx_knowledge_entity_fact`).
+fact it is knowledge OF. From v2.09 (TICKET-0097, BRIEF-0097-A) a row is
+unique per `(entity_id, fact_id)`: what an entity knows is identified by the
+fact it knows (`idx_knowledge_entity_fact`). The free-text `subject` column
+was dropped in v2.10 (BRIEF-0097-G); the name of what is known is the fact's
+content, and what it is about is the fact's participants.
 
 ```sql
 CREATE TABLE knowledge (
   id               TEXT PRIMARY KEY,
   entity_id        TEXT NOT NULL REFERENCES entity(id),
   fact_id          TEXT NOT NULL REFERENCES fact(id),
-  subject          TEXT NOT NULL,
-                   -- ex: "magic_existence", "the_11", "verkhaal_nexus",
-                   --     "the_unnamed", "faction_X_status"
   level            TEXT NOT NULL,
                    -- unaware | rumor | suspicious | partial | knows | fully_understands
   content          TEXT,            -- what exactly it knows
@@ -2018,7 +2015,8 @@ Day-plan precondition gate on one `agenda_step` (schema v1.94, TICKET-0075,
 BRIEF-0075-b). `goal_prerequisite` shape precedent, widened to a closed
 four-form vocabulary (`knowledge`, `relation_gte`, `resource`,
 `location_reachable`) and a `target_key` column for the two forms that gate
-on a string (a knowledge subject, a resource tag) rather than an entity. The
+on a string (a knowledge fact id since v2.09, TICKET-0097; a resource tag)
+rather than an entity. The
 per-type shape CHECK is the structural guarantee that an ill-formed row
 cannot exist: `relation_gte`/`location_reachable` require `target_entity_id`
 NOT NULL; `knowledge`/`resource` require `target_key` NOT NULL;
@@ -2392,10 +2390,6 @@ CREATE INDEX idx_entity_type         ON entity(type);
 -- "everything entity X knows"
 CREATE INDEX idx_knowledge_entity    ON knowledge(entity_id);
 
--- "who (if anyone) holds subject S" (schema v1.96, BRIEF-0078-a) — the
--- knowledge-gate anchoring lookup, day_plan._anchorable_subjects
-CREATE INDEX idx_knowledge_subject   ON knowledge(subject);
-
 -- "the fact this knowledge row is about" (schema v1.98, BRIEF-0082-b)
 CREATE INDEX idx_knowledge_fact      ON knowledge(fact_id);
 
```

## Scope OUT

- Rebuilding `knowledge` for any other reason.
- `discoverable_detail.subject` (a detail label, stays).
- Running the migrations on Nia's DB: the live gate does it.

## Invariants to defend

**The app refuses to boot when `schema_meta.static_version` != `EXPECTED_STATIC_SCHEMA_VERSION`** — v2.09 and v2.10 must both run before the cockpit. **History is sacred** — v2.10 refuses to drop a label that exists nowhere else. `migration` is a `danger_class`: human gate, no auto-merge.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- v2.10 aborts on a temp DB migrated by v2.09 from a fresh seed.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `knowledge_identity.py` K3 fails only on counts, with every reported file named in this brief's diff: re-run the census (see Done means) and report the table.

REPORT-ONLY:
- Any other file still naming `subject` in a comment or docstring.
- Timing of the corpus run.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat` of the commit lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` (regenerated).
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/knowledge_identity.py` → `PASS`.
- On a temp DB: `init_db.py`, `seed_pilot.py`, `seed_pilot.py` again (idempotent), then `migrate_v2_10_drop_knowledge_subject.py` twice: `knowledge.subject already gone — nothing to do.` (a fresh DB is created without the column) and `schema_meta.id=1` at `v2.10`.
- On a temp DB built at `main` (`git stash`/checkout `89fc38a`, `init_db`, `seed_pilot`), with Senna's two rows moved onto Reike's facts by SQL, then this branch: v2.09, v2.10, `apply_ticket_0097_fact_code_prompts.py` (five heads `v1 -> v2`), and `schema_reconcile.unaccounted_tables(engine, session)` → `[]`.
- `WORLD_ENGINE_ENV=test python tooling/verify/run.py --ticket TICKET-0097-knowledge-identity` → every check `PASS`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → `PASS: corpus_gate — 126 check(s) discovered, 126 executed, 126 passed`.
- `/review-step` then `/close-step` ran on the commit.

Census re-run (for the K3 ADAPT above): the census function is `census()` in
`knowledge_identity.py`; print it with
`WORLD_ENGINE_ENV=test python -c "import sys; sys.path.insert(0,'tooling/verify/checks'); import knowledge_identity as k; print(k.census())"`.

## Docs to update

This brief carries its docs: schema doc v2.10, changelog v2.10, decision entry `KNOWLEDGE.SUBJECT IS DROPPED … (BRIEF-0097-g, schema v2.10)`.
