# BRIEF — Step "Retire schema_0024's stale prerequisites check, add schema_0025"

## Context
`tooling/verify/checks/schema_0024.py`'s `check_prerequisites_column()` asserts
`npc_goal.prerequisites` is a nullable JSON column — an invariant
TICKET-0025/BRIEF-0025-c deliberately replaced with a relational
`goal_prerequisite` table (`canon.py:636-651`), documented in the comment
directly above the `GoalPrerequisite` class. No `schema_0025.py` was ever
written, so nothing today gates the new table's shape (`prereq_judge.py`
covers only the `goal_change complete` judge's *behavior*, not the schema).

## Scope IN
1. In `tooling/verify/checks/schema_0024.py`: delete
   `check_prerequisites_column()` and its call in `main()`. Drop the
   `BRIEF-0024-a` bullet from the module docstring. Drop the
   `"npc_goal.prerequisites present; "` fragment from the final `PASS`
   message.
2. Create `tooling/verify/checks/schema_0025.py` (new file), following
   `schema_0024.py`'s established shape (temp-file SQLite bootstrap via
   `WORLD_ENGINE_DATABASE_URL`, `sys.modules` purge, a `_fresh_engine()`-style
   helper). It must assert, against a fresh DB:
   - `goal_prerequisite` table exists with columns `id, world_id, goal_id,
     type, target_entity_id, threshold`.
   - The CHECK constraint named `ck_goal_prerequisite_type` exists and its
     DDL text (read via `SELECT sql FROM sqlite_master WHERE type='table' AND
     name='goal_prerequisite'`, same idiom `schema_0024.py`'s faction check
     already uses for its index DDL) contains the literal string
     `relation_gte`. This is the K1 closed-vocabulary guard — a
     column-presence check alone would still pass if the CHECK itself were
     dropped, which is the exact vacuous-pass failure mode this brief exists
     to avoid.
   - The CHECK constraint named `ck_goal_prerequisite_threshold` exists and
     its DDL text contains the `1` / `100` bound literals.
   - `idx_goal_prerequisite_unique` exists as a UNIQUE index on exactly
     `(goal_id, type, target_entity_id)`.
3. Add a short comment directly above the `type` DDL assertion noting that a
   future migration adding a second prerequisite type will require updating
   this check's expected string — naming the check's own future-staleness
   risk explicitly rather than leaving it implicit.

## Scope OUT
- No migration, no DDL change, no product code change — `goal_prerequisite`'s
  actual shape is asserted, not touched.
- Do not touch `check_faction_role_schema` or `check_no_metadata_roles_usage`
  in `schema_0024.py`.
- Do not touch `prereq_judge.py` — different concern (behavior, not schema),
  already correct.
- Do not verify FK declarations (`goal_id -> npc_goal.id`,
  `target_entity_id -> entity.id`) — SQLite does not enforce these by default
  and no existing schema check in this repo asserts FK declarations; out of
  scope here.
- Do not wire `schema_0025.py` into any ticket's machine-checkable section
  other than TICKET-0043 at this stage.

## Invariants to defend
- **Fail-closed checks over advisory rules / vacuous-proof prevention:** the
  new check must fail if the CHECK constraints are absent, not merely if the
  columns are — this is the entire point of this brief, not an incidental
  detail.
- **Closed vocabulary (K1):** `goal_prerequisite.type` accepts only
  `relation_gte` in v1; extension is a new enum value in a migration, never a
  free string — this check is that invariant's sole schema-level guard.

## Done means
- [ ] `python tooling/verify/checks/schema_0024.py` exits 0 and its output no
      longer mentions `prerequisites` anywhere.
- [ ] `python tooling/verify/checks/schema_0025.py` exits 0 on current `main`.
- [ ] Manually confirm, then revert before commit: removing the
      `ck_goal_prerequisite_type` CHECK constraint from a scratch copy of
      `canon.py` causes `schema_0025.py` to fail — proving the DDL-text
      assertion actually fires.
- [ ] `/review-step` run on this brief's diff is clean (touches
      `schema_0024.py`, adds `schema_0025.py` only).

## Docs to update
- This step IS the doc update for the check itself. No
  `ARCHITECTURE_DECISIONS.md` entry needed — no design decision changes, only
  verify-tooling catching up to an already-decided-and-shipped schema
  (BRIEF-0025-c).
