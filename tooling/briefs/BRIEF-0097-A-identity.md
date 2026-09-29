<!-- slug: identity -->
# BRIEF 0097-A — "Identity: unique (entity, fact), v2.09"

Lot: LOT-0097-knowledge-identity.md (authoritative on conflict)
Depends on: nothing in this lot
Commit header for decisions: `(BRIEF-0097-a, schema v2.09)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0097` before applying anything. Halt if one has moved.

- `src/world_engine/models/canon_knowledge.py:206-207` → `Index("idx_knowledge_subject", "subject"),` then `Index("idx_knowledge_fact", "fact_id"),` — no unique index on `(entity_id, fact_id)`
- `src/world_engine/models/canon.py:692` → `subject: str  # short tag, e.g. "lettre_innommee"` in `DiscoverableDetail`, no `fact_id`
- `src/world_engine/schema_version.py:15` → `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.08"`
- `scripts/seed_pilot.py` `kn-senna-existence`, `kn-senna-awakening` → created without `fact_id` (each gets its own fact)
- `tooling/tickets/TICKET-0096-world-cascade.md` → front matter `status: live-gate`, `current_brief: B`
- `tooling/verify/checks/knowledge_identity.py` → does not exist

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

### R-06 — the pilot seed splits two subjects
Opened: `scripts/seed_pilot.py:3403-3450`, a fresh `init_db` + `seed_pilot`.
Finding: `magic_existence` and `magic_awakening` are each held by Reike and
Senna on two facts (13 rows, 11 subjects, 13 facts).
Consequence: A seeds Senna's rows on Reike's facts (`_fact_of`); a test DB
seeded before 0097 is rebuilt, not migrated (v2.09 refuses it, E1).

### R-14 — foreign keys onto `fact` and `knowledge`
Opened: `SQLModel.metadata` (command below, gate (c)).
Finding: after A, `fact` ← `discoverable_detail.fact_id`, `fact_default`,
`fact_participant`, `knowledge`, `unresolved_mention`; `knowledge` ←
`unresolved_mention.knowledge_id`.
Consequence: v2.09's absorption repoints `unresolved_mention.knowledge_id`
before deleting a duplicate; `world_cascade.py`'s fixture orders
`discoverable_detail` after `fact`.

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

TICKET-0096 passed its live gate. This brief closes it, then lays the identity the whole lot stands on: a `knowledge` row is unique per `(entity_id, fact_id)`, a discoverable detail can point at its fact, and the v2.09 migration brings existing data to that shape without merging anything (E1).

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below to a file and run `git apply --check <file>` then `git apply <file>` from the
repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. **Commit 1 (on its own):** in `tooling/tickets/TICKET-0096-world-cascade.md` set `status: done` and empty `current_brief:`. Message: `chore(tickets): close TICKET-0096 — live gate passed (Nia, 2026-09-28)`.
2. **Commit 2:** apply the embedded diff (`git apply --check`, then `git apply`). It: adds `idx_knowledge_entity_fact` (UNIQUE) to `Knowledge` and `fact_id` (nullable FK) to `DiscoverableDetail`; bumps `schema_version.py`, the schema doc header and DDL, and the changelog to v2.09; creates `scripts/migrate_v2_09_knowledge_identity.py` (C-09); makes the pilot seed share Reike's facts with Senna (`_fact_of`); moves the `discoverable_detail` fixture row after `fact_participant` in `world_cascade.py` with a `fact_id`; creates `tooling/verify/checks/knowledge_identity.py` (K1, K2, K3); appends the decision entry.
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Commit 2 message: `feat(knowledge): identity by fact — unique (entity, fact), v2.09 (BRIEF-0097-a)`.

```diff
diff --git a/scripts/migrate_v2_09_knowledge_identity.py b/scripts/migrate_v2_09_knowledge_identity.py
new file mode 100644
index 0000000..195d755
--- /dev/null
+++ b/scripts/migrate_v2_09_knowledge_identity.py
@@ -0,0 +1,330 @@
+"""Migration v2.09 — knowledge identity by fact (TICKET-0097, BRIEF-0097-A).
+
+What an entity knows becomes identified by the fact it knows. One
+transaction, in this order:
+
+- S1 guard (E1): no world holds a `knowledge.subject` spread over more than
+  one `fact_id`, `creator_meta` excepted (each creator note is its own fact
+  on purpose). A split aborts the run, writing nothing, and lists the
+  groups — there is no merge.
+- S2 absorb (F1): every `(entity_id, fact_id)` group holding more than one
+  row keeps one survivor — highest level on `KNOWLEDGE_LEVEL_LADDER`, then
+  latest `updated_at`, then smallest `id` — and each other row's state is
+  appended to the survivor's `change_history` (`changed_by =
+  'migrate_v2_09'`, `absorbed_knowledge_id`) before the row is deleted.
+  `unresolved_mention.knowledge_id` pointing at an absorbed row is repointed
+  to the survivor first.
+- S3 `CREATE UNIQUE INDEX idx_knowledge_entity_fact ON knowledge(entity_id,
+  fact_id)`.
+- S4 link-agent facts (G): every fact whose content is exactly `npc:<id>`,
+  where `<id>` is an `entity` of the fact's own world (any status), gets
+  that entity as a `fact_participant` (read before write). When `<id>` has
+  the identity-token shape (`prose_render.TOKEN_RE`, a 36-character uuid),
+  the content is also rewritten to `[[e:<id>|<name>]]`, the previous content
+  appended to the fact's `change_history` first; a non-uuid id (the pilot
+  seed's hand-written ids) keeps its content. A `npc:<id>` fact whose id is
+  no entity of that world is left untouched and reported.
+- S5 `ALTER TABLE discoverable_detail ADD COLUMN fact_id TEXT REFERENCES
+  fact(id)` (H1).
+- S6 day gates (D1'a): every `agenda_step_requirement` of type `knowledge`
+  whose `target_key` equals the `subject` of knowledge rows of its world on
+  exactly one fact gets `target_key = <that fact_id>`. Any other key is left
+  untouched and reported.
+- S7 post-checks, then `schema_meta` converges to v2.09.
+
+`knowledge.subject` itself is not touched: v2.10 (BRIEF-0097-F) drops it.
+
+Idempotent: S1 and S2 find nothing on a second run; S3 and S5 are guarded
+by `sqlite_master` / `PRAGMA table_info`; S4 attaches a participant only when
+absent and tokenizes only `npc:<uuid>` content, which a first run rewrote; S6 matches only keys that are subjects.
+
+Run from the project root (after `python scripts/backup.py`), then run
+`migrate_v2_10_drop_knowledge_subject.py` before starting the cockpit:
+
+    python scripts/migrate_v2_09_knowledge_identity.py
+"""
+
+from __future__ import annotations
+
+import json
+import os
+import re
+import sys
+import uuid
+from datetime import UTC, datetime
+from pathlib import Path
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
+    print(
+        "migrate_v2_09_knowledge_identity.py refuses to run without WORLD_ENGINE_ENV "
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
+from world_engine.prose_render import entity_token  # noqa: E402
+from world_engine.writes.knowledge import KNOWLEDGE_LEVEL_LADDER  # noqa: E402
+
+TARGET_VERSION = "v2.09"
+CREATED_BY = "migrate_v2_09"
+CREATOR_META = "creator_meta"
+INDEX_NAME = "idx_knowledge_entity_fact"
+NPC_CONTENT = re.compile(r"^npc:(\S+)$")
+UUID_ID = re.compile(r"^[0-9a-fA-F-]{36}$")
+
+
+class Abort(Exception):
+    """A pre- or post-check failed; the transaction is rolled back."""
+
+
+def _now() -> str:
+    return datetime.now(UTC).isoformat()
+
+
+def split_subjects(cursor) -> list[tuple]:
+    """(world name, subject, fact count) of every subject spread over more
+    than one fact within a world, `creator_meta` excepted."""
+    return cursor.execute(
+        "SELECT w.name, k.subject, COUNT(DISTINCT k.fact_id) FROM knowledge k "
+        "JOIN entity e ON e.id = k.entity_id JOIN world w ON w.id = e.world_id "
+        "WHERE k.subject <> ? GROUP BY e.world_id, k.subject "
+        "HAVING COUNT(DISTINCT k.fact_id) > 1 ORDER BY w.name, k.subject",
+        (CREATOR_META,),
+    ).fetchall()
+
+
+def _rank(level: str) -> int:
+    return KNOWLEDGE_LEVEL_LADDER.index(level) if level in KNOWLEDGE_LEVEL_LADDER else -1
+
+
+def _absorb_group(cursor, rows: list[tuple]) -> int:
+    """rows: (id, level, content, source, is_incorrect, updated_at,
+    change_history). Keeps the survivor, absorbs the others. Returns the
+    number of rows deleted."""
+    ordered = sorted(rows, key=lambda r: r[0])
+    ordered = sorted(ordered, key=lambda r: r[5] or "", reverse=True)
+    ordered = sorted(ordered, key=lambda r: _rank(r[1]), reverse=True)
+    survivor, absorbed = ordered[0], ordered[1:]
+    history = json.loads(survivor[6] or "[]")
+    for row in absorbed:
+        history.append({
+            "level": row[1], "content": row[2], "source": row[3],
+            "is_incorrect": bool(row[4]), "updated_at": row[5],
+            "changed_by": CREATED_BY, "changed_at": _now(),
+            "absorbed_knowledge_id": row[0],
+        })
+        cursor.execute(
+            "UPDATE unresolved_mention SET knowledge_id = ? WHERE knowledge_id = ?",
+            (survivor[0], row[0]),
+        )
+        cursor.execute("DELETE FROM knowledge WHERE id = ?", (row[0],))
+    cursor.execute(
+        "UPDATE knowledge SET change_history = ? WHERE id = ?",
+        (json.dumps(history, ensure_ascii=False), survivor[0]),
+    )
+    return len(absorbed)
+
+
+def absorb_duplicates(cursor) -> list[tuple]:
+    """S2. Returns (entity_id, fact_id, rows deleted) per absorbed group."""
+    groups = cursor.execute(
+        "SELECT entity_id, fact_id FROM knowledge GROUP BY entity_id, fact_id "
+        "HAVING COUNT(*) > 1 ORDER BY entity_id, fact_id"
+    ).fetchall()
+    report = []
+    for entity_id, fact_id in groups:
+        rows = cursor.execute(
+            "SELECT id, level, content, source, is_incorrect, updated_at, change_history "
+            "FROM knowledge WHERE entity_id = ? AND fact_id = ?",
+            (entity_id, fact_id),
+        ).fetchall()
+        report.append((entity_id, fact_id, _absorb_group(cursor, rows)))
+    return report
+
+
+def create_unique_index(cursor) -> bool:
+    """S3. False when the index already exists."""
+    exists = cursor.execute(
+        "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?", (INDEX_NAME,)
+    ).fetchone()
+    if exists:
+        return False
+    cursor.execute(f"CREATE UNIQUE INDEX {INDEX_NAME} ON knowledge(entity_id, fact_id)")
+    return True
+
+
+def _rewrite_npc_fact(cursor, fact_id: str, content: str, world_id: str, history_raw) -> str | None:
+    """"token", "participant" (non-uuid id: participant only) or None
+    (no such entity in the fact's world: untouched)."""
+    entity_id = NPC_CONTENT.match(content).group(1)
+    entity = cursor.execute(
+        "SELECT name FROM entity WHERE id = ? AND world_id = ?", (entity_id, world_id)
+    ).fetchone()
+    if entity is None:
+        return None
+    attached = cursor.execute(
+        "SELECT 1 FROM fact_participant WHERE fact_id = ? AND entity_id = ?", (fact_id, entity_id)
+    ).fetchone()
+    if not attached:
+        cursor.execute(
+            "INSERT INTO fact_participant (id, world_id, fact_id, entity_id, role, position) "
+            "VALUES (?, ?, ?, ?, NULL, 0)",
+            (str(uuid.uuid4()), world_id, fact_id, entity_id),
+        )
+    if not UUID_ID.match(entity_id):
+        return "participant"
+    history = json.loads(history_raw or "[]")
+    history.append({"content": content, "changed_by": CREATED_BY, "at": _now()})
+    cursor.execute(
+        "UPDATE fact SET content = ?, change_history = ? WHERE id = ?",
+        (entity_token(entity_id, entity[0]), json.dumps(history, ensure_ascii=False), fact_id),
+    )
+    return "token"
+
+
+def rewrite_npc_facts(cursor) -> dict[str, list[str]]:
+    """S4. Fact ids by outcome: "token", "participant", "untouched"."""
+    facts = cursor.execute(
+        "SELECT id, content, world_id, change_history FROM fact WHERE content LIKE 'npc:%'"
+    ).fetchall()
+    outcome: dict[str, list[str]] = {"token": [], "participant": [], "untouched": []}
+    for fact_id, content, world_id, history_raw in facts:
+        result = None
+        if NPC_CONTENT.match(content):
+            result = _rewrite_npc_fact(cursor, fact_id, content, world_id, history_raw)
+        outcome[result or "untouched"].append(fact_id)
+    return outcome
+
+
+def add_detail_fact_column(cursor) -> bool:
+    """S5. False when the column already exists."""
+    columns = [row[1] for row in cursor.execute("PRAGMA table_info(discoverable_detail)")]
+    if "fact_id" in columns:
+        return False
+    cursor.execute("ALTER TABLE discoverable_detail ADD COLUMN fact_id TEXT REFERENCES fact(id)")
+    return True
+
+
+def rekey_knowledge_gates(cursor) -> tuple[int, list[tuple]]:
+    """S6. Returns (requirements rekeyed, (id, target_key) left untouched)."""
+    rows = cursor.execute(
+        "SELECT id, world_id, target_key FROM agenda_step_requirement WHERE type = 'knowledge'"
+    ).fetchall()
+    rekeyed, untouched = 0, []
+    for req_id, world_id, key in rows:
+        facts = cursor.execute(
+            "SELECT DISTINCT k.fact_id FROM knowledge k JOIN entity e ON e.id = k.entity_id "
+            "WHERE e.world_id = ? AND k.subject = ?",
+            (world_id, key),
+        ).fetchall()
+        if len(facts) == 1:
+            cursor.execute(
+                "UPDATE agenda_step_requirement SET target_key = ? WHERE id = ?", (facts[0][0], req_id)
+            )
+            rekeyed += 1
+        elif not cursor.execute("SELECT 1 FROM fact WHERE id = ?", (key,)).fetchone():
+            untouched.append((req_id, key))
+    return rekeyed, untouched
+
+
+def post_checks(cursor) -> None:
+    """S7."""
+    if split_subjects(cursor):
+        raise Abort("post-check: a subject is still spread over several facts")
+    duplicates = cursor.execute(
+        "SELECT COUNT(*) FROM (SELECT 1 FROM knowledge GROUP BY entity_id, fact_id HAVING COUNT(*) > 1)"
+    ).fetchone()[0]
+    if duplicates:
+        raise Abort(f"post-check: {duplicates} (entity_id, fact_id) group(s) still duplicated")
+    unbound = cursor.execute(
+        "SELECT COUNT(*) FROM fact f JOIN entity e ON e.world_id = f.world_id "
+        "AND f.content = 'npc:' || e.id WHERE NOT EXISTS (SELECT 1 FROM fact_participant p "
+        "WHERE p.fact_id = f.id AND p.entity_id = e.id)"
+    ).fetchone()[0]
+    if unbound:
+        raise Abort(f"post-check: {unbound} npc:<id> fact(s) of a known entity without participant")
+
+
+def migrate(cursor) -> dict:
+    """S1-S7 on an open transaction. Raises `Abort` on any failed check."""
+    splits = split_subjects(cursor)
+    if splits:
+        lines = "; ".join(f"{world!r} {subject!r} on {n} facts" for world, subject, n in splits)
+        raise Abort(f"a subject is spread over several facts, merge them first: {lines}")
+    report = {"absorbed": absorb_duplicates(cursor), "index_created": create_unique_index(cursor)}
+    report["npc_facts"] = rewrite_npc_facts(cursor)
+    report["detail_column_added"] = add_detail_fact_column(cursor)
+    report["gates_rekeyed"], report["gates_untouched"] = rekey_knowledge_gates(cursor)
+    post_checks(cursor)
+    return report
+
+
+def _print_report(report: dict) -> None:
+    print(f"S2 absorbed duplicate rows: {sum(n for _, _, n in report['absorbed'])} "
+          f"in {len(report['absorbed'])} group(s)")
+    for entity_id, fact_id, n in report["absorbed"]:
+        print(f"   entity {entity_id} fact {fact_id}: {n} row(s) absorbed")
+    print(f"S3 unique index created: {report['index_created']}")
+    npc = report["npc_facts"]
+    print(f"S4 npc:<id> facts: {len(npc['token'])} tokenized, {len(npc['participant'])} "
+          f"participant only, {len(npc['untouched'])} untouched {npc['untouched']}")
+    print(f"S5 discoverable_detail.fact_id added: {report['detail_column_added']}")
+    print(f"S6 knowledge gates rekeyed: {report['gates_rekeyed']}; "
+          f"left untouched: {len(report['gates_untouched'])} {report['gates_untouched']}")
+
+
+def _apply() -> None:
+    raw = engine.raw_connection()
+    try:
+        cursor = raw.cursor()
+        cursor.execute("BEGIN")
+        try:
+            report = migrate(cursor)
+        except Abort as exc:
+            cursor.execute("ROLLBACK")
+            raise SystemExit(f"Migration {TARGET_VERSION} aborted, rolled back. {exc}") from None
+        cursor.execute("COMMIT")
+        cursor.close()
+        _print_report(report)
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
+    print(f"Migration {TARGET_VERSION} — knowledge identity by fact")
+    _apply()
+    _converge_schema_meta()
+    print(f"\nMigration {TARGET_VERSION} applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index 2151d43..703fce9 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -120,6 +120,15 @@ def upsert_knowledge(session: Session, id: str, **fields):
     )
 
 
+def _fact_of(session: Session, knowledge_id: str) -> str:
+    """The `fact_id` of an already-seeded knowledge row. Two entities that
+    know the same thing share its fact (TICKET-0097, BRIEF-0097-A: a
+    knowledge row is identified by the fact it knows); passing it on
+    converges a row seeded on its own fact by an earlier run."""
+    session.flush()
+    return session.get(m.Knowledge, knowledge_id).fact_id
+
+
 def upsert_prompt_template(
     session: Session, id: str, *, system_prompt: str, user_template: str, **head_fields
 ):
@@ -3430,6 +3439,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-senna-existence",
         entity_id="npc-senna",
+        fact_id=_fact_of(session, "kn-reike-existence"),
         subject="magic_existence",
         level="knows",
         content="Savoir de base des Marcheurs : la magie est réelle, elle a dormi.",
@@ -3440,6 +3450,7 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         "kn-senna-awakening",
         entity_id="npc-senna",
+        fact_id=_fact_of(session, "kn-reike-awakening"),
         subject="magic_awakening",
         level="knows",
         content=(
diff --git a/src/world_engine/models/canon.py b/src/world_engine/models/canon.py
index daf8e76..9b79e2e 100644
--- a/src/world_engine/models/canon.py
+++ b/src/world_engine/models/canon.py
@@ -691,6 +691,9 @@ class DiscoverableDetail(SQLModel, table=True):
     location_id: str = Field(foreign_key="entity.id", nullable=False)
     subject: str  # short tag, e.g. "lettre_innommee"
     content: str  # what the player learns on discovery
+    # TICKET-0097 (BRIEF-0097-A, schema v2.09): the fact a discovery of this
+    # detail attaches to. NULL until the first approved discovery creates it.
+    fact_id: Optional[str] = Field(default=None, foreign_key="fact.id")
     access_level: str = Field(
         default="hidden",
         sa_column_kwargs={"server_default": text("'hidden'")},
diff --git a/src/world_engine/models/canon_knowledge.py b/src/world_engine/models/canon_knowledge.py
index 3c51f52..fe69670 100644
--- a/src/world_engine/models/canon_knowledge.py
+++ b/src/world_engine/models/canon_knowledge.py
@@ -205,6 +205,9 @@ class Knowledge(SQLModel, table=True):
         Index("idx_knowledge_entity", "entity_id"),
         Index("idx_knowledge_subject", "subject"),
         Index("idx_knowledge_fact", "fact_id"),
+        # TICKET-0097 (BRIEF-0097-A, schema v2.09): what an entity knows is
+        # identified by the fact it knows -- one row per (entity, fact).
+        Index("idx_knowledge_entity_fact", "entity_id", "fact_id", unique=True),
     )
 
     id: str = Field(default_factory=_uuid, primary_key=True)
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index 507ef9c..025a93f 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.08"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.09"
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 6a384b8..a4e6fd9 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17006,6 +17006,50 @@ rows (children first, BRIEF-0037-e), never commit, and are called only by
 `DELETE /api/worlds/{id}`, after the cascade, in its transaction; a refusal
 raises before them. Neither strata check learned an exception (G2).
 
+## KNOWLEDGE IDENTITY (TICKET-0097) -- A KNOWLEDGE ROW IS WHO KNOWS WHICH FACT (BRIEF-0097-a, schema v2.09)
+
+**B3 -- the fact is the identity, the subject goes.** Since TICKET-0082 every
+`knowledge` row points at the fact it is knowledge of, and since 0087 a
+`fact_participant` says what that fact is about. The free-text `subject`
+still carried three jobs on top: the dedup key of the mutation pipeline, a
+bridge to other tables (`discoverable_detail`, day gates, the link agent's
+`npc:<id>`), and a label. TICKET-0097 moves each job to the fact and v2.10
+drops the column. The label survives as the fact's content: a legacy fact's
+content is its old subject, unchanged (C1); a fact born after 0097 carries a
+sentence (M1).
+
+**F1 -- the index says it once.** `idx_knowledge_entity_fact` makes
+`(entity_id, fact_id)` unique. Prod held three duplicated pairs; v2.09
+absorbs each into its highest-level twin, the absorbed state appended to the
+survivor's `change_history` (history is sacred; `absorbed_knowledge_id`
+records which row it was).
+
+**E1 -- no merge, a guard.** Measured on prod: no subject spreads over two
+facts in a world, except `creator_meta`, whose facts are distinct on purpose.
+v2.09 refuses to run if that changes, rather than carrying a merge nobody
+exercised. A test database seeded from the pilot before this ticket held two
+such subjects; `seed_pilot.py` now shares their fact, and such a database is
+rebuilt (`init_db.py`, `seed_pilot.py`) rather than migrated.
+
+**G -- the link agent's facts get their participant.** 269 prod rows carried
+`subject = npc:<uuid>`, which `subject_resolve` never resolved, so "who knows
+what about X" missed 42 % of knowledge. v2.09 attaches the entity and writes
+its identity token as the content.
+
+**H1 -- a detail owns its fact.** `discoverable_detail.fact_id` is filled by
+the first approved discovery (BRIEF-0097-C); zero detail was ever discovered
+in prod, so nothing is backfilled.
+
+**D1'a, data half.** A persisted `knowledge` gate's `target_key` becomes the
+fact id of its subject; the planner learns to emit fact codes in
+BRIEF-0097-D.
+
+**The census.** `knowledge_identity.py` K3 pins, per file, every `subject`
+reference left in `src/`; each brief lowers it in the commit that removes a
+reference, so a new reader of `subject` is red.
+
+**Also closed here.** TICKET-0096 passed its live gate (Nia, 2026-09-28).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/knowledge_identity.py b/tooling/verify/checks/knowledge_identity.py
new file mode 100644
index 0000000..a0af6f0
--- /dev/null
+++ b/tooling/verify/checks/knowledge_identity.py
@@ -0,0 +1,312 @@
+"""G1 check for TICKET-0097 -- a knowledge row is identified by the fact it
+knows, never by its free-text `subject`.
+
+K1 -- model. `knowledge` declares the unique index
+   `idx_knowledge_entity_fact` on exactly `(entity_id, fact_id)`;
+   `discoverable_detail.fact_id` is a nullable foreign key to `fact.id`.
+K2 -- migration v2.09 (`scripts/migrate_v2_09_knowledge_identity.py`), run
+   on a v2.08-shaped fixture database:
+   a. a subject spread over two facts in one world aborts the run, and the
+      rolled-back database is unchanged; `creator_meta` spread over two
+      facts does not abort;
+   b. a duplicated `(entity_id, fact_id)` keeps its highest-level row, the
+      other row's state lands in the survivor's `change_history` with its
+      `absorbed_knowledge_id`, and `unresolved_mention.knowledge_id` follows
+      the survivor;
+   c. the unique index exists afterwards;
+   d. a `npc:<uuid>` fact of a known entity gets that entity as participant
+      and the content `[[e:<uuid>|<name>]]`; its previous content is in the
+      fact's `change_history`;
+   e. `discoverable_detail.fact_id` exists afterwards;
+   f. a knowledge gate keyed by a subject is rekeyed to that subject's
+      fact id; a gate keyed by an unknown string is untouched;
+   g. a second run changes nothing.
+K3 -- census. The `subject` references of `src/world_engine` (an attribute
+   `.subject`, a string constant `"subject"`, a `subject=` keyword or a
+   `subject` parameter), counted per file, equal `_SUBJECT_CENSUS` exactly.
+   Each brief of TICKET-0097 lowers it in the same commit that removes a
+   reference; a new reference is red until someone decides it belongs.
+
+Fresh temp-file SQLite databases (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB.
+"""
+from __future__ import annotations
+
+import ast
+import importlib.util
+import json
+import os
+import pathlib
+import sqlite3
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src"
+MIGRATION_V2_09 = ROOT / "scripts" / "migrate_v2_09_knowledge_identity.py"
+
+FAILURES: list[str] = []
+
+_SUBJECT_CENSUS: dict[str, int] = {
+    "src/world_engine/analyzer.py": 2,
+    "src/world_engine/analyzer_transcript.py": 13,
+    "src/world_engine/cockpit/crud/_shared.py": 3,
+    "src/world_engine/cockpit/crud/knowledge.py": 8,
+    "src/world_engine/cockpit/crud/locations.py": 7,
+    "src/world_engine/cockpit/mutations.py": 11,
+    "src/world_engine/cockpit/play_discovery.py": 3,
+    "src/world_engine/cockpit/routes/creator.py": 2,
+    "src/world_engine/cockpit/routes/day.py": 2,
+    "src/world_engine/cockpit/routes/mutations.py": 6,
+    "src/world_engine/cockpit/routes/npc_agent.py": 2,
+    "src/world_engine/context.py": 4,
+    "src/world_engine/day_mutations.py": 4,
+    "src/world_engine/day_plan.py": 3,
+    "src/world_engine/entity_author.py": 4,
+    "src/world_engine/knowledge_resolve.py": 1,
+    "src/world_engine/link_author.py": 5,
+    "src/world_engine/link_context.py": 4,
+    "src/world_engine/lore_render.py": 1,
+    "src/world_engine/lore_selectors.py": 2,
+    "src/world_engine/models/canon_knowledge.py": 1,
+    "src/world_engine/scene_format.py": 3,
+    "src/world_engine/subject_resolve.py": 4,
+    "src/world_engine/tick.py": 4,
+    "src/world_engine/tick_context.py": 1,
+    "src/world_engine/tick_normalize.py": 2,
+    "src/world_engine/writes/facets.py": 1,
+    "src/world_engine/writes/knowledge.py": 8,
+    "src/world_engine/writes/relations.py": 1,
+}
+
+A = "11111111-1111-1111-1111-111111111111"
+B = "22222222-2222-2222-2222-222222222222"
+P = "33333333-3333-3333-3333-333333333333"
+
+# The v2.08 shape of the one table v2.09 alters (the other tables come from
+# the current metadata; the index v2.09 creates is dropped before the run).
+_V2_08_DETAIL = (
+    "CREATE TABLE discoverable_detail (id TEXT PRIMARY KEY, world_id TEXT NOT NULL, "
+    "location_id TEXT NOT NULL, subject TEXT NOT NULL, content TEXT NOT NULL)"
+)
+
+_ROWS: tuple[tuple[str, dict], ...] = (
+    ("world", {"id": "w1", "name": "W"}),
+    ("entity", {"id": A, "world_id": "w1", "type": "character", "name": "Ana"}),
+    ("entity", {"id": B, "world_id": "w1", "type": "character", "name": "Bel"}),
+    ("entity", {"id": P, "world_id": "w1", "type": "character", "name": "Pio"}),
+    ("fact", {"id": "f-topic", "world_id": "w1", "content": "topic"}),
+    ("fact", {"id": "f-dup", "world_id": "w1", "content": "dup"}),
+    ("fact", {"id": "f-npc", "world_id": "w1", "content": f"npc:{B}"}),
+    ("fact", {"id": "f-meta-a", "world_id": "w1", "content": "note a"}),
+    ("fact", {"id": "f-meta-b", "world_id": "w1", "content": "note b"}),
+    ("knowledge", {"id": "k-a-topic", "entity_id": A, "fact_id": "f-topic", "subject": "topic",
+                   "level": "knows"}),
+    ("knowledge", {"id": "k-b-topic", "entity_id": B, "fact_id": "f-topic", "subject": "topic",
+                   "level": "rumor"}),
+    ("knowledge", {"id": "k-dup-low", "entity_id": A, "fact_id": "f-dup", "subject": "dup",
+                   "level": "rumor", "content": "low"}),
+    ("knowledge", {"id": "k-dup-high", "entity_id": A, "fact_id": "f-dup", "subject": "dup",
+                   "level": "knows", "content": "high"}),
+    ("knowledge", {"id": "k-npc", "entity_id": A, "fact_id": "f-npc", "subject": f"npc:{B}",
+                   "level": "knows"}),
+    ("knowledge", {"id": "k-meta-a", "entity_id": A, "fact_id": "f-meta-a",
+                   "subject": "creator_meta", "level": "unaware"}),
+    ("knowledge", {"id": "k-meta-b", "entity_id": B, "fact_id": "f-meta-b",
+                   "subject": "creator_meta", "level": "unaware"}),
+    ("unresolved_mention", {"id": "um-1", "world_id": "w1", "knowledge_id": "k-dup-low",
+                            "surface": "s", "reason": "inconnu"}),
+    ("agenda", {"id": "ag-1", "world_id": "w1", "owner_entity_id": P, "title": "t"}),
+    ("agenda_step", {"id": "ags-1", "agenda_id": "ag-1", "step_order": 1, "objective": "o"}),
+    ("agenda_step_requirement", {"id": "req-topic", "world_id": "w1", "step_id": "ags-1",
+                                 "type": "knowledge", "target_key": "topic"}),
+    ("agenda_step_requirement", {"id": "req-ghost", "world_id": "w1", "step_id": "ags-1",
+                                 "type": "knowledge", "target_key": "ghost"}),
+)
+_SPLIT_ROWS: tuple[tuple[str, dict], ...] = (
+    ("fact", {"id": "f-split", "world_id": "w1", "content": "topic"}),
+    ("knowledge", {"id": "k-split", "entity_id": P, "fact_id": "f-split", "subject": "topic",
+                   "level": "rumor"}),
+)
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_engine():
+    tmp_dir = tempfile.mkdtemp()
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(SRC))
+    for name in list(sys.modules):
+        if name == "world_engine" or name.startswith("world_engine."):
+            del sys.modules[name]
+    from world_engine.db import create_db_and_tables, engine
+    create_db_and_tables()
+    return engine, pathlib.Path(tmp_dir) / "check.db"
+
+
+def rule_k1(tables) -> None:
+    knowledge = tables["knowledge"]
+    matches = [ix for ix in knowledge.indexes if ix.name == "idx_knowledge_entity_fact"]
+    if not matches:
+        fail("K1 knowledge declares no idx_knowledge_entity_fact")
+    elif not matches[0].unique or [c.name for c in matches[0].columns] != ["entity_id", "fact_id"]:
+        fail("K1 idx_knowledge_entity_fact is not UNIQUE on exactly (entity_id, fact_id)")
+    column = tables["discoverable_detail"].c.get("fact_id")
+    if column is None:
+        fail("K1 discoverable_detail declares no fact_id")
+    elif not column.nullable or [fk.column.table.name for fk in column.foreign_keys] != ["fact"]:
+        fail("K1 discoverable_detail.fact_id is not a nullable foreign key to fact")
+
+
+def _insert(cursor, rows) -> None:
+    for table, values in rows:
+        values = dict(values)
+        if table == "fact":
+            values.setdefault("created_by", "check")
+            values.setdefault("change_history", "[]")
+        if table == "knowledge":
+            values.setdefault("change_history", "[]")
+            values.setdefault("updated_at", "2026-01-01 00:00:00")
+        columns = ", ".join(values)
+        marks = ", ".join("?" for _ in values)
+        cursor.execute(f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(values.values()))
+
+
+def _v2_08_database(db_path: pathlib.Path) -> sqlite3.Connection:
+    conn = sqlite3.connect(db_path, isolation_level=None)
+    conn.execute("DROP INDEX idx_knowledge_entity_fact")
+    conn.execute("DROP TABLE discoverable_detail")
+    conn.execute(_V2_08_DETAIL)
+    _insert(conn.cursor(), _ROWS)
+    return conn
+
+
+def _load_migration():
+    spec = importlib.util.spec_from_file_location("migrate_v2_09_check", MIGRATION_V2_09)
+    module = importlib.util.module_from_spec(spec)
+    spec.loader.exec_module(module)
+    return module
+
+
+def _snapshot(conn) -> dict:
+    return {
+        table: conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
+        for table in ("knowledge", "fact", "fact_participant", "agenda_step_requirement")
+    }
+
+
+def _run(conn, migration):
+    cursor = conn.cursor()
+    cursor.execute("BEGIN")
+    try:
+        report = migration.migrate(cursor)
+    except migration.Abort:
+        cursor.execute("ROLLBACK")
+        raise
+    cursor.execute("COMMIT")
+    return report
+
+
+def _k2a(conn, migration) -> None:
+    before = _snapshot(conn)
+    _insert(conn.cursor(), _SPLIT_ROWS)
+    try:
+        _run(conn, migration)
+        fail("K2a a subject on two facts did not abort the migration")
+    except migration.Abort as exc:
+        if "'topic' on 2 facts" not in str(exc):
+            fail(f"K2a abort message does not name the split subject: {exc}")
+    conn.execute("DELETE FROM knowledge WHERE id = 'k-split'")
+    conn.execute("DELETE FROM fact WHERE id = 'f-split'")
+    if _snapshot(conn) != before:
+        fail("K2a the aborted run changed the database")
+
+
+def _k2b_to_f(conn) -> None:
+    rows = conn.execute("SELECT id, level, change_history FROM knowledge WHERE fact_id = 'f-dup'").fetchall()
+    if [(r[0], r[1]) for r in rows] != [("k-dup-high", "knows")]:
+        fail(f"K2b duplicate group left {rows!r}, expected only k-dup-high")
+    else:
+        history = json.loads(rows[0][2])
+        if [h.get("absorbed_knowledge_id") for h in history] != ["k-dup-low"] or history[0]["content"] != "low":
+            fail(f"K2b survivor change_history is {history!r}")
+    if conn.execute("SELECT knowledge_id FROM unresolved_mention").fetchone() != ("k-dup-high",):
+        fail("K2b unresolved_mention does not follow the survivor")
+    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'idx_knowledge_entity_fact'").fetchone():
+        fail("K2c idx_knowledge_entity_fact missing after the run")
+    content, history = conn.execute("SELECT content, change_history FROM fact WHERE id = 'f-npc'").fetchone()
+    if content != f"[[e:{B}|Bel]]" or json.loads(history)[-1].get("content") != f"npc:{B}":
+        fail(f"K2d npc fact is {content!r} with history {history!r}")
+    if conn.execute("SELECT entity_id FROM fact_participant WHERE fact_id = 'f-npc'").fetchall() != [(B,)]:
+        fail("K2d npc fact does not carry its entity as participant")
+    if "fact_id" not in [r[1] for r in conn.execute("PRAGMA table_info(discoverable_detail)")]:
+        fail("K2e discoverable_detail.fact_id missing after the run")
+    gates = dict(conn.execute("SELECT id, target_key FROM agenda_step_requirement").fetchall())
+    if gates != {"req-topic": "f-topic", "req-ghost": "ghost"}:
+        fail(f"K2f gates are {gates!r}")
+
+
+def rule_k2(db_path: pathlib.Path) -> None:
+    migration = _load_migration()
+    conn = _v2_08_database(db_path)
+    _k2a(conn, migration)
+    try:
+        _run(conn, migration)
+    except migration.Abort as exc:
+        fail(f"K2 the migration aborted on a clean fixture: {exc}")
+        return
+    _k2b_to_f(conn)
+    before = _snapshot(conn)
+    report = _run(conn, migration)
+    if report["absorbed"] or report["index_created"] or report["npc_facts"]["token"] \
+            or report["detail_column_added"] or report["gates_rekeyed"] or _snapshot(conn) != before:
+        fail(f"K2g the second run changed something: {report!r}")
+
+
+def census() -> dict[str, int]:
+    counts: dict[str, int] = {}
+    for path in sorted((SRC / "world_engine").rglob("*.py")):
+        n = 0
+        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
+            if isinstance(node, ast.Attribute) and node.attr == "subject":
+                n += 1
+            elif isinstance(node, ast.Constant) and node.value == "subject":
+                n += 1
+            elif isinstance(node, (ast.keyword, ast.arg)) and node.arg == "subject":
+                n += 1
+        if n:
+            counts[path.relative_to(ROOT).as_posix()] = n
+    return counts
+
+
+def rule_k3() -> None:
+    counts = census()
+    for path in sorted(set(counts) | set(_SUBJECT_CENSUS)):
+        if counts.get(path, 0) != _SUBJECT_CENSUS.get(path, 0):
+            fail(f"K3 {path}: {counts.get(path, 0)} subject reference(s), census pins "
+                 f"{_SUBJECT_CENSUS.get(path, 0)}")
+
+
+def main() -> int:
+    _engine, db_path = _fresh_engine()
+    from sqlmodel import SQLModel
+
+    import world_engine.models  # noqa: F401 -- registers every table
+
+    rule_k1(SQLModel.metadata.tables)
+    rule_k2(db_path)
+    rule_k3()
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: knowledge_identity -- knowledge is unique per (entity, fact); v2.09 migrates "
+          "and is idempotent; the subject census matches")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index a5e7aa9..039ef04 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -113,8 +113,6 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
     ("agenda_step_requirement", {"id": "agr-{w}", "world_id": "{w}", "step_id": "ags-{w}",
                                  "type": "knowledge", "target_key": "k"}),
     ("batch", {"id": "bat-{w}", "session_id": "ses-{w}"}),
-    ("discoverable_detail", {"id": "dd-{w}", "world_id": "{w}", "location_id": "{w}-loc",
-                             "subject": "s", "content": "c"}),
     ("door", {"id": "door-{w}", "world_id": "{w}", "location_id": "{w}-loc",
               "target_location_id": "{w}-loc", "x": 0.0, "y": 0.0}),
     ("event", {"id": "ev-{w}", "world_id": "{w}", "title": "t"}),
@@ -125,6 +123,8 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
                       "scope_type": "world", "level": "knows", "created_by": "creator_crud"}),
     ("fact_participant", {"id": "fp-{w}", "world_id": "{w}", "fact_id": "fa-{w}",
                           "entity_id": "{w}-char"}),
+    ("discoverable_detail", {"id": "dd-{w}", "world_id": "{w}", "location_id": "{w}-loc",
+                             "subject": "s", "content": "c", "fact_id": "fa-{w}"}),
     ("gathering", {"id": "ga-{w}", "world_id": "{w}", "session_id": "ses-{w}",
                    "location_id": "{w}-loc"}),
     ("gathering_member", {"id": "gm-{w}", "gathering_id": "ga-{w}", "entity_id": "{w}-char"}),
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 3133180..3a38ae1 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,16 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.09** — TICKET-0097, BRIEF-0097-A: knowledge identity by fact —
+  `idx_knowledge_entity_fact`, a UNIQUE index on `knowledge(entity_id,
+  fact_id)`, and `discoverable_detail.fact_id` (nullable FK to `fact`).
+  `migrate_v2_09_knowledge_identity.py` refuses a world whose `subject`
+  spreads over several facts (`creator_meta` excepted), absorbs duplicated
+  `(entity_id, fact_id)` rows into their highest-level twin (history
+  appended), gives every `npc:<id>` fact its entity as participant (and the
+  identity token as content for a uuid id), and rekeys `knowledge` day gates
+  from a subject to its fact id. `knowledge.subject` is untouched; v2.10
+  drops it.
 - **v2.08** — TICKET-0095, BRIEF-0095-A: the K1 review record —
   `day_mention_choice_candidate` and `day_mention_choice_evidence` (a
   choice's candidates and evidence as rows, backfilled from the JSON
diff --git a/world-engine-schema.md b/world-engine-schema.md
index 1455119..bd1b56f 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.08
+Current schema version: v2.09
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -700,7 +700,9 @@ What each entity knows — structured and injectable into prompts.
 `fact_id` (schema v1.98, TICKET-0082, BRIEF-0082-b) anchors each row to the
 fact it is knowledge OF; `subject` is unchanged and still the identity key
 for the ten call sites enumerated in BRIEF-0082-b (cutover deferred to a
-successor ticket).
+successor ticket). From v2.09 (TICKET-0097, BRIEF-0097-A) a row is unique
+per `(entity_id, fact_id)`: what an entity knows is identified by the fact
+it knows (`idx_knowledge_entity_fact`).
 
 ```sql
 CREATE TABLE knowledge (
@@ -1695,6 +1697,11 @@ CREATE TABLE discoverable_detail (
                       -- propose time. Ambient rows never flip this (they are
                       -- never "discovered" — their visibility is the cluster
                       -- predicate below).
+  fact_id             TEXT REFERENCES fact(id),
+                      -- v2.09 (TICKET-0097, BRIEF-0097-A): the fact an
+                      -- approved discovery of this detail attaches the
+                      -- player's knowledge to. NULL until the first approved
+                      -- discovery creates it (content = this row's content).
   signpost_group      TEXT,
                       -- NULL = no cluster. Clusters one `ambient` panel row
                       -- with N `hidden` content rows that carry the SAME
@@ -2392,6 +2399,9 @@ CREATE INDEX idx_knowledge_subject   ON knowledge(subject);
 -- "the fact this knowledge row is about" (schema v1.98, BRIEF-0082-b)
 CREATE INDEX idx_knowledge_fact      ON knowledge(fact_id);
 
+-- one row per (entity, fact) (schema v2.09, TICKET-0097, BRIEF-0097-A)
+CREATE UNIQUE INDEX idx_knowledge_entity_fact ON knowledge(entity_id, fact_id);
+
 -- fact spine lookups (schema v1.98, BRIEF-0082-b)
 CREATE INDEX idx_fact_world               ON fact(world_id);
 CREATE INDEX idx_fact_relation            ON fact(relation_id);
```

## Scope OUT

- Any change to a reader or writer of `knowledge.subject` (B–G).
- Running the migration on any DB Nia uses: she runs v2.09 and v2.10 together after G.
- A merge of split subjects (E2, rejected).
- `fact_refs.py` (B).
- Every later brief of the lot: BRIEF-0097-B, BRIEF-0097-C, BRIEF-0097-D, BRIEF-0097-E, BRIEF-0097-F, BRIEF-0097-G.

## Invariants to defend

**History is sacred on BOTH write paths:** the absorption appends every absorbed row's state to the survivor's `change_history` before deleting it — never a silent drop. **A `fact_participant` row is the aboutness claim:** v2.09 reads before it attaches (`idx_fact_participant_unique`).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `migrate_v2_09_knowledge_identity.py` run on a fresh `init_db` + `seed_pilot` test DB aborts (it must not: the seed now shares its facts).

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `knowledge_identity.py` K3 fails only on counts, with every reported file named in this brief's diff: re-run the census (see Done means) and report the table.
- `pipeline_state.py` is red on `main` because `TICKET-0097` is deposited with an arrow to `knowledge_identity.py`, which this brief creates: expected before this commit, green after it.

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
- On a temp DB (`WORLD_ENGINE_DATABASE_URL=sqlite:///<tmp>/x.db`, `PYTHONPATH=src`): `init_db.py`, `seed_pilot.py`, then `migrate_v2_09_knowledge_identity.py` twice: both runs print `S2 absorbed duplicate rows: 0 in 0 group(s)` and `Migration v2.09 applied.` (a fresh DB is created with the index and the column; K2 exercises the migration on a v2.08-shaped DB).
- Mutation test: replace `absorb_duplicates(cursor)` by `[]` in `migrate()`; `knowledge_identity.py` no longer passes (the index creation raises); revert.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → `PASS: corpus_gate — 126 check(s) discovered, 126 executed, 126 passed`.
- `/review-step` then `/close-step` ran on the commit.

Census re-run (for the K3 ADAPT above): the census function is `census()` in
`knowledge_identity.py`; print it with
`WORLD_ENGINE_ENV=test python -c "import sys; sys.path.insert(0,'tooling/verify/checks'); import knowledge_identity as k; print(k.census())"`.

## Docs to update

This brief carries its docs: schema doc v2.09, changelog v2.09, decision entry `KNOWLEDGE IDENTITY (TICKET-0097) … (BRIEF-0097-a, schema v2.09)`.
