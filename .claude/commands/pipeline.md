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
   `live-gate`. When this rule resolves `live-gate`, additionally record
   the PR's mergeable state via `gh pr view --json mergeable,mergeStateStatus`.
   `live-gate` + `CONFLICTING` triggers the PR-conflict procedure below
   instead of stopping.
3. The ticket's own `## Escalations` section holds an open entry
   (`tooling/glue/escalation.py`'s `open_entries`) -> `escalated`.
4. Brief file(s) `tooling/briefs/BRIEF-NNNN*.md` exist -> eligible for
   `exec`.
5. A lot header `tooling/lots/LOT-NNNN-*.md` exists -> `brief`.
6. Otherwise -> `intake`.

Also reconcile `brief_ids` from the brief files actually observed on
disk.

This command is the ONLY writer of ticket front-matter. Nia never
hand-edits `status` — her acts (deposits, merges) are what this step
observes and records.

## Step 1 — act by status (SES1: chain to the next human gate)

- `done` -> say so, stop.
- `live-gate` -> if the PR's mergeable state is `CONFLICTING`, run the
  PR-conflict procedure (F1/O1) below instead of stopping. Otherwise say
  it awaits Nia's play-test and merge, stop.
- `brief` / `intake` -> name the missing artifact (the lot, or its
  briefs), stop. The lot RECON, the lot and its briefs are written in the
  chat session — this command never authors them.
- `escalated` -> display the open entry's Question and Options and take
  Nia's answer in this session (see Escalation below), then continue the
  chain from where it left off.
- Eligible for `exec` -> run the `/brief-exec` protocol for each brief in
  the order of the ticket's `brief_ids` (A before B), then run `/verify`
  for this ticket. Every commit goes `/review-step` then `/close-step` in
  the same turn, exactly as `/brief-exec` states; commits are
  pre-authorized.

## Step 2 — verify outcome (V1)

- Green -> go to Step 3.
- Red:
  - If `retry_count == 0`: attempt exactly one fix, strictly confined to
    the executed brief's Scope IN (no new design decision, no file
    outside the brief's stated perimeter). Set `retry_count: 1`.
    Re-run `/verify`.
  - If still red after that retry, OR if any D1 (a/b/c/d) trigger fires
    at any point in the chain: escalate (see Escalation below).

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

## PR-conflict procedure (F1/O1)

On `live-gate` with a CONFLICTING PR:
1. `git fetch origin`, then `git merge origin/main` on `ticket/NNNN`.
2. List conflicted paths: `git diff --name-only --diff-filter=U`.
3. If ANY conflicted path is under `src/`, or is
   `world-engine-schema-changelog.md`, or is `world-engine-schema.md`:
   `git merge --abort`, escalate (D1) with an entry citing the
   conflicted paths. The machine never resolves semantic or
   version-numbering conflicts (O1).
4. Otherwise (append-only docs only): resolve
   `tooling/standards/ARCHITECTURE_DECISIONS.md` keep-both — main's
   incoming sections first, this ticket's sections after them (the
   order proven on TICKET-0005's manual resolution). Regenerate
   `tooling/standards/DECISIONS_INDEX.md` via
   `python tooling/glue/gen_decisions_index.py`.
5. Run the FULL verify set (`python -m tooling.verify.run`) —
   including checks newly arrived from main. Red -> normal V1 retry
   rules apply.
6. Commit the merge, `git push origin ticket/NNNN`, re-derive status.

## Interruption (SES1)

If the session cannot complete the chain (e.g. context limit), set
`status: paused` and stop cleanly. A later `/pipeline TICKET-NNNN` run
re-derives everything from observable facts — Step 0 is idempotent by
construction, so re-running it changes nothing that hasn't actually
changed on disk or in git/GitHub.

## D1 escalation triggers (QF1)

Any of the following escalates and stops the chain — nothing else
escalates:

- **D1-a** — an unspecified user-visible behavior change.
- **D1-b** — a destructive/irreversible data operation.
- **D1-c** — an architecture change above the ticket's stated
  `blast_radius`.
- **D1-d** — two consecutive `/verify` failures (Step 2's retry
  exhausted).

## Escalation

An escalation lives in the ticket it stops, in its `## Escalations`
section. `tooling/glue/escalation.py` is the only writer of that section;
never edit it by hand.

1. Write, outside the repository, a JSON file with three strings — `context` (what was attempted;
   verdicts quoted verbatim if D1-d), `question` (exactly one precise
   question), `options` (lettered options, or "none proposed") — and run
   `python tooling/glue/escalation.py open TICKET-NNNN <D1-a|b|c|d> <brief letter>`
   with that file on stdin. It prints the new entry's id (`E-NN`).
2. Set `status: escalated`, commit the ticket on `ticket/NNNN` (do not
   push), and display the entry's Question and Options in this session.
3. When Nia answers, write her answer verbatim with
   `python tooling/glue/escalation.py answer TICKET-NNNN E-NN` (answer on
   stdin), commit, and resume the chain immediately.

Entries are never edited or deleted once written; an answered entry stays
in the ticket as its trace. If the session ends first, a later
`/pipeline TICKET-NNNN` finds the open entry at Step 0 and asks again.
