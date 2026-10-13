<!-- slug: review-storage -->
# BRIEF 0115-A — "v2.27, the creator's review stored round by round -- original_payload, mutation_review, mutation_review_change (schema v2.27)"

Lot: LOT-0115-creator-dashboard.md (authoritative on conflict)
Depends on: none (first of the lot)

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `src/world_engine/models/pipeline.py` -> `class ProposedMutation(SQLModel, table=True):` with `payload: Any = Field(sa_column=Column(JSON, nullable=False))` and no `original_payload`
- `src/world_engine/schema_version.py` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.26"`; `world-engine-schema.md` -> `Current schema version: v2.26`
- `src/world_engine/writes/worlds.py` -> `_DIRECT_WORLD_SCOPED_DELETES` ending `    "event_type_effect",` then `)`
- `tooling/verify/checks/world_cascade.py` -> the fixture's `("observation_mutation_link", {"id": "oml-{w}", "run_id": "or-{w}",`
- `tooling/verify/checks/json_ui_boundary.py` -> `    "ProposedMutation.payload",` in `JSON_COLUMN_ALLOWLIST`
- `scripts/migrate_v2_26_event_effects.py` exists; no `scripts/migrate_v2_27_*.py`, no `mutation_review` table, no `tooling/verify/checks/mutation_reviews.py`.

## Facts carried

### R-01 — approving overwrites the producer's payload [M]
Opened: `src/world_engine/cockpit/routes/mutations.py` (`_approve_apply_edited_payload` :539 replaces `mut.payload` with the body's; `approve_mutation` :631 calls it first); `frontend/src/creation/QueueCard.svelte:171` (the card always sends the payload).
Consequence: v2.27 keeps the producer's payload (`original_payload`) and what changed, value by value.

### R-07 — the lists this lot extends [M]
Opened: `src/world_engine/writes/worlds.py:83`, `tooling/verify/checks/world_cascade.py:201`, `src/world_engine/schema_version.py:15`, `world-engine-schema.md:3` and `:1603`, `scripts/migrate_v2_26_event_effects.py` (the shape this migration copies: refuse below the previous version, one raw transaction, post-checks, `schema_meta` last).

## Contracts

### C-01 — v2.27
Produced by: BRIEF-0115-A   Consumed by: B, D
`proposed_mutation.original_payload` (JSON, nullable). `mutation_review` (`world_id`, `mutation_id`, `round` >= 1 unique per mutation, `action` in `REVIEW_ACTIONS = ("approve", "reject")`, `via` in `REVIEW_VIAS = ("unit", "batch")`, `status_after` in `REVIEW_STATUSES = ("applied", "approved", "rejected")` -- `rejected` exactly when `reject` --, `edited` only on a unit approve, `step_verdict` NULL or in `STEP_VERDICTS = ("met", "unmet", "unknown", "none", "not_judged")`, `reviewed_at`). `mutation_review_change` (`world_id`, `review_id`, `path` unique per review, `field`, `kind` in `REVIEW_CHANGE_KINDS = ("added", "removed", "changed")`, `before_value` NULL when added, `after_value` NULL when removed). Both cascade with their world.

## Context

A3 and C1 of the dashboard: « accepted as proposed » and « accepted after a correction » must be told apart (D2, A1 of 0119), and a step change keeps what its condition said (M2). This brief stores it; B writes it.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `models/pipeline.py`: `original_payload`; `MutationReview`, `MutationReviewChange` and their five tuples; `models/__init__.py` exports them;
   - `migrate_v2_27_mutation_reviews.py` (new); `schema_version.py`, the schema doc and changelog at v2.27;
   - the world cascade and its fixture name both tables; the JSON allowlist names `ProposedMutation.original_payload`;
   - creates check `mutation_reviews.py` (MR1-MR3); appends the decision entry above the footer.
   The files it touches, exactly:
   - scripts/migrate_v2_27_mutation_reviews.py
   - src/world_engine/models/__init__.py
   - src/world_engine/models/pipeline.py
   - src/world_engine/schema_version.py
   - src/world_engine/writes/worlds.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/json_ui_boundary.py
   - tooling/verify/checks/mutation_reviews.py
   - tooling/verify/checks/world_cascade.py
   - world-engine-schema-changelog.md
   - world-engine-schema.md

````diff
diff --git a/scripts/migrate_v2_27_mutation_reviews.py b/scripts/migrate_v2_27_mutation_reviews.py
new file mode 100644
index 0000000..06262cf
--- /dev/null
+++ b/scripts/migrate_v2_27_mutation_reviews.py
@@ -0,0 +1,191 @@
+"""Migration v2.27 — the creator's review of a proposal, round by round
+(TICKET-0115, BRIEF-0115-A; decisions A3, C1 and H1a of the conditions
+series' dashboard).
+
+Schema, additive only; no data is written:
+
+- adds `proposed_mutation.original_payload` (JSON, nullable): the payload
+  as its producer wrote it, kept the first time the creator approves an
+  edited one;
+- creates `mutation_review` (one row per review call: round, approve or
+  reject, unit or batch, the status it left, edited or not, a step's
+  verdict) and `mutation_review_change` (one row per value changed in a
+  round: path, field, kind, a scalar's before and after), with their
+  indexes, exactly as the models declare them.
+
+A proposal reviewed before v2.27 has no `mutation_review` row: the
+dashboard counts only the reviews this schema records.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.26. Idempotent: each step checks what is already there. One raw
+transaction (`foreign_keys` set before it).
+
+Post-check, before `schema_meta` moves: `proposed_mutation` kept its row
+count; the column and both tables are in place; `PRAGMA foreign_key_check`
+on the tables this migration writes is empty (a dangling row elsewhere is a
+note, never a failure -- AMENDMENT-0107-01). `schema_meta` then moves to
+v2.27.
+
+Run from the project root:
+
+    python scripts/migrate_v2_27_mutation_reviews.py
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
+        "migrate_v2_27_mutation_reviews.py refuses to run without WORLD_ENGINE_ENV "
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
+_PREVIOUS_VERSION = "v2.26"
+_THIS_VERSION = "v2.27"
+# The tables this migration writes: the only ones its foreign-key post-check judges.
+_TOUCHED_TABLES = ("proposed_mutation", "mutation_review", "mutation_review_change")
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
+            f"Migration v2.27 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _columns(table: str) -> set[str]:
+    return {column["name"] for column in inspect(engine).get_columns(table)}
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
+def _plan() -> dict:
+    existing = set(inspect(engine).get_table_names())
+    return {
+        "original_payload": "original_payload" not in _columns("proposed_mutation"),
+        "review": "mutation_review" not in existing,
+        "change": "mutation_review_change" not in existing,
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
+        cursor.execute("BEGIN")
+        if plan["original_payload"]:
+            cursor.execute("ALTER TABLE proposed_mutation ADD COLUMN original_payload JSON")
+            applied.append("proposed_mutation.original_payload added")
+        if plan["review"]:
+            _create_from_model(cursor, models.MutationReview)
+            applied.append("mutation_review created")
+        if plan["change"]:
+            _create_from_model(cursor, models.MutationReviewChange)
+            applied.append("mutation_review_change created")
+        cursor.execute("COMMIT")
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
+    existing = set(inspect(engine).get_table_names())
+    problems = []
+    if after != before:
+        problems.append(f"row counts changed {before} -> {after}")
+    if "original_payload" not in _columns("proposed_mutation"):
+        problems.append("proposed_mutation.original_payload is missing")
+    for table in ("mutation_review", "mutation_review_change"):
+        if table not in existing:
+            problems.append(f"{table} was not created")
+    if dangling:
+        problems.append(f"foreign_key_check {dangling}")
+    if problems:
+        raise SystemExit("Migration v2.27 aborted, post-check failed: " + "; ".join(problems) + ".")
+    for table, rowid, parent, _fk in elsewhere:
+        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
+    print(f"Post-check: proposed_mutation.original_payload, mutation_review and mutation_review_change "
+          f"in place; counts kept {after}.")
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
+    print("Migration v2.27 — the creator's review of a proposal, round by round")
+    _refuse()
+    with engine.connect() as conn:
+        before = {"proposed_mutation": _count(conn, "proposed_mutation")}
+    applied = _apply(_plan())
+    print("Applied: " + ", ".join(applied) + "." if applied else "Migration v2.27 already fully applied.")
+    _post_checks(before)
+    _converge_schema_meta()
+    print("\nMigration v2.27 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index 3f4a8ce..7925390 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -160,8 +160,15 @@ from .pipeline import (
     LoreUsageEvent,
     ConditionDraft,
     CONDITION_DRAFT_OUTCOMES,
+    MutationReview,
+    MutationReviewChange,
     PassPlay,
     ProposedMutation,
+    REVIEW_ACTIONS,
+    REVIEW_CHANGE_KINDS,
+    REVIEW_STATUSES,
+    REVIEW_VIAS,
+    STEP_VERDICTS,
     PromptTemplate,
     PromptVariable,
     PromptVersion,
@@ -257,6 +264,13 @@ __all__ = [
     "Conversation",
     "ConversationMessage",
     "ProposedMutation",
+    "MutationReview",
+    "MutationReviewChange",
+    "REVIEW_ACTIONS",
+    "REVIEW_CHANGE_KINDS",
+    "REVIEW_STATUSES",
+    "REVIEW_VIAS",
+    "STEP_VERDICTS",
     "Event",
     "Artifact",
     "Item",
diff --git a/src/world_engine/models/pipeline.py b/src/world_engine/models/pipeline.py
index e791442..e1e6dc2 100644
--- a/src/world_engine/models/pipeline.py
+++ b/src/world_engine/models/pipeline.py
@@ -127,6 +127,12 @@ class ProposedMutation(SQLModel, table=True):
     target_table: Optional[str] = None
     target_id: Optional[str] = None
     payload: Any = Field(sa_column=Column(JSON, nullable=False))
+    # TICKET-0115 (BRIEF-0115-A, A3): the payload as its producer wrote it,
+    # kept the first time the creator approves an edited one -- NULL while
+    # nobody edited it. Written once by `writes/mutation_reviews.py`, never
+    # rendered in any UI surface (an audit snapshot, `change_history`'s
+    # posture); what changed is `mutation_review_change`'s rows.
+    original_payload: Any = Field(default=None, sa_column=Column(JSON, nullable=True))
 
     # control
     status: str = Field(
@@ -144,6 +150,82 @@ class ProposedMutation(SQLModel, table=True):
     applied_at: Optional[datetime] = None
 
 
+# -----------------------------------------------------------------------------
+# mutation_review / mutation_review_change  (the creator's review of a
+# proposal, round by round -- schema v2.27, TICKET-0115, BRIEF-0115-A;
+# decisions A3, C1 and H1a of the conditions series' dashboard)
+#
+# `mutation_review` -- one row per review call that moved a proposal: its
+# round (1, 2, ... per proposal: a « Needs attention » proposal approved
+# again is a second round), approve or reject, unit or batch, the status it
+# left, whether the creator edited the payload, and -- for an
+# `agenda_step_change` -- the verdict the step's own condition gave at that
+# moment (`completion` for `complete`, `failure` for `fail`; `none` when the
+# step has no such condition, `not_judged` when it cannot be judged).
+# `mutation_review_change` -- one row per value the creator changed in that
+# round: its path (`participants[Cible].entity_id`), its field (the path
+# without keys, `participants[].entity_id`), added / removed / changed, and
+# a scalar's before and after as JSON text (NULL for a whole element).
+# Both append-only, written only by `writes/mutation_reviews.py`. World
+# tables: deleted with their world by the cascade, like their proposal.
+# Non-canon.
+# -----------------------------------------------------------------------------
+REVIEW_ACTIONS: tuple[str, ...] = ("approve", "reject")
+REVIEW_VIAS: tuple[str, ...] = ("unit", "batch")
+REVIEW_STATUSES: tuple[str, ...] = ("applied", "approved", "rejected")
+STEP_VERDICTS: tuple[str, ...] = ("met", "unmet", "unknown", "none", "not_judged")
+REVIEW_CHANGE_KINDS: tuple[str, ...] = ("added", "removed", "changed")
+
+
+class MutationReview(SQLModel, table=True):
+    __tablename__ = "mutation_review"
+    __table_args__ = (
+        Index("idx_mutation_review_round", "mutation_id", "round", unique=True),
+        Index("idx_mutation_review_world", "world_id", "reviewed_at"),
+        CheckConstraint("round >= 1", name="ck_mutation_review_round"),
+        CheckConstraint("action IN ('approve','reject')", name="ck_mutation_review_action"),
+        CheckConstraint("via IN ('unit','batch')", name="ck_mutation_review_via"),
+        CheckConstraint("status_after IN ('applied','approved','rejected')", name="ck_mutation_review_status"),
+        CheckConstraint("(action = 'reject') = (status_after = 'rejected')", name="ck_mutation_review_outcome"),
+        CheckConstraint("edited = 0 OR (action = 'approve' AND via = 'unit')", name="ck_mutation_review_edited"),
+        CheckConstraint(
+            "step_verdict IS NULL OR step_verdict IN ('met','unmet','unknown','none','not_judged')",
+            name="ck_mutation_review_verdict",
+        ),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    mutation_id: str = Field(foreign_key="proposed_mutation.id", nullable=False)
+    round: int
+    action: str
+    via: str
+    status_after: str
+    edited: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
+    step_verdict: Optional[str] = None
+    reviewed_at: datetime = _created_ts()
+
+
+class MutationReviewChange(SQLModel, table=True):
+    __tablename__ = "mutation_review_change"
+    __table_args__ = (
+        Index("idx_mutation_review_change_path", "review_id", "path", unique=True),
+        Index("idx_mutation_review_change_field", "world_id", "field"),
+        CheckConstraint("kind IN ('added','removed','changed')", name="ck_mutation_review_change_kind"),
+        CheckConstraint("kind <> 'added' OR before_value IS NULL", name="ck_mutation_review_change_added"),
+        CheckConstraint("kind <> 'removed' OR after_value IS NULL", name="ck_mutation_review_change_removed"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    review_id: str = Field(foreign_key="mutation_review.id", nullable=False)
+    path: str
+    field: str
+    kind: str
+    before_value: Optional[str] = None
+    after_value: Optional[str] = None
+
+
 # -----------------------------------------------------------------------------
 # day_rewrite / day_mention_resolution  (the declaration rewrite and its
 # trace, schema vX.YY, TICKET-0081, BRIEF-0081-b — decisions A2'/B2/J2)
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index 22d8d07..99effc9 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.26"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.27"
diff --git a/src/world_engine/writes/worlds.py b/src/world_engine/writes/worlds.py
index 195528d..250b20c 100644
--- a/src/world_engine/writes/worlds.py
+++ b/src/world_engine/writes/worlds.py
@@ -80,7 +80,7 @@ _DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
     "attribute_value", "attribute_change",
     "event_type", "event_type_role", "event_type_role_type", "event_type_scope",
     "event_sorte", "event_participant", "condition_node_filter",
-    "event_type_effect",
+    "event_type_effect", "mutation_review", "mutation_review_change",
 )
 
 # Refusing tables (root_table, label_column, guarded_children, message) —
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 85c016b..9f9a809 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19666,6 +19666,36 @@ the world's entities and writes it straight to the journal (`POST
 `apply_ticket_0119_lore_prompt.py` fragment by fragment: the creator's
 edits are kept.
 
+
+## THE CREATOR'S REVIEW IS RECORDED ROUND BY ROUND (TICKET-0115) -- WHAT SHE CHANGED, AND WHAT A STEP'S CONDITION SAID (BRIEF-0115-a, schema v2.27)
+
+**A3, C1 of the dashboard.** Approving a proposal overwrote its payload with
+what the card sent (`_approve_apply_edited_payload`): what the model had
+proposed was lost, so « accepted as proposed » and « accepted after a
+correction » could not be told apart -- the measure D2 (auto-applying
+events) and A1 of 0119 (the tick retyped) wait on. v2.27 keeps the review
+itself: `proposed_mutation.original_payload` (the producer's payload, kept
+the first time an edited one is approved), `mutation_review` (one row per
+review call -- its round, approve or reject, unit or batch, the status it
+left, edited or not, and an `agenda_step_change`'s verdict before the
+apply, for M2) and `mutation_review_change` (one row per value changed:
+path, field, kind, a scalar's before and after).
+
+**Rounds, not one review.** A « Needs attention » proposal can be approved
+again, or rejected: each call is a round, append-only, so nothing a later
+call does rewrites an earlier one.
+
+**World tables.** A review dies with its world, like its proposal: the
+export (BRIEF-0115-D) is how an analysis keeps them. `original_payload` is
+an audit snapshot, never rendered (the `change_history` posture of
+`json_ui_boundary.py`); a change's values are a scalar's JSON text, in
+relational rows.
+
+**Rejected.** A2 (accepted = applied, edited or not): D2 and A1 of 0119
+could never be measured. One review per proposal, rewritten on a second
+call: history is sacred. A JSON diff column: the dashboard reads what
+changed, and UI-visible data is relational (INV-20).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/json_ui_boundary.py b/tooling/verify/checks/json_ui_boundary.py
index de4d8da..0902a2b 100644
--- a/tooling/verify/checks/json_ui_boundary.py
+++ b/tooling/verify/checks/json_ui_boundary.py
@@ -45,6 +45,11 @@ JSON_COLUMN_ALLOWLIST = {
     # review queue; shape is the mutation type's contract, not a UI
     # field. First structured UI consumer must relationalize.
     "ProposedMutation.payload",
+    # TICKET-0115 (BRIEF-0115-A, A3): the payload as its producer wrote it,
+    # kept beside `payload` once the creator approved an edited one -- an
+    # audit snapshot, never rendered in any UI surface (the change_history
+    # posture below); what changed is `mutation_review_change`'s rows.
+    "ProposedMutation.original_payload",
     # Append-only audit snapshots — never rendered in any UI surface.
     "Relation.change_history",
     "Knowledge.change_history",
diff --git a/tooling/verify/checks/mutation_reviews.py b/tooling/verify/checks/mutation_reviews.py
new file mode 100644
index 0000000..34ff25c
--- /dev/null
+++ b/tooling/verify/checks/mutation_reviews.py
@@ -0,0 +1,289 @@
+"""G1 check for TICKET-0115 -- the creator's review of a proposal is recorded, round by round.
+
+BRIEF-0115-A's rules (A3 and C1 of the conditions series' dashboard): the
+storage of v2.27.
+
+MR1 -- storage (import). `mutation_review` and `mutation_review_change`
+   carry exactly their contract's columns, CHECK names and index names, none
+   of them JSON; `proposed_mutation` has `original_payload`, JSON and
+   nullable; `REVIEW_ACTIONS`, `REVIEW_VIAS`, `REVIEW_STATUSES`,
+   `STEP_VERDICTS` and `REVIEW_CHANGE_KINDS` are the values their CHECKs
+   name; the code's schema version is v2.27 or later.
+MR2 -- constraints (fixture). A review round 0, an action, via, status or
+   verdict outside its tuple, a reject left `applied`, an approve left
+   `rejected`, an edited reject or an edited batch review, a second review
+   of one proposal with the same round, a change kind outside its tuple, an
+   `added` change with a before value, a `removed` change with an after
+   value, and one path twice in one review are each refused by the
+   database; a well-formed review and change are accepted.
+MR3 -- migration `scripts/migrate_v2_27_mutation_reviews.py`, on a v2.26
+   database (`proposed_mutation` in its v2.26 DDL, frozen below, one row;
+   no review table): at v2.25 it refuses and changes nothing; at v2.26 it
+   adds the column, creates both tables, keeps the row, and sets
+   `schema_meta` to v2.27; a second run writes nothing.
+
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
+MIGRATION = ROOT / "scripts" / "migrate_v2_27_mutation_reviews.py"
+
+FAILURES: list[str] = []
+
+REVIEW_COLUMNS = ("id", "world_id", "mutation_id", "round", "action", "via", "status_after", "edited",
+                  "step_verdict", "reviewed_at")
+REVIEW_CHECKS = ("ck_mutation_review_action", "ck_mutation_review_edited", "ck_mutation_review_outcome",
+                 "ck_mutation_review_round", "ck_mutation_review_status", "ck_mutation_review_verdict",
+                 "ck_mutation_review_via")
+REVIEW_INDEXES = ("idx_mutation_review_round", "idx_mutation_review_world")
+CHANGE_COLUMNS = ("id", "world_id", "review_id", "path", "field", "kind", "before_value", "after_value")
+CHANGE_CHECKS = ("ck_mutation_review_change_added", "ck_mutation_review_change_kind",
+                 "ck_mutation_review_change_removed")
+CHANGE_INDEXES = ("idx_mutation_review_change_field", "idx_mutation_review_change_path")
+
+# `proposed_mutation` as v2.26 declared it (frozen: MR3 builds the database
+# the migration was written for).
+V2_26_DDL: tuple[str, ...] = (
+    "CREATE TABLE schema_meta (id INTEGER NOT NULL, static_version VARCHAR NOT NULL, "
+    "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (id), "
+    "CONSTRAINT ck_schema_meta_singleton CHECK (id = 1))",
+    "CREATE TABLE world (id VARCHAR NOT NULL, name VARCHAR NOT NULL, PRIMARY KEY (id))",
+    "CREATE TABLE proposed_mutation (id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, "
+    "source_type VARCHAR NOT NULL, pass_play_id VARCHAR, conversation_id VARCHAR, tick_id VARCHAR, "
+    "mutation_type VARCHAR NOT NULL, target_table VARCHAR, target_id VARCHAR, payload JSON NOT NULL, "
+    "status VARCHAR DEFAULT 'proposed' NOT NULL, rationale VARCHAR, creator_notes VARCHAR, "
+    "proposed_by VARCHAR DEFAULT 'local_ai' NOT NULL, "
+    "proposed_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, reviewed_at DATETIME, applied_at DATETIME, "
+    "PRIMARY KEY (id), FOREIGN KEY(world_id) REFERENCES world (id), "
+    "FOREIGN KEY(pass_play_id) REFERENCES pass_play (id), "
+    "FOREIGN KEY(conversation_id) REFERENCES conversation (id))",
+    "CREATE INDEX idx_mutation_status ON proposed_mutation (status)",
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
+# --- MR1 -------------------------------------------------------------------------
+
+def _shape(table, columns, checks, indexes, label: str) -> None:
+    from sqlalchemy import JSON, CheckConstraint
+
+    if table is None:
+        fail(f"MR1: {label} is not declared")
+        return
+    if tuple(table.c.keys()) != columns:
+        fail(f"MR1: {label} columns are {tuple(table.c.keys())}")
+    found = tuple(sorted(c.name for c in table.constraints if isinstance(c, CheckConstraint)))
+    if found != checks:
+        fail(f"MR1: {label} CHECKs are {found}")
+    if tuple(sorted(i.name for i in table.indexes)) != indexes:
+        fail(f"MR1: {label} indexes are {sorted(i.name for i in table.indexes)}")
+    if any(isinstance(c.type, JSON) for c in table.c):
+        fail(f"MR1: {label} holds a JSON column")
+
+
+def _check_values(table, name: str) -> str:
+    from sqlalchemy import CheckConstraint
+
+    return next((str(c.sqltext) for c in table.constraints
+                 if isinstance(c, CheckConstraint) and c.name == name), "")
+
+
+def check_mr1() -> None:
+    from sqlalchemy import JSON
+    from sqlmodel import SQLModel
+
+    from world_engine import models
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+
+    tables = SQLModel.metadata.tables
+    review, change = tables.get("mutation_review"), tables.get("mutation_review_change")
+    _shape(review, REVIEW_COLUMNS, REVIEW_CHECKS, REVIEW_INDEXES, "mutation_review")
+    _shape(change, CHANGE_COLUMNS, CHANGE_CHECKS, CHANGE_INDEXES, "mutation_review_change")
+    column = tables["proposed_mutation"].c.get("original_payload")
+    if column is None or not isinstance(column.type, JSON) or not column.nullable:
+        fail("MR1: proposed_mutation.original_payload is not a nullable JSON column")
+    if review is None or change is None:
+        return
+    pairs = (
+        (models.REVIEW_ACTIONS, _check_values(review, "ck_mutation_review_action")),
+        (models.REVIEW_VIAS, _check_values(review, "ck_mutation_review_via")),
+        (models.REVIEW_STATUSES, _check_values(review, "ck_mutation_review_status")),
+        (models.STEP_VERDICTS, _check_values(review, "ck_mutation_review_verdict")),
+        (models.REVIEW_CHANGE_KINDS, _check_values(change, "ck_mutation_review_change_kind")),
+    )
+    for values, sql in pairs:
+        if not values or any(f"'{v}'" not in sql for v in values) or sql.count("'") != 2 * len(values):
+            fail(f"MR1: the tuple {values} is not its CHECK's values ({sql})")
+    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < (2, 27):
+        fail(f"MR1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")
+
+
+# --- MR2 -------------------------------------------------------------------------
+
+def _refused(engine, sql: str) -> bool:
+    from sqlalchemy import text
+    from sqlalchemy.exc import IntegrityError
+
+    with engine.connect() as conn:
+        try:
+            conn.execute(text(sql))
+            conn.rollback()
+            return False
+        except IntegrityError:
+            conn.rollback()
+            return True
+
+
+def check_mr2(engine) -> None:
+    from sqlalchemy import text
+
+    with engine.begin() as conn:
+        conn.execute(text("INSERT INTO world (id, name, created_at) VALUES ('w', 'Monde', '2026-10-12')"))
+        conn.execute(text("INSERT INTO proposed_mutation (id, world_id, source_type, mutation_type, payload) "
+                          "VALUES ('pm', 'w', 'conversation', 'event_creation', '{}')"))
+        conn.execute(text("INSERT INTO mutation_review (id, world_id, mutation_id, round, action, via, "
+                          "status_after, edited) VALUES ('r1', 'w', 'pm', 1, 'approve', 'unit', 'applied', 1)"))
+        conn.execute(text("INSERT INTO mutation_review_change (id, world_id, review_id, path, field, kind, "
+                          "before_value, after_value) VALUES ('c1', 'w', 'r1', 'title', 'title', 'changed', "
+                          "'\"a\"', '\"b\"')"))
+
+    def review(rid: str, round_: str = "2", action: str = "approve", via: str = "unit", status: str = "applied",
+               edited: str = "0", verdict: str = "NULL") -> str:
+        return ("INSERT INTO mutation_review (id, world_id, mutation_id, round, action, via, status_after, edited, "
+                f"step_verdict) VALUES ('{rid}', 'w', 'pm', {round_}, '{action}', '{via}', '{status}', {edited}, "
+                f"{verdict})")
+
+    def change(cid: str, path: str = "x", kind: str = "changed", before: str = "NULL", after: str = "NULL") -> str:
+        return ("INSERT INTO mutation_review_change (id, world_id, review_id, path, field, kind, before_value, "
+                f"after_value) VALUES ('{cid}', 'w', 'r1', '{path}', '{path}', '{kind}', {before}, {after})")
+
+    refused = {
+        "round 0": review("a", round_="0"),
+        "an unknown action": review("b", action="defer"),
+        "an unknown via": review("c", via="script"),
+        "an unknown status": review("d", status="proposed", action="approve"),
+        "an unknown verdict": review("e", verdict="'true'"),
+        "a reject left applied": review("f", action="reject", status="applied"),
+        "an approve left rejected": review("g", status="rejected"),
+        "an edited reject": review("h", action="reject", status="rejected", edited="1"),
+        "an edited batch review": review("i", via="batch", edited="1"),
+        "a second round 1": review("j", round_="1"),
+        "an unknown change kind": change("k", kind="moved"),
+        "an added change with a before value": change("l", kind="added", before="'1'"),
+        "a removed change with an after value": change("m", kind="removed", after="'1'"),
+        "one path twice in one review": change("n", path="title"),
+    }
+    for label, sql in refused.items():
+        if not _refused(engine, sql):
+            fail(f"MR2: {label} was accepted")
+    accepted = (review("ok", verdict="'not_judged'"), change("ok2", path="participants[Cible].entity_id",
+                                                            kind="added", after="'\"e\"'"))
+    for sql in accepted:
+        if _refused(engine, sql):
+            fail(f"MR2: a well-formed row was refused: {sql}")
+
+
+# --- MR3 -------------------------------------------------------------------------
+
+def _v2_26_db() -> str:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "v2_26.db")
+    with sqlite3.connect(db_path) as conn:
+        for statement in V2_26_DDL:
+            conn.execute(statement)
+        conn.executescript("""
+            INSERT INTO schema_meta (id, static_version) VALUES (1, 'v2.25');
+            INSERT INTO world (id, name) VALUES ('w', 'Monde');
+            INSERT INTO proposed_mutation (id, world_id, source_type, mutation_type, payload)
+              VALUES ('pm', 'w', 'conversation', 'event_creation', '{"title": "t"}');
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
+            "column": "original_payload" in [r[1] for r in conn.execute("PRAGMA table_info(proposed_mutation)")],
+            "review": bool(sql("mutation_review")) and bool(sql("idx_mutation_review_round")),
+            "change": bool(sql("mutation_review_change")) and bool(sql("idx_mutation_review_change_path")),
+            "rows": conn.execute("SELECT id, payload FROM proposed_mutation").fetchall(),
+        }
+
+
+def check_mr3() -> None:
+    if not MIGRATION.exists():
+        fail(f"MR3: {MIGRATION.name} not found")
+        return
+    db_path = _v2_26_db()
+    before = _snapshot(db_path)
+    refused = _run_migration(db_path)
+    if refused.returncode == 0 or _snapshot(db_path) != before:
+        fail(f"MR3: v2.25 was not refused untouched (exit {refused.returncode})")
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.26' WHERE id = 1")
+    result = _run_migration(db_path)
+    after = _snapshot(db_path)
+    want = {"version": "v2.27", "column": True, "review": True, "change": True,
+            "rows": [("pm", '{"title": "t"}')]}
+    if result.returncode != 0 or after != want:
+        fail(f"MR3: exit {result.returncode}, state {after}: {result.stderr.strip()[-300:]}")
+    again = _run_migration(db_path)
+    if again.returncode != 0 or "already fully applied" not in again.stdout or _snapshot(db_path) != after:
+        fail(f"MR3: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
+
+
+def main() -> None:
+    _fresh_db()
+    from sqlmodel import SQLModel
+
+    from world_engine import models  # noqa: F401 -- registers every table
+    from world_engine.db import engine
+
+    SQLModel.metadata.create_all(engine)
+    check_mr1()
+    check_mr2(engine)
+    check_mr3()
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        sys.exit(1)
+    print("PASS: mutation_reviews -- v2.27 stores a review round by round and its changes; the migration "
+          "refuses below v2.26 and runs once")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index bf09242..6270e66 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -200,6 +200,10 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
                            "mutation_type": "fixture", "payload": "{{}}"}),
     ("observation_mutation_link", {"id": "oml-{w}", "run_id": "or-{w}",
                                    "mutation_id": "pm-{w}"}),
+    ("mutation_review", {"id": "mr-{w}", "world_id": "{w}", "mutation_id": "pm-{w}", "round": 1,
+                         "action": "approve", "via": "unit", "status_after": "applied"}),
+    ("mutation_review_change", {"id": "mrc-{w}", "world_id": "{w}", "review_id": "mr-{w}",
+                                "path": "title", "field": "title", "kind": "changed"}),
     ("skill", {"id": "sk-{w}", "character_id": "{w}-char", "domain": "agility",
                "skill_definition_id": "sd-{w}"}),
     ("skill_resolution", {"id": "sr-{w}", "world_id": "{w}", "conversation_id": "co-{w}",
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index e71497f..459c453 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,15 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.27** — TICKET-0115, BRIEF-0115-A: the creator's review of a
+  proposal, round by round. `proposed_mutation` gains `original_payload`
+  (JSON, nullable: the payload as its producer wrote it, kept the first time
+  the creator approves an edited one). `mutation_review` (one row per review
+  call: round, approve or reject, unit or batch, the status it left, edited
+  or not, an `agenda_step_change`'s verdict) and `mutation_review_change`
+  (one row per value changed in a round: path, field, kind, a scalar's
+  before and after). `migrate_v2_27_mutation_reviews.py` writes no data; a
+  proposal reviewed before v2.27 has no review row.
 - **v2.26** — TICKET-0119, BRIEF-0119-A: what an event does to the state of
   the world. `event_type_effect` (an event type's effects: the role whose
   entity changes, the state -- a world's definition, or `État vital` /
diff --git a/world-engine-schema.md b/world-engine-schema.md
index b496a05..5294e78 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.26
+Current schema version: v2.27
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -1513,6 +1513,9 @@ CREATE TABLE proposed_mutation (
   target_table    TEXT,                    -- table the change applies to
   target_id       TEXT,                    -- row affected (NULL if creation)
   payload         JSON NOT NULL,           -- the proposed change, structured
+  original_payload JSON,                   -- v2.27: the payload as its producer wrote it,
+                                           -- kept the first time the creator approves an
+                                           -- edited one; NULL while nobody edited it
 
   -- control
   status          TEXT DEFAULT 'proposed',
@@ -1598,6 +1601,71 @@ faction scopes, `ENTITY_CREATION_QUOTA = 1`, own budget) and, dormantly, by
 conversation analysis (a shapeless payload tolerated at the pending-list
 read side rather than normalized).
 
+`original_payload` (v2.27, TICKET-0115) is written once, by
+`writes/mutation_reviews.py`, the first time the creator approves a payload
+she edited: the proposal as its producer wrote it, beside `payload`, the
+proposal as she approved it. Never rendered in any UI surface (an audit
+snapshot, `change_history`'s posture in `json_ui_boundary.py`).
+
+-----
+
+### `mutation_review` / `mutation_review_change`
+
+The creator's review of a proposal, round by round (v2.27, TICKET-0115,
+BRIEF-0115-A). Written only by `writes/mutation_reviews.py`, from the four
+review paths of `cockpit/routes/mutations.py` (approve, reject, and both in
+batch); append-only. World tables: the cascade deletes them with their
+world, like the proposal they review. Non-canon.
+
+```sql
+CREATE TABLE mutation_review (
+  id            TEXT PRIMARY KEY,
+  world_id      TEXT NOT NULL REFERENCES world(id),
+  mutation_id   TEXT NOT NULL REFERENCES proposed_mutation(id),
+  round         INTEGER NOT NULL,   -- 1, 2, ... per proposal (CHECK >= 1): a
+                                    -- « Needs attention » proposal approved again
+                                    -- is its second round
+  action        TEXT NOT NULL,      -- approve | reject
+  via           TEXT NOT NULL,      -- unit | batch
+  status_after  TEXT NOT NULL,      -- applied | approved | rejected
+                                    -- (CHECK: rejected exactly when action = reject)
+  edited        BOOLEAN NOT NULL DEFAULT 0,  -- the creator changed the payload
+                                    -- (CHECK: only an approve, only unit)
+  step_verdict  TEXT,               -- an agenda_step_change only: met | unmet |
+                                    -- unknown (the step's completion for complete,
+                                    -- its failure for fail, judged before the
+                                    -- apply) | none (no such condition) |
+                                    -- not_judged (no step, no character owner,
+                                    -- no action); NULL for every other type
+  reviewed_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
+);
+CREATE UNIQUE INDEX idx_mutation_review_round ON mutation_review(mutation_id, round);
+CREATE INDEX idx_mutation_review_world ON mutation_review(world_id, reviewed_at);
+
+CREATE TABLE mutation_review_change (
+  id            TEXT PRIMARY KEY,
+  world_id      TEXT NOT NULL REFERENCES world(id),
+  review_id     TEXT NOT NULL REFERENCES mutation_review(id),
+  path          TEXT NOT NULL,      -- participants[Cible].entity_id, title, steps[2]
+  field         TEXT NOT NULL,      -- the path without its keys: participants[].entity_id
+  kind          TEXT NOT NULL,      -- added | removed | changed
+  before_value  TEXT,               -- a scalar as JSON text; NULL when added, or
+  after_value   TEXT                -- when the value is a whole element
+);
+CREATE UNIQUE INDEX idx_mutation_review_change_path ON mutation_review_change(review_id, path);
+CREATE INDEX idx_mutation_review_change_field ON mutation_review_change(world_id, field);
+```
+
+What changed is computed by `review_diff.py` between the payload stored
+before the call and the one approved: an empty value (absent, null, empty
+text, list or object) equals an absent one; `type_name` (the name the card
+shows for `type_id`) and the keys an apply writes (`applied_changes`,
+`created_entity_id`) are never compared; a list's elements pair by their
+natural key (`participants` by role, `state_changes` by entity and state,
+`scopes` by kind and target, `roles` by name, `effects` by type), a list of
+plain values as a set, `steps` by position. A proposal reviewed before
+v2.27 has no `mutation_review` row.
+
 -----
 
 ### `event`
````

2. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
3. Run the checks below, then the full corpus.

## Scope OUT

- Writing any row of the new tables (BRIEF-0115-B), any route or reader (D, E).
- Back-filling reviews for proposals reviewed before v2.27: none is invented.
- Every later brief of this lot: BRIEF-0115-B to E.

## Invariants to defend

INV-20 (UI-visible data never in JSON): `original_payload` is an audit snapshot, never rendered -- its allowlist entry says so; a change's values are relational rows. INV-60 (boot guard): the constant, the doc header and the migration's `schema_meta` move together. INV-12: the new tables are deleted only by the world cascade, which lists them (W1).

## Decision rights

STOP:
- The migration would write or rewrite any existing row, or rebuild `proposed_mutation`.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- `lore_usage.py` timing out at 16-17 s inside the corpus: it does the same on `main` (pre-existing, R-09 of the lot).
- Log lines a check prints before its verdict (`[skip] …`, a Starlette deprecation warning).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`.
- `python tooling/verify/checks/mutation_reviews.py` -> `PASS`.
- `python tooling/verify/checks/world_cascade.py` -> `PASS`.
- `python tooling/verify/checks/json_ui_boundary.py` -> `PASS`.
- `python tooling/verify/checks/schema_version_agreement.py` -> `PASS`.
- `python tooling/verify/checks/schema_partition.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (163 on the prototype; `lore_usage.py` may time out as on `main` -- REPORT-ONLY).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **MR1** -- `models/pipeline.py` `REVIEW_VIAS`: `REVIEW_VIAS: tuple[str, ...] = ("unit", "batch")` -> `REVIEW_VIAS: tuple[str, ...] = ("unit", "batch", "script")`
  - **MR2** -- `models/pipeline.py` `MutationReview.__table_args__`: `        CheckConstraint("round >= 1", name="ck_mutation_review_round"),` -> (line deleted)
  - **MR3** -- `migrate_v2_27_mutation_reviews.py` `_apply`: `        if plan["change"]:` -> `        if False:`
- Live gate (Nia): After a backup (`python scripts/backup.py`), on a copy of the production database then on production: `python scripts/migrate_v2_27_mutation_reviews.py` -> « Migration v2.27 applied. »; a second run -> « already fully applied »; the cockpit boots.
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

`world-engine-schema.md` and its changelog, ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
