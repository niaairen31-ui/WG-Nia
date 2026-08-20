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

