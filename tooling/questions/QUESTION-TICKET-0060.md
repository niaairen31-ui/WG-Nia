# QUESTION — TICKET-0060
Trigger: D1-d
## Context

BRIEF-0060-d (the corpus gate, B1) is implemented, red-tested (five
transcripts: broken check caught, unimportable check reports ENVIRONMENT
rather than skipping, coverage proof independently re-globs and catches
both a trivial addition and an artificially narrowed discovery, self-
exclusion asserted exactly one, no recursion), and committed in two
commits (`tooling/verify/checks/corpus_gate.py`; docs). It works exactly
as designed: it discovers all 83 sibling checks, executes every one, and
proves coverage.

Three of those 83 are genuinely red on this tree, all pre-existing and
unrelated to this ticket's Observation migration:

- `npc_goal_read.py` — `NpcGoal` imported/referenced outside its allowlist
  in `src/world_engine/observation_runner.py` and in
  `tooling/verify/checks/observation_runner.py`.
- `pipeline_state.py` — three ticket files (`TICKET-0036`, `TICKET-0048`,
  `TICKET-0062`) carry a `status:` value with a trailing inline comment
  that fails the front-matter enum parse.
- `prompt_model_write.py` — the local dev DB's `npc_dialogue`
  `prompt_template` row has zero `prompt_version` rows; the check's own
  live `TestClient` round-trip hits `prompt_store.current_prompt`'s
  fail-closed `RuntimeError`. Needs a migration/seed step against this
  tree's dev DB, not a code fix provable from the gate alone.

BRIEF-0060-d's own Scope OUT item 1 is explicit: "Do not fix anything the
gate finds... A brief that both builds a gate and repairs whatever the
gate finds has no reviewable boundary." Its Done-means explicitly
anticipated this outcome: "Every red the gate finds is listed, classified,
and left unfixed, with an explicit escalation line naming what a
follow-up ticket would need to cover" — this file is that escalation
line.

Because TICKET-0060's own Machine-checkable section links `corpus_gate.py`
(as its own acceptance criteria require), and `corpus_gate.py` is
structurally red for reasons outside this ticket's brief perimeter,
`/verify` for TICKET-0060 is red and — per V1 — stays red under a retry:
`retry_count` was set to 1 and `/verify` re-run with zero code changes
(no in-scope fix existed to attempt, per Scope OUT above); the verdict is
byte-identical on both runs modulo timestamp:

```
"corpus_gate.py": FAIL — "SUMMARY: 3 check(s) failed (0 environment, 0 timeout, 3 other)"
```

(All eleven other linked checks — observation_surface, legacy_mount,
legacy_call, stylesheet_partition, module_budget, function_length,
frontend_build_fresh, graph_primitive, page_contract, creation_island,
shell_height_chain — PASS on both runs.)

## Question

Given `corpus_gate.py` is correct and behaves exactly as specified, but
its correctness necessarily surfaces three genuine, pre-existing,
out-of-brief-scope failures that keep TICKET-0060's own `/verify` red:
how do you want this ticket to close?

## Options

A. Open a follow-up ticket (or three, one per failing check) now to fix
   `npc_goal_read.py`'s finding, the three malformed ticket-status lines,
   and the dev DB's missing `npc_dialogue` prompt_version seed. Land that
   first; TICKET-0060's `/verify` then goes green on its own and proceeds
   to PR normally, with no change to this ticket's scope.

B. Open TICKET-0060's PR now with `/verify` red, and record in the PR body
   that the single failing check (`corpus_gate.py`) is red only because it
   correctly surfaces three pre-existing, unrelated defects — pointing at
   this QUESTION file and the `ARCHITECTURE_DECISIONS.md` record as the
   evidence trail. This is a deliberate exception to PR1's "green verdict"
   norm, decided here rather than assumed.

C. Drop `corpus_gate.py`'s arrow from TICKET-0060's own Machine-checkable
   section — its acceptance criteria are about the check's own behavior
   (already proven by the five red-test transcripts), not about this
   ticket's gate being green — and let `/verify` pass on the eleven
   checks that remain linked. `corpus_gate.py` stays committed and
   correct; wiring it into a ticket's own gate is deferred until the three
   pre-existing reds are cleared by a follow-up ticket.

## Response
Stopping the chain was correct. The D1-d escalation fired exactly as
intended and nothing here is a defect in the execution: `corpus_gate.py`
is correct, the five red tests prove it, and the three findings are
real.

The answer is none of A, B or C. The fault is upstream of all three.

**What is actually wrong.** `tooling/verify/run.py` does not evaluate the
text of an acceptance criterion. A `-> verify/checks/X.py` arrow means one
thing: X must exit 0 for this ticket to verify green. TICKET-0060 carries
two arrows to `corpus_gate.py`. Their criterion text says the gate
exists, excludes only itself, fails closed on a missing dependency, and
is red-tested. But the arrow asserts something else entirely — that the
corpus is green — which was never TICKET-0060's job and which
`BRIEF-0060-d`'s own Scope OUT item 1 explicitly forbids bringing about.
So the ticket demanded, through its wiring, the exact thing its brief
prohibited. That is a ticket-authoring error, not an execution problem,
and it is why no confined retry could resolve it.

Why not B: a documented exception to a fail-closed gate is a
disciplinary safeguard, not a structural one — safeguards hold by
construction, not by a well-argued PR body. It would set the precedent
that a green verdict is negotiable in writing, exactly the erosion
`corpus_gate.py` exists to make impossible.

Why not C as written: dropping the arrow and deferring the wiring leaves
`corpus_gate.py` referenced by no ticket at all — never executed,
invisible when it breaks. That is the `observation_surface.py` lapse of
TICKET-0059, reproduced on the very tool built to prevent it. The
instinct behind C is right; the deferral is what makes it wrong.

**Do this.**

1. Correct TICKET-0060's wiring, then close it. In
   `tooling/tickets/TICKET-0060-observation-surface-migration.md`, strike
   both `corpus_gate.py` arrows from `### Machine-checkable` and move the
   two criteria verbatim into `### Live -> human gate (Nia)`. They are
   human-verified criteria: the evidence is the five red-test transcripts
   and the diff, not a deterministic exit code. `/verify` then runs the
   remaining eleven checks. They are green. TICKET-0060 closes normally
   and the frontend refactor proceeds to TICKET-0061. Nothing in
   `corpus_gate.py` changes — do not weaken it, do not add an exclusion,
   do not soften `ENVIRONMENT` to a warning.

2. Open TICKET-0067 — clear the corpus. Sole machine-checkable criterion:

   - [ ] Every check in tooling/verify/checks/ exits 0  -> verify/checks/corpus_gate.py

   That ticket cannot close until the corpus is green, so the gate is
   wired to the one ticket whose job it actually is — a re-homing, not a
   deferral. Scope: the three findings, three confined commits, one
   brief.

   - `pipeline_state.py` — three ticket files (0036, 0048, 0062) with
     trailing comments on their `status:` values. Strip the comments. Do
     not relax the parser to tolerate them: the frontmatter contract is
     the thing being asserted.
   - `npc_goal_read.py` — the `NpcGoal` reference in
     `observation_runner.py`, in both the src and checks copies. Decide
     which of two things is true and say which: the read is legitimate
     and the allowlist is incomplete, or the read is a genuine boundary
     violation. Do not add an allowlist entry to silence a violation.
   - `prompt_model_write.py` — zero `prompt_version` rows for
     `npc_dialogue`. Triage this one before designing a fix, and report
     the measurement. The question is whether the check asserts code or
     data. If it asserts a seeded database, then either the dev
     environment needs a seed step 0067 supplies, or the check is
     environment-bearing and must declare that dependency the way
     `corpus_gate.py`'s contract expects. Both are legitimate answers;
     guessing between them is not. If this one turns out larger than a
     confined commit, split it into its own ticket and let 0067 land the
     other two — but say so before starting, not partway through.

3. Make the wiring structural, in the same ticket. `pipeline_state.py`
   already validates ticket files and is already being touched. Extend it
   with one rule: every ticket's `### Machine-checkable` section must
   link `corpus_gate.py`. That converts "remember to wire the gate into
   future tickets" from a convention into a check. Without it, the corpus
   drifts again the first time someone forgets an arrow — the failure
   this ticket series has now hit three times, at three different
   levels. Vacuity guard: zero ticket files discovered is a FAIL, not a
   pass. Red-test it: a ticket file without the arrow must FAIL.

**Sequencing.** TICKET-0060 closes first, on eleven green checks.
TICKET-0067 opens immediately after and is the first ticket to carry the
`corpus_gate.py` arrow under its own new rule.

`QUESTION-TICKET-0060.md` stays in the tree as the record. It is the
escalation working, not a problem that needed avoiding.
