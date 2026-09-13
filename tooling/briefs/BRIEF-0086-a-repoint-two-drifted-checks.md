<!-- slug: repoint-two-drifted-checks -->
# BRIEF — Step "Repoint two drifted checks"

## Context

`corpus_gate.py` fails on `main` itself (confirmed at `origin/main` HEAD
`d384a07`, after TICKET-0079/0081/0084 all merged) on two checks that drifted
behind legitimate refactors those same tickets made. Full diagnosis is in
TICKET-0086's Clarifications. Neither fix touches production code.

## Scope IN

1. **`tooling/verify/checks/day_narration.py`, `check_bounded_rewrite`
   (R6).** Currently walks only `resolve_day`'s own AST body in
   `src/world_engine/cockpit/routes/day.py` for a call named `rewrite`/
   `day_rewrite`. Widen it to also look inside the one helper function
   `resolve_day` calls for its narrate/judge/rewrite/repair sequence
   (`_narrate_and_judge`) — by name, the same way R6 already resolves
   `resolve_day` by name, not by walking every function in the file. Keep
   every existing assertion (exactly one call, reachable from exactly one
   `if`): only *where* the call site is looked for changes. Do not weaken
   the "exactly one, no retry loop" cardinality check to accommodate the
   new location — if the call now needs an `if` reachability check scoped
   to `_narrate_and_judge`'s own body instead of `resolve_day`'s, adjust
   that lookup accordingly, but the property being verified stays the same.

2. **`tooling/verify/checks/npc_goal_read.py`, `ALLOWED_MODULES`.** Add
   `"tooling/verify/checks/day_concordance_golden.py"`, with a one-line
   comment identifying it as a golden-fixture test file that constructs
   `NpcGoal` rows as scenario setup (TICKET-0081, BRIEF-0081-a) — matching
   the existing comment style for every other entry in the set.

## Scope OUT

- **No change to any production module.** `src/world_engine/cockpit/
  routes/day.py`, `src/world_engine/day_narration.py`,
  `src/world_engine/context.py` and every other file `npc_goal_read.py`
  already scans are untouched.
- **No change to `day_concordance_golden.py`'s fixture logic itself** — it
  is correct; only the checker's allowlist was missing it.
- **No new check, no relaxation of what either check actually verifies.**
  R6 still requires exactly one rewrite call site reachable from exactly
  one `if`; `npc_goal_read.py`'s allowlist stays a closed, named list —
  this step adds one entry, it does not loosen the mechanism (e.g. no glob,
  no "tests/" blanket exemption).
- **No touch to any other currently-passing check.**

## Invariants to defend

- The two checks keep verifying the SAME structural properties (R6's bounded
  -rewrite cardinality; the N1 `NpcGoal` visibility doctrine) — this step
  corrects where/what they look at, never what they tolerate.

## Done means

- [ ] `python tooling/verify/checks/day_narration.py` exits 0
- [ ] `python tooling/verify/checks/npc_goal_read.py` exits 0
- [ ] `python tooling/verify/checks/corpus_gate.py` exits 0 (full corpus)
- [ ] `python -m tooling.verify.run` (or equivalent full-suite invocation)
      is green
- [ ] A manual regression check: temporarily renaming `_narrate_and_judge`'s
      `rewrite_narration(...)` call, or adding an unlisted module that
      references `NpcGoal`, still makes the corresponding check FAIL (proves
      the fix widened recognition rather than disabling the gate) — do this
      as a throwaway local check, never committed
- [ ] Diff review: zero lines changed outside `tooling/verify/checks/
      day_narration.py` and `tooling/verify/checks/npc_goal_read.py`
- [ ] `/review-step` and `/close-step` run clean

## Docs to update

None — no schema change, no architecture decision (this is a check-drift
fix, not a design choice). No `ARCHITECTURE_DECISIONS.md` entry needed.
