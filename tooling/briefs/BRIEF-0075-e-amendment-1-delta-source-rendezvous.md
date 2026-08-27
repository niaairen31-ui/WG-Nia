# BRIEF-0075-e — AMENDMENT 1: delta source and rendezvous

**Amends:** `tooling/briefs/BRIEF-0075-e-mutation-emission-day-account.md`,
Scope IN items 1 and 3.
**Date:** 2026-08-25
**Trigger:** Claude Code escalation (no delta-computation contract;
`agenda_step_change` structurally dead).
**Author:** Claude (design).
**Status of the original:** unchanged on disk. Read alongside
`BRIEF-0075-d-amendment-1-no-direct-step-write.md`, which removes the direct
write that caused the second half of the escalation.

## The contract exists — it is on the payload, not on a column

The escalation looked for an `effects` or reward column on `AgendaStep` /
`AgendaStepRequirement` and correctly found none. The contract is not stored
on the step; it travels on the mutation.

`_apply_completion_effects` (`cockpit/mutations.py`, TICKET-0024 /
BRIEF-0024-c) is shared by `goal_change complete` and
`agenda_step_change complete`:

- `_EFFECT_TYPES = frozenset({"relation_delta", "ledger_transfer", "role_change"})`
- `_MAX_EFFECTS = 3`
- the subject is FORCED to the agenda's owner by the caller and is never read
  from the payload (the O1/H1 forcing precedent)
- an invalid effect rejects the WHOLE mutation; the caller's SAVEPOINT rolls
  back anything already written

So `agenda_step_change` is not structurally dead. It is the DESIGNED carrier
of a step's world footprint, and its `effects` list is exactly the delta
contract BRIEF-0075-e was told to populate. Nothing is invented.

## Corrected instruction — Scope IN item 1

`emit_mutations` builds, per resolved step, **one `agenda_step_change`**:

- `payload["step_id"]`, `payload["action"]` in `("complete", "fail")` from the
  step's band — `failure` maps to `fail`, `partial` and `success` to
  `complete`.
- `payload["effects"]`: a list drawn from `_EFFECT_TYPES`, at most
  `_MAX_EFFECTS`. Read each `_apply_effect_*` function and match its expected
  keys exactly; do not improvise a shape. Effects are emitted on `complete`
  only — the applier ignores them on `fail`.
- The subject is NOT set in the payload. The applier forces it.
- `rationale` names the step's objective and its band.

**`EMITTED_MUTATION_TYPES` is corrected** to:
`("knowledge_change", "relation_change", "agenda_step_change", "entity_creation")`.

- `resource_change` is REMOVED: resources travel as `ledger_transfer` effects
  on the step completion, so a parallel resource path would be a second
  vocabulary for the same thing.
- `relation_change` is KEPT, but only for relation movement that belongs to no
  step — an NPC's opinion shifting because of something the day established
  rather than because a step completed. When a relation change is caused by a
  step, it is a `relation_delta` effect, not a standalone mutation. State the
  rule in the module docstring.
- `agenda_creation` is REMOVED: under V1's boundary, creating a plan has no
  world footprint and stays a direct `write_day_plan` call (BRIEF-0075-b).
- `npc_move` remains absent (N1). Check R2 stands.

## Ordered approval — a new operational constraint

`_mutation_apply_agenda_step_change` already cascades. On `complete` it
selects the lowest-`step_order` `pending` step of the same agenda and
activates it; when none remain it completes the agenda. This is what makes a
multi-step day work under V1 (decision W2) with no change to the applier.

The consequence is real and must be surfaced, not absorbed:

- A day resolving N steps emits N `agenda_step_change` mutations. They must be
  approved in `step_order`. Approving out of order hits the stale guard
  (`"step no longer active — world moved since the tick"`) and rejects.
- The queue entry for each must therefore carry its `step_order` and a plain
  statement that it follows the previous one. Precedent for surfacing this
  kind of ordering drop already exists in
  `_tick_normalize_scope_agenda_step_change`, which drops a proposal when the
  agenda has no active step.
- The day account (item 4) shows the steps in order with per-step review
  state, so Nia can see where the chain of approvals has reached.
- **Do not** auto-approve, reorder or batch-apply to work around this. O1
  stands.

**`fail` ends the agenda.** The applier's `fail` branch fails the whole agenda
with no branching — in-code: *"the creator can reactivate via PATCH"*. Under
BRIEF-0075-d's truncation rule, a failed step therefore terminates the plan
rather than pausing it. Emit no further step mutations after a `fail`, state
it in the account in plain terms, and let BRIEF-0075-f's reconciliation be the
normal recovery path.

## Corrected instruction — Scope IN item 3, the rendezvous

Under V1 the rendezvous no longer needs `agenda_step_change` to write an
`objective`, which the applier cannot do. The step and its objective already
exist: `write_day_plan` created them.

Arming a rendezvous is therefore just the ordinary chain:

1. The day emits a `knowledge_change` giving the player character a
   `Knowledge` row stating the meeting (M5's shape; invent no column).
2. The step that established the meeting is completed by its
   `agenda_step_change`, and the applier's cascade activates the next step —
   whose `objective`, written at plan time, is the meeting itself.
3. On approval of both, the Journée surface reads the active step's objective
   plus the knowledge and offers the handoff to the conversation surface.

Nothing new is written, nothing is invented, and the rendezvous is armed only
after review — which was the intent all along.

If a day establishes a meeting the plan did not anticipate, **do not** patch
the agenda. Emit the `knowledge_change` alone and report that the plan had no
step for it; the next day's reconciliation picks it up. Bending the applier to
insert a step is out of scope.

## Skills — decision X1, named deferral

`_EFFECT_TYPES` covers relations, ledger and roles. Resources and objects
travel as `ledger_transfer`. **Skills have no carrier.**

Nia's original request named *"des ressources, des objets ou des
compétences"*. In v1 the day produces no skill gain. The account must say so
positively rather than silently omitting it: the gains block states which
categories the day can currently produce.

Reactivation condition: **when a skill effect type exists in `_EFFECT_TYPES`.**
Adding one touches `_apply_completion_effects`, shared with `goal_change` —
its own ticket, never an addition here.

## Check changes

- **R1** now asserts the corrected `EMITTED_MUTATION_TYPES` tuple, and the
  emission dispatch's key set equals it, both directions.
- **R3** is extended: no `resource_change` and no `agenda_creation` is
  constructed anywhere in the day chain.
- **R5** stands and now covers `agenda_step_change`.
- **New R10.** Every `effects` list built in `day_mutations.py` draws its
  types from `_EFFECT_TYPES` and is bounded by `_MAX_EFFECTS`, both read from
  `cockpit/mutations.py` rather than restated as literals. Fail-closed and
  vacuity-guarded: zero effects lists found is a FAILURE.
- **New R11.** No payload built in the day chain sets a subject key on an
  `agenda_step_change` — the applier forces it.

## Unaffected

The queue integration (item 2), the day account shape (item 4), the Journée
rendering, the germ path from BRIEF-0075-c, the `pass_play` anchoring, the
`proposed` status rule, and checks R4, R6, R7, R8, R9 all stand. The
positional wall stands. O1 stands: nothing in this chain applies without Nia.
