# BRIEF — Step "Verify gate retarget after the reconciliation move"

## Context

BRIEF-0077-a item 5 relocated six functions from `cockpit/routes/day.py` to
`cockpit/day_reconcile_apply.py`. Three rules in `tooling/verify/checks/day_plan.py`
still look for three of those functions in the old file and are RED on `main`
right now -- reproduced below. TICKET-0077's Machine-checkable section linked
six checks and not `day_plan.py`, and not `corpus_gate.py` either, so `run.py`
reported green on a corpus that was not. This step repairs the guards and closes
the hole that let it pass, before any further day-chain work lands on top.

## Mini-RECON (measured against the fresh tarball, `main`)

- [M] `python tooling/verify/checks/day_plan.py` exits **1** with exactly three
  failures:
  - `day_plan R12: src/world_engine/cockpit/routes/day.py: _reconcile_and_finalize not found`
  - `day_plan R14: src/world_engine/cockpit/routes/day.py: _finalize_replace not found`
  - `day_plan R19: src/world_engine/cockpit/routes/day.py: _finalize_continue not found`
- [M] `tooling/verify/checks/day_plan.py:98` -- `DAY_ROUTE_FILE = SRC / "cockpit" / "routes" / "day.py"`.
  It is the only path constant pointing at the route module; there is no
  constant for `day_reconcile_apply.py`.
- [M] R12 is `check_verdict_dispatch_bijection` (line 490), R14 is
  `check_replace_writes_nothing` (line 572), R19 is
  `check_continue_constructs_nothing` (line 672).
- [M] `cockpit/routes/day.py:76` imports `_reconcile_and_finalize` from
  `..day_reconcile_apply`; `_find_function` walks `FunctionDef` nodes only, so
  an import never satisfies it.
- [M] `tooling/verify/run.py:10,52` -- only checks named by a
  `-> verify/checks/NAME.py` arrow in the ticket's Machine-checkable section are
  executed.
- [M] `tooling/verify/checks/corpus_gate.py:1-27` exists precisely for this
  failure mode and names the identical precedent: `observation_surface.py` was
  red on `main` from TICKET-0059's merge until BRIEF-0060-a repaired it, because
  that ticket's Machine section linked eleven checks and not that one.
- [I] `corpus_gate.py` is therefore red on `main` too: it runs every check in
  the directory as a subprocess and classifies a non-zero exit as FAIL.
- [M] `python tooling/verify/checks/parked_plan_guard.py` exits 0 (PASS) --
  BRIEF-0077-a's own new check is sound; only the pre-existing TICKET-0075 guard
  was left pointing at the old location.

**STOP conditions.** Stop and escalate if: (1) `day_plan.py` is green when you
run it -- the tree then differs from this RECON and the whole premise is wrong;
(2) more than the three named rules fail; (3) fixing R12/R14/R19 requires
changing what they ASSERT rather than where they LOOK -- a retarget must not
weaken a rule, and if it seems to need to, the move in -a was not
behaviour-neutral and that is the finding.

## Scope IN

**1. Add the path constant (`tooling/verify/checks/day_plan.py`).** Beside
`DAY_ROUTE_FILE` at line 98, add:

    DAY_RECONCILE_APPLY_FILE = SRC / "cockpit" / "day_reconcile_apply.py"

**2. Retarget R12, R14 and R19 -- location only.** In
`check_verdict_dispatch_bijection`, `check_replace_writes_nothing` and
`check_continue_constructs_nothing`, replace every use of `DAY_ROUTE_FILE` that
resolves `_reconcile_and_finalize`, `_finalize_replace` or `_finalize_continue`
with `DAY_RECONCILE_APPLY_FILE`. Every assertion -- the bijection against
`EXPECTED_RECONCILE_VERDICTS`, the "constructs no `ProposedMutation`" walks, the
zero-keys vacuity branch -- stays byte-identical. Uses of `DAY_ROUTE_FILE` in
rules that legitimately still target the route module (R15's
`_load_standing_agenda` / `_guard_no_active_agenda` assertions) are NOT touched;
confirm by running the check before and after and seeing three failures become
zero, with no rule newly silent.

**3. Update the file's rule docstring (lines 40-80).** For R12, R14 and R19,
change the parenthesised file name from `routes/day.py` to
`day_reconcile_apply.py`, and append to each, verbatim:

    (retargeted by TICKET-0077/BRIEF-0077-b after BRIEF-0077-a item 5 relocated
    this function; the assertion is unchanged, only where it looks.)

**4. Add a location-drift guard, R22.** New function
`check_reconcile_finalizers_located()`, called from `main()` alongside the
others. It asserts that `_reconcile_and_finalize`, `_finalize_continue`,
`_finalize_modify`, `_finalize_replace`, `_reconciliation_dict` and
`_revised_plan_matches_remaining` are each defined in EXACTLY ONE of
`DAY_ROUTE_FILE` / `DAY_RECONCILE_APPLY_FILE`, and that the file is
`DAY_RECONCILE_APPLY_FILE`. Zero functions located is a FAILURE. Docstring
states, verbatim:

    R22 (TICKET-0077, BRIEF-0077-b): the six reconciliation finalizers live in
    `cockpit/day_reconcile_apply.py` and nowhere else. R12/R14/R19 each resolve
    a function by name in a fixed file and report "not found" when it moves —
    that is a correct failure, but a LATE one: it fires only after a relocation
    has already merged. This rule proves the location itself, so a future move
    is caught as a location change rather than as three unrelated "not found"
    messages. It proves WHERE the functions are, not that their bodies are
    correct — R12/R14/R19 still own that.

**5. Update the PASS line** at the end of `main()` to mention R22 alongside the
existing R11-R21 range.

**6. Close the gate hole in `tooling/tickets/TICKET-0077-multi-plan-day-chain.md`.**
Add to the Machine-checkable section, in this order, after the existing entries:

    - [ ] the reconciliation finalizers are located in day_reconcile_apply.py
          and TICKET-0075's plan-path guards are intact
          -> verify/checks/day_plan.py
    - [ ] every check in tooling/verify/checks/ runs and passes
          -> verify/checks/corpus_gate.py

## Scope OUT

- **Any change to `src/`.** This step touches `tooling/` only. If a rule can
  only be made green by editing engine code, STOP: that means -a shipped a real
  defect, not a stale anchor, and it needs its own brief.
- **Widening `EXPECTED_RECONCILE_VERDICTS`** or touching the handlers dict.
  BRIEF-0077-c.
- **Auditing the other ~95 checks** for the same class of stale anchor. If
  `corpus_gate.py` surfaces additional red checks unrelated to the -a move,
  REPORT them in the execution notes with their exact failure lines and STOP --
  do not repair them here.
- **Retro-editing BRIEF-0077-a.** It stays on disk as written; this brief is the
  append-only correction.
- **Changing `run.py`'s per-ticket arrow model.** `corpus_gate.py` is the
  sanctioned answer to it and item 6 is how it gets used.

## Invariants to defend

- **A check proves what it measures, nothing more.** Item 4's docstring must say
  so explicitly; R22 proves location, never correctness.
- **Fail-closed and vacuous-proof.** R22 collecting zero functions FAILS.
- **Never two copies of the same assertion.** R22 must not re-assert the
  bijection or the `ProposedMutation` absence; it asserts location only.
- **History is sacred.** BRIEF-0077-a is not edited.
- **No engine behaviour change.** The diff outside `tooling/` is empty.

## Done means

- [ ] `python tooling/verify/checks/day_plan.py` exits 0 and its PASS line names
      R22.
- [ ] Temporarily moving `_finalize_continue` back into `routes/day.py` makes
      R22 fail with a location message, and moving it back makes it pass again
      (spot check, reverted, reported).
- [ ] Temporarily emptying the `handlers` dict makes R12 fail -- proving the
      retarget did not silence the rule (spot check, reverted, reported).
- [ ] `python tooling/verify/checks/corpus_gate.py` exits 0, or its output is
      pasted verbatim into the execution notes with a STOP if anything other
      than `day_plan.py` was red.
- [ ] `python tooling/verify/run.py` against TICKET-0077 runs `day_plan.py` and
      `corpus_gate.py` among its checks and is green.
- [ ] `git diff --stat` shows changes under `tooling/` only.
- [ ] `/review-step` and `/close-step` NOT run -- no engine code touched; say so
      in the execution notes rather than running them.

## Docs to update

- `tooling/tickets/TICKET-0077-multi-plan-day-chain.md` -- item 6 above, plus
  `brief_ids` gaining `BRIEF-0077-b-verify-gate-retarget`.
- No schema changelog entry: no schema change.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` -- append one short paragraph to
  the existing corpus-gate section recording the second occurrence of the
  linked-checks-only failure mode, and the standing rule it now carries: **every
  ticket's Machine-checkable section links `corpus_gate.py`.** If no such
  section exists, create one and say it is the second occurrence.
