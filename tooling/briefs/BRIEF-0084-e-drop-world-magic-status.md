# BRIEF — Step "Remove world.magic_status"

## Context

`world.magic_status` was designed as a world-scale magical era
(`dormant | awakening | active | suppressed`) and was never wired to anything:
no reader, no creator form, no update route, and one writer in the whole repo —
`scripts/seed_pilot.py`. Its two siblings were already dealt with:
`location.magic_status` was unplugged from every prompt surface by decision D3,
and `faction.magic_knowledge_level` is named as `fact_default`'s direct
ancestor. With `skill_system` now answering "does magic exist here" by row
presence, keeping a world-level magic column would offer a second answer to the
same question — the exact ambiguity `skill_system` was introduced to remove.
This step removes it. Separate brief, separate migration, separate commit,
because it is the only destructive act in the ticket.

## Mini-RECON (executor, before any edit)

Four briefs have landed since this was written. Run this and **report before
editing**. STOP and report on any finding that contradicts the premise — in
particular, if ANY reader of `world.magic_status` has appeared, this step does
not proceed.

1. Grep the whole repo (excluding `node_modules`) for `magic_status` and
   classify each hit: is it `world.magic_status` or `location.magic_status`?
   Report the classification per hit. The expected world hits are the model
   field, the schema doc `CREATE TABLE world` block, and `seed_pilot.py`; any
   other world hit is new information.
2. Specifically resolve the comment at
   `frontend/src/creation/generatePanel.svelte.js` that mentions `magic_status`
   — report whether it refers to the location field or the world field. Do not
   assume.
3. Confirm there is still no reader: no assembler, no guard, no prompt, no
   endpoint, no Svelte component reads `world.magic_status`. Report the method
   you used to establish it, not just the conclusion.
4. Report the current schema version after BRIEF-0084-c (expected v2.02) so
   this step's version is version+1.
5. Report the SQLite version the project runs against and whether prior
   drop-column migrations in `scripts/` used `ALTER TABLE ... DROP COLUMN` or a
   table rebuild. Copy whichever technique
   `migrate_v1_40_drop_character_faction_id.py` uses; do not choose a new one.
6. Report the current value of `magic_status` on every row of the `world` table
   in the dev DB, and paste it into your report. It is the only data this
   ticket destroys and it should be visible in the record.

## Scope IN

1. **Remove the field from `src/world_engine/models/canon.py`** — the
   `magic_status` declaration on `class World` only. `Location.magic_status` is
   NOT touched, in any way, in this step.

2. **`scripts/migrate_v2_03_drop_world_magic_status.py`**, using the technique
   reported by mini-RECON step 5 and the fail-closed env preamble every
   migration in `scripts/` carries (refuse without `WORLD_ENGINE_ENV` or
   `WORLD_ENGINE_DATABASE_URL`, exit 1, message naming the script):

   - **Before dropping**, print the full contents of `world.id`,
     `world.name`, `world.magic_status` for every row, so the destroyed values
     are in the run log.
   - Drop the column.
   - **Idempotent**: if the column is already absent, report that and exit 0.
   - Post-checks before commit: the `world` table's row count is identical
     before and after; `world.id`, `name`, `is_active`, `current_phase` values
     are identical before and after (checksum the remaining columns); the
     column is gone.

3. **`scripts/seed_pilot.py`** — remove the `magic_status="awakening"` argument
   from the pilot world construction. Nothing replaces it: the pilot world does
   not get a seeded `skill_system` row either (that stayed out of BRIEF-0084-a
   and stays out here).

4. **`tooling/verify/checks/no_world_magic_status.py`** — a G1 check that fails
   if `magic_status` appears anywhere in a `world`-table context: on the
   `World` model, in the `CREATE TABLE world` block of
   `world-engine-schema.md`, or in any construction of `World(...)` under
   `src/` or `scripts/`. It must NOT fire on `location.magic_status`, which
   remains legitimate — the check needs to discriminate, and a check that
   cannot discriminate is worse than no check. Vacuous pass is a FAIL.

## Scope OUT

- **`location.magic_status`.** Not removed, not deprecated, not commented on.
  It has a documented posture (unplugged from prompts by D3, stored shape
  kept) and this step does not revisit it.
- **`faction.magic_knowledge_level`.** It still has a reader
  (`tick_context.py`) and a named reactivation path into `fact_default` owned
  by TICKET-0082. Not touched.
- **The `magic` entity type, `event.has_magic_impact`,
  `entity_profile.magic_link`, or any subculture key.** Out of scope entirely.
- **Replacing the column with anything** — no `skill_system.status`, no
  `skill_system.intensity`, no world-level narrative field. If Nia wants
  magical era back, it returns as a property of the system row in a future
  ticket, and that is written down in the docs rather than built here.
- **Seeding a magic system on the pilot world** to compensate.
- **Any change to the four earlier briefs' work.**

## Invariants to defend

- **"History is sacred."** This is the one step of the ticket that destroys
  data, which is why the migration prints the values before dropping and
  checksums every remaining column. No `world` row may be lost or altered.
  If the checksum differs, the migration must abort before commit, not repair.
- **"Commit before touching canon-write paths."** `world` is a canon table.
  The working tree must be clean before this migration runs.
- **"Schema is authoritative."** Model, schema doc, and DB agree after this
  step, and the new check enforces the schema-doc half.
- **B3.** After this step there is exactly one answer to "does magic exist in
  this world": the presence of a `skill_system` row. The
  ARCHITECTURE_DECISIONS entry below is the guard that keeps a future executor
  from inventing a second one.

## Done means

- [ ] The mini-RECON report is posted and shows zero readers of
      `world.magic_status`, and step 6's values are pasted in it.
- [ ] `git status` clean before running the migration.
- [ ] `python scripts/migrate_v2_03_drop_world_magic_status.py` prints every
      world's prior `magic_status` value, drops the column, and passes its
      post-checks.
- [ ] Re-running it reports the column already absent and exits 0.
- [ ] `sqlite3 <db> ".schema world"` no longer lists `magic_status`, and still
      lists `id`, `name`, `description`, `is_active`, `current_phase`,
      `created_at`, `updated_at`.
- [ ] `sqlite3 <db> "SELECT COUNT(*) FROM world"` unchanged from before.
- [ ] `python -m tooling.verify.checks.no_world_magic_status` returns PASS, and
      returns PASS on a repo where `location.magic_status` is present (it must
      not fire on the location field).
- [ ] The pilot world loads in the cockpit, one Play turn resolves, and one day
      pass completes — the full chain runs with the column gone.
- [ ] A fresh `seed_pilot.py` run against an empty DB succeeds.
- [ ] `pytest`, `no_print_in_src.py`, `undefined_names.py`, `import_cycle.py`
      green.
- [ ] `/review-step` and `/close-step` both run.
- [ ] One commit, containing the model change, the migration, the seed change,
      the check, and the docs — nothing else.

## Docs to update

- `world-engine-schema-changelog.md` — new entry **v2.03**, TICKET-0084,
  BRIEF-0084-e: the column dropped, the migration filename, its idempotence,
  the fact that it is the ticket's only destructive step, and the values it
  destroyed as reported by mini-RECON step 6.
- `world-engine-schema.md` — bump to v2.03; remove the `magic_status` line and
  its `-- dormant | awakening | active | suppressed` comment from the
  `CREATE TABLE world` block. Leave `location.magic_status` untouched.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — this exact paragraph:

  ```
  **`world.magic_status` was removed in schema v2.03 (TICKET-0084,
  BRIEF-0084-e).** It had no reader, no creator surface, and one writer
  (`scripts/seed_pilot.py`), so every world created through the cockpit
  carried the schema default `'dormant'` as an accident rather than a
  statement about that world. Its two siblings had already been dealt with:
  `location.magic_status` was unplugged from every prompt surface by D3, and
  `faction.magic_knowledge_level` is named as `fact_default`'s direct
  ancestor. Keeping a world-level magic column beside `skill_system` would
  have offered two answers to "does magic exist here" — the exact ambiguity
  `skill_system` exists to remove. Magic's existence is the presence of a
  `skill_system` row, and nothing else. Magic's narrative intensity, if it is
  ever wanted again, returns as a property of that row, never of the world.
  ```

- `CLAUDE.md` — remove any mention of `world.magic_status` if one exists (the
  mini-RECON will have found it), and add nothing in its place.
