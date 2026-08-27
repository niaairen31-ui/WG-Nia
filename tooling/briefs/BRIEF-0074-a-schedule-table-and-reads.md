# BRIEF — Step "npc_schedule table, the world phase, and the two reads"

TICKET-0074, brief -a of three. One commit for the schema plus the reads plus
the check; one separate commit if and only if the conditional fix in Scope IN
item 11 is triggered.

## Context

TICKET-0073 gave an NPC a standing occupation — a reason to be somewhere — but
nothing says where that somewhere is, or when. The only positional truth in the
tree is `character.current_location_id` (`models/canon.py:162`), a fact about
right now that says nothing about a phase three days out. The day-resolution
chain (K3, neighborhood-scoped tick) cannot scope a tick without a read that
answers "who is plausibly at this location at this phase". This step ships the
table, the phase, and the two reads. It does not ship a UI and does not touch
the tick.

## Mini-RECON — verify before writing

Every number below was measured against `main` at schema v1.91 on 2026-08-23.
Report `file:line` for each. **STOP and escalate** if any does not hold; do not
adapt the brief silently.

1. `src/world_engine/models/canon.py` is **993 lines / 2 top-level functions**.
   `tooling/verify/baselines/module_budget.json` **does not exist**, and
   `module_budget.py:107-109` treats a missing baseline as an empty exemption
   set — so the 1000-line cap is unconditional. Confirm both.
2. **STOP CONDITION, the one that gates this brief.** Draft the `World` change
   of Scope IN item 3 and count the physical lines it adds to `canon.py`. If
   the file would exceed 1000 lines, **STOP and escalate**: the ticket's T-B3
   reactivation condition has fired and an extraction brief must land first. Do
   NOT shorten the constraint, drop the comment, or reflow neighbouring code to
   make room.
3. `class World` is at `models/canon.py:64`, its `__table_args__` already a
   tuple containing `Index("idx_world_one_active", ...)`, and its columns are
   name, description, magic_status, is_active, created_at, updated_at — no
   temporal state. Confirm.
4. `CheckConstraint` is already imported in `canon.py` (import block at
   `canon.py:35-41`), so no new import line is needed. Confirm.
5. `models/config.py` is 49 lines and its docstring (`config.py:1-8`) records
   the budget-driven split precedent verbatim. Confirm; the new module's
   docstring cites it.
6. `models/__init__.py` is 166 lines, imports `ConversationWindowConfig` at
   `:77` and re-exports it in `__all__` at `:160`. Confirm both insertion
   points.
7. `writes/config.py` is 452 lines / 8 top-level functions, and
   `write_location_doors` is at `:296` with signature
   `(db, *, world_id, location_id, doors, changed_by)`, body =
   validate-all-or-nothing, then `db.execute(text("DELETE FROM door WHERE
   location_id = :location_id"), {...})`, then build-and-`db.add` the new rows,
   returning them for the caller to commit. Confirm the shape; item 8 copies it.
8. `tooling/verify/canon_write_policy.txt` is 117 lines, `[CANON_TABLES]` spans
   `:1-6`, `[ALLOWED_SITES]` opens at `:8`, `write_location_doors` is registered
   at `:33` as the 24th site and `upsert_conversation_window_config` at `:37` as
   the 28th. Report the highest site ordinal in the file; the new entry's
   comment states the next one.
9. `INTERVAL_HOP_RADIUS` is at `tick_context.py:85` with exactly the three keys
   `quelques heures` / `quelques jours` / `quelques semaines`, and
   `world_tick.py:427-449` asserts that key set by AST. Confirm. `SCHEDULE_PHASES`
   is a SEPARATE constant with its own check — never an extension of this dict.
10. `NpcGoal` is at `models/canon.py:495` with `ck_npc_goal_kind` at `:502`
    (`CheckConstraint("kind IN ('volition','standing')", name=...)`) — the
    one-line CHECK idiom item 3 and item 4 copy. Confirm.
11. `Character.character_type` holds `player | npc` (`canon.py:161`),
    `Character.vital_status` defaults to `alive` (`canon.py:166`), and
    `Entity.status` defaults to `active` (`canon.py:130`). Confirm all three;
    item 9's scoping uses them.
12. `GatheringMember` is at `models/ephemeral.py:66` with
    `left_at: Optional[datetime] = None` at `:77` (NULL = still present), and
    `Gathering.status` defaults to `open` with `dissolved_at` nullable
    (`ephemeral.py:56-60`). Confirm; the present-branch gathering lookup filters
    on both.
13. `AgendaStep` is at `models/canon.py:822` with `idx_agenda_step_one_active`
    (partial unique, `WHERE status = 'active'`) at `:832`. Confirm. Report
    whether `AgendaStep` carries any location column at all — **if it does not,
    STOP and escalate**: C1's agenda term needs a location and this brief
    assumes one is reachable from the step or its agenda.
14. `models/canon_faction.py:105-114` carries the two partial unique indexes on
    `faction_membership`. Confirm; they are cited in a comment, not used.
15. `scripts/migrate_v1_91_npc_goal_kind.py` is 90 lines with the
    fail-closed `WORLD_ENGINE_ENV` guard at `:31-39`, an idempotence probe, and
    post-checks that `raise SystemExit` on violation. Confirm; item 10 copies it.
16. `src/world_engine/schema_version.py:16` reads
    `EXPECTED_STATIC_SCHEMA_VERSION: str = "v1.91"`, `world-engine-schema.md:3`
    reads `Current schema version: v1.91`, and
    `schema_version_agreement.py` compares them. Confirm all three; they move
    together in one commit.
17. `src/world_engine/observation_reads.py` is 250 lines and is the
    reads-module precedent (writes in one module, reads in its parallel).
    Confirm it exists; the new reads module cites it.
18. `scripts/preview_tick_context.py` is 64 lines, sets
    `sys.stdout.reconfigure(encoding="utf-8")` for Windows French output, and
    inserts `src` on `sys.path` before importing `world_engine`. Confirm; item
    12 copies it.
19. `corpus_gate.py` discovers checks by globbing `checks/*.py`, so the new
    check file needs no registration. Confirm, and report `TIMEOUT_SECONDS`.
20. REPORT ONLY, do not fix: grep `src/` for
    `current_phase|world_day|day_index|game_time|world_clock|time_of_day`. The
    design measured **zero hits**. If anything now matches, report it with
    `file:line` — a second source of "now" is exactly what T-A1 exists to
    prevent, but resolving it is not this brief's business.

## Scope IN

1. **`src/world_engine/models/schedule.py` — new module.** Docstring opens by
   citing `models/config.py`'s split precedent verbatim in substance: split out
   of `canon.py` (993/1000 lines, no headroom —
   `tooling/verify/checks/module_budget.py`), not because the table belongs to a
   different stratum; it is canon curated-config, same family as
   `location_type_catalog` / `world_law`, no `change_history`.

2. **`SCHEDULE_PHASES` — the frozen vocabulary**, module-level in
   `models/schedule.py`, verbatim, in this order:

   ```python
   # The four named cycle phases (A1a, TICKET-0074). A DAY-CYCLE axis, with no
   # calendrical component in v1. Deliberately NOT a reuse of
   # `tick_context.INTERVAL_HOP_RADIUS`, which is a DURATION axis (a BFS hop
   # bound on `connects_to` -- how much time passed off-screen) and whose key
   # set is asserted by `tooling/verify/checks/world_tick.py`. Two axes, two
   # constants, two checks. Adding a calendar later means a nullable
   # `day_kind` column and a pair of PARTIAL unique indexes (see the
   # `NpcSchedule` index comment) -- it never means adding a key here.
   SCHEDULE_PHASES: tuple[str, ...] = ("matin", "apres-midi", "soir", "nuit")
   ```

   Re-export it from `models/__init__.py` alongside the model class.

3. **`world.current_phase` — the column, in `models/canon.py`.** Subject to the
   mini-RECON item 2 STOP. Add to `class World` (`canon.py:64`), as its LAST
   column, immediately before `created_at`:

   ```python
   # Creator-set current day-cycle phase (T-A1, TICKET-0074). Per-WORLD by
   # construction: two worlds are two rows. Advancing it writes this column
   # and nothing else -- no tick, no cascade. The literal list is kept equal
   # to `models.schedule.SCHEDULE_PHASES` by verify/checks/npc_schedule.py
   # (imported here would be an import cycle: schedule.py imports from canon).
   current_phase: str = Field(default="matin", sa_column_kwargs={"server_default": text("'matin'")})
   ```

   and to its `__table_args__` tuple, after the existing `Index`:

   ```python
   CheckConstraint("current_phase IN ('matin','apres-midi','soir','nuit')", name="ck_world_current_phase"),
   ```

4. **`NpcSchedule` — the table**, in `models/schedule.py`. Columns, exactly
   these and no others: `id` (TEXT PK, `_uuid`), `world_id` (FK `world.id`, NOT
   NULL), `npc_id` (FK `entity.id`, NOT NULL), `phase` (TEXT NOT NULL),
   `location_id` (FK `entity.id`, NOT NULL), `standing_goal_id` (FK
   `npc_goal.id`, NULLABLE), `created_at`, `updated_at`. **No
   `change_history`** — S-I1, the curated-config family carries none, and the
   check asserts its absence.

   `__table_args__`, verbatim:

   ```python
   CheckConstraint("phase IN ('matin','apres-midi','soir','nuit')", name="ck_npc_schedule_phase"),
   # One row per NPC per phase. When a calendar lands (A2's reactivation),
   # this does NOT widen to (npc_id, phase, day_kind): SQLite treats NULLs as
   # DISTINCT inside a UNIQUE index, so the widened index would silently stop
   # guaranteeing uniqueness for every default row. The correct path is the
   # `faction_membership` partial-unique idiom (models/canon_faction.py):
   # one partial UNIQUE `WHERE day_kind IS NULL`, one `WHERE day_kind IS NOT
   # NULL`. Recorded now so the migration that adds the calendar does not
   # have to rediscover it.
   Index("idx_npc_schedule_npc_phase", "npc_id", "phase", unique=True),
   # Drives who_is_at -- the inverse read the resolution chain uses most.
   Index("idx_npc_schedule_location_phase", "location_id", "phase"),
   ```

5. **`writes/config.py::write_npc_schedule` — the one write site.** Signature
   `(db, *, world_id, npc_id, rows, changed_by)`, `rows` a
   `list[dict]` of `{"phase": str, "location_id": str, "standing_goal_id":
   str | None}`. Full-replace per NPC, on the `write_location_doors` idiom
   (`writes/config.py:296`):

   - Validate all-or-nothing BEFORE any write: every `phase` in
     `SCHEDULE_PHASES`; no duplicate phase within one payload (defence in
     depth — `idx_npc_schedule_npc_phase` is the structural guard);
     `location_id` resolves to an ACTIVE location of the same world;
     `standing_goal_id`, when present, resolves to an `npc_goal` row belonging
     to `npc_id` with `kind == "standing"`.
   - Then `db.execute(text("DELETE FROM npc_schedule WHERE npc_id = :npc_id"),
     {"npc_id": npc_id})`. **Parameterized on `npc_id`, never unscoped** — the
     check asserts this, because `single_canon_write.py` attributes ORM writes
     by AST and a raw `db.execute` is a known blind spot for it.
   - Then build and `db.add` the new rows; return them for the caller to commit.
   - An empty `rows` list is legal and means "this NPC has no schedule" — the
     delete runs, nothing is inserted.

   Re-export from `writes/__init__.py` beside the other config writers.

6. **`tooling/verify/canon_write_policy.txt` — registration.** Add
   `npc_schedule` to `[CANON_TABLES]`, and ONE line to `[ALLOWED_SITES]`
   preceded by a comment naming the next ordinal reported by mini-RECON item 8:

   ```
   src/world_engine/writes/config.py::write_npc_schedule      npc_schedule
   ```

7. **`src/world_engine/schedule_reads.py` — new module, the two reads plus the
   companion.** Parallel to `writes/config.py`, on the `observation_reads.py`
   precedent. Nothing outside this module reads `npc_schedule` directly.

   `PRESENT_PRECEDENCE` and `FUTURE_PRECEDENCE` are module-level tuples,
   verbatim, with this comment:

   ```python
   # C1 -- time-relative precedence. TWO branches, ONE accessor. The present
   # is a set of FACTS (a roster, a stored location); a future phase is a set
   # of PREDICTIONS, where a stored `current_location_id` is only a last
   # known position and must NOT beat the schedule. A single total order
   # (rejected C2) lets a stale fact win a phase three days out -- the exact
   # failure this table exists to fix.
   #
   # These tuples are the ONLY place a source may be named. `where_is`
   # iterates them and dispatches through `_SOURCE_LOOKUPS`; it performs no
   # lookup of its own. verify/checks/npc_schedule.py asserts the bijection
   # between these names and that table's keys, and that `where_is`'s body
   # contains no `select(` call.
   PRESENT_PRECEDENCE: tuple[str, ...] = (
       "gathering", "current_location", "agenda_step", "schedule", "unknown",
   )
   FUTURE_PRECEDENCE: tuple[str, ...] = (
       "agenda_step", "schedule", "last_known", "unknown",
   )
   ```

   `_SOURCE_LOOKUPS: dict[str, Callable]` maps each name to a single-source
   lookup returning `str | None`. `"unknown"` maps to a lookup that always
   returns `None` — it is the TERMINAL TERM of the order, not an error branch.

8. **`where_is(npc_id, phase, session, *, is_present) -> Resolution`.**
   `Resolution` is a frozen dataclass carrying `npc_id`, `phase`,
   `location_id: str | None`, `source: str`, and `standing_goal_id: str | None`
   (populated only when `source == "schedule"`). The body selects the tuple from
   `is_present`, iterates it, calls `_SOURCE_LOOKUPS[name]`, and returns on the
   first non-None — except `"unknown"`, which returns
   `Resolution(location_id=None, source="unknown")`. **It never raises on the
   unresolved path** (T-D2). `is_present` is an explicit argument, not derived
   here: the caller knows whether it is asking about now or about later, and
   this module has no clock.

9. **`who_is_at(location_id, phase, session, *, is_present) -> list[str]`** and
   **`unresolved_npcs(phase, session, *, is_present) -> list[str]`.** Both scope
   to the ACTIVE world's alive NPCs: `Character.character_type == "npc"`,
   `Character.vital_status == "alive"`, `Entity.status == "active"`. Both run
   `where_is` per NPC and partition on the result — `who_is_at` collects those
   resolving to `location_id`, `unresolved_npcs` collects those resolving to
   `source == "unknown"`. One resolution rule, two readers; neither reimplements
   precedence.

10. **`scripts/migrate_v1_92_npc_schedule.py`**, on the
    `migrate_v1_91_npc_goal_kind.py` idiom: fail-closed `WORLD_ENGINE_ENV`
    guard, idempotent (`CREATE TABLE IF NOT EXISTS` for `npc_schedule`, column
    probe before `ALTER TABLE world ADD COLUMN`), both indexes, both CHECKs
    (SQLite has no `ADD CONSTRAINT`, so `world.current_phase`'s CHECK rides on
    the `ADD COLUMN` statement — the same asymmetry v1.91 documents), and
    post-checks that `raise SystemExit` on violation. **No seeding, no
    backfill** — B1 is sparse, and a script that invented a day for every NPC
    would be canon authored by script.

11. **Conditional fix, separate commit, narrow.** IF AND ONLY IF mini-RECON
    item 20 reports a pre-existing symbol matching that grep in `src/`: report
    it, and change nothing. There is no fix authorized in this brief. (Listed
    here so the executor does not treat a finding as licence.)

12. **`scripts/preview_npc_schedule.py`** — the CLI companion, on the
    `preview_tick_context.py` precedent (UTF-8 stdout reconfigure, `src` on
    `sys.path`). Two modes:
    - `--npc <id> [--phase <p>]` prints `where_is` for one NPC: with `--phase`,
      one row; without, all four phases, each with its winning `source`.
    - `--location <id> --phase <p>` prints `who_is_at`, then a second block
      listing `unresolved_npcs` for that phase.
    When `--phase` is omitted the script reads `world.current_phase` from the
    active world and prints which phase it used. **This is `current_phase`'s
    concrete consumer in this brief** — the column ships with a reader, per the
    no-structure-without-a-reader rule. `is_present` is true when the requested
    phase equals the world's current phase, false otherwise.

13. **`tooling/verify/checks/npc_schedule.py`** — new G1 check, stdlib `ast`
    only, no DB, on the `standing_goal.py` FAILURES/`fail()`/`_report_and_exit`
    idiom with `ROOT = parents[3]`. Rules R1-R7 as listed in the ticket's
    machine-checkable criteria. Every rule carries an anti-vacuity guard: a
    rule that locates zero items FAILS. Frontend and context rules (R9-R12) are
    NOT authored here — briefs -b and -c amend this file.

14. **Docs.** `world-engine-schema.md` gains the `npc_schedule` table and the
    `world.current_phase` column, and its header line moves to `v1.92`.
    `world-engine-schema-changelog.md` gains a `v1.92` entry at the top.
    `schema_version.py`'s `EXPECTED_STATIC_SCHEMA_VERSION` moves to `"v1.92"`.
    All three in the SAME commit as the migration.

## Scope OUT

Named because each is adjacent enough to be tempting.

- **Any UI.** No Svelte component, no API endpoint, no route. Brief -b owns all
  of it, including the cockpit phase control. The column shipping here is set by
  the migration default and read by the CLI; that is deliberate and sufficient
  for -a's live gate.
- **The L1 concordance wiring.** `context.py` is untouched by this brief.
  `_npc_context_standing` keeps its current signature. Brief -c owns it.
- **The day-resolution chain.** `Batch` / `PassPlay` reactivation (both declared
  in `models/pipeline.py` with zero readers outside `models/__init__.py` — do
  not wire them), the B4 pipeline, plan emission, the Python knapsack, the
  plan-reconciliation pass.
- **Any change to the tick.** Not its model-call structure, not its prompt set,
  not its accepted mutation vocabulary. In particular: do NOT add
  `schedule_change`. S-F (auto-approve) is a separate ticket.
- **`activity` in any form** — free text or enum. D1/H1 rejected both;
  TICKET-0073 gave occupation a typed home in `npc_goal`.
- **`gathering_id` on a schedule row.** A gathering is ephemeral and already
  outranks the schedule in the present branch.
- **`change_history` on `npc_schedule`.** S-I1. The check asserts its absence.
- **A `day_kind` column, a `world_calendar` table, or any calendrical axis.**
  A1a forbids it in v1. The index comment records the correct future path; it
  does not authorize taking it.
- **Extending `INTERVAL_HOP_RADIUS`** or the duration vocabulary. Two axes, two
  constants.
- **Re-opening `npc_goal`.** TICKET-0073 closed it. This brief adds an FK TO it
  and nothing else.
- **Seeding schedules for existing NPCs.** B1 is sparse by decision.
- **A coverage check on schedule completeness.** B1 makes coverage a REPORT.
  The F1 panel (brief -b) is the compensating control; do not substitute a
  check for it.
- **Lazy NPC creation.** C1 upstream; S-H says germ realization acquires no new
  obligation here.

## Invariants to defend

- **Two sanctioned canon-write paths only.** `write_npc_schedule` is creator
  CRUD, the second path. It must NOT emit a `ProposedMutation` (E2 rejected:
  creator CRUD proposing to itself inverts the doctrine), and no model-facing
  code may reach it.
- **Structural, never disciplinary.** The phase vocabulary is a CHECK plus a
  checked constant, not a validation convention. The precedence order is a
  constant the accessor cannot escape, not a comment describing what the
  accessor does.
- **No structure without a reader.** Every column shipping here has a consumer
  in this brief: `current_phase` -> the CLI's default-phase mode;
  `standing_goal_id` -> `Resolution.standing_goal_id`, printed by the CLI (its
  second reader, the L1 render, arrives in -c); `location_id`, `phase` -> both
  reads.
- **Fail-closed and vacuous-proof.** Every rule in the new check FAILS on zero
  items collected. A rule that finds nothing has not passed.
- **History is sacred.** The full-replace DELETE targets a table of standing
  defaults, not a narrative record — which is exactly why S-I1 gives it no
  `change_history`. Do not extend the same delete-then-insert shape to any
  table that has one.

## Done means

- [ ] `python scripts/migrate_v1_92_npc_schedule.py` runs clean, and running it
      a second time reports nothing to do and exits 0.
- [ ] `world-engine-schema.md:3`, `schema_version.py`'s constant, and the
      changelog's top entry all read `v1.92`; `schema_version_agreement.py`
      passes.
- [ ] `models/canon.py` is at or under 1000 lines; report the exact count.
- [ ] `python -m tooling.verify.checks.npc_schedule` passes, and each of R1-R7
      fails when its target is deliberately broken (report the seven verdicts;
      revert every deliberate break).
- [ ] `corpus_gate.py` is green on the whole corpus.
- [ ] `python scripts/preview_npc_schedule.py --npc <id>` prints four rows for
      an NPC with no schedule, all `source=unknown`, `location=None`, exit 0 —
      no exception.
- [ ] After inserting one schedule row by hand for one NPC at one phase, the
      same command shows that phase resolving with `source=schedule` and the
      other three `unknown`.
- [ ] `--location <id> --phase soir` prints a roster block and an unresolved
      block; both render even when empty.
- [ ] Omitting `--phase` prints which phase it read from the active world.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `world-engine-schema.md`: `npc_schedule` table, `world.current_phase` column,
  header to `v1.92`.
- `world-engine-schema-changelog.md`: new `v1.92` entry at the top.
- `src/world_engine/schema_version.py`: constant to `"v1.92"`.
- `tooling/verify/canon_write_policy.txt`: one `[CANON_TABLES]` word, one
  `[ALLOWED_SITES]` line plus its ordinal comment.
- `ARCHITECTURE_DECISIONS.md`: one section recording J1 (schedule is background,
  agenda is foreground, one accessor), C1 (two-branch precedence and why a
  single total order was rejected), and T-A1's two conditions.
- No `CLAUDE.md` change.
