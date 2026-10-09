<!-- slug: condition-draft-journal -->
# BRIEF 0112-B — "The interpreter keeps a journal of its proposals -- `condition_draft`, outside any world, its outcome moving one way to « saved »"

Lot: LOT-0112-condition-interpreter.md (authoritative on conflict)
Depends on: BRIEF-0112-A

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0112-A's commit).

- `src/world_engine/models/pipeline.py:388` -> `class LoreUsageEvent(SQLModel, table=True):`
- `src/world_engine/models/pipeline.py:425` -> `# skill_resolution  (one row per arbiter classification — the action`
- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.20"`
- `world-engine-schema.md:3` -> `Current schema version: v2.20`
- `world-engine-schema.md:1246` -> `CREATE INDEX idx_lore_usage_event_world ON lore_usage_event(world_ref, created_at);`
- `tooling/verify/checks/json_ui_boundary.py:113` -> `"LoreUsageEvent.model_calls",`
- `tooling/verify/checks/conditions.py:742` -> `"tables": sorted(t for t in tables if t.endswith("requirement") or t.startswith("condition")),`
- `src/world_engine/models/__init__.py:124` -> `LoreUsageEvent,`
- No `ConditionDraft` model, no `writes/condition_drafts.py`, no `scripts/migrate_v2_21_condition_draft.py` exist.

## Facts carried

### R-12 — the Lore journal is closed by its CHECKs [M]
Opened: `src/world_engine/models/pipeline.py:363-421` (`lore_usage_event`:
`kind` / `step` CHECK on two kinds, outcome CHECK, `payload` JSON, no
`world_id`, `world_ref` + `world_name`); `src/world_engine/lore_usage.py:34-41`
(`attempt_id`: the panel's UUID in canonical form, or a fresh one -- « a
journal id never fails the creator's request »);
`scripts/migrate_v2_13_lore_usage.py` (refuse when behind, idempotent,
zero-row post-check, `schema_meta` converged).
Consequence: IH2 would rebuild a CHECKed table; B creates its own table on
the same posture and reuses `attempt_id` and the migration's shape.

### R-13 — every JSON column is named and justified [M]
Opened: `tooling/verify/checks/json_ui_boundary.py:43-114`
(`JSON_COLUMN_ALLOWLIST`, ending with `LoreUsageEvent.payload`/`.model_calls`
`:112-113`; volet c fails on an unlisted JSON column).
Consequence: B adds `ConditionDraft.payload` and `.model_calls` with their
justification; the dashboard's rate reads relational columns only.

### R-14 — the canon-write gate attributes a write by its expression [M]
Opened: `tooling/verify/checks/single_canon_write.py:359-397` (`resolve`:
a name, a call, `.get(Model, …)`, a chained query, a subscript; not a
conditional expression), docstring `:9-12` and its implementation (an
unattributable site fails).
Consequence: the journal's writer assigns `db.get(ConditionDraft, …)` on a
statement of its own (a `x if y else None` is unattributable).

### R-15 — a check filters the condition tables by prefix [M]
Opened: `tooling/verify/checks/conditions.py:727-746` (`_cc3_state`:
`t.endswith("requirement") or t.startswith("condition")`, `:742`), its
CC3 expectation (exactly `condition`, `condition_node`).
Consequence: `condition_draft` turns CC3 red; B narrows the filter to the
two names, a one-line change named in its Scope IN.

### R-16 — the schema version moves in three places [M]
Opened: `src/world_engine/schema_version.py` (`EXPECTED_STATIC_SCHEMA_VERSION
= "v2.20"`); `world-engine-schema.md:3`; `world-engine-schema-changelog.md:14`
(newest first, `schema_partition.py`); `schema_version_agreement.py`.
Consequence: B bumps all three to v2.21 and documents the table after
`lore_usage_event` (`world-engine-schema.md:1204-1248`).

### R-20 — skills and offers of a world [M]
Opened: `src/world_engine/models/canon.py:594` (`BASE_SKILL_DOMAINS`),
`:633-655` (`SkillDefinition`: `world_id`, `name`, `base_domain`);
`src/world_engine/models/config.py:130` (`CONDITION_ROLES`).
Consequence: the `s` list is the four domains then the world's
definitions by name; `condition_draft.role` quotes `CONDITION_ROLES`.

### Case tables

b-2 -- the moves of `condition_draft.outcome` (C-07).

| from \ to     | proposed | refused | inserted | discarded | saved            |
|---------------|----------|---------|----------|-----------|------------------|
| needs_choice  | yes      | yes     | --       | yes       | --               |
| proposed      | --       | --      | yes      | yes       | --               |
| inserted      | --       | --      | --       | --        | `mark_draft_saved` only |
| refused, unavailable, parse_error, discarded, saved | -- | -- | -- | -- | -- |

First outcomes: proposed, needs_choice, refused, unavailable, parse_error.
Every outcome of `CONDITION_DRAFT_OUTCOMES` is a first outcome or reached
by a move (NB1).

b-4 -- `mark_draft_saved` (C-07, C-08).

| draft id         | draft's world | draft's outcome | result | row                                  |
|------------------|---------------|-----------------|--------|--------------------------------------|
| None / empty     | --            | --              | False  | unchanged                            |
| unknown          | --            | --              | False  | --                                   |
| known            | another       | any             | False  | unchanged                            |
| known            | this          | not `inserted`  | False  | unchanged                            |
| known            | this          | `inserted`      | True   | `saved`, `offer_ref`, `saved_as_proposed = (tree == payload.proposed)`, `decided_at` |

## Contracts

### C-07 — `condition_draft` and its writer
Produced by: BRIEF-0112-B   Consumed by: BRIEF-0112-D
Table (v2.21): `id, attempt_id, world_ref, world_name, role, instruction,
outcome, retried, offer_ref, saved_as_proposed, payload, model_calls,
created_at, decided_at`; CHECKs `ck_condition_draft_role` (role in
`CONDITION_ROLES`), `ck_condition_draft_outcome` (the eight outcomes),
`ck_condition_draft_saved` (`offer_ref` and `saved_as_proposed` set exactly
on `saved`); indexes `idx_condition_draft_attempt (attempt_id,
created_at)`, `idx_condition_draft_world (world_ref, created_at)`; no
`world_id`, no FK. `models.CONDITION_DRAFT_OUTCOMES` in CHECK order.
Writer (`writes/condition_drafts.py`): `FIRST_OUTCOMES`,
`CONDITION_DRAFT_MOVES` (b-2), `PAYLOAD_KEYS = {current, pending, mentions,
bindings, proposed, notes, errors}`;
`write_condition_draft(db, *, attempt_id, world_id, role, instruction,
outcome, payload, model_calls, retried=False) -> ConditionDraft`;
`move_condition_draft(db, draft, outcome, payload=None) -> ConditionDraft`;
`mark_draft_saved(db, *, world_id, draft_id, offer_id, tree) -> bool`.
Error cases: `ValueError` before any row for an empty attempt / world /
instruction, an unknown role, a first outcome outside `FIRST_OUTCOMES`, a
payload without exactly `PAYLOAD_KEYS`, a non-list `model_calls`, a move
outside b-2 (and any move to `saved`). `mark_draft_saved` never raises:
b-4. None commits.

## Context

The interpreter (BRIEF-0112-C) will propose; the creator will insert, discard, save. D1 of the series wants the acceptance rate measurable, and IH1 locked a journal of its own, relational where the rate is read. This brief creates the table (v2.21) and its one writer, before anything writes to it.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md` and `src/world_engine/cockpit/static/` are not in the
diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `models/pipeline.py`: `CONDITION_DRAFT_OUTCOMES` and `ConditionDraft` (C-07), after `LoreUsageEvent`; `models/__init__.py` exports both;
   - creates `src/world_engine/writes/condition_drafts.py`: `FIRST_OUTCOMES`, `CONDITION_DRAFT_MOVES`, `PAYLOAD_KEYS`, `write_condition_draft`, `move_condition_draft`, `mark_draft_saved` (C-07, b-2, b-4); every `db.get` on a statement of its own (R-14);
   - creates `scripts/migrate_v2_21_condition_draft.py` (the v2.13 migration's shape, R-12);
   - `schema_version.py`, `world-engine-schema.md` (header and the `condition_draft` section), `world-engine-schema-changelog.md`: v2.21 (R-16);
   - `json_ui_boundary.py`: `ConditionDraft.payload` and `.model_calls` allowlisted with their reason (R-13);
   - `conditions.py` CC3: the table filter names `condition` and `condition_node` instead of the prefix (R-15);
   - adds NB1-NB3 to `condition_interpreter.py`;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - scripts/migrate_v2_21_condition_draft.py
   - src/world_engine/models/__init__.py
   - src/world_engine/models/pipeline.py
   - src/world_engine/schema_version.py
   - src/world_engine/writes/condition_drafts.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/condition_interpreter.py
   - tooling/verify/checks/conditions.py
   - tooling/verify/checks/json_ui_boundary.py
   - world-engine-schema-changelog.md
   - world-engine-schema.md

````diff
diff --git a/scripts/migrate_v2_21_condition_draft.py b/scripts/migrate_v2_21_condition_draft.py
new file mode 100644
index 0000000..59c6aa7
--- /dev/null
+++ b/scripts/migrate_v2_21_condition_draft.py
@@ -0,0 +1,164 @@
+"""Migration v2.21 — `condition_draft`, the condition interpreter's journal
+(TICKET-0112, BRIEF-0112-B, decision IH1).
+
+Creates `condition_draft` (`id, attempt_id, world_ref, world_name, role,
+instruction, outcome, retried, offer_ref, saved_as_proposed, payload,
+model_calls, created_at, decided_at`, CHECKs `ck_condition_draft_role`,
+`ck_condition_draft_outcome`, `ck_condition_draft_saved`, indexes
+`idx_condition_draft_attempt` and `idx_condition_draft_world`). No
+`world_id` column and no FK to `world` or `quest_offer`: the journal
+outlives a deleted world or offer.
+
+Purely additive, zero rows created: the table starts empty and is filled
+only by the interpreter's routes going forward. Nothing is backfilled.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.20 (the migrations are sequential).
+
+Idempotent: the table's existence is checked before creating it.
+
+Post-check, before commit: the table exists and holds zero rows.
+
+Run from the project root:
+
+    python scripts/migrate_v2_21_condition_draft.py
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
+        "migrate_v2_21_condition_draft.py refuses to run without WORLD_ENGINE_ENV "
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
+_PREVIOUS_VERSION = "v2.20"
+_TABLE = "condition_draft"
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
+            f"Migration v2.21 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _create_table() -> None:
+    with engine.begin() as conn:
+        conn.execute(text(
+            """
+CREATE TABLE condition_draft (
+  id                 TEXT PRIMARY KEY NOT NULL,
+  attempt_id         TEXT NOT NULL,
+  world_ref          TEXT NOT NULL,
+  world_name         TEXT NOT NULL,
+  role               TEXT NOT NULL,
+  instruction        TEXT NOT NULL,
+  outcome            TEXT NOT NULL,
+  retried            BOOLEAN NOT NULL DEFAULT 0,
+  offer_ref          TEXT,
+  saved_as_proposed  BOOLEAN,
+  payload            JSON NOT NULL,
+  model_calls        JSON NOT NULL DEFAULT '[]',
+  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
+  decided_at         DATETIME,
+  CONSTRAINT ck_condition_draft_role CHECK (
+    role IN ('eligibility','prerequisite','completion')),
+  CONSTRAINT ck_condition_draft_outcome CHECK (
+    outcome IN ('proposed','needs_choice','refused','unavailable','parse_error',
+                'inserted','discarded','saved')),
+  CONSTRAINT ck_condition_draft_saved CHECK (
+    (offer_ref IS NOT NULL) = (outcome = 'saved')
+    AND (saved_as_proposed IS NOT NULL) = (outcome = 'saved'))
+)
+"""
+        ))
+        conn.execute(text(
+            "CREATE INDEX idx_condition_draft_attempt ON condition_draft(attempt_id, created_at)"
+        ))
+        conn.execute(text(
+            "CREATE INDEX idx_condition_draft_world ON condition_draft(world_ref, created_at)"
+        ))
+
+
+def _apply_ddl() -> list[str]:
+    if _TABLE in set(inspect(engine).get_table_names()):
+        print(f"Table {_TABLE!r} already exists — nothing to do.")
+        return []
+    _create_table()
+    return [f"{_TABLE} table + idx_condition_draft_attempt + idx_condition_draft_world"]
+
+
+def _post_checks() -> None:
+    if _TABLE not in set(inspect(engine).get_table_names()):
+        raise SystemExit(f"Migration v2.21 aborted, post-check failed: {_TABLE} is missing.")
+    with engine.connect() as conn:
+        count = conn.execute(text(f"SELECT COUNT(*) FROM {_TABLE}")).scalar()
+    if count != 0:
+        raise SystemExit(
+            f"Migration v2.21 aborted, post-check failed: {_TABLE} holds {count} row(s), "
+            "expected 0 — this migration creates zero rows."
+        )
+    print(f"Post-check: {_TABLE} row count = 0 (expected 0).")
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
+    print("Migration v2.21 — condition_draft")
+    _refuse_if_behind()
+    applied = _apply_ddl()
+    if applied:
+        print("Applied: " + ", ".join(applied) + ".")
+    else:
+        print("Migration v2.21 already fully applied — zero writes.")
+    _post_checks()
+    _converge_schema_meta()
+    print("\nMigration v2.21 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index eeb1f08..48aeb40 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -122,6 +122,8 @@ from .pipeline import (
     LoreEntry,
     LoreEntryRow,
     LoreUsageEvent,
+    ConditionDraft,
+    CONDITION_DRAFT_OUTCOMES,
     PassPlay,
     ProposedMutation,
     PromptTemplate,
@@ -185,6 +187,8 @@ __all__ = [
     "LoreEntry",
     "LoreEntryRow",
     "LoreUsageEvent",
+    "ConditionDraft",
+    "CONDITION_DRAFT_OUTCOMES",
     "DayMentionResolution",
     "SkillResolution",
     "Gathering",
diff --git a/src/world_engine/models/pipeline.py b/src/world_engine/models/pipeline.py
index e844ade..128ba12 100644
--- a/src/world_engine/models/pipeline.py
+++ b/src/world_engine/models/pipeline.py
@@ -421,6 +421,73 @@ class LoreUsageEvent(SQLModel, table=True):
     created_at: datetime = _created_ts()
 
 
+# -----------------------------------------------------------------------------
+# condition_draft  (the condition interpreter's journal, schema v2.21,
+# TICKET-0112, BRIEF-0112-B, decisions IH1 + D1 of the conditions series)
+#
+# One row per proposal of the interpreter: the creator's instruction for one
+# condition of a quest offer (`role`), the tree it started from, what the
+# model answered, what code made of it, and what became of it. `outcome`
+# moves along `CONDITION_DRAFT_MOVES` only (`writes/condition_drafts.py`, the
+# one writer): a proposal is `proposed` (insertable), `needs_choice` (a name
+# to pick first), `refused` (nothing insertable), `unavailable` (Ollama down)
+# or `parse_error`; the creator then inserts or discards it, and saving the
+# offer that holds an inserted one makes it `saved`, `offer_ref` naming the
+# offer and `saved_as_proposed` whether the saved tree is the proposed one.
+# The acceptance rate of the conditions series' dashboard (D1, TICKET-0115)
+# is a query on `outcome` and `saved_as_proposed`.
+#
+# Not a world's table (the I1 posture of `lore_usage_event`): `world_ref` and
+# `world_name` record the world without a FK, so the journal outlives a
+# deleted world and stays out of `delete_world_cascade` by construction;
+# `offer_ref` names its offer without a FK. `payload` and `model_calls` are
+# never rendered in any UI surface. Non-canon.
+# -----------------------------------------------------------------------------
+CONDITION_DRAFT_OUTCOMES: tuple[str, ...] = (
+    "proposed", "needs_choice", "refused", "unavailable", "parse_error", "inserted", "discarded", "saved",
+)
+
+
+class ConditionDraft(SQLModel, table=True):
+    __tablename__ = "condition_draft"
+    __table_args__ = (
+        Index("idx_condition_draft_attempt", "attempt_id", "created_at"),
+        Index("idx_condition_draft_world", "world_ref", "created_at"),
+        CheckConstraint(
+            "role IN ('eligibility','prerequisite','completion')",
+            name="ck_condition_draft_role",
+        ),
+        CheckConstraint(
+            "outcome IN ('proposed','needs_choice','refused','unavailable','parse_error',"
+            "'inserted','discarded','saved')",
+            name="ck_condition_draft_outcome",
+        ),
+        CheckConstraint(
+            "(offer_ref IS NOT NULL) = (outcome = 'saved') "
+            "AND (saved_as_proposed IS NOT NULL) = (outcome = 'saved')",
+            name="ck_condition_draft_saved",
+        ),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    attempt_id: str
+    world_ref: str
+    world_name: str
+    role: str
+    instruction: str
+    outcome: str
+    retried: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
+    offer_ref: Optional[str] = None
+    saved_as_proposed: Optional[bool] = None
+    payload: Any = Field(sa_column=Column(JSON, nullable=False))
+    model_calls: Any = Field(
+        default_factory=list,
+        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
+    )
+    created_at: datetime = _created_ts()
+    decided_at: Optional[datetime] = None
+
+
 # -------------------------------------------------------------------------
 # skill_resolution  (one row per arbiter classification — the action
 # lexicon's audit trail; schema v2.02, TICKET-0084)
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index 373d733..ea11411 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.20"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.21"
diff --git a/src/world_engine/writes/condition_drafts.py b/src/world_engine/writes/condition_drafts.py
new file mode 100644
index 0000000..38d3635
--- /dev/null
+++ b/src/world_engine/writes/condition_drafts.py
@@ -0,0 +1,118 @@
+"""The condition interpreter's journal writer (TICKET-0112, BRIEF-0112-B,
+decision IH1).
+
+`condition_draft` is non-canon: one row per proposal of the interpreter,
+whose `outcome` moves along `CONDITION_DRAFT_MOVES` and nowhere else. This
+module is its one writer; nothing here deletes a row, and nothing deletes
+the journal -- not even the world cascade (no `world_id` column). Nothing
+here commits; the caller owns the transaction.
+
+- `write_condition_draft(...)` : insert one proposal, in one of the
+  `FIRST_OUTCOMES`.
+- `move_condition_draft(...)`  : move a proposal to its next outcome, the
+  payload replaced whole when a new one is given (a name picked).
+- `mark_draft_saved(...)`      : the offer holding an inserted proposal was
+  saved -- `saved`, its offer and whether the saved tree is the proposed
+  one. Never fails the creator's save: a draft it cannot mark is skipped.
+
+Every shape the schema CHECKs is asserted here first, so a malformed record
+fails as a `ValueError` naming the field rather than as an `IntegrityError`.
+"""
+
+from __future__ import annotations
+
+from datetime import UTC, datetime
+from typing import Any, Optional
+
+from fastapi.encoders import jsonable_encoder
+from sqlmodel import Session
+
+from ..models import CONDITION_DRAFT_OUTCOMES, CONDITION_ROLES, ConditionDraft, World
+
+# What the interpreter may record first, and where each outcome may go.
+FIRST_OUTCOMES: tuple[str, ...] = ("proposed", "needs_choice", "refused", "unavailable", "parse_error")
+CONDITION_DRAFT_MOVES: dict[str, tuple[str, ...]] = {
+    "needs_choice": ("proposed", "refused", "discarded"),
+    "proposed": ("inserted", "discarded"),
+    "inserted": ("saved",),
+}
+# The payload of a proposal, by key: the tree it started from (the dict form
+# of `conditions.node_to_dict`, or None), the model's tree as code read it
+# with names still to pick (`pending`), the names it mentions and the picks
+# made, the tree code validated (`proposed`, dict form), the notes and the
+# errors shown to the creator.
+PAYLOAD_KEYS: frozenset[str] = frozenset({
+    "current", "pending", "mentions", "bindings", "proposed", "notes", "errors",
+})
+WORLD_NAME_UNKNOWN = "(monde introuvable)"
+
+
+def _payload(payload: Any) -> dict:
+    if not isinstance(payload, dict) or set(payload) != PAYLOAD_KEYS:
+        got = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
+        raise ValueError(f"condition_draft: a payload carries exactly {sorted(PAYLOAD_KEYS)}, got {got}")
+    return jsonable_encoder(payload)
+
+
+def write_condition_draft(
+    db: Session, *, attempt_id: str, world_id: str, role: str, instruction: str, outcome: str,
+    payload: dict, model_calls: list[dict], retried: bool = False,
+) -> ConditionDraft:
+    """Insert one proposal. `ValueError` on an empty attempt, world or
+    instruction, a role outside `CONDITION_ROLES`, an outcome outside
+    `FIRST_OUTCOMES`, a payload without exactly `PAYLOAD_KEYS`, or
+    `model_calls` that is not a list."""
+    for name, value in (("attempt_id", attempt_id), ("world_id", world_id), ("instruction", instruction)):
+        if not isinstance(value, str) or not value.strip():
+            raise ValueError(f"condition_draft: {name} is empty")
+    if role not in CONDITION_ROLES:
+        raise ValueError(f"condition_draft: unknown role {role!r}")
+    if outcome not in FIRST_OUTCOMES:
+        raise ValueError(f"condition_draft: a proposal cannot start {outcome!r}")
+    if not isinstance(model_calls, list):
+        raise ValueError("condition_draft: model_calls is not a list")
+    world = db.get(World, world_id)
+    draft = ConditionDraft(
+        attempt_id=attempt_id, world_ref=world_id,
+        world_name=world.name if world is not None else WORLD_NAME_UNKNOWN,
+        role=role, instruction=instruction.strip(), outcome=outcome, retried=bool(retried),
+        payload=_payload(payload), model_calls=jsonable_encoder(model_calls),
+    )
+    db.add(draft)
+    return draft
+
+
+def move_condition_draft(
+    db: Session, draft: ConditionDraft, outcome: str, payload: Optional[dict] = None,
+) -> ConditionDraft:
+    """Move `draft` to `outcome`; `ValueError` when `CONDITION_DRAFT_MOVES`
+    does not allow it. `saved` is `mark_draft_saved`'s alone."""
+    if outcome == "saved" or outcome not in CONDITION_DRAFT_MOVES.get(draft.outcome, ()):
+        raise ValueError(f"condition_draft: a {draft.outcome!r} proposal cannot become {outcome!r}")
+    if payload is not None:
+        draft.payload = _payload(payload)
+    draft.outcome = outcome
+    draft.decided_at = datetime.now(UTC)
+    db.add(draft)
+    return draft
+
+
+def mark_draft_saved(
+    db: Session, *, world_id: str, draft_id: Optional[str], offer_id: str, tree: Optional[dict],
+) -> bool:
+    """The offer `offer_id` was saved holding `tree` (dict form) where the
+    creator inserted `draft_id`. True when the draft was marked; False --
+    and nothing written -- when there is no such draft in `world_id`, or it
+    is not `inserted`."""
+    if not draft_id:
+        return False
+    draft = db.get(ConditionDraft, draft_id)
+    if draft is None or draft.world_ref != world_id or draft.outcome != "inserted":
+        return False
+    draft.outcome = "saved"
+    draft.offer_ref = offer_id
+    draft.saved_as_proposed = jsonable_encoder(tree) == draft.payload.get("proposed")
+    draft.decided_at = datetime.now(UTC)
+    db.add(draft)
+    return True
+
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 4930046..bf2b723 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18546,6 +18546,27 @@ object. The client is a parameter, so a check that replaces a caller's
 `chat` still reaches the call. `lore_write_draft._world_facts` becomes the
 public `world_fact_ids`, for the interpreter's context.
 
+## THE INTERPRETER KEEPS A JOURNAL OF ITS PROPOSALS (TICKET-0112) -- `condition_draft`, OUTSIDE ANY WORLD, ITS OUTCOME MOVING ONE WAY TO « SAVED » (BRIEF-0112-b, schema v2.21)
+
+**IH1.** Every proposal of the condition interpreter is one
+`condition_draft` row: the creator's instruction for one condition of a
+quest offer (its role), the tree it started from, what the model answered
+and code made of it, the notes and errors she was shown. Its `outcome`
+moves along `writes/condition_drafts.CONDITION_DRAFT_MOVES` only:
+`proposed` / `needs_choice` / `refused` / `unavailable` / `parse_error` at
+first, then `inserted` or `discarded`, and `saved` once the offer holding
+an inserted proposal is saved -- with `offer_ref` and `saved_as_proposed`
+(whether the saved tree is the proposed one). The conditions series'
+acceptance rate (D1, the dashboard of TICKET-0115) is a query on those two
+relational columns; `payload` and `model_calls` are JSON, never rendered.
+Like `lore_usage_event` (I1 of TICKET-0103), the table has no `world_id`
+and no FK: it outlives a deleted world or offer and stays out of the world
+cascade. `writes/condition_drafts.py` is its one writer.
+
+**Rejected.** IH2 (a new `kind` in `lore_usage_event`): a rebuild of its
+CHECKs, and an acceptance counted inside JSON. IH3 (an export only): D1
+would not be measurable.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/condition_interpreter.py b/tooling/verify/checks/condition_interpreter.py
index c4c50c4..c0845b1 100644
--- a/tooling/verify/checks/condition_interpreter.py
+++ b/tooling/verify/checks/condition_interpreter.py
@@ -22,6 +22,32 @@ NA2 -- one templated JSON call (BRIEF-0112-A; static, AST, and a stub).
    and records one exchange whose raw output is the stub's reply.
    `lore_write_draft.world_fact_ids` is public and `_world_facts` gone.
 
+NB1 -- the journal's table (BRIEF-0112-B, IH1; import). `condition_draft`
+   carries exactly its contract's columns, CHECK names and texts, and its
+   two indexes; no column is `world_id` and no column has a FK;
+   `CONDITION_DRAFT_OUTCOMES` is the outcome CHECK's list, in order, and
+   equals `FIRST_OUTCOMES` with every outcome `CONDITION_DRAFT_MOVES`
+   reaches; the role CHECK quotes `CONDITION_ROLES`; `JSON_COLUMN_ALLOWLIST`
+   names `ConditionDraft.payload` and `ConditionDraft.model_calls`; the
+   code's schema version is v2.21 or later.
+NB2 -- the writer (fixture). `write_condition_draft` records a proposal
+   with its world's name; refused with a `ValueError` and no row: an
+   unknown role, a first outcome `inserted`, a payload missing a key, an
+   empty instruction. `move_condition_draft` takes `needs_choice` to
+   `proposed` with a new payload and `proposed` to `inserted`, stamping
+   `decided_at`; it refuses `proposed` -> `saved`, `refused` -> `inserted`
+   and `inserted` -> `discarded`, changing nothing. `mark_draft_saved`
+   marks an inserted draft `saved` with its offer and `saved_as_proposed`
+   true for the proposed tree and false for another; it returns False and
+   writes nothing for a draft of another world, a `proposed` draft, an
+   unknown id and None. The database refuses a `saved` row without an
+   offer, and an outcome outside the list.
+NB3 -- migration `scripts/migrate_v2_21_condition_draft.py` on a database
+   without the table: at v2.19 it refuses and creates nothing; at v2.20 it
+   creates the table with the model's columns and CHECK names, zero rows,
+   and sets `schema_meta` to the code's version; a second run says nothing
+   to do; a row written through the writer reads back its JSON.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -31,11 +57,15 @@ import ast
 import json
 import os
 import pathlib
+import re
+import sqlite3
+import subprocess
 import sys
 import tempfile
 
 ROOT = pathlib.Path(__file__).resolve().parents[3]
 SRC = ROOT / "src" / "world_engine"
+MIGRATION = ROOT / "scripts" / "migrate_v2_21_condition_draft.py"
 
 FAILURES: list[str] = []
 
@@ -223,18 +253,263 @@ def check_na2(engine) -> None:
     _na2_stub(engine)
 
 
+# --- NB1 -----------------------------------------------------------------------
+
+DRAFT_COLUMNS = ("id", "attempt_id", "world_ref", "world_name", "role", "instruction", "outcome", "retried",
+                 "offer_ref", "saved_as_proposed", "payload", "model_calls", "created_at", "decided_at")
+DRAFT_CHECKS = {
+    "ck_condition_draft_role": "role IN ('eligibility','prerequisite','completion')",
+    "ck_condition_draft_outcome": "outcome IN ('proposed','needs_choice','refused','unavailable','parse_error',"
+                                  "'inserted','discarded','saved')",
+    "ck_condition_draft_saved": "(offer_ref IS NOT NULL) = (outcome = 'saved') "
+                                "AND (saved_as_proposed IS NOT NULL) = (outcome = 'saved')",
+}
+DRAFT_INDEXES = {"idx_condition_draft_attempt": ("attempt_id", "created_at"),
+                 "idx_condition_draft_world": ("world_ref", "created_at")}
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+def check_nb1() -> None:
+    from sqlalchemy import CheckConstraint
+
+    from world_engine.models import CONDITION_DRAFT_OUTCOMES, CONDITION_ROLES, ConditionDraft
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+    from world_engine.writes.condition_drafts import CONDITION_DRAFT_MOVES, FIRST_OUTCOMES
+
+    table = ConditionDraft.__table__
+    columns = tuple(c.name for c in table.columns)
+    if columns != DRAFT_COLUMNS:
+        fail(f"NB1: condition_draft columns are {columns}")
+    if any(c.foreign_keys for c in table.columns) or "world_id" in columns:
+        fail("NB1: condition_draft carries a FK or a world_id")
+    checks = {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
+    if checks != DRAFT_CHECKS:
+        fail(f"NB1: condition_draft CHECKs are {checks}")
+    indexes = {i.name: tuple(c.name for c in i.columns) for i in table.indexes}
+    if indexes != DRAFT_INDEXES:
+        fail(f"NB1: condition_draft indexes are {indexes}")
+    quoted = tuple(re.findall(r"'([a-z_]+)'", checks.get("ck_condition_draft_outcome", "")))
+    reached = set(FIRST_OUTCOMES) | {o for moves in CONDITION_DRAFT_MOVES.values() for o in moves}
+    if quoted != CONDITION_DRAFT_OUTCOMES or set(CONDITION_DRAFT_OUTCOMES) != reached:
+        fail(f"NB1: outcomes {CONDITION_DRAFT_OUTCOMES} vs CHECK {quoted} vs moves {sorted(reached)}")
+    roles = tuple(re.findall(r"'([a-z_]+)'", checks.get("ck_condition_draft_role", "")))
+    if roles != CONDITION_ROLES:
+        fail(f"NB1: the role CHECK quotes {roles}, not CONDITION_ROLES")
+    boundary = (ROOT / "tooling" / "verify" / "checks" / "json_ui_boundary.py").read_text(encoding="utf-8")
+    for name in ("ConditionDraft.payload", "ConditionDraft.model_calls"):
+        if f'"{name}"' not in boundary:
+            fail(f"NB1: JSON_COLUMN_ALLOWLIST does not name {name}")
+    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < (2, 21):
+        fail(f"NB1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")
+
+
+# --- NB2 -----------------------------------------------------------------------
+
+def _payload(**over) -> dict:
+    base = {"current": None, "pending": None, "mentions": [], "bindings": {}, "proposed": None,
+            "notes": [], "errors": []}
+    base.update(over)
+    return base
+
+
+def _nb2_refusals(session, world_id: str) -> None:
+    from sqlmodel import func, select
+
+    from world_engine.models import ConditionDraft
+    from world_engine.writes.condition_drafts import write_condition_draft
+
+    before = session.exec(select(func.count()).select_from(ConditionDraft)).one()
+    bad = {"an unknown role": dict(role="reward"), "a first outcome inserted": dict(outcome="inserted"),
+           "a payload missing a key": dict(payload={"current": None}), "an empty instruction": dict(instruction=" ")}
+    for label, over in bad.items():
+        kwargs = dict(attempt_id="a", world_id=world_id, role="eligibility", instruction="x",
+                      outcome="proposed", payload=_payload(), model_calls=[])
+        kwargs.update(over)
+        try:
+            write_condition_draft(session, **kwargs)
+            fail(f"NB2: the writer accepted {label}")
+        except ValueError:
+            pass
+    session.rollback()
+    if session.exec(select(func.count()).select_from(ConditionDraft)).one() != before:
+        fail("NB2: a refused proposal wrote a row")
+
+
+def _nb2_moves(session, world_id: str) -> None:
+    from world_engine.writes.condition_drafts import move_condition_draft, write_condition_draft
+
+    tree = {"op": "leaf", "type": "vital_status", "subject_role": "doer", "subject_entity_id": None,
+            "target_entity_id": None, "target_key": None, "threshold": None, "value": "alive"}
+    draft = write_condition_draft(session, attempt_id="a", world_id=world_id, role="completion",
+                                  instruction="Le joueur est en vie", outcome="needs_choice",
+                                  payload=_payload(), model_calls=[])
+    session.commit()
+    if draft.world_name != "Interprète NB" or draft.decided_at is not None:
+        fail(f"NB2: a proposal reads world {draft.world_name!r}, decided {draft.decided_at}")
+    move_condition_draft(session, draft, "proposed", _payload(proposed=tree))
+    move_condition_draft(session, draft, "inserted")
+    session.commit()
+    if draft.outcome != "inserted" or draft.payload["proposed"] != tree or draft.decided_at is None:
+        fail(f"NB2: the moves left {draft.outcome}, {draft.payload['proposed']}")
+    refused = write_condition_draft(session, attempt_id="a", world_id=world_id, role="completion",
+                                    instruction="x", outcome="refused", payload=_payload(), model_calls=[])
+    proposed = write_condition_draft(session, attempt_id="a", world_id=world_id, role="completion",
+                                     instruction="x", outcome="proposed", payload=_payload(), model_calls=[])
+    session.commit()
+    for row, outcome in ((proposed, "saved"), (refused, "inserted"), (draft, "discarded")):
+        was = row.outcome
+        try:
+            move_condition_draft(session, row, outcome)
+            fail(f"NB2: {was} -> {outcome} was allowed")
+        except ValueError:
+            if row.outcome != was:
+                fail(f"NB2: a refused move changed {was} to {row.outcome}")
+    return draft, proposed, tree
+
+
+def _nb2_saved(session, world_id: str, other_world: str, draft, proposed, tree) -> None:
+    from world_engine.writes.condition_drafts import mark_draft_saved, move_condition_draft, write_condition_draft
+
+    for label, args in (("another world", (other_world, draft.id)), ("a proposed draft", (world_id, proposed.id)),
+                        ("an unknown id", (world_id, "no-such-draft")), ("None", (world_id, None))):
+        if mark_draft_saved(session, world_id=args[0], draft_id=args[1], offer_id="offer-1", tree=tree):
+            fail(f"NB2: mark_draft_saved marked {label}")
+    if proposed.outcome != "proposed" or draft.outcome != "inserted":
+        fail("NB2: a skipped mark wrote a row")
+    if not mark_draft_saved(session, world_id=world_id, draft_id=draft.id, offer_id="offer-1", tree=dict(tree)):
+        fail("NB2: an inserted draft was not marked")
+    other = write_condition_draft(session, attempt_id="b", world_id=world_id, role="eligibility",
+                                  instruction="y", outcome="proposed", payload=_payload(proposed=tree),
+                                  model_calls=[])
+    move_condition_draft(session, other, "inserted")
+    mark_draft_saved(session, world_id=world_id, draft_id=other.id, offer_id="offer-2",
+                     tree={**tree, "value": "dead"})
+    session.commit()
+    if (draft.outcome, draft.offer_ref, draft.saved_as_proposed) != ("saved", "offer-1", True) \
+            or (other.outcome, other.saved_as_proposed) != ("saved", False):
+        fail(f"NB2: saved drafts read {draft.outcome, draft.offer_ref, draft.saved_as_proposed}, "
+             f"{other.outcome, other.saved_as_proposed}")
+
+
+def _nb2_database(db_path: str) -> None:
+    with sqlite3.connect(db_path) as conn:
+        for label, outcome, offer, saved in (("a saved row without offer", "saved", None, None),
+                                             ("an outcome outside the list", "accepted", None, None)):
+            try:
+                conn.execute(
+                    "INSERT INTO condition_draft (id, attempt_id, world_ref, world_name, role, instruction, "
+                    "outcome, offer_ref, saved_as_proposed, payload) VALUES (?, 'a', 'w', 'n', 'eligibility', "
+                    "'x', ?, ?, ?, '{}')", (f"raw-{outcome}", outcome, offer, saved))
+                fail(f"NB2: the database accepted {label}")
+            except sqlite3.IntegrityError:
+                pass
+
+
+def check_nb2(engine, db_path: str) -> None:
+    from sqlmodel import Session
+
+    from world_engine.models import World
+
+    with Session(engine) as session:
+        world, other = World(name="Interprète NB", is_active=False), World(name="Autre NB", is_active=False)
+        session.add(world)
+        session.add(other)
+        session.commit()
+        _nb2_refusals(session, world.id)
+        draft, proposed, tree = _nb2_moves(session, world.id)
+        _nb2_saved(session, world.id, other.id, draft, proposed, tree)
+    _nb2_database(db_path)
+
+
+# --- NB3 -----------------------------------------------------------------------
+
+def _run_migration(db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
+                          text=True, cwd=str(ROOT), timeout=120)
+
+
+def _draft_state(db_path: str):
+    with sqlite3.connect(db_path) as conn:
+        sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'condition_draft'").fetchone()
+        shape = [r[1] for r in conn.execute("PRAGMA table_info(condition_draft)")]
+        count = conn.execute("SELECT COUNT(*) FROM condition_draft").fetchone()[0] if sql else None
+        version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0]
+    checks = set(re.findall(r"CONSTRAINT (ck_[a-z_]+)", sql[0])) if sql else set()
+    return shape, checks, count, version
+
+
+def _set_version(db_path: str, version: str) -> None:
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("DROP TABLE IF EXISTS condition_draft")
+        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))
+
+
+def check_nb3() -> None:
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, SQLModel
+
+    from world_engine.models import ConditionDraft, SchemaMeta, World
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+    from world_engine.writes.condition_drafts import write_condition_draft
+
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "migrate.db")
+    eng = create_engine(f"sqlite:///{db_path}")
+    SQLModel.metadata.create_all(eng)
+    with Session(eng) as session:
+        session.add(SchemaMeta(id=1, static_version="v2.20"))
+        session.commit()
+    eng.dispose()
+    _set_version(db_path, "v2.19")
+    result = _run_migration(db_path)
+    if result.returncode == 0 or _draft_state(db_path)[0]:
+        fail(f"NB3: v2.19 was not refused (exit {result.returncode})")
+    _set_version(db_path, "v2.20")
+    result = _run_migration(db_path)
+    shape, checks, count, version = _draft_state(db_path)
+    if result.returncode != 0 or tuple(shape) != DRAFT_COLUMNS or checks != set(DRAFT_CHECKS) or count != 0 \
+            or version != EXPECTED_STATIC_SCHEMA_VERSION:
+        fail(f"NB3: exit {result.returncode}, shape {shape}, checks {sorted(checks)}, count {count}, "
+             f"version {version}: {result.stderr.strip()[-200:]}")
+    again = _run_migration(db_path)
+    if again.returncode != 0 or "nothing to do" not in again.stdout:
+        fail(f"NB3: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
+    eng = create_engine(f"sqlite:///{db_path}")
+    with Session(eng) as session:
+        world = World(name="Migrée", is_active=False)
+        session.add(world)
+        session.commit()
+        payload = _payload(notes=["une note"])
+        row = write_condition_draft(session, attempt_id="a", world_id=world.id, role="prerequisite",
+                                    instruction="x", outcome="refused", payload=payload,
+                                    model_calls=[{"usage": "u"}])
+        session.commit()
+        back = session.get(ConditionDraft, row.id)
+        if back.payload != payload or back.model_calls != [{"usage": "u"}] or back.retried is not False:
+            fail("NB3: the migrated table does not read back a written row")
+    eng.dispose()
+
+
 def main() -> int:
-    _fresh_db()
+    db_path = _fresh_db()
     from world_engine.db import create_db_and_tables, engine
     create_db_and_tables()
     check_na1(engine)
     check_na2(engine)
+    check_nb1()
+    check_nb2(engine, db_path)
+    check_nb3()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print("PASS: condition_interpreter -- one coded list names facts, quest offers and skills by code; "
-          "one templated JSON call serves the creator's authoring tools")
+          "one templated JSON call serves the creator's authoring tools; v2.21 journals every proposal "
+          "of the interpreter, outside any world, its outcome moving one way to « saved »")
     return 0
 
 
diff --git a/tooling/verify/checks/conditions.py b/tooling/verify/checks/conditions.py
index e1f990b..846bb4c 100644
--- a/tooling/verify/checks/conditions.py
+++ b/tooling/verify/checks/conditions.py
@@ -739,7 +739,9 @@ def _cc3_state(db_path: str) -> dict:
                     trees[(column, owner, role)] = nodes
         return {
             "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
-            "tables": sorted(t for t in tables if t.endswith("requirement") or t.startswith("condition")),
+            # TICKET-0112 (BRIEF-0112-B): `condition_draft` shares the prefix; the
+            # rule is about the two requirement tables and the condition tree's two.
+            "tables": sorted(t for t in tables if t.endswith("requirement") or t in ("condition", "condition_node")),
             "trees": trees,
         }
 
diff --git a/tooling/verify/checks/json_ui_boundary.py b/tooling/verify/checks/json_ui_boundary.py
index 5577b2d..133814d 100644
--- a/tooling/verify/checks/json_ui_boundary.py
+++ b/tooling/verify/checks/json_ui_boundary.py
@@ -111,6 +111,14 @@ JSON_COLUMN_ALLOWLIST = {
     # UI consumer must relationalize (the D2 reactivation condition).
     "LoreUsageEvent.payload",
     "LoreUsageEvent.model_calls",
+    # The condition interpreter's journal (TICKET-0112, BRIEF-0112-B, IH1):
+    # what each proposal started from and became, and every model exchange,
+    # kept for the acceptance rate and an offline analysis. Never rendered in
+    # any UI surface: the editor shows a proposal from the route's answer, and
+    # the rate reads the relational `outcome` and `saved_as_proposed`. The
+    # FIRST UI consumer of these two columns must relationalize.
+    "ConditionDraft.payload",
+    "ConditionDraft.model_calls",
 }
 
 
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 8919741..f7c34b1 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,14 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.21** — TICKET-0112, BRIEF-0112-B: the condition interpreter's
+  journal. `condition_draft` (one row per proposal: the creator's
+  instruction for one condition of an offer, what the model answered and
+  code made of it, its outcome -- proposed, needs a name picked, refused,
+  unavailable, unparsable, then inserted, discarded or saved with the offer,
+  and whether it was saved as proposed) is added, without `world_id` and
+  without FK. `migrate_v2_21_condition_draft.py` creates it empty and
+  refuses a database older than v2.20.
 - **v2.20** — TICKET-0111, BRIEF-0111-C: the condition language. `condition`
   (one per owner and role: an offer's eligibility, an offer step's or an
   agenda step's prerequisite or completion) and `condition_node` (a tree of
diff --git a/world-engine-schema.md b/world-engine-schema.md
index c00110e..0d2bd0d 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.20
+Current schema version: v2.21
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -1248,6 +1248,65 @@ CREATE INDEX idx_lore_usage_event_world ON lore_usage_event(world_ref, created_a
 
 -----
 
+### `condition_draft`
+
+The condition interpreter's journal (schema v2.21, TICKET-0112, BRIEF-0112-B,
+decision IH1): one row per proposal of the interpreter -- the creator's
+`instruction` for one condition of a quest offer (`role`: `eligibility`,
+`prerequisite` or `completion`), grouped by `attempt_id`, the id the editor
+holds for one use. `payload` is what the proposal started from and became
+(`current`, `pending`, `mentions`, `bindings`, `proposed`, `notes`,
+`errors`); `model_calls` is every model exchange of it (prompt version,
+model, rendered messages, raw output, error); `retried` says the model was
+asked once more after code refused its first answer (II1).
+
+`outcome` moves along `writes/condition_drafts.CONDITION_DRAFT_MOVES` only.
+A proposal starts `proposed` (insertable), `needs_choice` (a name to pick
+first), `refused` (nothing insertable), `unavailable` (Ollama down) or
+`parse_error`; `needs_choice` becomes `proposed`, `refused` or `discarded`
+once the creator picks; `proposed` becomes `inserted` or `discarded`; an
+`inserted` proposal becomes `saved` when the offer holding it is saved --
+`offer_ref` names that offer and `saved_as_proposed` says whether the saved
+tree is the proposed one; both are set on exactly that outcome. `decided_at`
+is the time of the last move. The conditions series' acceptance rate (D1)
+reads `outcome` and `saved_as_proposed`.
+
+Not a world's table (the I1 posture of `lore_usage_event`): `world_ref` and
+`world_name` record the world without a FK, so the journal outlives a
+deleted world and stays out of `delete_world_cascade` by construction;
+`offer_ref` names its offer without a FK. Never deleted. Non-canon.
+
+```sql
+CREATE TABLE condition_draft (
+  id                 TEXT PRIMARY KEY NOT NULL,
+  attempt_id         TEXT NOT NULL,
+  world_ref          TEXT NOT NULL,
+  world_name         TEXT NOT NULL,
+  role               TEXT NOT NULL,
+  instruction        TEXT NOT NULL,
+  outcome            TEXT NOT NULL,
+  retried            BOOLEAN NOT NULL DEFAULT 0,
+  offer_ref          TEXT,
+  saved_as_proposed  BOOLEAN,
+  payload            JSON NOT NULL,
+  model_calls        JSON NOT NULL DEFAULT '[]',
+  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
+  decided_at         DATETIME,
+  CONSTRAINT ck_condition_draft_role CHECK (
+    role IN ('eligibility','prerequisite','completion')),
+  CONSTRAINT ck_condition_draft_outcome CHECK (
+    outcome IN ('proposed','needs_choice','refused','unavailable','parse_error',
+                'inserted','discarded','saved')),
+  CONSTRAINT ck_condition_draft_saved CHECK (
+    (offer_ref IS NOT NULL) = (outcome = 'saved')
+    AND (saved_as_proposed IS NOT NULL) = (outcome = 'saved'))
+);
+CREATE INDEX idx_condition_draft_attempt ON condition_draft(attempt_id, created_at);
+CREATE INDEX idx_condition_draft_world ON condition_draft(world_ref, created_at);
+```
+
+-----
+
 ### `skill_resolution`
 
 ```sql
````

2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit as one commit: `BRIEF-0112-B: condition_draft journal, schema v2.21`.
4. Do not run the migration on Nia's database: she runs it at the live gate (TICKET-0112, Live). NB3 runs it on a temporary copy.

## Scope OUT

- A `world_id` column, a FK to `world` or `quest_offer`, a place in `delete_world_cascade` (the I1 posture; `world_cascade.py` must stay green untouched).
- Any reader of the journal: no route, no export script, no dashboard (TICKET-0115).
- A new `kind` in `lore_usage_event` (IH2, rejected).
- Any delete of a `condition_draft` row.
- The interpreter, its routes, its editor (BRIEF-0112-C to E).

## Invariants to defend

**UI-visible data never lives in JSON** -- `payload` and `model_calls` are never rendered; the rate reads `outcome` and `saved_as_proposed`, relational (NB1, `json_ui_boundary.py`). **Schema is authoritative** -- model, migration, doc header, changelog and the code constant move together (`schema_version_agreement.py`, `schema_partition.py`). **History is sacred** -- the writer never deletes and moves an outcome one way only (b-2). **Two sanctioned canon-write paths** -- `condition_draft` is non-canon; `single_canon_write.py` must attribute every site (R-14). **Nia's database is never touched by an executor** -- NB3 migrates a temporary copy.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A named mutation does not turn its rule red.
- `world_cascade.py` turns red (the table must not be world-scoped).
- The migration would need to rebuild or alter an existing table.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `conditions.py` CC3 already filters by name (someone narrowed it since): keep theirs, drop that hunk, report it.

REPORT-ONLY:
- Timing of the corpus run; a check that times out under load and passes when rerun alone (name it).
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- `schema_reconcile` listing `condition_draft` among the static tables at boot.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/condition_interpreter.py` -> `PASS: condition_interpreter -- one coded list names facts, quest offers and skills by code; one templated JSON call serves the creator's authoring tools; v2.21 journals every proposal of the interpreter, outside any world, its outcome moving one way to « saved »`
- `conditions.py`, `json_ui_boundary.py`, `single_canon_write.py`, `world_cascade.py`, `schema_version_agreement.py`, `schema_partition.py`, `lore_usage.py`, `module_budget.py`, `function_length.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`condition_interpreter.py` exits 1 with the rule named):
  - in `src/world_engine/writes/condition_drafts.py`, `    "inserted": ("saved",),` -> `    "inserted": ("saved", "discarded"),` -> `NB2`
  - in `src/world_engine/writes/condition_drafts.py`, `    draft.saved_as_proposed = jsonable_encoder(tree) == draft.payload.get("proposed")` -> `    draft.saved_as_proposed = True` -> `NB2`
  - in `src/world_engine/models/pipeline.py`, `        Index("idx_condition_draft_world", "world_ref", "created_at"),` -> `        Index("idx_condition_draft_world", "world_ref"),` -> `NB1`
  - in `scripts/migrate_v2_21_condition_draft.py`, `_PREVIOUS_VERSION = "v2.20"` -> `_PREVIOUS_VERSION = "v2.19"` -> `NB3`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 145/145.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Schema v2.21: `world-engine-schema.md` (header, `condition_draft` section) and `world-engine-schema-changelog.md` -- in the diff. Decision entry « THE INTERPRETER KEEPS A JOURNAL OF ITS PROPOSALS (TICKET-0112) -- `condition_draft`, OUTSIDE ANY WORLD, ITS OUTCOME MOVING ONE WAY TO « SAVED » (BRIEF-0112-b, schema v2.21) » -- in the diff.
