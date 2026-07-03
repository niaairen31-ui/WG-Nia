<!-- slug: pipeline-command-surface -->
# BRIEF — Step "Recon absorption, CA1 relay, inline escalation, PR-conflict capability" (BRIEF-0006-b)

## Context
TICKET-0006, second half. RECON-0006 located every gap precisely: Step 1's
`recon` branch stops instead of executing (finding 9); the only push in the
whole command surface is Step 3's end-of-ticket push, so nothing is
raw-URL-readable before the full brief chain completes (findings 10, 22);
the CA1 unattended clause is written at the `/pipeline`↔`/close-step`
boundary but the real call path goes through `/brief-exec`, which carries
zero wiring for it (finding 12); no QUESTION has ever been written and
"empty" has no machine definition (findings 13-15) — BRIEF-0006-a shipped
`question_response.py` as the single writer; PR mergeability is never
checked and 0005's conflict was resolved 100% manually (finding 16); the
two append-only files grow in opposite directions (finding 17). Depends on
BRIEF-0006-a.

## Scope IN

1. **`.claude/commands/pipeline.md` — Step 1 `recon` branch (C1).**
   Replace the current "name the missing artifact, stop" handling for
   status `recon` with, verbatim:
   > `recon` -> execute the recon protocol (as defined in
   > `.claude/commands/recon.md`) against the ticket's spec, in this
   > session. Create `ticket/NNNN` from `main` if it does not exist yet.
   > Commit the result file on `ticket/NNNN`, then
   > `git push origin ticket/NNNN` so the result is readable from the
   > chat-side raw-URL channel. Then STOP and say so: the brief phase is
   > chat-side (P1). A ticket with NO recon spec on disk is not an error:
   > the recon phase is inapplicable by construction (intake judged it
   > unnecessary) and status derivation already proceeds past it.
   `recon.md` itself is unchanged and remains available standalone
   (finding 11: nothing to retire).

2. **`pipeline.md` — Step 0 gains the mergeability fact.** When rule 2
   resolves `live-gate`, additionally record the PR's mergeable state via
   `gh pr view --json mergeable,mergeStateStatus`. `live-gate` +
   `CONFLICTING` triggers the conflict procedure (item 3) instead of
   stopping.

3. **`pipeline.md` — PR-conflict procedure (F1/O1), new subsection.**
   Verbatim skeleton to include:
   > On `live-gate` with a CONFLICTING PR:
   > 1. `git fetch origin`, then `git merge origin/main` on `ticket/NNNN`.
   > 2. List conflicted paths: `git diff --name-only --diff-filter=U`.
   > 3. If ANY conflicted path is under `src/`, or is
   >    `world-engine-schema-changelog.md`, or is `world-engine-schema.md`:
   >    `git merge --abort`, escalate (D1) with a QUESTION file citing the
   >    conflicted paths. The machine never resolves semantic or
   >    version-numbering conflicts (O1).
   > 4. Otherwise (append-only docs only): resolve
   >    `tooling/standards/ARCHITECTURE_DECISIONS.md` keep-both — main's
   >    incoming sections first, this ticket's sections after them (the
   >    order proven on TICKET-0005's manual resolution). Regenerate
   >    `tooling/standards/DECISIONS_INDEX.md` via
   >    `python tooling/glue/gen_decisions_index.py`.
   > 5. Run the FULL verify set (`python -m tooling.verify.run`) —
   >    including checks newly arrived from main. Red -> normal V1 retry
   >    rules apply.
   > 6. Commit the merge, `git push origin ticket/NNNN`, re-derive status.

4. **`.claude/commands/brief-exec.md` — the CA1 relay (M1).** Add,
   verbatim, adjacent to its step 3:
   > If this execution was invoked from `/pipeline`, invoke `/review-step`
   > and `/close-step` in unattended mode (CA1) and state so explicitly at
   > each invocation; do not wait for a manual `/close-step` between
   > briefs of the same ticket.

5. **`pipeline.md` — escalation flow, inline answer (E1) + N1 corollary.**
   In the escalation subsection: after writing the QUESTION file, commit it
   on `ticket/NNNN` (append-only trace) but do NOT push it (the cockpit
   reads the local tree; chat never reads QUESTION files). Then, verbatim:
   > Display the `## Question` and `## Options` sections in this session
   > and offer to take the answer here. If Nia answers in-session, write it
   > through `python tooling/glue/question_response.py answer <file>`
   > (stdin) — the single sanctioned writer — commit, and resume the chain
   > immediately, without requiring a relaunch. The relaunch path (Step 0
   > detecting a filled `## Response`) remains valid and unchanged.
   Also update the QF1 skeleton note: "empty `## Response`" is defined by
   `tooling/glue/question_response.py:is_open` (stripped content == `""`) —
   the prose points at the code; the code is the definition.

6. **`.claude/settings.json` — permission additions (Q1 + flagged
   extensions).** Add exactly these entries to `permissions.allow`:
   `"Bash(git fetch origin:*)"`, `"Bash(git merge origin/main:*)"`,
   `"Bash(git merge --abort:*)"`, `"Bash(git diff:*)"`,
   `"Bash(git status:*)"`, `"Bash(gh pr view:*)"`, `"Bash(gh pr list:*)"`.
   Nothing else changes; no generic `Bash(*)`; `block-main-push` and
   `block-db-in-git` untouched (GH1).

7. **`tooling/verify/checks/pipeline_state.py` — extension** (deterministic
   grep-grade, per TICKET-0006's machine criteria): fail unless
   `.claude/commands/pipeline.md` contains BOTH sentinel phrases
   `A ticket with NO recon spec on disk is not an error` AND
   `git push origin ticket/NNNN` within the Step 1 recon branch text; fail
   unless `.claude/commands/brief-exec.md` contains
   `unattended mode (CA1)`.

## Scope OUT
- No cockpit change (BRIEF-0006-a owns `tooling/pipeline_cockpit/`).
- No changelog/schema-version renumbering automation (O2 rejected: any
  changelog or schema-file conflict escalates).
- No retirement of `/recon` (stays for ad-hoc use).
- No early push of QUESTION files, ever (N1 corollary).
- No `pipeline_state.py` inspection of `## Response` bodies (existence
  check stands; the writer guard lives in `question_response.py`).
- No change to Nia-owned transitions (SM1): `/pipeline` still never
  authors tickets/briefs, never merges to `main`, never performs
  `live-gate -> done`.
- No `git checkout`/`git switch` allowlist entry (see drafting flags —
  escalate via D1 if a permission wall is hit at the recon-phase branch
  step; do not silently extend `settings.json`).
- No V1 retry-rule change; no D1 trigger change beyond the new conflict
  trigger.

## Invariants to defend
- **Never push `main`** (C1/PR1): every new push site in this brief targets
  `ticket/NNNN` only; `block-main-push` remains the net.
- **Append-only QUESTION files** (QF1): the only write path is
  `question_response.py`; the inline flow uses it, never direct edits.
- **History is sacred**: the conflict procedure only ever merges and
  appends; keep-both never reorders or rewrites existing sections; abort +
  escalate is the answer everywhere judgment would be required.
- **NT2**: status remains derived from facts; the new mergeability fact and
  recon-execution rule extend the derivation table, they add no
  hand-written status anywhere.

## Done means
- [ ] Staged test A (recon absorption): a fixture ticket + recon spec, no
      result → `/pipeline TICKET-XXXX` runs the recon, commits and pushes
      the result on its ticket branch, stops; the result is fetchable at
      its `raw.githubusercontent.com` URL.
- [ ] Staged test B (no-recon rule): a fixture ticket with no recon spec →
      `/pipeline` proceeds past recon with no error and no stop-for-recon.
- [ ] Staged test C (chaining): a two-brief fixture ticket chains -a → -b
      with zero manual `/close-step` between them.
- [ ] Staged test D (inline escalation): a forced escalation displays the
      question in-session; a natural-language answer is transcribed under
      `## Response` via the glue writer and the chain resumes; the same
      QUESTION, left unanswered instead, is visible and answerable from the
      cockpit Questions surface.
- [ ] Staged test E (conflict): a fabricated CONFLICTING PR whose only
      conflict is in `ARCHITECTURE_DECISIONS.md` is auto-resolved
      keep-both, index regenerated, full verify green, re-pushed; a
      fabricated conflict touching `src/` aborts and escalates with the
      paths cited.
- [ ] `python -m tooling.verify.run` green, including the extended
      `pipeline_state.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: new section "PIPELINE
  SECOND PASS — recon absorption, CA1 relay, inline escalation, bounded
  conflict resolution (BRIEF-0006-b, no schema change)" recording C1 (as
  amended: recon execution is `/pipeline`-owned; intake and briefs stay
  chat-side per P1), M1, N1 (invoker half + no-early-push corollary), O1,
  F1 procedure, Q1 (+ flagged read-only extensions). Header passes the
  strict gate; index regenerated per close-step.
- `CLAUDE.md`: one line under the pipeline conventions: recon results are
  pushed at recon time (the first early-push point); everything else still
  publishes at Step 3.
- No schema change; no changelog entry.
