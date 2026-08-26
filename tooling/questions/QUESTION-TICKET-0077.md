# QUESTION — TICKET-0077
Trigger: D1-c
## Context

`/pipeline TICKET-0077` reconciled status: BRIEF-0077-a is merged (PR #101),
and `ticket/0077` already carries BRIEF-0077-b (verify-gate retarget) and
BRIEF-0077-c (dedicated plan selection and the resume action) as committed,
unreviewed work — no PR open for the current HEAD (`6ea7726`). A fresh full
`python tooling/verify/run.py --ticket TICKET-0077-multi-plan-day-chain` was
run to get an authoritative verdict before opening the PR:

```
{
  "ticket": "TICKET-0077-multi-plan-day-chain",
  "green": false,
  "checks": [
    {"check": "parked_plan_guard.py", "status": "PASS"},
    {"check": "module_budget.py", "status": "PASS"},
    {"check": "function_length.py", "status": "PASS"},
    {"check": "single_canon_write.py", "status": "PASS"},
    {"check": "schema_version_agreement.py", "status": "PASS"},
    {"check": "day_prompt_delivery.py", "status": "PASS"},
    {"check": "day_plan.py", "status": "PASS"},
    {"check": "corpus_gate.py", "status": "FAIL"}
  ]
}
```

Every day-chain check this ticket actually touches is green.
`corpus_gate.py`'s failure, reproduced directly:

```
FAIL: pipeline_state.py — FAIL: TICKET-0075-amendment-1-b4-pipeline-order.md:
no parseable YAML front-matter block
```

`tooling/verify/checks/pipeline_state.py:34,177` globs `tooling/tickets/
TICKET-*.md` and runs `check_ticket()` (demands a YAML front-matter block)
against every match. `tooling/tickets/TICKET-0075-amendment-1-b4-pipeline-
order.md` is not a ticket in the governed sense — it is a prose AMENDMENT
note (same *kind* of artifact as `tooling/briefs/AMENDMENT-0060-c-1-post-
brief-e.md`, which is named outside the `TICKET-*`/`BRIEF-*` glob and so is
never scanned as a ticket). CLAUDE.md's Artifact convention documents
front-matter requirements for tickets (`slug:`) and recon/briefs (`<!--
slug: ... -->`) but says nothing about amendments — this file was simply
named with a `TICKET-0075-` prefix and fell into the ticket glob by
accident of filename, not by the artifact's actual shape.

This is a pre-existing, unrelated gap — untouched by BRIEF-0077-a/-b/-c,
already flagged (not fixed) in the BRIEF-0077-b commit (`12ef62e`: "day_
plan.py green, corpus_gate.py red on pre-existing unrelated failure") and
in `7df9cab`'s decision record. It reproduces on a clean full verify run
regardless of branch, because `pipeline_state.py` scans the filesystem, not
git history — any ticket's `/pipeline` run hits this same red right now.

Fixing it requires touching either `tooling/verify/checks/pipeline_state.py`
(the ticket-glob/amendment-class boundary) or a `TICKET-0075` artifact's
filename/front-matter — both outside BRIEF-0077-c's stated perimeter
(day-chain plan selection, `blast_radius: medium`) and outside what a V1
scope-confined retry can touch. D1-c: an architecture-adjacent fix above
this ticket's blast radius, escalating on sight rather than after a doomed
in-scope retry attempt.

## Question

How should the `TICKET-0075-amendment-1-b4-pipeline-order.md` /
`pipeline_state.py` mismatch be resolved so `corpus_gate.py` (and therefore
TICKET-0077's own Machine-checkable gate, per BRIEF-0077-b's amendment)
goes green?

## Options

A. Rename `tooling/tickets/TICKET-0075-amendment-1-b4-pipeline-order.md` to
   the `AMENDMENT-NNNN-...` pattern already established by `AMENDMENT-0060-
   c-1-post-brief-e.md` (pure rename, zero content or check-logic change —
   it simply leaves the `TICKET-*.md` glob). This is what I'd do absent
   other direction; smallest fix, matches precedent already in the tree.

B. Widen `pipeline_state.py`'s ticket recognition to exclude filenames
   matching `TICKET-NNNN-amendment-*` (or require a `type: amendment` front-
   matter marker instead of skipping YAML entirely), keeping this file's
   current name. Touches verify-check logic, not just a filename.

C. Give this specific file a minimal parseable YAML front-matter block so
   `pipeline_state.py` accepts it as a ticket-shaped artifact as-is.

D. Something else Nia specifies (e.g. treat this as out of TICKET-0077's
   concern entirely and open the PR with this one pre-existing corpus_gate
   line accepted/documented as a known gap, to be closed by a separate
   ticket).

## Response

