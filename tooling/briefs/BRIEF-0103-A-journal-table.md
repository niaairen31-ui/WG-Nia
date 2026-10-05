<!-- slug: journal-table -->
# BRIEF 0103-A — "The journal table: `lore_usage_event`, schema v2.13"

Lot: LOT-0103-lore-usage-journal.md (authoritative on conflict)
Depends on: nothing in this lot
Commit header for decisions: `(BRIEF-0103-a, schema v2.13)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0103`, cut from `main` at `d9c5a6a` or later, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/models/pipeline.py:345` → `class LoreEntryRow(SQLModel, table=True):`; `:361` → `    action: str` (last line of the class, followed by a blank line).
- `src/world_engine/models/__init__.py:107` → `    LoreEntryRow,`; `:153` → `    "LoreEntryRow",`.
- `src/world_engine/schema_version.py:15` → `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.12"`.
- `world-engine-schema.md:3` → `Current schema version: v2.12`; `:1195` → `CREATE UNIQUE INDEX idx_lore_entry_row_entry`.
- `world-engine-schema-changelog.md:16` → `- **v2.12** — TICKET-0101, BRIEF-0101-D: `.
- `tooling/verify/checks/json_ui_boundary.py:101` → `    "EntityTypeHistory.definition_snapshot",` followed by `}` on `:102`.
- `tooling/verify/checks/world_cascade.py:9-11` → W1 defines the world-reaching tables as those with « a `world_id` column, or a foreign key to a world-reaching table ».
- `scripts/migrate_v2_12_zone_borde.py:67` → `_PREVIOUS_VERSION = "v2.11"` (v2.12 is the newest migration).
- `src/world_engine/writes/lore_usage.py`, `scripts/migrate_v2_13_lore_usage.py` and `tooling/verify/checks/lore_usage.py` do not exist.

## Facts carried

### R-01 — what the writing path keeps today [M]
Opened: `src/world_engine/models/pipeline.py:333-361` (`LoreEntry`,
`LoreEntryRow`), `src/world_engine/writes/lore_entries.py:19-47`.
Finding: only a successful commit leaves a trace: `lore_entry` (statement,
questions, answers) and one `lore_entry_row` per canon row written. Both
carry `world_id` and are deleted by the world cascade.
Consequence: the draft, abandoned attempts, refusals and model replies are
not recoverable today; the journal is a new table, not an extension of
`lore_entry` (whose rows die with their world, F2).

### R-10 — what the world cascade calls a world's table [M]
Opened: `tooling/verify/checks/world_cascade.py:9-14` (W1) and its
implementation `_reaching_tables` 208-224.
Finding: a table is world-reaching if it has a `world_id` column or a FK to
a world-reaching table; every such table must be named by
`delete_world_cascade`.
Consequence: I1 — the journal has `world_ref` and `world_name`, no
`world_id`, no FK at all; U1 asserts it, U4 proves a row outlives its world.

### R-11 — JSON columns and `json.loads` are gated [M]
Opened: `tooling/verify/checks/json_ui_boundary.py:43-102` (volet c: every
`Column(JSON` is a named allow-list entry), `tooling/verify/checks/
llm_parse_chokepoint.py:3-16` (a `json.loads` site in `src/` must be the
chokepoint or allow-listed).
Finding: both gates are fail-closed on a new site.
Consequence: A allow-lists `LoreUsageEvent.payload` and `.model_calls` with
their reason; the recorder copies payloads with
`fastapi.encoders.jsonable_encoder` (no `json.loads`; `fastapi` is already
imported outside `cockpit/`, enumeration E11).

### R-12 — schema version and migrations [M]
Opened: `src/world_engine/schema_version.py:15` (`"v2.12"`),
`world-engine-schema.md:3`, `world-engine-schema-changelog.md:16`,
`scripts/migrate_v2_12_zone_borde.py:67` (`_PREVIOUS_VERSION = "v2.11"`),
`scripts/migrate_v2_11_lore_entry.py` (the additive-table template),
`tooling/verify/checks/schema_version_agreement.py`, `schema_partition.py`.
Finding: v2.12 is current; constant, header and newest changelog entry move
together; earlier migrations converge `schema_meta` to the code constant;
no check pins `"v2.12"` (enumeration E4).
Consequence: v2.13, purely additive, refuses a database below v2.12.

## Contracts

### C-01 — `writes/lore_usage.write_usage_event`
Produced by: BRIEF-0103-A   Consumed by: BRIEF-0103-C (through C-04), U3, U6d
Signature: `write_usage_event(db, *, attempt_id: str, world_ref: str,
world_name: str, kind: str, step: str, outcome: str, payload: dict,
model_calls: list[dict], lore_entry_ref: Optional[str] = None) ->
LoreUsageEvent`. Adds the row; never commits.
Table `lore_usage_event`: `id, attempt_id, world_ref, world_name, kind,
step, outcome, payload JSON, model_calls JSON, lore_entry_ref, created_at`;
no `world_id`, no FK. `LORE_USAGE_STEPS = {"write": ("questions", "draft",
"commit"), "consult": ("ask", "resolve")}`; `LORE_USAGE_OUTCOMES = ("ok",
"unavailable", "parse_error", "refused")`.
Error cases (`ValueError`): empty `attempt_id`/`world_ref`/`world_name`; a
`(kind, step)` outside `LORE_USAGE_STEPS`; an unknown outcome; a payload
not carrying exactly `PAYLOAD_KEYS[step]`; `payload["error"]` None on a
non-`ok` outcome or set on `ok`; a model call not carrying exactly
`MODEL_CALL_KEYS` or with an empty `usage`; `lore_entry_ref` set anywhere
but on `commit`/`ok`, or missing there.

### C-02 — the journal's two key families
Produced by: BRIEF-0103-A   Consumed by: B (U5), C, E
`MODEL_CALL_KEYS = {usage, prompt_version_id, prompt_version_number, model,
system_prompt, user_message, raw_output, error}`.
`PAYLOAD_KEYS` (one entry per step; written before any member, re-read
after the fifth):
- `questions`: `statement, questions, error`
- `draft`: `statement, answers, draft, error`
- `commit`: `proposal, result, error`
- `ask`: `question, response, error`
- `resolve`: `question, plan, bindings, response, error`
`error` is None on `ok` and the message the creator was shown otherwise;
the answer key (`questions`, `draft`, `result`, `response`) is None when the
step did not answer.

## Context

Nia wants every use of the Lore shell kept — what the model proposed, what she refused, what she changed — so a later Claude Code session can analyse the tool. This first brief lays the table and its writer only; nothing writes to it yet. The table is deliberately not a world's table (I1): it outlives the test worlds Nia deletes.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`)
are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: adds `LORE_USAGE_STEPS`, `LORE_USAGE_OUTCOMES` and the `LoreUsageEvent` model (C-01) to `models/pipeline.py` after `LoreEntryRow`, and exports it from `models/__init__.py`; creates `writes/lore_usage.py` (`MODEL_CALL_KEYS`, `PAYLOAD_KEYS`, `write_usage_event`, C-01/C-02); creates `scripts/migrate_v2_13_lore_usage.py` (on the `migrate_v2_11_lore_entry.py` template: refuses below v2.12, creates the table and its two indexes, post-checks zero rows, converges `schema_meta`); moves `schema_version.py`, the schema doc header and the changelog to v2.13 and documents the table after `lore_entry_row`; adds `LoreUsageEvent.payload` and `LoreUsageEvent.model_calls` to `json_ui_boundary.py`'s `JSON_COLUMN_ALLOWLIST` with their reason; creates `tooling/verify/checks/lore_usage.py` (U0-U4); appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): lore_usage_event, the Lore shell's usage journal (BRIEF-0103-a, schema v2.13)`.

````diff
diff --git a/scripts/migrate_v2_13_lore_usage.py b/scripts/migrate_v2_13_lore_usage.py
new file mode 100644
index 0000000..eb85ef9
--- /dev/null
+++ b/scripts/migrate_v2_13_lore_usage.py
@@ -0,0 +1,159 @@
+"""Migration v2.13 — `lore_usage_event`, the Lore shell's usage journal
+(TICKET-0103, BRIEF-0103-A, decisions A2 + B1 + C1 + D1 + F2 + I1).
+
+Creates `lore_usage_event` (`id, attempt_id, world_ref, world_name, kind,
+step, outcome, payload, model_calls, lore_entry_ref, created_at`, CHECKs
+`ck_lore_usage_event_step`, `ck_lore_usage_event_outcome`,
+`ck_lore_usage_event_entry`, indexes `idx_lore_usage_event_attempt` and
+`idx_lore_usage_event_world`). No `world_id` column and no FK to `world` or
+`lore_entry` (I1): the journal outlives a deleted world.
+
+Purely additive, zero rows created: the table starts empty and is filled
+only by the Lore shell's routes going forward. Nothing is backfilled.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.12 (the migrations are sequential).
+
+Idempotent: the table's existence is checked before creating it.
+
+Post-check, before commit: the table exists and holds zero rows.
+
+Run from the project root:
+
+    python scripts/migrate_v2_13_lore_usage.py
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
+        "migrate_v2_13_lore_usage.py refuses to run without WORLD_ENGINE_ENV "
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
+_PREVIOUS_VERSION = "v2.12"
+_TABLE = "lore_usage_event"
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
+            f"Migration v2.13 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _create_table() -> None:
+    with engine.begin() as conn:
+        conn.execute(text(
+            """
+CREATE TABLE lore_usage_event (
+  id              TEXT PRIMARY KEY NOT NULL,
+  attempt_id      TEXT NOT NULL,
+  world_ref       TEXT NOT NULL,
+  world_name      TEXT NOT NULL,
+  kind            TEXT NOT NULL,
+  step            TEXT NOT NULL,
+  outcome         TEXT NOT NULL,
+  payload         JSON NOT NULL,
+  model_calls     JSON NOT NULL DEFAULT '[]',
+  lore_entry_ref  TEXT,
+  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
+  CONSTRAINT ck_lore_usage_event_step CHECK (
+    (kind = 'write' AND step IN ('questions','draft','commit'))
+    OR (kind = 'consult' AND step IN ('ask','resolve'))),
+  CONSTRAINT ck_lore_usage_event_outcome CHECK (
+    outcome IN ('ok','unavailable','parse_error','refused')),
+  CONSTRAINT ck_lore_usage_event_entry CHECK (
+    (lore_entry_ref IS NOT NULL) = (step = 'commit' AND outcome = 'ok'))
+)
+"""
+        ))
+        conn.execute(text(
+            "CREATE INDEX idx_lore_usage_event_attempt ON lore_usage_event(attempt_id, created_at)"
+        ))
+        conn.execute(text(
+            "CREATE INDEX idx_lore_usage_event_world ON lore_usage_event(world_ref, created_at)"
+        ))
+
+
+def _apply_ddl() -> list[str]:
+    if _TABLE in set(inspect(engine).get_table_names()):
+        print(f"Table {_TABLE!r} already exists — nothing to do.")
+        return []
+    _create_table()
+    return [f"{_TABLE} table + idx_lore_usage_event_attempt + idx_lore_usage_event_world"]
+
+
+def _post_checks() -> None:
+    if _TABLE not in set(inspect(engine).get_table_names()):
+        raise SystemExit(f"Migration v2.13 aborted, post-check failed: {_TABLE} is missing.")
+    with engine.connect() as conn:
+        count = conn.execute(text(f"SELECT COUNT(*) FROM {_TABLE}")).scalar()
+    if count != 0:
+        raise SystemExit(
+            f"Migration v2.13 aborted, post-check failed: {_TABLE} holds {count} row(s), "
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
+    print("Migration v2.13 — lore_usage_event")
+    _refuse_if_behind()
+    applied = _apply_ddl()
+    if applied:
+        print("Applied: " + ", ".join(applied) + ".")
+    else:
+        print("Migration v2.13 already fully applied — zero writes.")
+    _post_checks()
+    _converge_schema_meta()
+    print("\nMigration v2.13 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index f9f7182..dfd8654 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -105,6 +105,7 @@ from .pipeline import (
     DayRewrite,
     LoreEntry,
     LoreEntryRow,
+    LoreUsageEvent,
     PassPlay,
     ProposedMutation,
     PromptTemplate,
@@ -151,6 +152,7 @@ __all__ = [
     "DayRewrite",
     "LoreEntry",
     "LoreEntryRow",
+    "LoreUsageEvent",
     "DayMentionResolution",
     "SkillResolution",
     "Gathering",
diff --git a/src/world_engine/models/pipeline.py b/src/world_engine/models/pipeline.py
index cfb3c3a..e844ade 100644
--- a/src/world_engine/models/pipeline.py
+++ b/src/world_engine/models/pipeline.py
@@ -361,6 +361,66 @@ class LoreEntryRow(SQLModel, table=True):
     action: str
 
 
+# -----------------------------------------------------------------------------
+# lore_usage_event  (the Lore shell's usage journal, schema v2.13, TICKET-0103,
+# BRIEF-0103-A, decisions A2 + B1 + C1 + D1 + F2 + I1)
+#
+# One row per step of a use of the Lore shell -- writing (questions, draft,
+# commit) or consultation (ask, resolve) -- grouped by `attempt_id`. `payload`
+# is what the step received and answered, as it was; `model_calls` is every
+# model exchange of the step (prompt version, rendered input, raw output).
+# Kept for an offline analysis of the tool (`scripts/export_lore_usage.py` is
+# its reader); nothing in the application reads it back.
+#
+# Not a world's table (I1): `world_ref` names the world it was recorded in,
+# without a FK, so the journal outlives a deleted world (F2) and stays out of
+# `delete_world_cascade` by construction -- there is no `world_id` column.
+# `lore_entry_ref` likewise names, without a FK, the `lore_entry` a successful
+# commit wrote. Append-only: no UPDATE, no DELETE. Non-canon.
+# -----------------------------------------------------------------------------
+LORE_USAGE_STEPS: dict[str, tuple[str, ...]] = {
+    "write": ("questions", "draft", "commit"),
+    "consult": ("ask", "resolve"),
+}
+LORE_USAGE_OUTCOMES: tuple[str, ...] = ("ok", "unavailable", "parse_error", "refused")
+
+
+class LoreUsageEvent(SQLModel, table=True):
+    __tablename__ = "lore_usage_event"
+    __table_args__ = (
+        Index("idx_lore_usage_event_attempt", "attempt_id", "created_at"),
+        Index("idx_lore_usage_event_world", "world_ref", "created_at"),
+        CheckConstraint(
+            "(kind = 'write' AND step IN ('questions','draft','commit')) "
+            "OR (kind = 'consult' AND step IN ('ask','resolve'))",
+            name="ck_lore_usage_event_step",
+        ),
+        CheckConstraint(
+            "outcome IN ('ok','unavailable','parse_error','refused')",
+            name="ck_lore_usage_event_outcome",
+        ),
+        CheckConstraint(
+            "(lore_entry_ref IS NOT NULL) = (step = 'commit' AND outcome = 'ok')",
+            name="ck_lore_usage_event_entry",
+        ),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    attempt_id: str
+    world_ref: str
+    world_name: str
+    kind: str
+    step: str
+    outcome: str
+    payload: Any = Field(sa_column=Column(JSON, nullable=False))
+    model_calls: Any = Field(
+        default_factory=list,
+        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
+    )
+    lore_entry_ref: Optional[str] = None
+    created_at: datetime = _created_ts()
+
+
 # -------------------------------------------------------------------------
 # skill_resolution  (one row per arbiter classification — the action
 # lexicon's audit trail; schema v2.02, TICKET-0084)
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index d68deab..c69cf2e 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.12"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.13"
diff --git a/src/world_engine/writes/lore_usage.py b/src/world_engine/writes/lore_usage.py
new file mode 100644
index 0000000..f2fdc4b
--- /dev/null
+++ b/src/world_engine/writes/lore_usage.py
@@ -0,0 +1,80 @@
+"""The Lore shell's usage journal writer (TICKET-0103, BRIEF-0103-A, C-01).
+
+`lore_usage_event` is non-canon and append-only: this module inserts, never
+updates or deletes, and nothing deletes the journal -- not even the world
+cascade (I1: the table carries no `world_id`). Nothing here commits; the
+caller owns the transaction. Every shape the schema CHECKs is asserted here
+first, so a malformed record fails as a `ValueError` naming the field
+rather than as an `IntegrityError` at flush.
+"""
+
+from __future__ import annotations
+
+from typing import Any, Optional
+
+from sqlmodel import Session
+
+from ..models import LoreUsageEvent
+from ..models.pipeline import LORE_USAGE_OUTCOMES, LORE_USAGE_STEPS
+
+MODEL_CALL_KEYS: frozenset[str] = frozenset({
+    "usage", "prompt_version_id", "prompt_version_number", "model",
+    "system_prompt", "user_message", "raw_output", "error",
+})
+# The payload of each step, by key (C-02). `error` is None on `ok` and the
+# message the creator was shown otherwise; the step's answer key is None
+# whenever the step did not answer.
+PAYLOAD_KEYS: dict[str, frozenset[str]] = {
+    "questions": frozenset({"statement", "questions", "error"}),
+    "draft": frozenset({"statement", "answers", "draft", "error"}),
+    "commit": frozenset({"proposal", "result", "error"}),
+    "ask": frozenset({"question", "response", "error"}),
+    "resolve": frozenset({"question", "plan", "bindings", "response", "error"}),
+}
+
+
+def _validate_model_call(call: Any) -> None:
+    if not isinstance(call, dict) or set(call) != MODEL_CALL_KEYS:
+        got = sorted(call) if isinstance(call, dict) else type(call).__name__
+        raise ValueError(f"lore_usage_event: a model call must carry exactly {sorted(MODEL_CALL_KEYS)}, got {got}")
+    if not isinstance(call["usage"], str) or not call["usage"]:
+        raise ValueError("lore_usage_event: a model call has no usage")
+
+
+def write_usage_event(
+    db: Session, *, attempt_id: str, world_ref: str, world_name: str, kind: str,
+    step: str, outcome: str, payload: dict, model_calls: list[dict],
+    lore_entry_ref: Optional[str] = None,
+) -> LoreUsageEvent:
+    """Insert one `lore_usage_event`. `ValueError` on any shape the schema
+    refuses: an empty id or world, a `(kind, step)` pair outside
+    `LORE_USAGE_STEPS`, an outcome outside `LORE_USAGE_OUTCOMES`, a payload
+    without exactly the step's `PAYLOAD_KEYS` or whose `error` disagrees with
+    the outcome, a model call without exactly `MODEL_CALL_KEYS`, or a
+    `lore_entry_ref` present anywhere but on a successful commit (and absent
+    there)."""
+    for name, value in (("attempt_id", attempt_id), ("world_ref", world_ref), ("world_name", world_name)):
+        if not isinstance(value, str) or not value.strip():
+            raise ValueError(f"lore_usage_event: {name} is empty")
+    if step not in LORE_USAGE_STEPS.get(kind, ()):
+        raise ValueError(f"lore_usage_event: step {step!r} is not a step of kind {kind!r}")
+    if outcome not in LORE_USAGE_OUTCOMES:
+        raise ValueError(f"lore_usage_event: unknown outcome {outcome!r}")
+    if not isinstance(payload, dict) or set(payload) != PAYLOAD_KEYS[step]:
+        got = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
+        raise ValueError(f"lore_usage_event: a {step} payload carries exactly {sorted(PAYLOAD_KEYS[step])}, got {got}")
+    if (payload["error"] is None) != (outcome == "ok"):
+        raise ValueError("lore_usage_event: payload error is set exactly when the outcome is not ok")
+    if not isinstance(model_calls, list):
+        raise ValueError("lore_usage_event: model_calls is not a list")
+    for call in model_calls:
+        _validate_model_call(call)
+    if (lore_entry_ref is not None) != (step == "commit" and outcome == "ok"):
+        raise ValueError("lore_usage_event: lore_entry_ref is set exactly on a successful commit")
+    event = LoreUsageEvent(
+        attempt_id=attempt_id, world_ref=world_ref, world_name=world_name, kind=kind,
+        step=step, outcome=outcome, payload=payload, model_calls=model_calls,
+        lore_entry_ref=lore_entry_ref,
+    )
+    db.add(event)
+    return event
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 5498a87..00a7837 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17610,6 +17610,29 @@ on a second 500 on an entity route that `registry_model_columns.py` would not
 have caught. C2, a repair script for the roles a failed create never posted:
 Nia re-enters them through the fiche.
 
+
+## THE LORE SHELL KEEPS A USAGE JOURNAL (TICKET-0103) -- IT OUTLIVES ITS WORLD (BRIEF-0103-a, schema v2.13)
+
+**A2, D1, F2, I1.** `lore_usage_event` records every step of a use of the Lore
+shell -- writing (`questions`, `draft`, `commit`) and consultation (`ask`,
+`resolve`) -- grouped by an `attempt_id`, with the step's payload as it was
+received and answered (fixed keys per step, `writes/lore_usage.PAYLOAD_KEYS`)
+and every model exchange (`MODEL_CALL_KEYS`). Nothing is diffed at write time:
+what the creator removed, changed or added is computed by the analysis, from
+the draft and the committed proposal of the same attempt. The table carries
+`world_ref` and `world_name`, never `world_id`, and no FK at all: it is a
+global journal tagged by world, not a world's table, so
+`delete_world_cascade` never reaches it and `world_cascade.py` W1 stays
+unexempted. `lore_usage.py` U0 keeps the journal named by its model and its
+writer only.
+
+**Rejected.** D2, a per-element verdict table written at commit: reactivates
+when a reader inside the application needs per-element verdicts. F1, the
+journal in the world cascade: Nia deletes test worlds, and their journal is
+the analysis material. I2, a `world_id` column exempted by name in W1:
+reactivates when a second table must outlive its world AND be read by the
+application itself.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/json_ui_boundary.py b/tooling/verify/checks/json_ui_boundary.py
index ab9b179..4d6639e 100644
--- a/tooling/verify/checks/json_ui_boundary.py
+++ b/tooling/verify/checks/json_ui_boundary.py
@@ -99,6 +99,13 @@ JSON_COLUMN_ALLOWLIST = {
     # the instant of the event, never rendered in any UI surface (same
     # posture as the change_history columns above).
     "EntityTypeHistory.definition_snapshot",
+    # The Lore shell's usage journal (TICKET-0103, BRIEF-0103-A, D1):
+    # what each step received and answered, and every model exchange, kept
+    # as they were for an offline analysis. Never rendered in any UI
+    # surface; its sole reader is scripts/export_lore_usage.py. The FIRST
+    # UI consumer must relationalize (the D2 reactivation condition).
+    "LoreUsageEvent.payload",
+    "LoreUsageEvent.model_calls",
 }
 
 
diff --git a/tooling/verify/checks/lore_usage.py b/tooling/verify/checks/lore_usage.py
new file mode 100644
index 0000000..3a11a1f
--- /dev/null
+++ b/tooling/verify/checks/lore_usage.py
@@ -0,0 +1,330 @@
+"""G1 check for TICKET-0103 -- the Lore shell's usage journal.
+
+The lot adds its modules brief by brief; this check grows with it (the
+`lore_write.py` precedent, TICKET-0098). Each brief adds its rules below in
+the same commit.
+
+U0 -- census. The files under `src/world_engine` that name the journal
+   (`LoreUsageEvent` or `lore_usage_event`) equal `_NAMING_FILES` exactly,
+   and the files that call `write_usage_event` equal `_WRITER_CALLERS`:
+   nothing in the application reads the journal, and one module writes it.
+U1 -- schema (BRIEF-0103-A, v2.13, I1). `lore_usage_event` has no
+   `world_id` column and no foreign key at all; `world_ref`, `world_name`,
+   `attempt_id`, `kind`, `step`, `outcome`, `payload`, `model_calls` are NOT
+   NULL; the CHECK `ck_lore_usage_event_step` lists exactly the pairs of
+   `LORE_USAGE_STEPS`, `ck_lore_usage_event_outcome` exactly
+   `LORE_USAGE_OUTCOMES`; the indexes are `idx_lore_usage_event_attempt
+   (attempt_id, created_at)` and `idx_lore_usage_event_world (world_ref,
+   created_at)`.
+U2 -- migration `scripts/migrate_v2_13_lore_usage.py`, on a v2.12-shaped
+   database (the current schema minus the table):
+   a. at v2.11 it refuses (non-zero exit) and creates nothing;
+   b. at v2.12 it creates the table, empty, with the columns, NOT NULLs and
+      CHECK names of the model, and moves `schema_meta` to the code constant;
+   c. a second run changes nothing and exits zero;
+   d. on the migrated table a row written by `write_usage_event` reads back
+      with its JSON intact, and a raw INSERT with outcome 'x' is refused by
+      the database.
+U3 -- writer (C-01, C-02). `_good()` is inserted once; every row of
+   `_REFUSALS` raises `ValueError` and inserts nothing.
+U4 -- the journal outlives its world (F2). A world tagged by a journal row
+   is deleted by `delete_world_cascade`; the journal row is still there,
+   with its `world_ref` and `world_name` unchanged.
+
+Fresh temp-file SQLite database for any fixture rule
+(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
+Nia's DB. A rule that collects zero items is a FAILURE.
+"""
+from __future__ import annotations
+
+import os
+import pathlib
+import re
+import sqlite3
+import subprocess
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+MIGRATION = ROOT / "scripts" / "migrate_v2_13_lore_usage.py"
+
+FAILURES: list[str] = []
+
+_NAMING_FILES: frozenset[str] = frozenset({
+    "models/pipeline.py", "models/__init__.py", "writes/lore_usage.py",
+})
+_WRITER_CALLERS: frozenset[str] = frozenset({"writes/lore_usage.py"})
+_NOT_NULL = ("attempt_id", "world_ref", "world_name", "kind", "step", "outcome",
+             "payload", "model_calls")
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _call(**over) -> dict:
+    call = {"usage": "lore_question_to_plan", "prompt_version_id": "pv-1",
+            "prompt_version_number": 1, "model": "llama3.1:8b", "system_prompt": "s",
+            "user_message": "u", "raw_output": "{}", "error": None}
+    call.update(over)
+    return call
+
+
+def _good(**over) -> dict:
+    record = {"attempt_id": "att-1", "world_ref": "w-1", "world_name": "Aestia",
+              "kind": "write", "step": "draft", "outcome": "ok",
+              "payload": {"statement": "s", "answers": None, "draft": {"facts": []}, "error": None},
+              "model_calls": [_call()], "lore_entry_ref": None}
+    record.update(over)
+    return record
+
+
+_COMMIT_OK = {"proposal": {}, "result": {"entry_id": "le-1"}, "error": None}
+
+_REFUSALS: tuple[tuple[str, dict], ...] = (
+    ("empty attempt", _good(attempt_id=" ")),
+    ("empty world", _good(world_ref="")),
+    ("empty world name", _good(world_name="")),
+    ("unknown kind", _good(kind="play")),
+    ("step of the other kind", _good(kind="consult", step="draft")),
+    ("unknown outcome", _good(outcome="x")),
+    ("payload not a dict", _good(payload=["s"])),
+    ("payload missing a key", _good(payload={"statement": "s", "draft": {}, "error": None})),
+    ("payload of another step", _good(payload={"question": "q", "response": None, "error": None})),
+    ("ok with an error", _good(payload={"statement": "s", "answers": None, "draft": None, "error": "x"})),
+    ("failure without an error", _good(outcome="unavailable")),
+    ("model_calls not a list", _good(model_calls={})),
+    ("model call missing a key", _good(model_calls=[{k: v for k, v in _call().items() if k != "error"}])),
+    ("model call with an extra key", _good(model_calls=[_call(extra=1)])),
+    ("model call without usage", _good(model_calls=[_call(usage="")])),
+    ("entry ref on a draft", _good(lore_entry_ref="le-1")),
+    ("ok commit without entry ref", _good(step="commit", payload=_COMMIT_OK)),
+    ("entry ref on a refused commit", _good(step="commit", outcome="refused", lore_entry_ref="le-1",
+                                            payload=dict(_COMMIT_OK, result=None, error="x"))),
+)
+
+
+def _naming(path: pathlib.Path) -> bool:
+    text = path.read_text(encoding="utf-8")
+    return "LoreUsageEvent" in text or "lore_usage_event" in text
+
+
+def check_u0() -> None:
+    files = sorted(SRC.rglob("*.py"))
+    if not files:
+        fail("U0: no source file collected")
+        return
+    named = {p.relative_to(SRC).as_posix() for p in files if _naming(p)}
+    for extra in sorted(named - _NAMING_FILES):
+        fail(f"U0: {extra} names the journal but is not in _NAMING_FILES")
+    for missing in sorted(_NAMING_FILES - named):
+        fail(f"U0: {missing} is in _NAMING_FILES but does not name the journal")
+    callers = {p.relative_to(SRC).as_posix() for p in files
+               if "write_usage_event" in p.read_text(encoding="utf-8")}
+    for extra in sorted(callers - _WRITER_CALLERS):
+        fail(f"U0: {extra} calls write_usage_event but is not in _WRITER_CALLERS")
+    for missing in sorted(_WRITER_CALLERS - callers):
+        fail(f"U0: {missing} is in _WRITER_CALLERS but never names write_usage_event")
+
+
+def _check_sql(table, name: str) -> str:
+    sql = next((str(c.sqltext) for c in table.constraints if getattr(c, "name", None) == name), None)
+    if sql is None:
+        fail(f"U1: lore_usage_event has no CHECK {name}")
+        return ""
+    return sql
+
+
+def check_u1() -> None:
+    from world_engine.models import LoreUsageEvent
+    from world_engine.models.pipeline import LORE_USAGE_OUTCOMES, LORE_USAGE_STEPS
+
+    table = LoreUsageEvent.__table__
+    if "world_id" in table.c:
+        fail("U1: lore_usage_event has a world_id column (I1: world_ref, never world_id)")
+    fks = [fk.target_fullname for c in table.c for fk in c.foreign_keys]
+    if fks:
+        fail(f"U1: lore_usage_event declares foreign keys {fks}")
+    for name in _NOT_NULL:
+        if name not in table.c or table.c[name].nullable:
+            fail(f"U1: lore_usage_event.{name} is missing or nullable")
+    step_sql = _check_sql(table, "ck_lore_usage_event_step")
+    pairs = {(kind, step) for kind, steps in re.findall(r"kind = '([a-z]+)' AND step IN \(([^)]*)\)", step_sql)
+             for step in re.findall(r"'([a-z_]+)'", steps)}
+    want = {(kind, step) for kind, steps in LORE_USAGE_STEPS.items() for step in steps}
+    if not pairs or pairs != want:
+        fail(f"U1: ck_lore_usage_event_step lists {sorted(pairs)}, expected {sorted(want)}")
+    outcomes = tuple(re.findall(r"'([a-z_]+)'", _check_sql(table, "ck_lore_usage_event_outcome")))
+    if outcomes != LORE_USAGE_OUTCOMES:
+        fail(f"U1: ck_lore_usage_event_outcome lists {outcomes}, expected {LORE_USAGE_OUTCOMES}")
+    _check_sql(table, "ck_lore_usage_event_entry")
+    indexes = {i.name: [c.name for c in i.columns] for i in table.indexes}
+    if indexes != {"idx_lore_usage_event_attempt": ["attempt_id", "created_at"],
+                   "idx_lore_usage_event_world": ["world_ref", "created_at"]}:
+        fail(f"U1: lore_usage_event indexes are {indexes}")
+
+
+def _run_migration(db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
+                          text=True, cwd=str(ROOT), timeout=120)
+
+
+def _shape(conn) -> list[tuple[str, int]]:
+    return [(r[1], r[3]) for r in conn.execute("PRAGMA table_info(lore_usage_event)")]
+
+
+def _set_version(db_path: str, version: str) -> None:
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("DROP TABLE IF EXISTS lore_usage_event")
+        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))
+
+
+def check_u2(db_path: str) -> None:
+    from sqlmodel import Session
+
+    from world_engine.db import create_db_and_tables, engine
+    from world_engine.models import SchemaMeta
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+    from world_engine.writes.lore_usage import write_usage_event
+
+    create_db_and_tables()
+    with Session(engine) as session:
+        if session.get(SchemaMeta, 1) is None:
+            session.add(SchemaMeta(id=1, static_version="v2.12"))
+            session.commit()
+    engine.dispose()
+    with sqlite3.connect(db_path) as conn:
+        model_shape = _shape(conn)
+        model_sql = conn.execute(
+            "SELECT sql FROM sqlite_master WHERE name = 'lore_usage_event'").fetchone()[0]
+    if not model_shape:
+        fail("U2: the model-created table has no column")
+        return
+    _set_version(db_path, "v2.11")
+    result = _run_migration(db_path)
+    with sqlite3.connect(db_path) as conn:
+        exists = conn.execute(
+            "SELECT 1 FROM sqlite_master WHERE name = 'lore_usage_event'").fetchone()
+    if result.returncode == 0 or exists:
+        fail(f"U2a: v2.11 was not refused (exit {result.returncode})")
+    _set_version(db_path, "v2.12")
+    result = _run_migration(db_path)
+    with sqlite3.connect(db_path) as conn:
+        version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0]
+        shape = _shape(conn)
+        sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'lore_usage_event'").fetchone()
+        count = conn.execute("SELECT COUNT(*) FROM lore_usage_event").fetchone()[0] if sql else None
+    checks = set(re.findall(r"CONSTRAINT (ck_[a-z_]+)", sql[0])) if sql else set()
+    want_checks = set(re.findall(r"CONSTRAINT (ck_[a-z_]+)", model_sql))
+    if (result.returncode != 0 or count != 0 or version != EXPECTED_STATIC_SCHEMA_VERSION
+            or shape != model_shape or not want_checks or checks != want_checks):
+        fail(f"U2b: exit {result.returncode}, count {count}, version {version!r}, "
+             f"shape {shape} vs {model_shape}, checks {sorted(checks)} vs {sorted(want_checks)}: "
+             f"{result.stderr.strip()[-200:]}")
+    again = _run_migration(db_path)
+    if again.returncode != 0 or "nothing to do" not in again.stdout:
+        fail(f"U2c: second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
+    with Session(engine) as session:
+        event = write_usage_event(session, **_good())
+        session.commit()
+        event_id = event.id
+    with Session(engine) as session:
+        from world_engine.models import LoreUsageEvent
+
+        back = session.get(LoreUsageEvent, event_id)
+        if back is None or back.payload != _good()["payload"] or back.model_calls != [_call()]:
+            fail("U2d: the migrated table does not read back a written row's JSON")
+    with sqlite3.connect(db_path) as conn:
+        try:
+            conn.execute(
+                "INSERT INTO lore_usage_event (id, attempt_id, world_ref, world_name, kind, step, "
+                "outcome, payload) VALUES ('x', 'a', 'w', 'n', 'write', 'draft', 'x', '{}')")
+            fail("U2d: the database accepted outcome 'x'")
+        except sqlite3.IntegrityError:
+            pass
+    engine.dispose()
+
+
+def _rows(session) -> int:
+    from sqlalchemy import text
+
+    return session.exec(text("SELECT COUNT(*) FROM lore_usage_event")).one()[0]
+
+
+def check_u3() -> None:
+    from sqlmodel import Session
+
+    from world_engine.db import engine
+    from world_engine.writes.lore_usage import write_usage_event
+
+    with Session(engine) as session:
+        before = _rows(session)
+        write_usage_event(session, **_good(attempt_id="att-u3"))
+        session.commit()
+        if _rows(session) != before + 1:
+            fail("U3: the good record was not inserted once")
+        for label, record in _REFUSALS:
+            try:
+                write_usage_event(session, **record)
+                fail(f"U3: {label!r} was accepted")
+            except ValueError:
+                pass
+            session.rollback()
+        if _rows(session) != before + 1:
+            fail("U3: a refused record left a row")
+
+
+def check_u4() -> None:
+    from sqlalchemy import text
+    from sqlmodel import Session
+
+    from world_engine.db import engine
+    from world_engine.models import LoreUsageEvent, World
+    from world_engine.writes import delete_world_cascade
+    from world_engine.writes.lore_usage import write_usage_event
+
+    with Session(engine) as session:
+        world = World(name="Doomed 0103")
+        session.add(world)
+        session.flush()
+        event = write_usage_event(session, **_good(attempt_id="att-u4", world_ref=world.id,
+                                                   world_name=world.name))
+        session.commit()
+        world_id, event_id = world.id, event.id
+    with Session(engine) as session:
+        delete_world_cascade(world_id, session)
+        session.commit()
+    with Session(engine) as session:
+        gone = session.exec(text("SELECT COUNT(*) FROM world WHERE id = :w").bindparams(w=world_id)).one()[0]
+        kept = session.get(LoreUsageEvent, event_id)
+        if gone != 0:
+            fail("U4: the doomed world was not deleted")
+        if kept is None or kept.world_ref != world_id or kept.world_name != "Doomed 0103":
+            fail("U4: the journal row did not outlive its world")
+
+
+def main() -> int:
+    tmp = tempfile.mkdtemp(prefix="lore_usage_")
+    db_path = f"{tmp}/u.db"
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+    check_u0()
+    check_u1()
+    check_u2(db_path)
+    check_u3()
+    check_u4()
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: lore_usage -- the journal is named by its model and its writer only; "
+          "v2.13 declares it without world_id or FK and migrates from v2.12 only; the "
+          "writer refuses every malformed record; a journal row outlives its world")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index fecefea..5125032 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,11 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.13** — TICKET-0103, BRIEF-0103-A: `lore_usage_event`, the Lore
+  shell's usage journal (one row per writing or consultation step, with its
+  payload and model exchanges, grouped by `attempt_id`). No `world_id` and no
+  FK (I1): it outlives a deleted world. `migrate_v2_13_lore_usage.py` creates
+  it empty and refuses a database older than v2.12.
 - **v2.12** — TICKET-0101, BRIEF-0101-D: `borde`, the geographic link that
   touches a zone. `idx_relation_oriented_social` is rebuilt with the
   predicate `type NOT IN ('connects_to','borde','controls')`;
diff --git a/world-engine-schema.md b/world-engine-schema.md
index 919a408..2d4c020 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.12
+Current schema version: v2.13
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -1198,6 +1198,53 @@ CREATE UNIQUE INDEX idx_lore_entry_row_entry
 
 -----
 
+### `lore_usage_event`
+
+The Lore shell's usage journal (schema v2.13, TICKET-0103, BRIEF-0103-A,
+decisions A2 + B1 + C1 + D1 + F2 + I1): one row per step of a use of the Lore
+shell — writing (`questions`, `draft`, `commit`) or consultation (`ask`,
+`resolve`) — grouped by `attempt_id`, the id the panel holds for one use.
+`payload` is what the step received and answered, as it was; `model_calls`
+is every model exchange of the step (prompt version, model, rendered system
+prompt and user message, raw output, error). `outcome` is `ok`, `unavailable`
+(Ollama down), `parse_error` (the model's reply did not parse) or `refused`
+(the request was refused after it reached the model or the apply step).
+Kept for an offline analysis of the tool: its sole reader is
+`scripts/export_lore_usage.py`; nothing in the application reads it back.
+
+Not a world's table (I1): `world_ref` and `world_name` record the world the
+step ran in, without a FK, so the journal outlives a deleted world and stays
+out of `delete_world_cascade` by construction. `lore_entry_ref` names, without
+a FK, the `lore_entry` a successful commit wrote — set on exactly that step.
+Append-only: no UPDATE, no DELETE. Non-canon.
+
+```sql
+CREATE TABLE lore_usage_event (
+  id              TEXT PRIMARY KEY NOT NULL,
+  attempt_id      TEXT NOT NULL,
+  world_ref       TEXT NOT NULL,
+  world_name      TEXT NOT NULL,
+  kind            TEXT NOT NULL,
+  step            TEXT NOT NULL,
+  outcome         TEXT NOT NULL,
+  payload         JSON NOT NULL,
+  model_calls     JSON NOT NULL DEFAULT '[]',
+  lore_entry_ref  TEXT,
+  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
+  CONSTRAINT ck_lore_usage_event_step CHECK (
+    (kind = 'write' AND step IN ('questions','draft','commit'))
+    OR (kind = 'consult' AND step IN ('ask','resolve'))),
+  CONSTRAINT ck_lore_usage_event_outcome CHECK (
+    outcome IN ('ok','unavailable','parse_error','refused')),
+  CONSTRAINT ck_lore_usage_event_entry CHECK (
+    (lore_entry_ref IS NOT NULL) = (step = 'commit' AND outcome = 'ok'))
+);
+CREATE INDEX idx_lore_usage_event_attempt ON lore_usage_event(attempt_id, created_at);
+CREATE INDEX idx_lore_usage_event_world ON lore_usage_event(world_ref, created_at);
+```
+
+-----
+
 ### `skill_resolution`
 
 ```sql
````

## Scope OUT

- Running `migrate_v2_13_lore_usage.py` on Nia's database (live gate, after `scripts/backup.py`).
- Any `world_id` column or FK on the journal, and any edit to `world_cascade.py` or `writes/worlds.py` (I1: the journal is out of the cascade by construction, not by exemption).
- Backfilling the journal from existing `lore_entry` rows.
- Retention or pruning of the journal (carried forward in the ticket).
- Anything that writes to the journal: capture (B), routes (C), panels (D), export (E).
- Every later brief of the lot: BRIEF-0103-B, C, D, E.

## Invariants to defend

**History is sacred:** the journal is append-only; the writer only inserts, and no delete path names the table (`single_canon_write.py`'s hard-delete list is untouched). **The app refuses to boot on a schema mismatch:** constant, schema header and newest changelog entry move together to v2.13. **UI-visible data never lives in JSON:** the two JSON columns are allow-listed as never rendered; their first UI consumer must relationalize. The cascade's W1 must still pass without being edited.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- `world_cascade.py` W1 or W4 fails after the commit (the journal must not be world-reaching).
- The full corpus is not green after the commit, for a reason the diff does not explain.
- The changelog's newest entry is no longer v2.12: another migration landed and v2.13 is no longer free.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- Any Starlette/httpx deprecation warning printed by a check.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `python tooling/verify/checks/lore_usage.py` → `PASS: lore_usage -- the journal is named by its model and its writer only; v2.13 declares it without world_id or FK and migrates from v2.12 only; the writer refuses every malformed record; a journal row outlives its world`.
- `world_cascade.py`, `json_ui_boundary.py`, `schema_version_agreement.py`, `schema_partition.py`, `decisions_index.py`, `single_canon_write.py`, `env_guard.py` → `PASS`.
- Mutation test: in `writes/lore_usage.py`, delete the two lines of the `lore_entry_ref` guard; U3 fails on three rows (`entry ref on a draft`, `ok commit without entry ref`, `entry ref on a refused commit`); revert.
- Mutation test: in `models/pipeline.py`, drop `'refused'` from `ck_lore_usage_event_outcome`; U1 fails; revert.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 137/137.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

This step is the doc update for the schema: `world-engine-schema.md` (header v2.13, `lore_usage_event` section), `world-engine-schema-changelog.md` (v2.13 entry), decision entry `THE LORE SHELL KEEPS A USAGE JOURNAL (TICKET-0103) -- IT OUTLIVES ITS WORLD (BRIEF-0103-a, schema v2.13)` — all in the diff. CLAUDE.md is untouched here (its invariant arrives with the reader, E).
