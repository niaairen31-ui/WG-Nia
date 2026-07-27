# BRIEF-0050-a — Step "conversation_window_config table + reader"

## Context

TICKET-0050 makes the NPC dialogue context window governed and creator-tunable. This first step
lays the persisted, relational config that every later step reads: word budget, verbatim-turn
count, and a summary kill-switch — one row per world. Decision I2 (configurable now), L1 (dedicated
narrow table), M1 (`summary_enabled` default TRUE). No prompt-assembly change lands here; this step
is pure infrastructure with its reader declared for briefs (b) and (d).

## Scope IN

1. **New model class `ConversationWindowConfig`** in a NEW module
   `src/world_engine/models/config.py` (NOT `canon.py` — it sits at 974/1000 lines,
   `tooling/verify/checks/module_budget.py:31-32`). Columns:
   - `id: str` PK (uuid, same `_uuid` default factory pattern as sibling models).
   - `world_id: str` FK -> `world.id`, `nullable=False`, with a UNIQUE index
     (`idx_conversation_window_config_world`, unique) — one row per world.
   - `word_budget: int`, `server_default=text("1200")`.
   - `verbatim_turns: int`, `server_default=text("6")` — counted in player/npc MESSAGE rows
     (6 rows = 3 exchanges; mirrors the existing `history_only[-6:]` slice at
     `cockpit/play.py:198`).
   - `summary_enabled: bool`, `server_default=text("1")` (M1).
   - `updated_at: datetime` via the module's `_created_ts()` pattern.
   Re-export `ConversationWindowConfig` from `src/world_engine/models/__init__.py` so it is a
   registered static model table (required by the boot guard
   `schema_reconcile.unaccounted_tables`, CLAUDE.md:328).

2. **Migration** `scripts/migrate_v1_XX_conversation_window_config.py` (Claude Code assigns the
   version, owns the number). Creates the table with the exact columns/defaults above and the
   unique index. Idempotent (guarded create, same shape as recent migrations e.g.
   `scripts/migrate_v1_87_entity_type.py`). Bump the static schema version + `schema_version.py`
   expected value per the standing migration procedure. Do NOT back-fill any rows — absence is
   handled by the reader default (item 4).

3. **Curated-config write chokepoint** `upsert_conversation_window_config(...)` in
   `src/world_engine/writes/config.py`, modelled on `upsert_location_type`
   (`writes/config.py:339`) — an UPSERT-ONE (never a `DELETE FROM ... `full-replace; there is one
   row per world). Signature:
   `upsert_conversation_window_config(db, *, world_id, word_budget=None, verbatim_turns=None,
   summary_enabled=None) -> ConversationWindowConfig`. Semantics: fetch-or-create the world's row;
   apply only the non-None fields (partial update); set `updated_at`; add + return (caller
   commits, same transaction discipline as the sibling writers). No `change_history` — metadata-
   config category (CLAUDE.md:276). Reject `word_budget <= 0` and `verbatim_turns <= 0` fail-closed
   (ValueError) before the write.

4. **Reader** `load_conversation_window_config(world_id, db) -> ConversationWindowConfig | a
   defaults object` in the NEW module `src/world_engine/conversation_window.py` (created here so
   later briefs extend it; G1). If no row exists, return an in-memory defaults object carrying
   `word_budget=1200, verbatim_turns=6, summary_enabled=True` (do NOT insert a row on read —
   reads never write). Expose the three defaults as module constants
   `DEFAULT_WORD_BUDGET = 1200`, `DEFAULT_VERBATIM_TURNS = 6`, `DEFAULT_SUMMARY_ENABLED = True`
   so the migration server-defaults and the reader defaults have a single source of truth in
   comments cross-referencing each other.

5. **Policy registration.** Add `conversation_window_config` to `[CANON_TABLES]` in
   `tooling/verify/canon_write_policy.txt`, and register the writer site in `[ALLOWED_SITES]`
   (the `upsert_conversation_window_config` call site), so `single_canon_write.py:425` passes.
   Mini-RECON before editing: open `tooling/verify/canon_write_policy.txt`, copy the exact
   `[ALLOWED_SITES]` line format used by `upsert_location_type` (site key -> table), and mirror it.

6. **Verify check** `tooling/verify/checks/conversation_window_config.py` using the standard idiom
   (FAILURES list, `_report_and_exit`, ROOT via `parents[3]`, vacuous-proof guard — zero-result is
   a failure). Assert against `sqlite_master` DDL text (not column-presence-only): table exists,
   the four data columns exist, `summary_enabled` carries a default of `1`, `word_budget` default
   `1200`, `verbatim_turns` default `6`, and the unique index on `world_id` exists.

## Scope OUT

- No change to `cockpit/play.py`, `_say_npc_generation`, or the message-list shape — that is
  brief (b).
- No `conversation_summary` prompt usage, registry entry, or seed — that is brief (c).
- No trigger wiring, no word counting against live history, no summarization call — that is
  brief (d).
- No creator UI / route to edit the config — that is brief (e). This step ships the write
  chokepoint and reader ONLY; the sole caller of `upsert_conversation_window_config` in this brief
  is the verify/seed path, not a live route.
- Do NOT make `verbatim_turns` mean "exchanges". It is message rows. Do not "helpfully" double it.
- Do NOT add the table to `canon.py`. Do NOT give it a `change_history` companion table.
- Do NOT insert a config row during `load_...` (read-writes are forbidden here).

## Invariants to defend

- **json_ui_boundary** (CLAUDE.md:327): config is creator-visible -> typed relational columns,
  never a JSON blob. This step's whole point is to keep it relational.
- **single canon-write** (CLAUDE.md:276, `single_canon_write.py`): the new table is governed
  curated-config; its only writer is the registered chokepoint. Registration in the policy file is
  mandatory or the check fails.
- **schema boot guard** (CLAUDE.md:328): the table must be a static model table (re-exported from
  `models/__init__.py`) or the app refuses to boot.
- **no structure without a reader**: the reader (`load_conversation_window_config`) ships in the
  same brief; its consumers are briefs (b)/(d), named in Scope OUT.
- **module budget**: `models/config.py` and `conversation_window.py` are new and small; `canon.py`
  is untouched.

## Done means

- [ ] `python scripts/migrate_v1_XX_conversation_window_config.py` on a copy of the dev DB creates
      `conversation_window_config` with the stated columns, defaults, and unique index (verified by
      `.schema conversation_window_config` in sqlite3).
- [ ] App boots (no `unaccounted_tables` failure) with the new table present.
- [ ] `load_conversation_window_config(world_id, db)` on a world with no row returns
      `word_budget=1200, verbatim_turns=6, summary_enabled=True` and inserts nothing (row count
      stays 0).
- [ ] `upsert_conversation_window_config(db, world_id=W, word_budget=800)` creates the row with
      `word_budget=800` and the other two at their server defaults; a second call with
      `verbatim_turns=4` updates only that field.
- [ ] `upsert_conversation_window_config(..., word_budget=0)` raises before writing.
- [ ] `python tooling/verify/checks/conversation_window_config.py` PASSES; on a DB missing the
      table it FAILS (vacuous-proof).
- [ ] `python tooling/verify/checks/single_canon_write.py` PASSES with the new writer/table
      registered.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- Schema changelog: new entry `vX.YY — conversation_window_config (TICKET-0050, BRIEF-0050-a)`,
  metadata-config category, no change_history, one row per world.
- `world-engine-schema.md`: add the table to the metadata-config section.
- `ARCHITECTURE_DECISIONS.md`: record decisions L1 (dedicated table), M1 (`summary_enabled`
  default TRUE), and named deferral **D-0050** (config editing migrates from the prompts surface
  to a future world-configuration surface — see brief e).
