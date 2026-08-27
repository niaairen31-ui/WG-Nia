# BRIEF-0075-d — AMENDMENT 1: no direct step write (V1)

**Amends:** `tooling/briefs/BRIEF-0075-d-resolution-narration.md`, Scope IN
item 1, the "Persist" bullet.
**Date:** 2026-08-25
**Trigger:** Claude Code escalation on BRIEF-0075-e (dead-proposal / D1).
**Author:** Claude (design), owning the error.
**Status of the original:** unchanged on disk.

## The escalation was correct, and the fault is in -d

BRIEF-0075-e states, in its Invariants section, that the brief *"adds a
PROPOSER, not a writer."* BRIEF-0075-d, item 1, states:

> Persist: each attempted step's `AgendaStep.status` moves to `completed` or
> `failed`, `outcome` gets a short factual line [...] The next unattempted
> step becomes `active`.

Both cannot be true. -d made the day chain a direct canon writer, which is
what makes -e's `agenda_step_change` proposals dead on arrival: by the time
they reach the queue the step is no longer `active`, and
`_mutation_apply_agenda_step_change`'s stale guard rejects them. That is
BRIEF-0075-e's S1 STOP condition, correctly detected.

The error is -d's. -e was right and -d was wrong.

## Decision V1 (locked)

**The day chain proposes step transitions; it never writes them.**

## The boundary, stated once

The line is EMPTY FOOTPRINT vs. WORLD FOOTPRINT, not agenda vs. non-agenda:

- **Creating a plan has no world footprint.** It records what the player
  intends to attempt. `write_day_plan` (BRIEF-0075-b) stays a direct write:
  it is the player's own declared intent, transcribed. No review needed.
- **Completing a step has a world footprint.** It carries `effects` —
  relations, ledger, roles — and it advances the agenda. It goes through the
  queue, always.

This is why `agenda_creation` may be direct while `agenda_step_change` may
not, and the distinction must be written into the module docstring so the
next reader does not "unify" them.

## Corrected instruction (supersedes the "Persist" bullet)

`day_resolve.py` computes outcomes and stops there.

- `resolve_steps` returns `StepOutcome` objects as specified. **No
  persistence function.** Delete `persist_step_outcomes` entirely if it was
  written; do not leave it unreferenced.
- No call to `write_agenda_step_status`, `write_agenda_status` or
  `write_agenda_step` anywhere in `day_resolve.py`.
- `AgendaStep.status`, `outcome` and `change_history` are untouched by the day
  chain. They move only when Nia approves an `agenda_step_change`.
- The fact sheet (item 2) is unchanged in shape and is now the ONLY carrier of
  what the day produced. It is what BRIEF-0075-e reads to build payloads.
- The narration (item 3) is unchanged: it renders the fact sheet, which
  describes what happened, regardless of whether canon has caught up. Under
  A1 the player reads the account only after review anyway.

## Check change

Add to `tooling/verify/checks/day_narration.py`:

- **R11.** `day_resolve.py` imports no writer from `writes/goals_agendas.py`
  and contains no `db.add(`, no `.commit(`, and no assignment to
  `.status`, `.outcome` or `.change_history` on an `AgendaStep`. Fail-closed
  and vacuity-guarded: zero modules scanned is a FAILURE.

Any check authored in -d that asserts the direct write must be retargeted to
assert its ABSENCE, not deleted.

## Consequences carried into -e

Recorded here so the amendment chain is self-contained; BRIEF-0075-e
AMENDMENT 1 specifies them:

1. **Ordered approval.** `_mutation_apply_agenda_step_change` already
   cascades: on `complete` it activates the lowest-`step_order` `pending`
   step, or completes the agenda when none remain. So a multi-step day works
   — but the N proposals must be approved in `step_order`. Out-of-order
   approval hits the stale guard.
2. **`fail` ends the agenda.** The applier's `fail` branch fails the WHOLE
   agenda, by design and with no branching. Under -d's truncation rule a
   failed step therefore terminates the plan rather than pausing it.
   Recovery is BRIEF-0075-f's reconciliation, or a creator PATCH.

## Unaffected

Everything else in BRIEF-0075-d stands: `resolve_physical` as the only dice
source, the pure banding/truncation split, the frozen fact sheet and
`authorised_names`, the `day_narration` prompt, the T1 judge and its
anti-vacuity guard, `MAX_REWRITE_ATTEMPTS = 1`, the `local_summary` /
`final_result` repurposing subject to D3, the `PassPlay.history` append
contract, and checks R1 through R10.
