# BRIEF - Step "continue-guard verdict split"

TICKET-0080, brief b of b. Ships AFTER BRIEF-0080-a is merged and green.

## Mini-RECON (measured on `main`, schema v1.96)

| Fact | Anchor | Tag |
|---|---|---|
| The single conflated verdict | `src/world_engine/cockpit/day_reconcile_apply.py:52-63` | [M] |
| `_finalize_continue` signature (no `character`) | `day_reconcile_apply.py:43` | [M] |
| Caller has `character` in scope | `day_reconcile_apply.py:152-153` | [M] |
| `resume` reuses `continue`'s handler | `day_reconcile_apply.py:186` | [M] |
| Per-step evaluation block to extract | `src/world_engine/day_resolve.py:199-221` | [M] |
| `evaluate_requirements(step, character, db)` | `src/world_engine/day_plan.py:243` | [M] |
| `EvaluatedStep`, `PlanStep`, `RequirementSpec`, `Verdict` all live in `day_plan.py` | `day_plan.py:86-118` | [M] |
| `requirement_detail_fr(verdict) -> str`, fail-closed | `src/world_engine/day_resolve.py:284-291` | [M] |
| `day_resolve.py` imports `day_plan`, never `cockpit` - so `day_reconcile_apply -> day_resolve` is acyclic | `day_resolve.py:70-89` | [M] |
| `day_plan.py` does NOT yet import `AgendaStep` / `AgendaStepRequirement` | `day_plan.py:49-58` | [M] |
| Module budgets: day_plan 506/1000, day_resolve 471/1000, day_reconcile_apply 200/1000, verify/day_plan 1116 | `wc -l` | [M] |

Note on the last row: `tooling/verify/checks/day_plan.py` is at 1116 lines.
Confirm whether `module_budget.py`'s cap applies to `tooling/` before adding
rules there - see STOP condition S4.

## Context

After BRIEF-0080-a the `resume` path no longer reaches the guard: the
transition promotes a pending step. One path still reaches it - a plan born
with `active_step_index = None` (feasibility veto retained zero steps) that
was never parked, selected with a `continue` verdict. For that plan the guard
is correct to refuse and wrong in what it says: it reports exhaustion when the
plan is blocked, and prescribes `abandoned` when the work is intact. Two
failure modes sharing one message is what sent Nia toward destroying a
recoverable plan.

## Scope IN

### Commit 1 - pure move, no behaviour change

1. **Extract the per-step evaluation into `day_plan.py`.** Add, immediately
   after `evaluate_requirements`:

   ```python
   def evaluate_agenda_step(agenda_step: AgendaStep, character: Character, db: Session) -> EvaluatedStep:
   ```

   Its body is `day_resolve._load_evaluated_steps`'s loop body, moved
   byte-identical: the `select(AgendaStepRequirement).where(
   AgendaStepRequirement.step_id == agenda_step.id)` read, the `PlanStep`
   construction from `objective`/`cost`/`domain`/`requirements`, the
   `evaluate_requirements` call, and the `EvaluatedStep` construction. Add
   `AgendaStep` and `AgendaStepRequirement` to `day_plan.py`'s `.models`
   import.

   Docstring, verbatim:

   > One `agenda_step` row plus its requirement rows, judged against
   > `character`'s current state (TICKET-0080, BRIEF-0080-b). Carved out of
   > `day_resolve._load_evaluated_steps` unchanged so that the day chain's
   > resolve walk and `_finalize_continue`'s refusal path share ONE
   > evaluation, rather than growing a second copy that can drift.

2. **`day_resolve._load_evaluated_steps` calls it.** Replace the loop body
   with `evaluated_steps.append(evaluate_agenda_step(agenda_step, character,
   db))`. Add `evaluate_agenda_step` to the existing `from .day_plan import
   (...)` block. Remove `AgendaStepRequirement` and `RequirementSpec` from
   `day_resolve.py`'s imports ONLY if they become unused - check, do not
   assume.

3. This commit changes no behaviour. If it does, that is S1.

### Commit 2 - the verdict split

4. **`_finalize_continue` takes `character`.** New signature:

   ```python
   def _finalize_continue(
       character: Character, pass_play: PassPlay, agenda: Agenda,
       recon: Reconciliation, db: Session,
   ) -> dict:
   ```

   Update the two dispatch entries in `_reconcile_and_finalize`'s `handlers`
   dict (`"continue"` and, through the alias assignment, `"resume"`).
   `character` is already a parameter of `_reconcile_and_finalize`.

5. **Split the refusal.** Replace lines 52-63 with:

   ```python
       active_step = db.exec(
           select(AgendaStep).where(AgendaStep.agenda_id == agenda.id, AgendaStep.status == "active")
       ).first()
       if active_step is None:
           _refuse_unstarted_plan(character, agenda, db)
   ```

   and add a module-level helper `_refuse_unstarted_plan(character, agenda,
   db) -> NoReturn` that always raises. Two branches:

   - **Exhausted** - no `pending` step either. Raise 409 with detail,
     verbatim:

     ```
     the standing plan {title!r} has no step left at all - every step is
     completed or failed. Close it (PATCH its status to 'completed' or
     'abandoned') before declaring again.
     ```

   - **Unstarted** - at least one `pending` step exists (lowest
     `step_order`). Raise 422 with detail, verbatim:

     ```
     the standing plan {title!r} has not started: its first remaining step
     ({objective!r}) was judged infeasible when the plan was created and no
     step is active. Reason: {detail}. The plan is intact - do NOT abandon
     it.
     ```

     `{detail}` is built by calling `evaluate_agenda_step` on that pending
     step and joining `requirement_detail_fr(v)` over every verdict with
     `v.met is False`, separated by `"; "`. If every verdict is met, or the
     step carries no requirements, `{detail}` is the literal string
     `"aucun prerequis non satisfait - le veto de faisabilite a juge l'action
     elle-meme irrealisable"`.

   The word `abandoned` must not appear in the 409 branch as a lone remedy,
   and the 422 branch must state that the plan is intact.

6. **Import `requirement_detail_fr`** into `day_reconcile_apply.py` via
   `from ..day_resolve import requirement_detail_fr`, and
   `evaluate_agenda_step` via the existing `..day_plan` import path. Both are
   acyclic per the mini-RECON.

7. **Extend `tooling/verify/checks/day_plan.py`** with two rules, in that
   file's existing idiom:

   - **R13 (two verdicts, no false remedy):** across `_finalize_continue` and
     `_refuse_unstarted_plan` in `cockpit/day_reconcile_apply.py`, the set of
     `status_code` constants on `HTTPException` raises equals exactly
     `{409, 422}`. At least one `ast.Compare` against the string constant
     `"pending"` appears. No string constant in the 409 raise contains
     `abandoned` as the only prescribed action - concretely: if a constant
     contains `abandoned`, it must also contain `completed`. Zero raises
     collected is a FAILURE.

   - **R14 (one evaluation, two readers):** `evaluate_agenda_step` has exactly
     one `ast.FunctionDef` under `src/world_engine/`, in `day_plan.py`; and it
     is called from BOTH `day_resolve.py` and `cockpit/day_reconcile_apply.py`.
     Fewer than two calling modules is a FAILURE - the rule exists to prove
     the extraction has readers, not just a home.

   Add both to `main()` before the vacuity rule; `_record` counts for each;
   update the module docstring and PASS message.

8. **Commit shape.** Exactly two commits, in the order above. The pure move
   lands first so the logic diff is readable and the module budget picture
   stays honest.

## Scope OUT

- **Do NOT make the 422 branch recover.** Promoting the blocked step,
  re-running the veto, re-emitting the plan, or auto-abandoning it are all the
  G3 workstream. This brief refuses correctly and says why. The 422 firing in
  a live session IS G3's reactivation condition - swallowing it here would
  erase the trigger.

- **Do NOT touch `cockpit/routes/day.py:484`.** Same reason as BRIEF-0080-a.

- **Do NOT touch `plan_action`'s mapping** (`day_reconcile.py:73-90`) or
  `EXPECTED_PLAN_ACTIONS`. The four actions and the handler bijection stay
  exactly as they are; `resume` still aliases `continue`'s handler.

- **Do NOT change `_finalize_modify`'s 422** ("revised plan cannot be
  expressed as agenda_step_change mutations"). Different failure, different
  brief, leave its wording alone.

- **Do NOT touch the `blocked` band or `_append_blocked_step`.** Resolve-time
  narration is TICKET-0078's and stays untouched.

- **Do NOT add prompt examples anywhere.** Standing rule.

- **No schema change**, no version bump, no migration.

## Invariants to defend

- **The guard asserts, it does not write.** `_refuse_unstarted_plan` reads and
  raises. No `db.add`, no `write_*`, no `db.commit()`. Any repair belongs at
  the transition (BRIEF-0080-a) or in G3, never here.

- **Fail-closed.** `requirement_detail_fr` already raises on an unknown
  requirement type. Do not wrap it in a `try` that degrades to a generic
  string - an unknown type must fail loudly.

- **No structure without a reader.** `evaluate_agenda_step` ships with two
  readers on day one, and R14 is what proves it rather than asserting it.

- **Two things meaning the same thing is an anti-pattern.** The whole reason
  for commit 1: a second, hand-rolled requirement evaluation inside the guard
  would drift from the resolve walk within one ticket.

- **Player-facing French.** The 422's `{detail}` renders through
  `requirement_detail_fr`, the existing single source of a blocked step's
  reason. The surrounding English message text is developer-facing (an
  HTTPException detail); only the requirement clause is player-facing French.
  Do not translate the frame, do not anglicise the clause.

## STOP conditions

- **S1** - the extraction in commit 1 cannot be made behaviour-identical (for
  example the `_day_reachable_ids` per-call caching inside
  `evaluate_requirements` behaves differently once called per step from a new
  site). REPORT, do not optimise, do not "fix while here".
- **S2** - `from ..day_resolve import requirement_detail_fr` trips
  `tooling/verify/checks/import_cycle.py`. Do not reach for the sanctioned
  lazy-import idiom on your own judgement - report the cycle and stop.
- **S3** - `_finalize_continue` or `_refuse_unstarted_plan` would exceed the
  80-line function ceiling.
- **S4** - `tooling/verify/checks/day_plan.py` is at 1116 lines; if
  `module_budget.py` covers `tooling/` and R13/R14 would breach the cap, STOP
  and report rather than exempting. An extraction ticket is the answer, not a
  waiver.
- **S5** - `_finalize_continue` turns out to have callers beyond the handlers
  dict in `_reconcile_and_finalize`.

Everything else found: REPORT ONLY.

## Done means

Machine-checkable:

- [ ] `python tooling/verify/checks/day_plan.py` exits 0, PASS names R13/R14.
- [ ] Break R13 (collapse the two raises back into one 409): exits 1, names
      it. Restore.
- [ ] Break R14 (delete the call in `day_resolve.py`): exits 1 and names the
      missing reader module. Restore.
- [ ] Break R14 the other way (paste a second `evaluate_agenda_step`
      definition into `day_resolve.py`): exits 1. Restore.
- [ ] `grep -rn "abandoned" src/world_engine/cockpit/day_reconcile_apply.py`
      returns only lines that also offer `completed`.
- [ ] `python tooling/verify/checks/import_cycle.py` exits 0.
- [ ] `python tooling/verify/checks/module_budget.py` exits 0.
- [ ] `python tooling/verify/checks/function_length.py` exits 0.
- [ ] `python tooling/verify/checks/parked_plan_guard.py` still exits 0
      (BRIEF-0080-a's R7/R8 unaffected).
- [ ] `/review-step` and `/close-step` both run.

Live gate (Nia):

- [ ] A plan born inert (first step blocked on an unmet prerequisite), still
      `active`, never parked, is targeted by a declaration that reconciles to
      `continue`. Response is **422**, the message names the step's objective
      and the unmet requirement in French, and states the plan is intact.
- [ ] A plan whose every step is terminal but whose agenda is still open is
      targeted the same way. Response is **409**, message names exhaustion,
      remedy offers `completed` as well as `abandoned`.
- [ ] The BRIEF-0080-a case still passes: a parked plan with pending steps
      resumes to 200, never reaching either branch.
- [ ] A normal day on a plan with an active step is unaffected - 200,
      `reconciliation.action == "continue"`.

## Docs to update

- **No schema version bump.** State the absence in the commit body.
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: extend BRIEF-0080-a's
  subsection with the verdict split - the two distinct failure modes, why they
  were conflated, and the rule that a guard asserts and never repairs.
- Record G3's reactivation condition in the same place, in its verifiable
  form: *the 422 branch of `_refuse_unstarted_plan` firing in a live session*.
- `CLAUDE.md`: no change.

## Drafting decisions embedded in this brief

1. **422 rather than 409 for the unstarted plan.** 409 says "conflict, resolve
   it"; the plan is not in conflict, the request is unprocessable against its
   current state. The split is also what makes R13 checkable at all - two
   codes, not two strings.

2. **The extraction is in this brief rather than its own.** It is ~15 lines
   and exists only to serve the 422's detail. Splitting it into a third brief
   would ship a helper with one reader, violating "no structure without a
   reader" for a full brief's duration. If you would rather it stand alone,
   say so and I will renumber.

3. **The message frame stays English, the requirement clause French.** These
   are HTTPException details, developer-facing, and the rest of the module is
   English. Only the part that quotes player-facing content is French. Reverse
   it if you would rather the whole detail be French.

4. **The 422 explicitly says "do NOT abandon it".** Blunt, and deliberately
   so: the current message's prescription is what nearly destroyed a plan.

5. **R13 checks the `abandoned` / `completed` pairing rather than banning the
   word.** A ban would be brittle - the exhausted branch legitimately offers
   abandonment. The pairing is what encodes "closure is a choice, not the only
   remedy".
