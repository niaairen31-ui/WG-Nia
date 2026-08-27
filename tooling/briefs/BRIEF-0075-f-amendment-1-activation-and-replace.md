# BRIEF-0075-f — AMENDMENT 1: step activation and `replace`

**Amends:** `tooling/briefs/BRIEF-0075-f-reconciliation-closure.md`, Scope IN
item 2 (`continue` and `replace`), the Scope OUT bullet on widening
`agenda_step_change`, and check R4.
**Date:** 2026-08-25
**Trigger:** Claude Code escalation — `continue` requires a `pending -> active`
flip that `_mutation_apply_agenda_step_change` cannot express, while the
brief's own Scope OUT forbids widening it.
**Author:** Claude (design), owning one error of reasoning.
**Status of the original:** unchanged on disk.

## The escalation was correct; the framing shifts

The escalation is right that `_mutation_apply_agenda_step_change` accepts only
`action in {complete, fail}`, that a bare `pending -> active` flip has no
mutation, and that the state — active agenda, zero active steps, pending steps
waiting — is genuinely reachable, since `PATCH /agendas/{id}` reactivates a
failed agenda and failing an agenda never touches its pending steps.

Two facts change what to do about it.

**The mechanism already exists.**
`PATCH /agenda-steps/{step_id}` accepts `status='active'` and performs exactly
that flip today (`cockpit/crud/agendas.py`), relying on the partial unique
index to reject a second active step, with the `IntegrityError` surfacing as a
409. This is CREATOR CRUD — the second sanctioned canon-write path. So nothing
is missing from the engine; the open question was only whether the day chain
may use that authority.

**In the normal case there is nothing to activate.**
After yesterday's completions are approved,
`_mutation_apply_agenda_step_change`'s cascade has already activated the
lowest-`step_order` pending step. `continue` is then a true no-op. The gap
opens only in the RECOVERY state, which is reachable exclusively through a
manual creator act — reactivating a failed agenda.

## Decision Z4 (locked) — repair the invariant at its source

The incoherent state stops being reachable, rather than being worked around
downstream.

**`PATCH /agendas/{agenda_id}` with `status='active'`** additionally activates
the lowest-`step_order` `pending` step of that agenda when the agenda has no
active step.

- Same transaction as the agenda status write.
- Uses `write_agenda_step_status` so `change_history` is appended, per that
  helper's contract. History stays sacred.
- When the agenda has NO pending steps, the route does nothing further and
  says so in its response. That agenda is inert: it is a `replace` case, not a
  `continue` case, and item 2 below handles it.
- When a step is already active, the route does nothing further. Idempotent.
- No change to `PATCH /agenda-steps/{step_id}`, which keeps working as the
  creator's manual override.

This is a repair to an existing creator route, not a widening of
`agenda_step_change`. **The Scope OUT bullet forbidding that widening stands
unchanged** — Z1 (an `activate` action on the mutation) was considered and
rejected as unnecessary once Z4 exists.

**Corrected `continue` instruction** (supersedes the Scope IN item 2
`continue` bullet):

`continue` proposes NOTHING. It is a classification with no structural effect.
The day proceeds to budget and resolve against the standing agenda's active
step. When the standing agenda has no active step AND no pending steps, the
day reports that the plan is exhausted and stops without emitting; the verdict
should have been `replace`, and the next declaration can say so.

Emitting an empty proposal for a no-op is noise in the queue and is forbidden.

## Decision AA2 (locked) — `replace` is a creator act

### An error in the original brief, corrected

BRIEF-0075-f states:

> R4. The `replace` path never emits a status of `abandoned` [...]

That reasoning was wrong. It conflated *do not erase history* with *do not use
the `abandoned` status*. `abandoned` preserves history exactly as `failed`
does — it is simply the correct terminal state: the player changed their mind,
they did not fail. `failed` additionally triggers `_cascade_agenda_status_to_goals`,
which abandons every `npc_goal` still linked to the agenda. Forcing `failed`
onto a plan the player merely dropped is both semantically wrong and a real
side effect.

### Corrected `replace` instruction (supersedes the Scope IN item 2 `replace` bullet)

`replace` emits nothing and writes nothing.

- The chain records the verdict, its cited step and its rationale, reports
  that the standing plan is being replaced, and STOPS the day. No
  `agenda_step_change`, no `agenda_creation`, no new plan.
- The response and the Journée surface state plainly that the standing plan
  must be closed before a new one can start, naming the standing agenda's
  title.
- Nia closes it through the existing `PATCH /agendas/{agenda_id}` with
  `status='abandoned'`. The old agenda stays on file with every step and every
  `change_history` entry intact.
- The player then re-declares, and with no active agenda the chain takes
  BRIEF-0075-b's fresh-plan path unchanged.

Rejected: AA1 (propose `agenda_step_change fail` — wrong terminal state plus
the goal cascade) and AA3 (add an `abandon` action or an `agenda_status_change`
mutation type — correct and automatic, but scope creep into the shared applier;
its own ticket if the manual step proves tiresome).

**Named deferral.** AA3's reactivation condition: *when `replace` has required
a manual abandon on five separate days.* Below that, the manual step is
cheaper than a new mutation type in a shared applier.

### `modify` is unaffected

`modify` still re-runs `emit_plan` with the standing agenda's remaining steps
as context and proposes the diff as `agenda_step_change` mutations bounded by
what the applier accepts. If the diff needs an action the applier does not
have, that remains S2 and a STOP.

## Check changes

- **R4 is replaced.** It no longer asserts the absence of `abandoned`. It now
  asserts: `day_reconcile.py` contains no `db.delete(`, and the `replace` path
  constructs no `ProposedMutation` at all. Fail-closed and vacuity-guarded.
- **New R10.** The `continue` path constructs no `ProposedMutation`. A no-op
  verdict emits nothing.
- **New R11.** `PATCH /agendas/{agenda_id}`'s reactivation branch calls
  `write_agenda_step_status` for the activation rather than assigning
  `.status` directly, so `change_history` is appended. Vacuity-guarded: zero
  activation branches found is a FAILURE.
- The Scope OUT check on widening `agenda_step_change` stands: assert the
  applier's action tuple is still exactly `("complete", "fail")`.

## Done means — additions

- [ ] Reactivating a failed agenda that has pending steps activates the
      lowest-`step_order` pending step in the same call, with the transition
      appended to `change_history`.
- [ ] Reactivating an agenda with no pending steps activates nothing and says
      so; a following declaration classified `continue` reports the plan
      exhausted and stops without emitting.
- [ ] Reactivating an agenda that already has an active step changes nothing.
- [ ] A `continue` verdict on a normal standing agenda emits zero mutations
      and resolves against the already-active step.
- [ ] A `replace` verdict emits zero mutations, stops the day, and names the
      standing agenda in the response.
- [ ] After a manual `PATCH /agendas/{id}` to `abandoned`, the old agenda and
      all its steps are still present with `change_history` intact, and the
      next declaration produces a fresh plan.
- [ ] No linked `npc_goal` is abandoned as a side effect of a `replace`.
- [ ] `_mutation_apply_agenda_step_change` still accepts exactly
      `("complete", "fail")`.

## Docs to update — additions

- `tooling/standards/ARCHITECTURE_DECISIONS.md`: record Z4 as an invariant
  repair at the source — an active agenda with pending steps always has
  exactly one active step, enforced where the state could be broken rather
  than patched downstream. Record AA2 and the correction: `abandoned` is the
  history-preserving terminal state for a dropped plan, and `failed` is
  reserved for a plan that was attempted and lost, because `failed` cascades
  to linked goals.
- `tooling/standards/DECISIONS_INDEX.md`: Z4, AA2, and AA3's deferral with its
  reactivation condition.

## Unaffected

The reconciliation prompt and its strict validation, the mandatory
`cited_step_order` against real values, the refusal to default to `continue`,
the `modify` path, the removal of BRIEF-0075-b's S3 refusal, the ticket
closure sweep, the vestigial-column report and the rewrite-firing counter all
stand.
