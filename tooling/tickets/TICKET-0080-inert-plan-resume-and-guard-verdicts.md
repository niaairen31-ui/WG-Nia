---
id: TICKET-0080
title: Inert plan resume and continue-guard verdict split
type: bug
status: exec
created: 2026-09-01
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: medium
brief_ids: [BRIEF-0080-a, BRIEF-0080-b]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"Lorsqu'un plan est en pause et que je veux faire une journee qui
corresponderais a ce plan, on me met l'erreur : the standing plan '...' has no
active or pending step left - close it (PATCH its status to 'abandoned')
before declaring again. Je veux que cela se fasse authomatiquement."

## Clarifications resolved (intake)

- The plan's remaining steps are `pending`; the plan itself is `paused`. The
  guard's message is therefore FALSE as written: it claims no pending step
  remains, and it prescribes `abandoned`, which would destroy resumable work.
  Automating that closure would have automated a loss. [M]

- Measured cause, three facts:

  1. `cockpit/day_reconcile_apply.py:52-63` (`_finalize_continue`) filters on
     `AgendaStep.status == "active"` only. It never counts `pending`. Its
     docstring relies on the Z4 guarantee ("an ACTIVE agenda either already
     has an active step, or has no pending step left at all"). That guarantee
     does not hold. [M]

  2. `cockpit/routes/day.py:484` -> `active_step_index = 0 if
     verdict.veto_retained > 0 else None`. When the feasibility veto retains
     ZERO steps, `write_day_plan` (`writes/goals_agendas.py:639`) writes every
     step `pending` and none `active`. The plan is born `active` with no
     active step. This is the TICKET-0078 shape: the first step blocked on an
     unmet prerequisite. [M]

  3. Z4's repair (`_activate_lowest_pending_step_if_none_active`,
     `cockpit/crud/agendas.py:216`) runs on ONE of the two paths that produce
     an `active` agenda: the creator PATCH route (`crud/agendas.py:250`). The
     day chain's `resume` branch calls `write_agenda_status(..., status=
     "active")` directly (`cockpit/day_reconcile_apply.py:176`) and skips the
     repair. The 409 is structurally guaranteed for any parked plan with no
     active step. [M]

- Locked decisions:
  - **F2** - the repair moves to the `-> active` transition itself, inside
    `write_agenda_status`, so every path that produces an `active` agenda is
    covered by construction rather than by remembering to call a helper.
  - **H2** - `_finalize_continue` splits one message into two verdicts: a plan
    truly out of steps (409, closure is the right remedy) versus a plan with
    pending steps and no started one (422, the true reason named).
  - **G3** - a plan born with `active_step_index = None` is INERT BY
    INTENTION, not by accident: the veto judged nothing feasible. Deciding
    what "resume a blocked plan" means is a separate workstream. Locked as
    doctrine here, deferred out of this ticket per I2.
  - **I2** - this ticket ships F2 + H2 only.

- Deferred, with reactivation conditions:
  - **G3 behaviour** (what a born-inert plan does when selected). Reactivation
    condition: the first live session in which BRIEF-0080-b's 422 branch
    fires. Until then the plan is refused with a true message, which is
    already strictly better than today's false one.
  - **Explicit day-declaration intent** (`continue` vs `new` stated by Nia
    rather than inferred by `reconcile`). Reactivation condition: the first
    live session in which `day_plan_select` + `reconcile` place a declaration
    on the wrong plan.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `write_agenda_status` calls the pending-step promotion helper on the
      `status == "active"` branch  -> verify/checks/parked_plan_guard.py (R7)
- [ ] No `FunctionDef` named `_activate_lowest_pending_step_if_none_active`
      exists anywhere under `src/` outside `writes/goals_agendas.py`
      -> verify/checks/parked_plan_guard.py (R8)
- [ ] `_finalize_continue` raises with BOTH status codes 409 and 422, and its
      409 detail string contains no `abandoned` literal
      -> verify/checks/day_plan.py (R13)
- [ ] `_finalize_continue` contains a `select` filtering
      `AgendaStep.status == "pending"`  -> verify/checks/day_plan.py (R13)
- [ ] `evaluate_agenda_step` is defined in `day_plan.py` and called from BOTH
      `day_resolve.py` and `cockpit/day_reconcile_apply.py` (two readers)
      -> verify/checks/day_plan.py (R14)
- [ ] Every new rule is vacuous-proof: zero items collected is a FAILURE
      -> both checks' existing vacuity rule

### Live  ->  human gate (Nia)

- [ ] A parked plan whose steps are all `pending` is selected by a day
      declaration, resumes, and the day proceeds to `resolving` with NO 409.
- [ ] `agenda_step.change_history` on the promoted step shows the
      `pending -> active` transition; nothing was edited retroactively.
- [ ] A plan that is genuinely out of steps (every step terminal, agenda still
      open) still refuses, with a 409 whose message names exhaustion and
      whose remedy is closure.
- [ ] A plan born inert and never parked refuses with a 422 that names the
      unmet requirement in French, and never suggests `abandoned`.
- [ ] `PATCH /agendas/{id}` with `status: "active"` behaves exactly as before
      the ticket.
