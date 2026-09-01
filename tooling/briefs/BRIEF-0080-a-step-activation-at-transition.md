# BRIEF - Step "step activation at the agenda transition"

TICKET-0080, brief a of b. Ships BEFORE BRIEF-0080-b.

## Mini-RECON (measured on `main`, schema v1.96)

| Fact | Anchor | Tag |
|---|---|---|
| The false 409 | `src/world_engine/cockpit/day_reconcile_apply.py:52-63` | [M] |
| Guard filters `status == "active"` only, never counts `pending` | same, line 53 | [M] |
| Z4 repair helper | `src/world_engine/cockpit/crud/agendas.py:216-234` | [M] |
| Z4's only call site | `src/world_engine/cockpit/crud/agendas.py:250` | [M] |
| `resume` activates without the repair | `src/world_engine/cockpit/day_reconcile_apply.py:176` | [M] |
| Plan born with zero active steps | `src/world_engine/cockpit/routes/day.py:484` | [M] |
| `write_day_plan` honours `active_step_index=None` | `src/world_engine/writes/goals_agendas.py:639` | [M] |
| `write_agenda_status`, lines 488-547 (60 lines, cap 80) | `src/world_engine/writes/goals_agendas.py:488` | [M] |
| `write_agenda_step_status` already in the same module, defined earlier | `src/world_engine/writes/goals_agendas.py:318` | [M] |
| `AgendaStep` already imported in `goals_agendas.py` | module header | [M] |
| Call sites of `write_agenda_status` (5, exhaustive) | mutations.py:820, mutations.py:822, crud/agendas.py:246, day_reconcile_apply.py:176, day_plans.py:56 | [M] |
| Module budgets: goals_agendas 646/1000, crud/agendas 297/1000 | `wc -l` | [M] |

Of the five call sites, exactly two can pass `status="active"`:
`crud/agendas.py:246` (creator PATCH, any agenda) and
`day_reconcile_apply.py:176` (day chain `resume`, player plan only). The other
three pass `completed`, `failed`, or `paused` and are unaffected. [M]

## Context

The day chain's `resume` branch and the creator's PATCH route are the two
canon-write paths that can turn an agenda `active`. Only the second repairs
the "active agenda with pending steps but no active step" state. A parked day
plan therefore resumes into a state `_finalize_continue` refuses, with a
message that prescribes destroying the plan. The repair belongs at the
transition, not at one of its callers - the same reasoning that put the
one-active-per-character guard inside `write_agenda_status` in BRIEF-0077-a
rather than at each caller.

## Scope IN

1. **Relocate the helper.** Move `_activate_lowest_pending_step_if_none_active`
   from `src/world_engine/cockpit/crud/agendas.py` to
   `src/world_engine/writes/goals_agendas.py`, as a module-level private
   function placed immediately BEFORE `write_agenda_status`. The body is moved
   BYTE-IDENTICAL except:
   - the parameter type annotation `db: DbSession` becomes `db: Session`
     (the type name in scope in the destination module);
   - the docstring gains the paragraph in item 3 below.

   No behaviour change in the moved body. Do not "improve" the query, the
   ordering, or the idempotence check.

2. **Call it from the transition.** In `write_agenda_status`
   (`writes/goals_agendas.py:488`), after `db.add(agenda)` and after the
   `_cascade_agenda_status_to_goals` block, and BEFORE `return agenda`, add:

   ```python
       if status == "active":
           _activate_lowest_pending_step_if_none_active(agenda, db)
   ```

   Placement is load-bearing: it must run AFTER the one-active-per-character
   guard has passed (so a rejected activation promotes nothing) and AFTER
   `agenda.status` has been written (so the row and its steps move in one
   transaction).

3. **Docstring, verbatim.** Append this paragraph to the relocated helper's
   docstring, exactly as written:

   > Relocated from `cockpit/crud/agendas.py` to this module (TICKET-0080,
   > BRIEF-0080-a) and called from `write_agenda_status`'s `active` branch.
   > Z4 was a repair at ONE of the two paths that produce an `active`
   > agenda; the day chain's `resume` branch reached the other one
   > (`day_reconcile_apply.py`) and skipped it, so a parked plan with no
   > active step resumed into a state `_finalize_continue` refuses. Binding
   > the repair to the TRANSITION rather than to a caller is the same move
   > BRIEF-0077-a made for the one-active-per-character guard: structural,
   > not by convention.

4. **Delete the call site and the definition in `crud/agendas.py`.** Remove
   the helper's definition and the `if body.status == "active":
   _activate_lowest_pending_step_if_none_active(agenda, db)` block at
   `crud/agendas.py:249-250`. `write_agenda_status` now does it. The route's
   observable behaviour must be IDENTICAL - same response body, same status
   codes, same rows written.

5. **Clean the orphaned imports in `crud/agendas.py`.** After the deletion,
   check whether `AgendaStep`, `select`, and `write_agenda_step_status` are
   still used in that module. Remove only those that are genuinely unused.
   Report which ones were removed.

6. **Extend `tooling/verify/checks/parked_plan_guard.py`** with two rules, in
   that file's existing `FAILURES` / `_record` / `check_vacuity` /
   `_report_and_exit` idiom (do not invent a new one):

   - **R7 (repair at the transition):** the `write_agenda_status` FunctionDef
     in `writes/goals_agendas.py` contains at least one `ast.Call` whose func
     is an `ast.Name` with id `_activate_lowest_pending_step_if_none_active`.
     Zero is a FAILURE. `_record("R7", n_calls_found)`.

   - **R8 (single definition):** walk every `*.py` file under
     `src/world_engine/`. Any `ast.FunctionDef` named
     `_activate_lowest_pending_step_if_none_active` in a file other than
     `writes/goals_agendas.py` is a FAILURE naming `file:lineno`. Exactly one
     definition must exist in total; zero, or two or more, is a FAILURE.
     `_record("R8", n_files_scanned)` - scanning zero files is vacuous and
     must fail.

   Add both to `main()` in order, before `check_vacuity()`. Update the
   module docstring's rule list and the PASS message to mention them.

7. **Commit shape.** Two commits, in this order:
   - `refactor: relocate step activation repair to write_agenda_status`
     (items 1-5, pure relocation plus the one call, no verify changes)
   - `test: parked_plan_guard R7/R8 - repair bound to the transition`
     (item 6)

## Scope OUT

Named temptations, all of them discussed and deliberately excluded:

- **Do NOT touch `cockpit/routes/day.py:484**` (`active_step_index = 0 if
  verdict.veto_retained > 0 else None`). A plan born with no active step is
  INERT BY INTENTION (locked decision G3): the feasibility veto judged nothing
  startable. Forcing step 1 active there would overwrite that judgement. That
  behaviour is a separate workstream with its own reactivation condition.

- **Do NOT make the promotion conditional on requirements.** The full G3
  shape - re-evaluate the pending step's requirements and refuse to promote an
  unmet one - is deferred. This brief promotes unconditionally, exactly as Z4
  does today at the PATCH route. Day resolution re-evaluates requirements
  anyway (`day_resolve.py:199-221`) and the `blocked` band (BRIEF-0078-b)
  already surfaces an unmet prerequisite as a narrated outcome, so an
  unconditional promotion cannot produce a false success.

- **Do NOT change `_finalize_continue`'s message or status code.** That is
  BRIEF-0080-b. After this brief the guard is unreachable via `resume`; it
  stays reachable via `continue` on a born-inert plan, and its message stays
  wrong until b lands. This is accepted, sequenced, not forgotten.

- **Do NOT add explicit day-declaration intent** (`continue` vs `new`). Named
  deferral with its own reactivation condition in the ticket.

- **Do NOT widen `agenda_step_change`'s action vocabulary.** It stays exactly
  `("complete", "fail")`, as BRIEF-0075-f AMENDMENT 1 already states.

- **Do NOT extract or refactor `write_agenda_status`** beyond the three added
  lines. It is 60 lines and the cap is 80; there is headroom and no reason.

- **No schema change.** No column, no constraint, no migration, no version
  bump.

## Invariants to defend

- **Single canon-write authority.** The promotion goes through
  `write_agenda_step_status`, never a direct `step.status = ...` assignment.
  `change_history` is appended on every transition - history stays sacred.

- **History is sacred.** The relocated helper appends; it never edits. No
  retroactive rewrite of any `change_history` entry.

- **Structural over disciplinary.** The whole point: the repair stops being
  something a caller must remember and becomes a property of the transition.
  R7/R8 are what make that checkable rather than asserted.

- **No structure without a reader.** No new field or table. The relocated
  helper's reader is `write_agenda_status` itself, and R8 proves there is no
  second, silently divergent copy.

- **Autoflush trap.** `write_agenda_step_status` calls `db.add`; the caller at
  `day_reconcile_apply.py:177` already has the `db.flush()` that makes the
  promoted step visible to `_finalize_continue`'s subsequent SELECT in the
  same session. Do not remove that flush. Do not add a `db.commit()` inside
  the helper - the transaction belongs to the caller.

- **Faction owners keep their multi-agenda freedom.** The promotion is
  unconditional on owner type, exactly as Z4 is today at the PATCH route. This
  is preservation, not widening; do not add an owner-type filter.

## STOP conditions

The executor STOPS and reports rather than deciding, if any of these hold:

- **S1** - `write_agenda_status` has call sites beyond the five enumerated in
  the mini-RECON. Enumeration scope discipline: the coverage claim in this
  brief is only valid over a complete inventory.
- **S2** - removing the helper from `crud/agendas.py` changes the PATCH
  route's observable behaviour in any way other than "identical" (different
  response body, different status code, different rows).
- **S3** - the relocated body cannot be moved without modification beyond the
  two changes named in item 1.
- **S4** - `parked_plan_guard.py` would exceed the module budget, or its
  existing idiom does not admit R7/R8 as described.

Everything else found during execution: REPORT ONLY, no fix.

## Done means

Machine-checkable:

- [ ] `python tooling/verify/checks/parked_plan_guard.py` exits 0 and its PASS
      message names R7 and R8.
- [ ] Deliberately break R7 (comment out the call in `write_agenda_status`):
      the check exits 1 and names it. Restore.
- [ ] Deliberately break R8 (paste a second definition of the helper into
      `cockpit/crud/agendas.py`): the check exits 1 and names `file:lineno`.
      Restore.
- [ ] `grep -rn "_activate_lowest_pending_step_if_none_active" src/` returns
      exactly two lines: the definition and the call, both in
      `writes/goals_agendas.py`.
- [ ] `python tooling/verify/checks/module_budget.py` exits 0.
- [ ] `python tooling/verify/checks/function_length.py` exits 0.
- [ ] `python tooling/verify/checks/single_canon_write.py` exits 0.
- [ ] `/review-step` and `/close-step` both run (engine code is touched).

Live gate (Nia):

- [ ] A day plan is created whose first step has an unmet prerequisite, so it
      is born with zero active steps. It is then parked (declare an unrelated
      day, `replace` verdict). A third declaration targeting the parked plan
      resumes it: the response is 200 with `reconciliation.action == "resume"`,
      NOT a 409.
- [ ] The promoted step's `change_history` shows one appended entry with the
      previous `pending` status. No prior entry is altered.
- [ ] `PATCH /agendas/{id}` with `status: "active"` on a plan with no active
      step still promotes the lowest pending step, exactly as before.
- [ ] A plan whose every step is terminal, activated via PATCH, promotes
      nothing and returns normally (idempotent no-op preserved).

## Docs to update

- **No schema version bump.** No DDL. Do not touch the
  `Current schema version:` line in `world-engine-schema.md`. State this
  explicitly in the commit body so the absence reads as a decision.
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: new subsection under the day
  chain, recording (a) that step activation is bound to the `-> active`
  transition rather than to its callers, (b) the two paths that were
  asymmetric and why, (c) the G3 deferral - born-inert plans are inert by
  intention - with its reactivation condition (BRIEF-0080-b's 422 branch
  firing in a live session).
- `CLAUDE.md`: no change. This adds no new invariant, it enforces an existing
  one structurally. Do not spend budget.

## Drafting decisions embedded in this brief

Flagged for Nia to reverse before sending:

1. **The promotion stays unconditional.** G3 is locked as doctrine but its
   behavioural half is deferred, so this brief promotes without re-evaluating
   requirements. Justification: the `blocked` band already catches an unmet
   prerequisite at resolve time, so this cannot yield a false success. If you
   want the conditional promotion NOW, this brief grows an import from
   `day_plan.py` into `writes/goals_agendas.py` and stops being a pure
   relocation - say so and I will restructure rather than patch.

2. **Placement after the cascade block, not before.** Chosen so a rejected
   activation (the one-active guard raising) promotes nothing. The alternative
   - promote first, guard after - would leave a promoted step behind a raised
   `ValueError`.

3. **`crud/agendas.py` keeps its route unchanged rather than being simplified
   further.** There is a visible temptation to also fold the `body.status`
   validation or the `_agenda_dict` call; excluded to keep the diff a
   relocation.

4. **R8 scans all of `src/world_engine/`, not just the two known files.** More
   expensive, but a copy of the helper appearing in a third module is exactly
   the failure this rule exists to catch.
