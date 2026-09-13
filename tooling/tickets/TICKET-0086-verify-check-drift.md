---
id: TICKET-0086
slug: verify-check-drift
title: corpus_gate red on main -- two checks drifted behind legitimate refactors (day_narration R6, npc_goal_read allowlist)
type: bug
status: intake
created: 2026-09-13
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: [BRIEF-0086-a]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> [From the TICKET-0085 pipeline run, on being told corpus_gate.py was red
> for reasons outside that ticket's scope:] "If they are not [in flight on
> 0079/0081/0084]: they are two pre-existing defects with no owner, and
> waiting on unrelated tickets to finish unrelated scope would couple 0085
> to work it has nothing to do with. They get their own small ticket,
> landed first. Either way 0085 does not merge red."

Confirmed: TICKET-0079, TICKET-0081 and TICKET-0084 are all merged into
`origin/main` (PRs #104, #106, #110 — `d384a07` is current `origin/main`
HEAD). `corpus_gate.py` still fails on `main` itself, exactly as it does on
`ticket/0085`, on two checks unrelated to lore consultation:

```
FAIL: day_narration.py — FAIL: day_narration R6: src/world_engine/cockpit/routes/day.py:
  resolve_day never calls the rewrite pass
FAIL: npc_goal_read.py — FAIL: tooling/verify/checks/day_concordance_golden.py:153:
  NpcGoal referenced outside the allowlist
```

## Clarifications resolved (intake)

**Both are check drift, not engine regressions — verified by reading the
actual code, not just the failure message.**

**Defect 1 — `day_narration.py`'s `check_bounded_rewrite` (R6) looks for the
rewrite call site in the wrong function.** R6's AST walk (`tooling/verify/
checks/day_narration.py:check_bounded_rewrite`) scans `resolve_day`'s own
function body in `src/world_engine/cockpit/routes/day.py` for a call named
`rewrite`/`day_rewrite`. TICKET-0079's BRIEF-0079-b carved the narration/
judge/rewrite/repair sequence out of `resolve_day` into a helper,
`_narrate_and_judge` (`cockpit/routes/day.py:794-834`), "for the function-
length ceiling" (its own docstring says so). The actual call —
`rewrite_narration(...)` at `day.py:820`, aliased from `day_narration.
rewrite` — is real, is bounded to exactly one `if delta is not None:` branch,
and behaves exactly as R6 requires; it is simply one call frame deeper than
R6's AST walk looks. R6 was written before that refactor existed and never
updated for it — the same risk the check's own comment at
`day_narration.py:69-71` names for the sibling `repair` call ("R6 counts
rewrite/day_rewrite by name and would not see a call named repair — this is
why R19 is its own rule"), but the carve-out broke R6's OWN target too, not
just the `repair` case R19 was written to cover.

**Defect 2 — `npc_goal_read.py`'s `ALLOWED_MODULES` never gained the golden
fixture TICKET-0081 added.** `tooling/verify/checks/day_concordance_golden.py`
(added by TICKET-0081, BRIEF-0081-a, "concordance-robustness-and-casting")
constructs `NpcGoal(...)` rows directly at line 153 as scenario setup for its
own occupation-casting golden fixtures (`_make_standing_goal`) — a test
fixture, not a new production read path into NPC interiority. `npc_goal_
read.py`'s `ALLOWED_MODULES` is a hard, enumerated allowlist of source paths
permitted to reference `NpcGoal` at all (N1 doctrine, TICKET-0013); the new
golden file was never added to it.

**Neither fix touches `src/world_engine/` production code, prompts, or the
schema.** Both are `tooling/verify/checks/*.py`-only changes:

1. `day_narration.py`'s `check_bounded_rewrite`: also recognize the rewrite
   call site when it is reachable through the one function `resolve_day`
   calls for its narrate/judge/rewrite/repair sequence
   (`_narrate_and_judge`), not only directly inside `resolve_day` itself —
   matching R19's already-established precedent of following a named helper
   rather than assuming everything lives inline. The "reachable from exactly
   one `if` condition, exactly one call" property still gets checked; only
   *where* the call site is looked for changes.
2. `npc_goal_read.py`'s `ALLOWED_MODULES`: add
   `"tooling/verify/checks/day_concordance_golden.py"`, with a comment
   naming it as a test-fixture exception (same pattern as the file's
   existing comments justifying each entry).

## Acceptance criteria

### Machine-checkable -> G1 deterministic gate

- [ ] The rewrite call-site scan resolves an aliased import instead of
      matching a bare name only, with no change to
      `src/world_engine/cockpit/routes/day.py` or
      `src/world_engine/day_narration.py` -> verify/checks/day_narration.py
- [ ] The golden-fixture file that seeds `NpcGoal` rows for its own test
      corpus is in the allowlist, with no change to `src/world_engine/
      context.py` or any other production module -> verify/checks/npc_goal_read.py
- [ ] Every check in the corpus passes -> verify/checks/corpus_gate.py

### Live -> human gate (Nia)

- [ ] `python -m tooling.verify.run` (full corpus) is green on `ticket/0086`
- [ ] Reading the diff confirms both changes are check-file-only
