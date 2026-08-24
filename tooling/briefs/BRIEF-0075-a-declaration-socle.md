# BRIEF — Step "Declaration socle"

## Context

TICKET-0075 opens the day-resolution chain. This first step is PLUMBING ONLY:
a player can declare a day, the declaration is stored, listed and read back.
Nothing resolves, and no model is called anywhere in this brief.

Two things motivate doing it alone. First, `Batch` and `PassPlay` have been
declared since the pipeline package split and have never had a reader — a
standing "no structure without a reader" violation this step clears. Second,
decision L1 makes the day the batch's ordinal, and decision U1 makes that
ordinal an explicit column; that migration must land before anything reasons
about "tomorrow".

Resolution, plan emission, concordance and narration are all later briefs.

## Mini-RECON

Measured against `main` on 2026-08-24, schema v1.92. Re-measure before
executing; every anchor below is a STOP condition if it does not hold.

- **[M1]** `Batch` — `src/world_engine/models/pipeline.py:30`. Fields: `id`,
  `session_id` (FK `session.id`, NOT NULL), `status` (default `'pending'`),
  `local_summary`, `message_to_claude`, `claude_raw_response`, `final_result`,
  `creator_notes`, `created_at`, `processed_at`, `applied_at`. **No ordinal
  column, no `__table_args__`, no uniqueness of any kind.**
- **[M2]** `PassPlay` — `pipeline.py:52`. `__table_args__` =
  `(Index("idx_passplay_batch", "batch_id"),)`. Fields: `id`, `batch_id`,
  `session_id`, `character_id` (FK `entity.id`), `declared_action: str`,
  `injected_context` (JSON, nullable), `creator_notes`, `status` (default
  `'submitted'`), `batch_order` (nullable int), `history` (JSON NOT NULL,
  server default `'[]'`), `submitted_at`, `applied_at`.
- **[M3]** Readers of both, exhaustively: `models/__init__.py:92-93` and
  `:130-131` (re-export only), and `tooling/verify/checks/json_ui_boundary.py:56-57`
  (names `PassPlay.injected_context` and `PassPlay.history` as JSON columns
  that must not cross the UI boundary). No other module in `src/` imports
  either class.
- **[M4]** `Session` — `models/ephemeral.py:25`. `world_id`, `number: int`,
  `title`, `started_at`, `ended_at`, `status` (default `'open'`), `summary`,
  `creator_notes`.
- **[M5]** Open-session idiom — `cockpit/play.py:735-756`: select the
  highest-numbered `status == "open"` session for the world, else allocate
  `max(number) + 1` and insert with `title="Live play session"`.
- **[M6]** `Character` — `models/canon.py:147`. `character_type` is
  `player | npc`; partial unique index `idx_character_one_pc_per_user_world`
  on `(world_id, user_id)` where `character_type = 'player'`
  (`canon.py:156-159`). `user_id` is nullable with no FK.
- **[M7]** `EXPECTED_STATIC_SCHEMA_VERSION = "v1.92"` —
  `src/world_engine/schema_version.py`. Bumped in the SAME commit as the
  `schema_meta` singleton and the `world-engine-schema.md` header.
- **[M8]** Migration precedent for ADD COLUMN on an existing table —
  `scripts/migrate_v1_91_npc_goal_kind.py`. Fail-closed on
  `WORLD_ENGINE_ENV` / `WORLD_ENGINE_DATABASE_URL` before any import of
  `world_engine.db`; idempotent.
- **[M9]** Shell routes are mirrored in two places that a check compares:
  `frontend/src/lib/router.js:10` (`SHELL_ROUTES`) and
  `src/world_engine/cockpit/app.py:284` (`_SHELL_ROUTES`), currently
  `("/", "/play", "/creation", "/creation/{sub_tab}", "/observation")`.
  `verify/checks/legacy_mount.py` asserts they agree.
- **[M10]** Shell-native surface pattern — `frontend/src/observation/`
  (`Observation.svelte` + `observation.svelte.js`). The component is ALWAYS
  mounted from `App.svelte`; a single `let { active = false } = $props();`
  toggles its own root's visibility. No legacy bridge call.
- **[M11]** Router registration — `cockpit/app.py:115-126`, one
  `include_router` per route module.
- **[M12]** Verify check idiom — `ROOT = pathlib.Path(__file__).resolve().parents[3]`,
  module-level `FAILURES: list[str]`, a `fail()` appender, and a
  print-all-then-`sys.exit(1)` tail. Precedent:
  `tooling/verify/checks/npc_schedule.py`.

**STOP conditions.** Escalate rather than proceed if any of these holds:

- S1. `Batch` already carries an ordinal, sequence or uniqueness constraint.
- S2. Any importer of `Batch` or `PassPlay` exists in `src/` beyond the M3
  enumeration. This enumeration is the brief's load-bearing claim; do not
  assume it, re-run it.
- S3. The target DB holds more than one `character_type = 'player'` row for
  the active world, or none.
- S4. `SHELL_ROUTES` and `_SHELL_ROUTES` already disagree.
- S5. `batch` is non-empty in the target DB (the backfill branch in item 1
  is written but never exercised in this project's state; if it must run,
  stop and confirm).

## Scope IN

### 1. Migration — the day ordinal (U1)

New `scripts/migrate_vX_YY_batch_day_number.py`, following the M8 precedent.

- Add `Batch.day_number` — `INTEGER NOT NULL`. SQLite requires a default on
  `ADD COLUMN ... NOT NULL`; use `DEFAULT 0`, then, in the same script,
  assign real values and create the unique index (a row that kept `0`
  alongside another `0` in the same session would collide, which is the
  point).
- Add unique index `idx_batch_session_day` on `(session_id, day_number)`.
- Backfill branch, executed only if `batch` is non-empty: per `session_id`,
  order by `created_at` ascending and assign `1..n`. Under S5 this branch is
  expected to be dead; write it anyway, and print the row count it touched.
- Idempotent: safe to re-run.
- Model change in `models/pipeline.py`: add the field and give `Batch` a
  `__table_args__` carrying the unique index, so a fresh `create_all` and
  this migration produce identical DDL.
- Bump `EXPECTED_STATIC_SCHEMA_VERSION`, the `schema_meta` singleton and the
  `world-engine-schema.md` header line, in this same commit.

### 2. Write path — `src/world_engine/writes/pipeline.py` (new)

Registered in `writes/__init__.py` alongside the existing write modules.

- `write_batch(db, *, session_id, changed_by) -> Batch`. Allocates
  `day_number` as `max(day_number) + 1` for that `session_id`, or `1` when
  the session has none. Sets `status='pending'`. Does NOT commit; the caller
  adds and commits, matching `write_npc_schedule`'s contract.
- `write_pass_play(db, *, batch_id, session_id, character_id, declared_action) -> PassPlay`.
  Validates all-or-nothing before any write: `declared_action` stripped is
  non-empty and its length is at most `MAX_DECLARATION_CHARS`, declared in
  this module as a named module-level constant with the value `4000`. Sets
  `status='submitted'`, `batch_order=1`, `history=[]`.
- `PASS_PLAY_STATUSES: tuple[str, ...] = ("submitted", "resolving", "resolved", "flagged")`.
  Declared here, in this brief, because item 3 renders it. `flagged` is the
  reserved value for a future input classifier; nothing in this brief ever
  writes it.
- Neither function ever updates `declared_action`. There is no update path
  for that field anywhere in this brief, and none may be added later.

### 3. Routes — `src/world_engine/cockpit/routes/day.py` (new)

Registered in `cockpit/app.py` with the other `include_router` calls (M11).

- `POST /api/day/declare`, body `{"declared_action": str}`. Resolves, in
  order: the active world; the open session for that world, allocated by the
  M5 idiom (extract it to a shared helper or duplicate it — do NOT import
  from `cockpit/play.py`, which would couple this surface to the sealed Play
  module); the single `character_type='player'` character in that world.
  More than one, or none, is a fail-closed 4xx naming the count found, never
  a silent pick. Then `write_batch` + `write_pass_play`, one commit, and
  return the day dict.
- `GET /api/days` — every day for the active world, newest `day_number`
  first: `id`, `day_number`, `status`, `declared_action`, `created_at`.
- `GET /api/day/{batch_id}` — one day, same shape, 404 when the batch does
  not belong to the active world (scoping at query construction, not by a
  post-hoc check).
- No PUT, no PATCH, no DELETE on any of these.
- `injected_context` and `history` are NEVER included in any response body
  (M3: `json_ui_boundary.py` names both).

### 4. Frontend — the declaration surface (Q1)

New `frontend/src/journee/` with `Journee.svelte` and `journee.svelte.js`,
following the M10 pattern exactly: always mounted from `App.svelte`, a single
`active` prop toggling its own root, no legacy bridge call.

- `App.svelte`: `<Journee active={currentSurface === 'journee'} />`, sibling
  to `<Creation>` and `<Observation>`. `applyRoute` must NOT route `journee`
  through `showSurface()` — extend the existing `surface !== 'observation'`
  guard to exclude it too.
- `Header.svelte`: a fourth `mode-tab`, label `Journée`, after Observation.
- `/journee` added to BOTH `SHELL_ROUTES` (`frontend/src/lib/router.js`) and
  `_SHELL_ROUTES` (`cockpit/app.py`), and to `parse()`.
- The surface holds: a textarea bounded client-side at
  `MAX_DECLARATION_CHARS` with a live character count, a submit button, and a
  read-only list of past days showing day number, status and the declaration
  as submitted. Selecting one shows it in full.
- Once submitted, a declaration is never editable in this UI. No edit
  control, no delete control.
- No agenda data is fetched, rendered or referenced anywhere in this surface.
- Scoped `<style>` block, no raw-HTML injection directive, per the M10
  precedent.

### 5. Verify — `tooling/verify/checks/pipeline_wiring.py` (new)

Stdlib `ast` only, no DB, M12 idiom. Fail-closed and vacuity-guarded
throughout: any check that collects zero items FAILS.

- R1. `Batch` and `PassPlay` each have at least one importer in `src/`
  outside `models/__init__.py`. This is the no-reader violation clearing.
- R2. `Batch.__table_args__` declares a unique index over exactly
  `("session_id", "day_number")`.
- R3. No assignment to any `.declared_action` attribute anywhere in `src/`,
  and no `declared_action` key in any `update()` / `setattr()` call. The one
  legal write is the `PassPlay(...)` constructor inside
  `writes/pipeline.py`; the rule is stated as "constructor only, one module".
- R4. `MAX_DECLARATION_CHARS` and `PASS_PLAY_STATUSES` are module-level
  constants in `writes/pipeline.py`, and the route module reads the bound
  from there rather than restating a literal.
- R5. `routes/day.py` contains no `PUT`/`PATCH`/`DELETE` decorator, and no
  response builder in it references `injected_context` or `history`.
- R6. Vacuity guard: the module count scanned, the constant count found and
  the route count found are each asserted non-zero, with the failure message
  naming which one came back empty.

## Scope OUT

Every item below was discussed during planning and borders this step.

- **All resolution.** No plan emission (F1), no prerequisite judge (S1), no
  budget arithmetic, no dice, no concordance (C1), no narration, no rewrite
  guard (T1), no reconciliation (R1). No model call of any kind, local or
  remote, appears in this brief's code.
- **Mutation emission.** No `ProposedMutation` row is written with
  `source_type='pass_play'`. That is a later brief.
- **`Agenda` / `AgendaStep`.** Not read, not written, not rendered.
- **`world.current_phase`.** Read nowhere in this brief. The four-slot budget
  (M1 in the ticket) is a later brief's concern; `PUT /api/world/phase` and
  its deliberately inert body are untouched.
- **`schedule_reads.py`.** Untouched. No precedence term is added, no
  positional read is performed.
- **`flag_reason` column and any input classifier.** Only the `flagged`
  status VALUE is reserved, and only because item 4 renders the status
  vocabulary. A nullable `flag_reason` column with no reader would be the
  exact violation this brief exists to clear.
- **Vestigial `Batch` columns** — `message_to_claude`, `claude_raw_response`,
  and possibly `local_summary` / `final_result`. Do not drop, rename or
  repurpose them. REPORT ONLY: note in the execution notes which of the four
  still have zero writers after this brief.
- **`batch_order` beyond the constant `1`**, and everything multiplayer.
- **TICKET-0069**, the Play surface migration. The Journée surface must not
  touch `LegacyFrame.svelte`, `legacy/`, or `showSurface()`.
- **Auto-approve** (O1). No whitelist, no code-review path.
- **`Session` semantics.** Sessions keep their current meaning and lifecycle;
  this brief only consumes the open one.

## Invariants to defend

- **No structure without a reader.** This step exists partly to clear a
  standing violation. It must not create a replacement: every column, constant
  and status value introduced here has a named consumer inside this same
  brief. `flag_reason` was cut for exactly this reason.
- **History is sacred.** `declared_action` is write-once by construction:
  constructor-only, one module, enforced by R3. `history` stays `[]` here and
  is append-only when a later brief starts using it.
- **Model proposes, code judges.** Vacuously safe in this brief — there is no
  model. The risk is a later brief widening one of these routes; R5 is the
  tripwire.
- **Fail-closed.** No silent pick of a player character, no silent pick of a
  session, no unbounded declaration length. Each has a named bound or a 4xx.
- **Query-level scoping.** `GET /api/day/{batch_id}` filters by active world
  in the query, not after the fetch.

## Done means

- [ ] Migration runs on a fresh DB and on the existing one; re-running it a
      second time changes nothing and prints so.
- [ ] `EXPECTED_STATIC_SCHEMA_VERSION`, the `schema_meta` singleton and the
      `world-engine-schema.md` header all name the same new version, in one
      commit.
- [ ] Cockpit boots with the version guard green.
- [ ] `POST /api/day/declare` with a two-sentence declaration returns a day
      with `day_number = 1`; a second call returns `day_number = 2`.
- [ ] Inserting a duplicate `(session_id, day_number)` by hand raises an
      integrity error.
- [ ] An empty or whitespace-only declaration returns 4xx and writes nothing.
- [ ] A declaration over `MAX_DECLARATION_CHARS` returns 4xx and writes
      nothing.
- [ ] `GET /api/days` and `GET /api/day/{id}` return the declarations, newest
      first, with neither `injected_context` nor `history` in the payload.
- [ ] `GET /api/day/{id}` for a batch outside the active world returns 404.
- [ ] Live: the Journée tab appears, a declaration can be typed and submitted,
      it appears in the list immediately, and reloading `/journee` directly
      lands on the surface with the list intact.
- [ ] Browser Back from `/journee` leaves the surface without replaying a
      legacy boot.
- [ ] `python tooling/verify/checks/pipeline_wiring.py` is green, and each of
      R1–R6 has been observed to FAIL at least once under a deliberate local
      mutation before being reverted (the anti-vacuity proof).
- [ ] `python tooling/verify/checks/legacy_mount.py` is green with the new
      route on both sides.
- [ ] `python tooling/verify/checks/json_ui_boundary.py` is green.
- [ ] `corpus_gate.py` green.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `world-engine-schema-changelog.md`: entry at the next version — the
  `Batch.day_number` column and `idx_batch_session_day`, naming TICKET-0075 /
  BRIEF-0075-a and decision U1, and stating that the day IS the batch ordinal
  (L1) and that the ordinal is scoped to a session.
- `world-engine-schema.md`: header version line, and the `batch` table entry.
- `src/world_engine/schema_version.py`: the constant.
- `tooling/standards/DECISIONS_INDEX.md`: L1, Q1, U1.
- `CLAUDE.md`: only if the surface list is enumerated there; if it is, add
  Journée. Otherwise no change — TICKET-0071's hygiene pass owns that file.
