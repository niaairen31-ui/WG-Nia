# BRIEF — Step "Parked-plan socle"

## Context

TICKET-0075 gave the player one day plan at a time: an `agenda` owned by the
player character. A second, unrelated declaration is refused outright -- the
chain returns 409 and demands a manual abandon (`cockpit/routes/day.py:607-620`).
Nia wants a player to hold SEVERAL plans, each with a status, so an unrelated
day 2 does not destroy day 1's plan and a later day can pick it back up. This
step adds the parked state, stores which plan each day advanced, and turns the
`replace` refusal into park-and-open. Plan SELECTION from a declaration
(BRIEF-0077-b) and plan REVISION against a moved world (BRIEF-0077-c) are not
in this step: after this brief the day-3 resume is done by hand from Creation.

## Mini-RECON (measured against the fresh tarball, `main`)

All anchors verified against the tree. **If any of these contradicts what you
find, STOP and escalate -- do not adapt the brief yourself.**

- [M] `models/canon.py:811-830` -- `Agenda`; CHECK `ck_agenda_status` is
  `status IN ('active','completed','failed','abandoned')`.
- [M] `writes/goals_agendas.py:234-281` -- `write_agenda`; lines 263-271 hold the
  one-active-per-character guard (explicit existence check, `ValueError`).
- [M] `writes/goals_agendas.py:440-444` -- `_AGENDA_GOAL_CASCADE_MAP` has keys
  `completed`/`failed`/`abandoned` only.
- [M] `writes/goals_agendas.py:488-523` -- `write_agenda_status`; appends the
  previous `{status, updated_at}` to `change_history` BEFORE overwriting, then
  cascades only when `was_active and goal_status is not None`.
- [M] `writes/goals_agendas.py:578-622` -- `write_day_plan`.
- [M] `models/pipeline.py:62-83` -- `PassPlay`; no `agenda_id` column;
  `__table_args__` is `(Index("idx_passplay_batch", "batch_id"),)`.
- [M] `cockpit/routes/day.py` -- 946 physical lines.
  `_load_standing_agenda` at 457-463, `_finalize_plan` at 466-512,
  `_reconciliation_dict` at 515-526, `_finalize_continue` at 529-553,
  `_revised_plan_matches_remaining` at 556-566, `_finalize_modify` at 569-605,
  `_finalize_replace` at 607-620, `_reconcile_and_finalize` at 623-644,
  `plan_day` at 647-690, `_load_resolvable_day` at 693-713,
  `_load_active_agenda` at 716-724.
- [M] `cockpit/crud/agendas.py:238-252` -- `update_agenda_status`; rejects any
  status outside `('active','abandoned')`, calls `write_agenda_status`, then
  `_activate_lowest_pending_step_if_none_active` on reactivation.
- [M] `tooling/verify/canon_write_policy.txt:53,56` -- `write_agenda` and
  `write_agenda_status` are the two allow-listed writers of table `agenda`.
- [M] `scripts/migrate_v1_8_gatherings.py:39-66` -- the only table-rebuild
  precedent: `PRAGMA foreign_keys=OFF`, `PRAGMA legacy_alter_table=ON`, drop
  indexes, `RENAME TO <t>_old`, `Model.__table__.create(conn)`,
  `INSERT INTO <t> (...) SELECT ... FROM <t>_old`, `DROP TABLE <t>_old`, both
  pragmas restored, all inside one `engine.begin()`.
- [M] `scripts/migrate_v1_94_agenda_step_plan.py:23-45` -- the fail-closed env
  preamble every migration carries.
- [M] `src/world_engine/db.py:93-146` -- `isolation_level = None` plus an
  explicit `BEGIN` listener; DDL joins the surrounding transaction.
- [M] `frontend/src/creation/intrigues.svelte.js:49-63` -- `setAgendaStatus`;
  `Intrigues.svelte:163-168` branches on `agenda.status === 'active'` to choose
  between the abandon and the reactivate button.

**STOP conditions.** Stop and escalate, without writing code, if: (1) any
anchor above is materially different; (2) `agenda` turns out to be referenced by
a foreign key from a table not in `{agenda_step, goal_agenda_link}` -- the
rebuild's FK handling would then be wider than this brief assumes; (3) the live
DB already contains an `agenda` row with `status='paused'`; (4) the guard in
Scope IN item 4 would need to know whether the caller is the day chain or the
creator CRUD in order to be correct -- that would mean the invariant is not
actually chokepoint-enforceable and the design must be revisited.

## Scope IN

Numbered items 1-2 and 3 are one commit (schema + migration). Item 5 is its own
pure-move commit and MUST land before items 6-9. Items 4, 6-12 follow.

**1. `agenda.status` vocabulary widened (`src/world_engine/models/canon.py`).**
In `Agenda.__table_args__`, replace the `ck_agenda_status` CheckConstraint's SQL
with, verbatim:

    "status IN ('active','paused','completed','failed','abandoned')"

Immediately above the `Agenda` class, append to the existing header comment
block, verbatim:

    # `paused` (schema vX.YY, TICKET-0077, BRIEF-0077-a): a NON-TERMINAL state
    # for a player plan set aside and resumable later. It is deliberately
    # absent from `_AGENDA_GOAL_CASCADE_MAP` — parking a plan must never touch
    # a linked npc_goal, unlike `failed`/`abandoned`. The one-active-agenda
    # rule for `character` owners is unchanged and now enforced at BOTH
    # canon-write sites (`write_agenda`, `write_agenda_status`): a player may
    # hold any number of `paused` plans and at most one `active` one.

**2. `pass_play.agenda_id` (`src/world_engine/models/pipeline.py`).**
Add to `PassPlay`, placed immediately after `character_id`:

    agenda_id: Optional[str] = Field(default=None, foreign_key="agenda.id")

and extend `__table_args__` to
`(Index("idx_passplay_batch", "batch_id"), Index("idx_passplay_agenda", "agenda_id"))`.
Add above the column, verbatim:

    # Which plan this day advanced (schema vX.YY, TICKET-0077, BRIEF-0077-a).
    # NULL for every pre-BRIEF-0077-a row and for a day that never reached
    # plan emission — `/resolve` falls back to the player's active agenda in
    # that case. Written once, at plan time, and never rewritten: once plans
    # can be parked, "which plan did day N advance" stops being derivable
    # from current state.

**3. Migration `scripts/migrate_vX_YY_parked_plans.py`.**
Copy the fail-closed env preamble from `migrate_v1_94_agenda_step_plan.py:23-45`
verbatim (module path bootstrap, `WORLD_ENGINE_ENV` refusal, `sys.exit(1)`).
Two independent, idempotent pieces:
  a. Rebuild `agenda` to pick up the widened CHECK, following
     `migrate_v1_8_gatherings.py:48-66` exactly: one `engine.begin()`,
     `PRAGMA foreign_keys=OFF`, `PRAGMA legacy_alter_table=ON`,
     `DROP INDEX IF EXISTS idx_agenda_owner_status`,
     `ALTER TABLE agenda RENAME TO agenda_old`,
     `models.Agenda.__table__.create(conn)`, column-explicit
     `INSERT INTO agenda (...) SELECT ... FROM agenda_old`,
     `DROP TABLE agenda_old`, both pragmas restored. Column list written out
     explicitly, never `SELECT *`. Skip the whole piece when the live CHECK
     already contains `'paused'` (read via
     `inspect(engine).get_check_constraints("agenda")` or the `sqlite_master`
     SQL text -- whichever the tree's other migrations already use; if neither,
     read `sqlite_master.sql` and substring-match `'paused'`).
  b. `ALTER TABLE pass_play ADD COLUMN agenda_id TEXT REFERENCES agenda(id)`
     plus `CREATE INDEX IF NOT EXISTS idx_passplay_agenda ON pass_play(agenda_id)`
     (`migrate_v1_94` precedent). Skip when the column is already present.
  Print one line per piece applied or skipped. No backfill of `agenda_id`:
  historical days keep NULL and use the fallback.

**4. `write_agenda_status` -- accept `paused`, guard the chokepoint
(`src/world_engine/writes/goals_agendas.py`).**
Before the history append, insert the guard:

    if status == "active":
        owner = db.get(Entity, agenda.owner_entity_id)
        if owner is not None and owner.type == "character":
            other = db.exec(
                select(Agenda).where(
                    Agenda.owner_entity_id == agenda.owner_entity_id,
                    Agenda.status == "active",
                    Agenda.id != agenda.id,
                )
            ).first()
            if other is not None:
                raise ValueError(
                    "write_agenda_status: character owner already holds an active "
                    f"agenda ({other.title!r}) — park it before activating this one"
                )

Extend the docstring with, verbatim:

    `paused` (TICKET-0077, BRIEF-0077-a) is a non-terminal set-aside state and
    is absent from `_AGENDA_GOAL_CASCADE_MAP`, so parking a plan cascades
    NOTHING onto linked goals — checked by `parked_plan_guard.py`, not left to
    reading. The one-active-per-character guard above is the SAME rule
    `write_agenda` enforces at creation (goals_agendas.py:263-271), replayed
    here because this is the other canon-write site that can produce an
    `active` agenda: `PATCH /agendas/{id}` reached it without the guard before
    this brief. Faction owners keep their multi-agenda freedom.

Do NOT touch `_AGENDA_GOAL_CASCADE_MAP`: `'paused'` must stay absent, and
`.get(status)` returning `None` is already the correct no-cascade behaviour.

**5. Pure-move commit (no behaviour change).**
Create `src/world_engine/cockpit/day_reconcile_apply.py` and move, BYTE-IDENTICAL
bodies, in this order: `_reconciliation_dict`, `_finalize_continue`,
`_revised_plan_matches_remaining`, `_finalize_modify`, `_finalize_replace`,
`_reconcile_and_finalize`. Carry their imports. `routes/day.py` imports them from
the new module. Module docstring states it is a relocation from
`cockpit/routes/day.py` for module-budget headroom (TICKET-0077, BRIEF-0077-a),
byte-identical otherwise -- the `models/config.py::AgendaStep` relocation
precedent. Commit this alone and verify the diff is a move before item 6.

**6. New module `src/world_engine/day_plans.py` -- reads and the transition
decision.** No model call, no HTTP, no mutation. Exactly:

    OPEN_PLAN_STATUSES: tuple[str, ...] = ("active", "paused")

    def open_plans(character, db) -> list[Agenda]
        # owner_entity_id == character.id, status in OPEN_PLAN_STATUSES,
        # ordered active-first then created_at DESC. Explicitly filtered —
        # never a bare select(Agenda) (enumeration scope discipline).

    def active_plan(character, db) -> Optional[Agenda]
        # the single status == 'active' row, or None.

    def park_active_plan(character, db) -> Optional[Agenda]
        # find the active plan; if none, return None. Otherwise call
        # writes.write_agenda_status(db, agenda=..., status="paused"),
        # db.flush(), and return it. The flush is REQUIRED: write_agenda's
        # one-active guard is a SELECT, so a plan created later in the same
        # transaction would otherwise still see the old 'active' row.

Module docstring states, verbatim:

    Parking and activating a player plan is a DIRECT WRITE, not a proposal.
    `day_mutations.py` records the governing precedent: under V1 creating a
    plan has no world footprint and stays `write_day_plan`'s direct write.
    A status swap between two plans of the SAME player has the same property —
    no NPC sees it, no relation, knowledge or ledger row moves — so there is
    nothing for Nia to approve, and therefore nothing that can leave the day
    blocked behind an unreviewed queue row. The audit trail is
    `agenda.change_history`, appended by `write_agenda_status` on every
    transition, exactly as for every other agenda status change.

**7. `_finalize_replace` becomes park-and-open
(`cockpit/day_reconcile_apply.py`).** Replace the raising body. New behaviour,
in this order, one transaction: `day_plans.park_active_plan(character, db)` ->
`emit_plan(...)` with the same `concordance_summary` the fresh-plan path uses ->
`_finalize_plan(...)` unchanged. The signature gains whatever `_finalize_plan`
needs (`world_id`, `character`, `pass_play`, `concordance_result`, `db`);
`recon` stays for the response's `reconciliation` block. The returned dict is
`_finalize_plan`'s dict plus `"reconciliation": _reconciliation_dict(recon, [])`.
If `emit_plan` raises `LlmParseError`, raise `HTTPException(502, ...)` -- the
park is rolled back with the rest of the transaction, so a failed emission
leaves the standing plan active. Keep the function at or under 80 lines; extract
a helper if needed.

**8. `/plan` writes the binding (`cockpit/routes/day.py`, `_finalize_plan`).**
`write_day_plan` returns the `Agenda`; capture it and set
`pass_play.agenda_id = agenda.id` at the SAME place `pass_play.status =
"resolving"` is set, before the existing `db.add(pass_play)` and single
`db.commit()`. Do not add a second commit. The three reconciliation finalizers
that keep a standing plan (`_finalize_continue`, `_finalize_modify`) set
`pass_play.agenda_id = agenda.id` for the standing agenda at their own
`pass_play.status = "resolving"` line, same discipline.

**9. `/resolve` binds through the stored link (`cockpit/routes/day.py`,
`_load_active_agenda`).** Change the signature to take the `PassPlay` as well.
When `pass_play.agenda_id` is set, `db.get(Agenda, pass_play.agenda_id)`; raise
`HTTPException(409, ...)` if it is missing or its `owner_entity_id` is not the
player character. When it is NULL, keep today's behaviour exactly (the single
`status == 'active'` agenda, 409 when absent) and note in the docstring that
this is the pre-BRIEF-0077-a fallback. Do NOT require the bound plan to be
`active` here -- BRIEF-0077-c may resolve a plan the same request just resumed.

**10. Creation reads and drives the parked state.**
  a. `cockpit/crud/agendas.py::update_agenda_status` -- widen the accepted set
     to `("active", "paused", "abandoned")` and update the 422 message to name
     the three. `_activate_lowest_pending_step_if_none_active` stays gated on
     `body.status == "active"`, unchanged. Convert the `ValueError` from the new
     guard into `HTTPException(409, str(exc))` so Nia sees the message rather
     than a 500.
  b. `frontend/src/creation/intrigues.svelte.js::setAgendaStatus` -- its
     `linkedGoalCount` confirmation currently fires for any non-`active`
     status; exempt `'paused'` (parking cascades nothing, so the warning would
     be false).
  c. `frontend/src/creation/Intrigues.svelte` -- in the branch at 163-168, show
     a Pause button (title `Mettre l'intrigue en pause`) for an `active` agenda
     alongside the existing abandon control, and keep the reactivate button for
     both `paused` and `abandoned`. The status badge must render `paused`
     distinctly from `abandoned`.

**11. Verify check `tooling/verify/checks/parked_plan_guard.py`.** Follows the
`FAILURES` list + `_report_and_exit` + ROOT via `parents[3]` idiom. AST-based,
no runtime DB. Fail-closed and vacuous-proof -- each rule that collects zero
items FAILS. Rules:
  R1. The `ck_agenda_status` CheckConstraint SQL in `models/canon.py` contains
      exactly the five values `active|paused|completed|failed|abandoned`.
  R2. `_AGENDA_GOAL_CASCADE_MAP`'s key set is exactly
      `{completed, failed, abandoned}` -- `paused` absent.
  R3. Both `write_agenda` and `write_agenda_status` contain a comparison against
      the string literal `"character"` and a `Agenda.status == "active"`
      existence query. Zero functions collected -> FAIL.
  R4. `PassPlay` declares `agenda_id`, and at least one module outside
      `src/world_engine/models/` references `pass_play.agenda_id` or
      `PassPlay.agenda_id`. Zero readers -> FAIL.
  R5. `day_plans.py` contains no `ProposedMutation` reference and no string
      literal `"proposed"` -- the direct-write posture is checked, not trusted.
  Each rule states what it proves in its docstring, and R3 states explicitly
  that it proves the guard EXISTS at both sites, not that it is correct.

**12. Register the check** in whatever manifest `run.py`/`pipeline_state.py`
uses to discover checks, following the most recently added check's pattern
(`day_prompt_delivery.py`).

## Scope OUT

None of the following, however tempting while in these files:

- **The dedicated plan-selection model call** and its prompt template/usage.
  That is BRIEF-0077-b. Do not widen `day_reconcile`'s inputs to see more than
  the one standing agenda; do not add a `usage` to the prompt registry.
- **The `resume` verdict.** `RECONCILE_VERDICTS` stays the three-value tuple and
  the dispatch dict stays a bijection with it. BRIEF-0077-b.
- **Plan revision / E3.** Do not touch `_finalize_modify`'s 422, do not extend
  `_mutation_apply_agenda_step_change` with insert/reorder/edit actions, do not
  add a `superseded` step status. BRIEF-0077-c.
- **Any player-facing plan selector or Journee UI change.** F1 is locked: the
  Journee surface is untouched except as a consequence of item 7 no longer
  returning 409.
- **A cap on open plans.** G is locked at none. Do not add `MAX_OPEN_PLANS`.
- **A denormalized `agenda.owner_type` column with a partial unique index**
  `(owner_entity_id) WHERE status='active' AND owner_type='character'`.
  Considered and rejected at intake: it buys structural enforcement at the cost
  of a denormalized copy of `entity.type` that can drift, when the two
  canon-write sites are already a complete chokepoint. *Reactivation condition:
  if a third canon-write site for `agenda.status` is ever introduced.*
- **Auto-approved mutations of any kind.** No new `mutation_type`, no code path
  that creates a `ProposedMutation` with `status != 'proposed'`.
- **NPC multi-plan.** The one-active rule for NPC characters is unchanged and
  its four readers (`tick.py`, `tick_normalize.py`, `routes/mutations.py`) are
  not to be touched.
- **Deduplicating the `connects_to` readers, the `_get_or_open_session`
  duplication, or any other duplication noticed in these files.** REPORT ONLY.
- **Backfilling `pass_play.agenda_id`** for historical days.

## Invariants to defend

- **One active agenda per character owner.** This step's central risk: A1 exists
  precisely to let a player hold several plans, and the guard is what keeps
  "several" from meaning "several active". After this brief the rule holds at
  BOTH canon-write sites, and it holds STRICTLY MORE than before (item 4 closes
  the `PATCH /agendas/{id}` hole). Faction owners keep multi-agenda freedom.
- **Single canon-write authority per resource type.** `agenda` keeps exactly two
  writers, both already allow-listed (`canon_write_policy.txt:53,56`).
  `day_plans.park_active_plan` calls `write_agenda_status`; it must contain no
  `db.add(Agenda...)` of its own, or `single_canon_write.py` will fail and
  should.
- **History is sacred.** Every status transition goes through
  `write_agenda_status`, which appends before overwriting. Parked plans are
  never deleted and their steps are never rewritten.
- **Model proposes, code judges.** This step adds NO model call. The park
  decision is Python's, derived from measured status, never from a verdict.
- **No structure without a reader.** `pass_play.agenda_id`'s reader is item 9,
  in this same brief. `'paused'`'s readers are items 6, 7 and 10.
- **The positional wall.** Untouched -- nothing here reads or writes a location.
- **Enumeration scope discipline.** Every `select(Agenda)` added in item 6
  carries an explicit `owner_entity_id` filter.

## Done means

- [ ] `python scripts/migrate_vX_YY_parked_plans.py` runs on the live DB, prints
      both pieces applied, and running it a second time prints both skipped.
- [ ] A `backup.py` run precedes the migration (canon table rebuild).
- [ ] `sqlite3 ~/.world_engine/world_engine.db ".schema agenda"` shows the
      five-value CHECK; the row count of `agenda` before and after the rebuild
      is identical.
- [ ] `sqlite3 ... ".schema pass_play"` shows `agenda_id` and
      `idx_passplay_agenda`.
- [ ] The move commit (item 5) has a diff that is a pure relocation: no line of
      the six moved functions differs.
- [ ] `wc -l src/world_engine/cockpit/routes/day.py` is under 1000 after every
      commit in this brief.
- [ ] Live, day 1: declare -> emit plan -> resolve. Same output as before.
- [ ] Live, day 2: declare something unrelated to day 1. Response is 200 with a
      `reconciliation` block whose verdict is `replace`, plus a fresh `steps`
      list. No 409.
- [ ] After day 2, the Creation intrigues tab lists BOTH plans, plan A badged
      `paused`, plan B `active`.
- [ ] `GET /api/mutations?status=proposed` contains NO row describing the park.
- [ ] `POST /api/day/{batch}/resolve` for day 2 completes without a
      pending-proposal 409.
- [ ] `sqlite3 ... "SELECT agenda_id FROM pass_play ORDER BY submitted_at DESC LIMIT 1"`
      returns plan B's id.
- [ ] Plan A's `change_history` contains an entry whose `status` is `active`
      (the snapshot taken before the move to `paused`).
- [ ] In Creation, clicking reactivate on plan A while plan B is active returns
      a readable 409 naming plan B, not a 500 and not an IntegrityError.
- [ ] In Creation, pausing plan B then reactivating plan A succeeds; a linked
      `npc_goal`, if any, is still `active` after the pause.
- [ ] `python tooling/verify/run.py` is green, including the new
      `parked_plan_guard.py`.
- [ ] `parked_plan_guard.py` fails when temporarily fed a tree with `'paused'`
      added to `_AGENDA_GOAL_CASCADE_MAP` (vacuous-proof spot check, reverted).
- [ ] `/review-step` and `/close-step` run and reported.

## Docs to update

- `world-engine-schema-changelog.md` -- new `vX.YY` entry: the `agenda.status`
  vocabulary widening and the rebuild it required, `pass_play.agenda_id`, and
  the statement that `paused` is deliberately absent from the goal cascade.
- `world-engine-schema.md` -- the `agenda` section (five-value status, the
  one-active rule now enforced at both write sites, replacing the text at
  line 1546) and the `pass_play` section.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` -- a new subsection recording
  (a) why parking is a direct write and not an auto-approved mutation, with the
  `day_mutations.py:12-16` precedent quoted; (b) the rejection of the
  denormalized `owner_type` index and its reactivation condition; (c) the
  amendment to the one-active-personal-agenda text at line 5526.
- `CLAUDE.md` -- no change expected; the invariant is not stated there. If the
  contract check disagrees, report rather than edit.
- `tooling/verify/canon_write_policy.txt` -- no new site. If the AST check
  demands one, STOP: it means item 6 grew a write it should not have.
