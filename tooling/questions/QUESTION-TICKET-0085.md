# QUESTION — TICKET-0085
Trigger: D1-d
## Context

All five briefs (BRIEF-0085-a through -e) are executed and committed on
`ticket/0085`. `/verify` was run after BRIEF-0085-e (the last brief, the
consultation surface):

```
{
  "ticket": "TICKET-0085-lore-consultation",
  "when": "2026-09-13T19:45:54.069331+00:00",
  "green": false,
  "checks": [
    {"check": "lore_resolve.py", "status": "PASS", ...},
    {"check": "lore_selectors.py", "status": "PASS", ...},
    {"check": "lore_isolation.py", "status": "PASS", ...},
    {"check": "corpus_gate.py", "status": "FAIL",
     "msg": "SUMMARY: 2 check(s) failed (0 environment, 0 crash, 0 timeout, 2 other)"}
  ]
}
```

The two `corpus_gate.py` failures, verbatim:

```
FAIL: day_narration.py — FAIL: day_narration R6: src/world_engine/cockpit/routes/day.py:
  resolve_day never calls the rewrite pass
FAIL: npc_goal_read.py — FAIL: tooling/verify/checks/day_concordance_golden.py:153:
  NpcGoal referenced outside the allowlist
```

Both are unrelated to this ticket's own scope (`day_narration.py`/`day.py`'s
rewrite pass is TICKET-0075/0081 territory; `npc_goal_read.py`'s allowlist
check concerns `NpcGoal`, which TICKET-0084 introduced). I confirmed both
failures pre-date TICKET-0085 entirely: checked out commit `92b08cf`
("TICKET-0084 verify result — G1 green", the exact parent of BRIEF-0085-a's
first commit) into a scratch worktree and ran `corpus_gate.py` there —
same `day_narration.py` R6 failure and same `npc_goal_read.py` failure were
already present before a single line of lore-consultation code existed.
(That same worktree run also hit a `day_mutations.py` CRASH not present on
`ticket/0085` HEAD — a third pre-existing corpus issue, apparently already
fixed by later work on this branch, noted here only for completeness.)

Per V1, retry_count was 0: I looked for a fix "strictly confined to the
executed brief's Scope IN" (BRIEF-0085-e: `frontend/src/lore/`,
`App.svelte`, `Header.svelte`, `router.js`, `app.py`'s `_SHELL_ROUTES`
only). No fix within that perimeter can touch `cockpit/routes/day.py`'s
rewrite-pass wiring or `day_concordance_golden.py`'s `NpcGoal` allowlist —
both are outside every one of TICKET-0085's five briefs' Scope IN, and nothing
in this ticket ever names or touches either file. I did not spend the retry
on an out-of-scope change; I'm escalating instead of fabricating a "fix" the
brief itself forbids.

`ticket/0085` is stacked on top of TICKET-0079/0081/0084's own commits
(none of the three merged into `main` yet — `main` is 25 commits behind).
The two failing checks most likely belong to unfinished work on one or both
of those tickets, not to a regression TICKET-0085 introduced.

## Question

Given `corpus_gate.py`'s two failures are confirmed pre-existing and outside
every BRIEF-0085 brief's Scope IN, how should TICKET-0085 proceed to a PR?

## Options

- (a) Merge/land TICKET-0079 and/or TICKET-0081's fix for `day_narration.py`
  R6 and TICKET-0084's fix for `npc_goal_read.py` first (on `main` or
  earlier in this stack), then re-run `/verify` for TICKET-0085 against a
  clean corpus.
- (b) Open TICKET-0085's PR now with the verdict JSON as-is, noting in the
  PR body that the two failures are pre-existing and unrelated, for Nia to
  judge at the live gate rather than blocking on a corpus_gate check this
  ticket cannot make green by itself.
- (c) Something else — Nia may know these two failures are already being
  tracked/fixed elsewhere, or want a different resolution order across the
  0079/0081/0084/0085 stack.

## Response
(a). Do not merge on a red /verify â€” that gate does not get waived by judgment.

Confirmed: TICKET-0079 (PR #104), TICKET-0081 (PR #106) and TICKET-0084
(PR #110) are all already merged into origin/main (local `main` was stale;
fetched and confirmed at d384a07). Neither the day_narration.py R6 defect
nor the npc_goal_read.py allowlist defect is in flight anywhere â€” both are
pre-existing, ownerless defects on main itself, unrelated to TICKET-0085.

Per the branching instruction: they get their own small ticket, landed
first. TICKET-0086 (verify-check-drift) was opened from main, diagnosed
precisely (an aliased import broke R6's name match; a golden fixture file
was missing from the N1 allowlist), fixed check-file-only with regression
tests proving each fix still fails on a real regression, and its PR is
open: https://github.com/niaairen31-ui/WG-Nia/pull/111 (corpus_gate 106/106
green).

TICKET-0085 does not merge red. Its own PR is opened now, marked blocked
on TICKET-0086 landing first, per the instruction to make the work visible
without waiving the gate.

Also reclassified per your second point: the /api/lore/ask ping-gate is a
blocking defect (fails both BRIEF-0085-d's and BRIEF-0085-e's Ollama-down
live-gate item), not a REPORT-only note â€” left untouched on this branch,
to come back as its own brief once you've decided the shape of the fix.

Confirmed by live test (temporary OLLAMA_HOST override, no code changes,
reverted after):
- /api/lore/resolve does NOT pre-flight ping.
- With Ollama unreachable, POST /api/lore/resolve carrying a
  previously-obtained plan returns HTTP 200 with `"renderer":"template"`
  and correct prose â€” the offline path already works today for a
  resolve/disambiguation round-trip. Only a FRESH /api/lore/ask question
  cannot be answered offline (draft_plan has no non-model path â€” the
  planner cannot be bypassed, not a wiring bug).

Ambiguous-mention path live-verified: seeded two same-named "Doubleon"
characters via the Creation API, asked "Qui est Doubleon ?", confirmed the
ambiguity prose + candidate chooser render, the Confirm control stays
disabled until a choice is made, and confirming posts the plan unchanged to
/api/lore/resolve and resolves to the chosen entity. Both test entities
soft-deleted (status -> inactive) afterward; resolver confirmed to no
longer find them.
