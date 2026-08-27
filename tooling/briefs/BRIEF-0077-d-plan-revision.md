# BRIEF — Step "Plan revision against the moved world"

## Context

A plan parked for several days can come back partly impossible: a contact has
moved, a resource is spent, a location is no longer reachable. BRIEF-0077-c
resumes such a plan unchanged, because the tree has no way to change one:
`_apply_mutation`'s `agenda_step_change` applier accepts only `complete`/`fail`
on the ACTIVE step, so `_finalize_modify` re-emits a plan, finds it differs, and
returns 422. This step gives a plan a revision path -- the remaining steps are
re-emitted against the current world, re-judged, re-budgeted and re-vetoed, and
written into the SAME agenda, with the superseded steps kept on disk. It closes
Nia's decision E3 and, with it, TICKET-0077.

## Mini-RECON (measured against the fresh tarball, `main`)

- [M] `cockpit/day_reconcile_apply.py:74-113` -- `_finalize_modify` re-runs
  `emit_plan` with `standing_steps_summary`, compares via
  `_revised_plan_matches_remaining` (line 61), and raises 422 on any difference.
- [M] `cockpit/mutations.py:766-823` -- `_mutation_apply_agenda_step_change`:
  `action not in ("complete","fail")` is rejected at line 773; `step.status !=
  "active"` is rejected at line 780 ("world moved since the tick"); on
  `complete` it promotes the lowest `pending` step, else completes the agenda.
- [M] `models/config.py:71-74` -- `ck_agenda_step_status` is
  `status IN ('pending','active','completed','failed')`. No set-aside value.
- [M] `models/config.py:79-88` -- `idx_agenda_step_agenda` (`agenda_id`,
  `step_order`) and `idx_agenda_step_one_active` (partial unique on `agenda_id`
  WHERE `status = 'active'`).
- [M] `models/config.py:122-148` -- `agenda_step_requirement.step_id` is an FK
  to `agenda_step.id`, with a unique index on
  `(step_id, type, target_entity_id, target_key)`.
- [M] `writes/goals_agendas.py:578-622` -- `write_day_plan` creates the agenda
  via `write_agenda`, then steps via `write_agenda_step`, then requirement rows;
  `_clean_plan_steps` (line 566) validates everything BEFORE any row is built.
- [M] `writes/goals_agendas.py:284-316` -- `write_agenda_step` is the sole
  `AgendaStep` constructor; `write_agenda_step_status` (line 319) is the sole
  status writer, appending to `change_history` before overwriting.
- [M] `tooling/verify/canon_write_policy.txt:42,53-56` -- allow-listed writers:
  `write_day_plan` (`agenda_step_requirement`), `write_agenda` (`agenda`),
  `write_agenda_step` (`agenda_step`), `write_agenda_step_status`
  (`agenda_step`), `write_agenda_status` (`agenda`).
- [M] `cockpit/routes/day.py:468-518` -- `_finalize_plan`: evaluate ->
  `budget_cut` -> `feasibility_veto` -> `write_day_plan` ->
  `write_day_feasibility` -> `pass_play.status`/`agenda_id` -> one commit.
- [M] `scripts/migrate_v1_95_parked_plans.py` -- the agenda table-rebuild this
  step's `agenda_step` rebuild copies, itself following
  `migrate_v1_8_gatherings.py:48-66`.
- [M] `src/world_engine/schema_version.py:15` -- `EXPECTED_STATIC_SCHEMA_VERSION
  = "v1.95"`.
- [M] `tooling/verify/checks/day_plan.py` has a rule named
  `check_applier_action_vocabulary_unwidened` -- it asserts
  `agenda_step_change`'s action vocabulary has NOT been widened. This step must
  leave that rule green, which it does: revision writes directly and adds no
  applier action.

**STOP conditions.** Stop and escalate if: (1) BRIEF-0077-c has not landed;
(2) `agenda_step` turns out to be referenced by a foreign key from a table other
than `agenda_step_requirement` -- the rebuild's FK handling would then be wider
than assumed; (3) the live DB already holds an `agenda_step` row with
`status='superseded'`; (4) a revision cannot be expressed without either
deleting a row or editing an existing step's `objective` in place -- both are
forbidden and the design must be re-decided, not adapted; (5)
`check_applier_action_vocabulary_unwidened` goes red -- that means the revision
leaked into the mutation applier, which is exactly what this brief forbids.

## Scope IN

**1. `agenda_step.status` gains `'superseded'` (`src/world_engine/models/config.py`).**
CHECK becomes, verbatim:

    "status IN ('pending','active','superseded','completed','failed')"

Add above the class, verbatim:

    # `superseded` (schema vX.YY, TICKET-0077, BRIEF-0077-d): a step the player
    # never attempted, set aside by a plan revision. It is NOT `failed` — the
    # step did not fail, the plan changed around it — and it is deliberately
    # NOT a deletion: the superseded rows and their agenda_step_requirement
    # children stay on disk, which is what makes "what did this plan look like
    # before the world moved" answerable. `superseded` is terminal: no writer
    # transitions a row out of it.

**2. Migration `scripts/migrate_vX_YY_step_superseded.py`.** Same fail-closed
env preamble as `migrate_v1_95_parked_plans.py`. One piece: rebuild
`agenda_step` following the v1.95 script's own sequence exactly -- one
`engine.begin()`, `PRAGMA foreign_keys=OFF`, `PRAGMA legacy_alter_table=ON`,
`DROP INDEX IF EXISTS idx_agenda_step_agenda` and
`DROP INDEX IF EXISTS idx_agenda_step_one_active`,
`ALTER TABLE agenda_step RENAME TO agenda_step_old`,
`models.AgendaStep.__table__.create(conn)`, column-explicit
`INSERT INTO agenda_step (...) SELECT ... FROM agenda_step_old`,
`DROP TABLE agenda_step_old`, both pragmas restored. Never `SELECT *`. Skip when
the live CHECK already contains `'superseded'`. Print one line. Idempotent.

**3. `writes/goals_agendas.py::write_plan_revision` -- the sole revision write.**

    def write_plan_revision(
        db: Session, *, world_id: str, agenda: Agenda, steps: list[PlanStep],
        active_step_index: Optional[int] = None,
    ) -> list[AgendaStep]:

All-or-nothing, `write_day_plan`'s shape: call `_clean_plan_steps` FIRST, before
any row is touched. Then, in order:
  a. Read the agenda's steps ordered by `step_order`. Partition: terminal
     (`completed`, `failed`, `superseded`) and non-terminal (`active`,
     `pending`).
  b. Transition every NON-TERMINAL step to `superseded` through
     `write_agenda_step_status` -- never a bare attribute assignment, so
     `change_history` is appended on each. Then `db.flush()`: the partial unique
     index `idx_agenda_step_one_active` would otherwise reject the new active
     step while the old one is still `active`.
  c. Write the revised steps through `write_agenda_step`, `step_order`
     continuing from `max(existing step_order) + 1` -- never renumbered, never
     reused. Terminal steps keep their original ordinals; the plan's history
     reads as one increasing sequence.
  d. Attach `AgendaStepRequirement` rows exactly as `write_day_plan` does.
  e. Return the new steps.
Raise `ValueError` (not `HTTPException`) on any validation failure, matching
`write_day_plan`. Docstring states, verbatim:

    Revision NEVER deletes and NEVER edits an existing step's `objective`:
    it sets the untried steps aside and appends the new ones. Completed and
    failed steps are untouchable — history is sacred, and a revision that
    rewrote them would make the day accounts already narrated to the player
    false in retrospect.

Add to `tooling/verify/canon_write_policy.txt`, in the same shape as
`write_day_plan`'s entry and with a comment naming this brief:

    src/world_engine/writes/goals_agendas.py::write_plan_revision  agenda_step_requirement

`write_plan_revision`'s own body must `db.add` nothing but
`AgendaStepRequirement`; the `agenda_step` writes go through the two existing
allow-listed helpers.

**4. `_finalize_modify` becomes the revision path
(`cockpit/day_reconcile_apply.py`).** Replace the 422. In order:
  a. `remaining = [s for s in steps if s.status in ("active","pending")]` and the
     existing `remaining_summary` -- unchanged.
  b. `emit_plan(...)` with both summaries -- unchanged; `LlmParseError` -> 502
     with the existing message.
  c. If `_revised_plan_matches_remaining(revised_steps, remaining)` -> the
     revision is a no-op: write NOTHING, set `pass_play.status`/`agenda_id`,
     commit, and return `_reconciliation_dict(recon, [])` with
     `"revision": None`. A revision that changes nothing must not churn
     `change_history`.
  d. Otherwise: evaluate requirements, `budget_cut`, `feasibility_veto` -- the
     SAME three Python judges `_finalize_plan` runs, in the same order, on the
     revised steps. Reuse `_finalize_plan`'s helpers rather than reimplementing
     them; if that needs a shared private function, extract one and have BOTH
     call sites use it.
  e. `write_plan_revision(db, world_id=..., agenda=agenda, steps=[...],
     active_step_index=0 if verdict.veto_retained > 0 else None)`,
     `ValueError` -> `HTTPException(422, str(exc))`.
  f. `write_day_feasibility(db, pass_play=pass_play, verdict=verdict)`, then
     `pass_play.status = "resolving"`, `pass_play.agenda_id = agenda.id`,
     `db.add(pass_play)`, ONE `db.commit()`.
  g. Return `_reconciliation_dict(recon, [])` plus a `"revision"` block:
     `{"superseded_count": <int>, "steps": [...]}` where `steps` uses
     `_plan_step_dict`'s existing shape. Still no `agenda_id`, still no
     `step_id`.
Keep the function at or under 80 lines; extract helpers as needed.

**5. `plan_action`'s paused-`modify` row (`src/world_engine/day_reconcile.py`).**
BRIEF-0077-c mapped `("modify","paused") -> "resume"` with an inline comment
saying revision was not yet available. Change it to `"modify"` and replace the
comment with, verbatim:

    # BRIEF-0077-d: revision exists now — a `modify` on a parked plan revises
    # it rather than resuming it unchanged. The resume swap in
    # `_reconcile_and_finalize` still runs first (action != "replace"), so the
    # revision writes into an agenda that is already `active`.

**6. Stale-proposal interaction -- REPORT ONLY, no code.** A pending
`agenda_step_change` proposal whose step this revision supersedes becomes stale.
[M] `_mutation_apply_agenda_step_change` already returns
`"agenda_step_change: step no longer active — world moved since the tick"` for
exactly that case, so the existing stale guard covers it. Add NOTHING; state in
the execution notes that the guard was checked and found sufficient. Do not add
a pre-revision sweep of the queue and do not extend
`_guard_no_pending_agenda_step_change`.

**7. Extend `tooling/verify/checks/day_plan.py` -- R25, R26, R27.**
  - R25 `check_step_status_vocabulary()`: `ck_agenda_step_status`'s SQL is
    exactly the five values `pending|active|superseded|completed|failed`.
  - R26 `check_revision_never_deletes()`: `write_plan_revision` contains no
    `.delete(`, no `db.delete`, and no `Assign` to an `AgendaStep`'s `objective`
    or `step_order` attribute; and it calls `write_agenda_step_status` and
    `write_agenda_step`. Zero calls located -> FAIL. Docstring states it proves
    the append-only SHAPE, not that the revision is semantically right.
  - R27 `check_revision_reuses_the_three_judges()`: `_finalize_modify`'s body
    references `evaluate_requirements` (or the shared helper extracted in item
    4d), `budget_cut` and the feasibility veto, and calls `write_plan_revision`.
    Zero references -> FAIL. This is the rule that keeps a revised plan from
    escaping the budget the fresh path is held to.
  - `check_applier_action_vocabulary_unwidened` is NOT modified and must stay
    green.

**8. Creation intrigues tab.** `frontend/src/creation/Intrigues.svelte` renders
`superseded` steps distinctly from `failed` and offers no action button on them
(they are terminal). `intrigues.svelte.js::setStepStatus` is NOT widened --
`superseded` is written by the revision path only, never by hand.

## Scope OUT

- **Widening `_mutation_apply_agenda_step_change`.** No `insert`, no `reorder`,
  no `edit`, no `supersede` action. Revision is a direct write for the same
  reason parking is: a plan's untried steps have no world footprint. If a
  reviewer asks for a queue path, that is a decision to reopen, not to
  implement.
- **Transitioning a row OUT of `superseded`.** It is terminal. No un-supersede,
  no reactivate, no CRUD control.
- **Touching `completed` or `failed` steps** in any way.
- **Renumbering `step_order`.**
- **Revising an NPC-owned agenda.** `write_plan_revision` is reached only from
  the day chain, whose agenda is always the player's. Do not expose it in the
  Creation CRUD.
- **`replace` and `continue`/`resume` behaviour.** Unchanged from -c.
- **The selection call and its prompt.** Unchanged from -c; no new usage, no new
  head, no ninth-to-tenth head count edit.
- **A new prompt for revision.** `emit_plan`'s existing `day_plan` head with
  `standing_steps_summary` is the revision emitter, exactly as `_finalize_modify`
  already uses it.
- **`_load_active_agenda`'s NULL fallback**, still untouched.

## Invariants to defend

- **History is sacred.** This step's central risk. Superseded rows and their
  requirement children stay on disk; every status move appends to
  `change_history`; no `objective` is ever edited in place; no row is deleted.
- **Single canon-write authority per resource type.** `agenda_step` keeps
  exactly two writers. `write_plan_revision` orchestrates them and adds only
  `AgendaStepRequirement` rows of its own -- one new allow-list line, no more.
- **Model proposes, code judges.** The revised step list is a proposal; the
  three Python judges (requirements, budget, veto) run on it in the same order
  as on a fresh plan. Item 7's R27 is what keeps that true.
- **The structural one-active-step invariant.** The flush in item 3b is what
  keeps `idx_agenda_step_one_active` satisfied across the supersede/append
  boundary; without it the write fails with an IntegrityError.
- **Fail-closed on validation.** `_clean_plan_steps` runs before any row is
  touched: a malformed revision leaves the plan exactly as it was.
- **No structure without a reader.** `superseded`'s readers are item 4's
  partition, item 8's Creation rendering, and R25/R26.
- **The positional wall.** Untouched.

## Done means

- [ ] A `backup.py` run precedes the migration (canon table rebuild).
- [ ] `python scripts/migrate_vX_YY_step_superseded.py` runs, prints applied,
      and a second run prints skipped.
- [ ] `sqlite3 ~/.world_engine/world_engine.db ".schema agenda_step"` shows the
      five-value CHECK and both indexes recreated under their original names;
      the row count before and after the rebuild is identical.
- [ ] `SELECT COUNT(*) FROM agenda_step_requirement` is unchanged by the
      rebuild.
- [ ] Live: park a plan, advance the world so one of its remaining steps'
      requirements is no longer met, then declare a day that resumes and bends
      that plan. The response carries `reconciliation.action == "modify"` and a
      `revision` block with `superseded_count >= 1`.
- [ ] After that revision: the plan's completed steps are untouched; its former
      `pending` steps read `superseded`; the new steps carry `step_order` values
      strictly greater than every pre-existing one; exactly one step is
      `active`.
- [ ] Each superseded step's `change_history` has a new entry whose `status` is
      its pre-revision value.
- [ ] `SELECT COUNT(*) FROM agenda_step_requirement WHERE step_id IN (<superseded ids>)`
      is non-zero -- the children survived.
- [ ] A revision whose re-emitted plan is identical to the remaining steps
      writes nothing: no `change_history` entry is added, `revision` is null.
- [ ] A pending `agenda_step_change` proposal for a superseded step, approved
      after the revision, returns the existing stale message and applies
      nothing.
- [ ] The Creation intrigues tab renders `superseded` distinctly and offers no
      button on those steps.
- [ ] `python tooling/verify/checks/day_plan.py` exits 0 with R25-R27 in its
      PASS line, and `check_applier_action_vocabulary_unwidened` still green.
- [ ] `python tooling/verify/checks/single_canon_write.py` exits 0 with exactly
      one new allow-list line.
- [ ] `python tooling/verify/run.py` green, `corpus_gate.py` included.
- [ ] `wc -l` on every touched `src/` module under 1000; no function over 80
      lines.
- [ ] `/review-step` and `/close-step` run and reported.

## Docs to update

- `world-engine-schema-changelog.md` -- new `vX.YY` entry: the
  `agenda_step.status` widening, the rebuild it required, and the statement that
  `superseded` is terminal and never deleted.
- `world-engine-schema.md` -- the `agenda_step` section (five-value status, the
  append-only revision shape) and the `Current schema version:` line.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` -- new subsection: why revision
  is a direct write rather than a widened `agenda_step_change` applier; why
  superseded steps are kept rather than deleted; and the closure note for
  TICKET-0077's decision E3.
- `tooling/verify/canon_write_policy.txt` -- one new line, item 3.
- `CLAUDE.md` -- no change expected; report if the contract check disagrees.
