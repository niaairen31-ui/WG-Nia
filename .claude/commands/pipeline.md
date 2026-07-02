---
description: Orchestrate a ticket through exec -> verify -> PR (live-gate), chaining brief-exec/verify/review-step/close-step.
---
Input: `TICKET-NNNN` (bare id). Resolve to the full slug by globbing
`tooling/tickets/TICKET-NNNN-*.md`; exactly one match required, else stop
and report the ambiguity.

## Step 0 — reconcile status (NT2)

Derive `status` from observable facts and write it to the ticket's
front-matter, in this precedence order:

1. `ticket/NNNN` is merged into `main` -> `done`.
2. The verdict JSON at `tooling/verify/results/<full-slug>.json` is green
   AND a PR exists for the branch (`gh pr list --head ticket/NNNN`) ->
   `live-gate`.
3. A `tooling/questions/QUESTION-TICKET-NNNN.md` exists with an empty
   `## Response` section -> `escalated`.
4. Brief file(s) `tooling/briefs/BRIEF-NNNN*.md` exist -> eligible for
   `exec`.
5. A recon result (`tooling/recon/RECON-NNNN*.result.md`) exists ->
   `brief`.
6. A recon spec (`tooling/recon/RECON-NNNN*.md`) exists -> `recon`.
7. Otherwise -> `intake`.

Also reconcile `brief_ids` from the brief files actually observed on
disk.

This command is the ONLY writer of ticket front-matter. Nia never
hand-edits `status` — her acts (deposits, merges) are what this step
observes and records.

## Step 1 — act by status (SES1: chain to the next human gate)

- `done` -> say so, stop.
- `live-gate` -> say it awaits Nia's play-test and merge, stop.
- `brief` / `recon` / `intake` -> name the missing artifact (brief, recon
  spec, or recon result), stop. Those stages are chat-side per P1 — this
  command does not author them.
- `escalated` with a filled `## Response` -> resume applying the
  response, then continue the chain from where it left off.
- Eligible for `exec` -> run the `/brief-exec` protocol for each brief in
  suffix order (e.g. `-a` before `-b`), then run `/verify` for this
  ticket. When invoking `/review-step` and `/close-step` from within this
  chain, state explicitly that the invocation is unattended (CA1), so
  `close-step` skips its approval wait.

## Step 2 — verify outcome (V1)

- Green -> go to Step 3.
- Red:
  - If `retry_count == 0`: attempt exactly one fix, strictly confined to
    the executed brief's Scope IN (no new design decision, no file
    outside the brief's stated perimeter). Set `retry_count: 1`.
    Re-run `/verify`.
  - If still red after that retry, OR if any D1 (a/b/c/d) trigger fires
    at any point in the chain: write the QUESTION file (see below), set
    `status: escalated`, stop.

## Step 3 — open the PR (PR1)

1. `git push origin ticket/NNNN`.
2. `gh pr create --base main --head ticket/NNNN` with title
   `TICKET-NNNN: <ticket title>` and a body containing: the ticket id,
   the brief id(s) executed, and the verdict JSON inline (fenced code
   block).
3. Set `status: live-gate` in the ticket front-matter.
4. Report the PR URL, stop.

Never push to `main`; never merge — merging is Nia's gate, always.
`block-main-push` remains the structural net regardless.

## Interruption (SES1)

If the session cannot complete the chain (e.g. context limit), set
`status: paused` and stop cleanly. A later `/pipeline TICKET-NNNN` run
re-derives everything from observable facts — Step 0 is idempotent by
construction, so re-running it changes nothing that hasn't actually
changed on disk or in git/GitHub.

## D1 escalation triggers (QF1)

Any of the following writes the QUESTION file below, sets
`status: escalated`, and stops the chain — nothing else escalates:

- **D1-a** — an unspecified user-visible behavior change.
- **D1-b** — a destructive/irreversible data operation.
- **D1-c** — an architecture change above the ticket's stated
  `blast_radius`.
- **D1-d** — two consecutive `/verify` failures (Step 2's retry
  exhausted).

QUESTION file, created at `tooling/questions/QUESTION-TICKET-NNNN.md`
(verbatim skeleton):

```
# QUESTION — TICKET-NNNN
Trigger: <D1-a|b|c|d>
## Context
<what was attempted; verdicts quoted verbatim if D1-d>
## Question
<exactly one precise question>
## Options
<lettered options if the executor sees any; else "none proposed">
## Response
<empty — Nia writes here>
```

The file persists after resolution — it is an append-only trace, never
deleted or rewritten, even once `## Response` is filled and the chain
resumes.

## CA1 — unattended invocations

When this command invokes `/review-step` or `/close-step` as part of the
chain, it states explicitly that the invocation is unattended (from
`/pipeline`), so `close-step` knows to skip its normal approval wait and
commit directly. All other steps of `close-step` (changelog, decisions
index, message quality) are unchanged.
