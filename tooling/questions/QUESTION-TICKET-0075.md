# QUESTION — TICKET-0075
Trigger: D1-c
## Context

Executing BRIEF-0075-f-reconciliation-closure.md. Mini-RECON (M3) read
`_mutation_apply_agenda_step_change` (`src/world_engine/cockpit/mutations.py:766`):
its payload accepts only `{step_id, action}` with `action in ("complete",
"fail")`. There is no action that flips a `pending` `AgendaStep` to `active`
without an existing `active` step to complete first.

BRIEF-0075-f's Scope IN item 2 (`continue` verdict) requires exactly that:

> **`continue`** — no structural change. The standing agenda's next
> `pending` step is proposed `active` via `agenda_step_change`.

This is not a rare corner case invented during RECON — it is the ticket's
own documented recovery path. `ARCHITECTURE_DECISIONS.md`'s BRIEF-0075-d
AMENDMENT 1 (V1) section states: "`fail` fails the WHOLE agenda ... so a
failed step terminates the day's plan rather than pausing it; recovery is
BRIEF-0075-f's reconciliation." The BRIEF-0075-e section on the armed
rendezvous repeats it: "the next day's reconciliation (BRIEF-0075-f) is the
recovery path."

The state a failed-then-reactivated agenda is in is real and reachable
today: `PATCH /agendas/{agenda_id}` (`cockpit/crud/agendas.py:212`) lets
Nia set a `failed` agenda back to `active` ("reactivate"). Failing an
agenda (`_mutation_apply_agenda_step_change`, action=`fail`) only
transitions the failing step to `failed` and the agenda to `failed` — it
never touches the remaining `pending` steps. So a reactivated agenda can
have `status='active'` with ZERO `active` steps and one or more `pending`
steps waiting — precisely the state BRIEF-0075-f's `continue` verdict must
recover from.

BRIEF-0075-f's own Scope OUT, however, says:

> **Widening `agenda_step_change`.** If the `modify` diff does not fit,
> STOP.

Adding an "activate a pending step with no prior active step" action IS a
widening of `agenda_step_change` — the same widening the brief forbids for
`modify`. The brief asks for an effect and forbids the only mechanism that
could express it, for the exact scenario the rest of the ticket has been
deferring to this brief since -d-amendment-1.

## Question

How should `day_reconcile.py`'s `continue` verdict express "activate the
standing agenda's next pending step" when no step is currently active,
given `agenda_step_change` currently accepts only `action in ("complete",
"fail")`?

## Options

A. Widen `agenda_step_change` with a new `action: "activate"` — payload
   `{step_id, action: "activate"}`, no `effects`, no completion side
   effects (`_apply_completion_effects` not invoked). Same review-queue
   gate as `complete`/`fail`; `_mutation_apply_agenda_step_change` gains
   one more accepted action, guarded by the same `step.status == "pending"`
   / partial-unique-index discipline. Smallest, most literal fix — this is
   what I'd implement absent other direction.

B. Narrow BRIEF-0075-f's `continue` verdict: when the standing active
   agenda has zero active steps, treat it the same as "no active agenda"
   at `/plan` time (skip reconciliation, emit a fresh plan) rather than
   resuming the old one — defer true mid-agenda recovery-from-failure to a
   later ticket. Leaves the `PATCH /agendas/{id}` "reactivate" affordance
   present but practically inert for continuing a plan.

C. Something else Nia specifies.

## Response

