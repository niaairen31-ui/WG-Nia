# QUESTION — TICKET-0067
Trigger: D1-c
## Context
BRIEF-0067-a commit 2 wires `prompt_model_write.py`'s fixture to seed a v1
`prompt_version` row via `write_prompt_version` (Scope IN 2.1/2.2), exactly
as specified. That repair works: the versionless-head `RuntimeError` no
longer fires.

Fixing that crash lets `main()` (tooling/verify/checks/prompt_model_write.py:222)
run to completion for the first time, because `check_write_path_and_list_route()`
used to abort with an *uncaught* exception before `main()` ever reached its
`if FAILURES: print(...)` block. That masked whatever `check_seed_model_free()`
(lines 63-66) had already appended to the shared `FAILURES` list earlier in
the same run.

With the crash gone, that masked failure now prints:

```
FAIL: scripts/seed_pilot.py sets a `model=` value on a prompt_template row — S-null violated
```

It is a false positive. `check_seed_model_free`'s regex is `\bmodel\s*=`
applied to the whole file text (not AST-aware, no comment stripping). It
matches three comments documenting `model=NULL` (Q1) at
`scripts/seed_pilot.py:2206`, `:2227`, `:2339` — none of them assign
`model=` on any actual `PromptTemplate(...)` construction. Grepping the
file confirms these are the only three matches and all three are inside
`#` comments.

This is a second, independent, previously-invisible defect in the same
check file this brief already touches — not named anywhere in
TICKET-0067 or BRIEF-0067-a, and not something the mini-RECON could have
measured (it never ran far enough to surface it). The brief's own Hard
STOP condition 5 anticipates exactly this shape of discovery
("A different failure means a different defect... STOP and report; do
not proceed, do not work around") and I'm honoring it rather than
patching the regex as a drive-by.

Commit 1 (`npc_goal_read.py`) is done and committed
(`c5a76ac` on `ticket/0067`). Commit 2's `write_prompt_version` wiring is
staged in the working tree but not yet committed, pending this decision.

## Question
Should this brief's scope grow by one line item — repairing
`check_seed_model_free`'s false positive so `prompt_model_write.py` can
exit 0 as this ticket's acceptance criteria require — or should that
repair be deferred to its own ticket, leaving `prompt_model_write.py`
red for now (which would break this ticket's stated Done-means and
corpus_gate.py's expected "exactly one remaining failure" count)?

## Options
A. Fix `check_seed_model_free` now, inside BRIEF-0067-a commit 2 (same
   file the brief already touches): narrow the regex so it only matches
   a `model=` keyword argument/assignment in actual code — e.g. anchor
   it against a `PromptTemplate(` construction, or strip `#` comment
   text before scanning. Record it as a third, explicitly-named repair
   in the commit message and this ticket's Machine section, same
   discipline as the other two.
B. Defer to a new ticket (next id via `tooling/glue/next_id.py`). This
   brief's commit 2 lands only the `write_prompt_version` fix and
   accepts that `prompt_model_write.py` stays red until the new ticket
   lands — which means this ticket's own acceptance criteria and
   `corpus_gate.py`'s "exactly one remaining failure" bullet cannot be
   met as written; both would need amending.
C. Something else Nia specifies.

## Response
