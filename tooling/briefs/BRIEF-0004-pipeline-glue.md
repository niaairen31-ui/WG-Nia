# BRIEF — Step "/pipeline orchestration glue" (BRIEF-0004)

Ticket: TICKET-0004. Recon: RECON-0004 (result). Single brief, THREE
ordered commits on branch `ticket/0004`. Engine code untouched — this is
tooling + governance; /review-step + /close-step apply per commit.

**Creator prerequisite (Nia, before exec starts):** `gh` installed and
authenticated — `gh auth status` and `gh pr list --state all` must both
succeed FROM THE REPO DIRECTORY. If either fails, stop before commit 2.

## Context

All design is locked (P1, Q1, R1+SM1, V1, QF1, PR1, SES1, CA1, NT2, GT-A,
GH1, H1 — consolidated in TICKET-0004's clarifications). RECON-0004
established the ground truth this brief builds on: no existing command
reads or writes ticket front-matter (the glue is first reader AND first
writer); `run.py --ticket` requires the FULL SLUG (`TICKET-0003-single-canon-write`,
not `TICKET-0003`) — result files on disk prove it; branch convention is
`ticket/NNNN`; merges are plain merge commits (PR #2); `close-step.md`
currently waits for commit approval (CA1 amends); `.claude/settings.json`
has no `permissions` key (GH1 adds one); the working-tree `.gitignore`
hides `tooling/tickets|recon|briefs` and six real artifacts are untracked
(GT-A reverts); `tooling/questions/` does not exist (QF1 creates);
TICKET-0001 has no front-matter and an out-of-enum `status: draft` (NT2
backfills).

## Scope IN

### Commit 1 — GT-A housekeeping (provenance rescue)

1. Remove the three lines `tooling/tickets/`, `tooling/recon/`,
   `tooling/briefs/` from `.gitignore` (working-tree modification revert;
   the DB and backup patterns stay untouched).
2. `git add` every untracked file under `tooling/tickets/`,
   `tooling/recon/`, `tooling/briefs/`, and `tooling/verify/results/`.
   Expected set per RECON-0004: BRIEF-0003-a/-b, RECON-0003 spec+result,
   RECON-0004 spec (+result if present), TICKET-0004, the two verdict
   JSONs. **Stop-and-report if any file outside this expected family
   appears** (anything non-markdown/non-json, anything not matching the
   pipeline naming families).
3. NT2 backfill of `tooling/tickets/TICKET-0001-doc-partition.md`: give it
   a full TEMPLATE.md front-matter block (`id: TICKET-0001`,
   `type: feature`, `status: done`, `created: 2026-07-01` (or the file's
   real creation date if recoverable), `model_lane` as template default,
   `danger_class: []`, `blast_radius: small`,
   `brief_ids: [BRIEF-0001-a, BRIEF-0001-b]`,
   `schema_version_touched: none`, `retry_count: 0`); remove the three
   bare prose lines (`status: draft`, `brief_ids:`,
   `schema_version_touched:`) they replace. Body untouched.

### Commit 2 — the glue itself

4. **Create `.claude/commands/pipeline.md`.** Contract, to be written as
   numbered prose steps in the repo's existing command style
   (description-only frontmatter):

   - **Input**: `TICKET-NNNN` (bare id). Resolve to the full slug by
     globbing `tooling/tickets/TICKET-NNNN-*.md`; exactly one match
     required, else stop with the ambiguity.
   - **Step 0 — reconcile (NT2).** Derive `status` from observable facts
     and write it to the front-matter, in this precedence order:
     `ticket/NNNN` merged into `main` → `done`; verdict JSON green AND a
     PR exists for the branch (`gh pr list --head ticket/NNNN`) →
     `live-gate`; a `tooling/questions/QUESTION-TICKET-NNNN.md` exists
     with empty `## Response` → `escalated`; brief file(s)
     `tooling/briefs/BRIEF-NNNN*.md` exist → eligible for `exec`;
     recon result exists → `brief`; recon spec exists → `recon`; else
     `intake`. Also reconcile `brief_ids` from the brief files observed.
     The glue is the ONLY writer of front-matter; Nia never hand-edits
     status (her acts — deposits, merge — are what the glue observes).
   - **Step 1 — act by status (SES1: chain to the next human gate).**
     `done` → say so, stop. `live-gate` → say it awaits Nia's play+merge,
     stop. `brief`/`recon`/`intake` → name the missing artifact, stop
     (those stages are chat-side per P1). `escalated` with filled
     `## Response` → resume applying the response, then continue the
     chain. Eligible for `exec` → run the `/brief-exec` protocol for each
     brief in suffix order, then `/verify`, chaining within the session.
   - **Step 2 — verify outcome (V1).** Green → step 3. Red →
     if `retry_count` == 0: one fix attempt STRICTLY confined to the
     executed brief's Scope IN (no new design decision, no file outside
     the brief's perimeter), `retry_count: 1`, re-verify. Red again (or
     any D1 a/b/c trigger at any point) → write the QUESTION file
     (step 4), `status: escalated`, stop.
   - **Step 3 — PR (PR1).** `git push origin ticket/NNNN`, then
     `gh pr create --base main --head ticket/NNNN` with title
     `TICKET-NNNN: <ticket title>` and body containing: ticket id, brief
     id(s), and the verdict JSON inline (fenced). Set `status: live-gate`,
     report the PR URL, stop. Never push main; never merge (Nia's gate;
     block-main-push remains the structural net).
   - **Interruption (SES1)**: if the session cannot complete the chain
     (context limit), set `status: paused` and stop cleanly; a later
     `/pipeline TICKET-NNNN` re-derives everything from facts (step 0 is
     idempotent by construction).
   - **CA1**: when this command invokes `/review-step`/`/close-step`, it
     states the unattended context explicitly.

5. **Amend `.claude/commands/close-step.md`** — after the
   wait-for-approval sentence, add verbatim:

   ```
   Unattended mode: when invoked from /pipeline (the invoker will say
   so), skip the approval wait and commit directly. All other steps
   (changelog, decisions index, message quality) unchanged.
   ```

6. **Create `tooling/questions/`** (with `.gitkeep`) and specify the QF1
   file format inside `pipeline.md` (verbatim skeleton):

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

   The file persists after resolution (append-only trace; never deleted).

7. **GH1 — add a `permissions` key to `.claude/settings.json`** with a
   narrow, nominative allowlist covering exactly what the chain runs
   unattended: `gh pr create`, `git push origin ticket/*`,
   `python tooling/glue/*`, `python -m tooling.verify.run`, and the two
   git read families the reconcile step needs (`git branch`, `git log`).
   Use Claude Code's current permission-rule syntax (verify against the
   installed version's documentation; **stop-and-report if the syntax
   differs from what the docs describe** rather than guessing). Nothing
   generic (`Bash(*)` forbidden); the hooks stay untouched.

### Commit 3 — the gate

8. **Create `tooling/verify/checks/pipeline_state.py`** (exit 0/1, no DB):
   every `tooling/tickets/TICKET-*.md` (TEMPLATE excluded) must have a
   parseable YAML front-matter block containing all TEMPLATE.md fields;
   `status` must be in the enum verbatim; `retry_count` an integer 0–2;
   if `status: escalated`, the matching QUESTION file must exist.
   Failure message names file + field.
9. **Append the consolidated decision record** to
   `tooling/standards/ARCHITECTURE_DECISIONS.md` (before
   `## Deferred decisions`), header exactly:

   ```
   ## PIPELINE GLUE — /pipeline orchestration, derived ticket status, structural permissions (BRIEF-0004, no schema change)
   ```

   Body: one-line records of P1, Q1, SM1 (transition ownership), V1, QF1,
   PR1, SES1, CA1 (approval moved to PR surface), NT2 (status = derived
   fact; amends SM1's literal ownership: Nia owns acts, glue records
   consequences), GT-A (pipeline artifacts tracked; provenance rationale),
   GH1 (narrow allowlist as the structural declaration of unattended
   rights), H1 (F2 stands; D1-b is the net). Regenerate DECISIONS_INDEX
   (close-step covers it).
10. **Update TICKET-0004 front-matter** (`brief_ids: [BRIEF-0004]`) and
    add the Machine line:

    ```
    - [ ] pipeline state conformity  -> verify/checks/pipeline_state.py
    ```

## Scope OUT

- No automation of the chat-side segment (intake, brief authoring, recon
  launch) — P1's boundary; the deposit gesture stays manual until a
  future A2 ticket.
- No front-end (B3), no agent teams (F1), no webhook/scheduler.
- No `gh pr merge` capability anywhere — merging is Nia's gate, always.
- No backup hook (H1; F2 stands).
- No retroactive re-run of old tickets through /pipeline; 0001/0003 are
  reconciled by status only.
- No new verify checks beyond pipeline_state.py; the forced-failure drill
  (ticket live criterion) uses a disposable scratch ticket at live-gate
  time, not shipped machinery.
- `review-step.md` untouched (its verdict stays chat-output; only
  close-step gains the unattended clause).

## Invariants to defend

- **C1**: nothing in the glue can reach `main` — push targets `ticket/*`
  only, the allowlist encodes it, block-main-push double-locks it.
- **Single source of truth**: `status` is derived from observable facts;
  step 0 must stay idempotent (running /pipeline twice changes nothing).
- **D1 escalation semantics**: the four triggers escalate; nothing else
  does; the retry never widens the brief's Scope IN.
- **History is sacred**: QUESTION files and verdict JSONs are never
  deleted or rewritten; ARCHITECTURE_DECISIONS is append-only.

## Done means

- [ ] Commit 1 merged view: `git ls-files tooling/` shows all pipeline
      artifacts tracked; plain `git status` is clean of invisible orphans;
      TICKET-0001 parses against TEMPLATE fields.
- [ ] `python tooling/verify/checks/pipeline_state.py` exits 0; red test:
      temporarily set an out-of-enum status in a scratch ticket → exit 1
      naming file+field; revert.
- [ ] `/verify TICKET-0004` green (this check + the three existing ones).
- [ ] `/pipeline TICKET-0004` invoked on its own ticket at status
      `live-gate`-minus (i.e., after commit 3, before PR): step 0
      reconciles correctly, chain reaches PR creation, PR URL reported,
      `status: live-gate` written. (This brief's own PR is the glue's
      first live output — dogfooding.)
- [ ] Live gate (Nia): per the ticket — one real end-to-end run + the
      forced-failure drill (scratch ticket with a deliberately failing
      check → exactly one confined retry → escalated + well-formed
      QUESTION file).

## Docs to update

Step 9 IS the decisions update. CLAUDE.md: add one line under the pipeline
governance section naming `/pipeline` as the orchestration entry point and
`tooling/questions/` as the escalation surface (wording free, one line
each). No schema change, no changelog entry.
