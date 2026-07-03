---
id: TICKET-0006
title: Pipeline second pass — pipeline cockpit, single-command derivation, inline escalation, multi-brief chaining, PR-conflict capability
type: feature
status: exec
created: 2026-07-02
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0006-a, BRIEF-0006-b]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

Second improvement pass on the ticket-management pipeline after the first
full live run (TICKET-0005). Nia's stated pain points, in her words:

- Numbering/renaming artifacts via `next_id.py`: « Je ne veux pas avoir à
  faire cette tâche »
- Depositing ticket + recon spec into `tooling/tickets/` / `tooling/recon/`:
  « Je ne veux pas avoir à faire cette tâche »
- Launching `/recon RECON-XXXX` as a separate command: « Je ne veux plus
  avoir à faire cette tâche »
- Pasting the recon report back into chat: « Je ne veux plus avoir à faire
  cette tâche »
- Depositing briefs into `tooling/briefs/`: « Je ne veux plus avoir à faire
  cette tâche »
- Escalation UX: « je ne veux [plus] avoir à aller ouvrir un fichier et
  écrire dedans, je voudrais plus de convivialité »
- Observed on 0005: the chain stopped between briefs (-a, -b, -c) waiting
  for a manual `/close-step` each time, despite CA1.
- Observed on 0005: PR was `CONFLICTING`; resolution (keep-both on
  append-only docs, index regeneration, full verify, smoke test) was done
  manually on request and worked; Nia merged.

## Clarifications resolved (intake)

- **A+ (asymmetric chat↔repo channel).** The repo is public
  (`niaairen31-ui/WG-Nia`). Chat READS directly and unauthenticated via
  `raw.githubusercontent.com` (validated live during this intake: HTTP 200
  on `tooling/glue/next_id.py` and `CLAUDE.md`; note that `api.github.com`
  is rate-limited on the shared egress IP and is NOT the channel — raw
  fetches only). Chat WRITES nothing: no PAT, no token, zero credential
  surface. The write direction is covered by the pipeline cockpit (H1/I1):
  Nia pastes chat-delivered artifacts into a "Soumettre" surface, which
  performs numbering, naming, and placement. One paste replaces four file
  manipulations.
- **B (re-resolved, SM1 unamended).** Because the deposit gesture survives
  as the cockpit paste, SM1 stands verbatim: depositing a brief (now via
  cockpit) IS the green light. No verbal gate, no draft status, no
  amendment.
- **C1 (recon absorbed by `/pipeline`).** `/pipeline TICKET-NNNN` becomes
  the single Claude Code command. Derivation rule, locked: recon spec
  present on disk AND no result file → execute recon, commit the result on
  `ticket/NNNN`, **push the branch** (so chat can read the result), stop.
  Recon spec ABSENT → recon phase inapplicable by construction (intake
  judged it unnecessary); this is not an error and not a bug. No flag, no
  hand-written status — pure NT2 fact derivation.
- **D2 (escalation surface in the pipeline cockpit).** The cockpit gains a
  "Questions" surface: list of QUESTION files with an empty `## Response`,
  a response box, machine-written fill of `## Response`. QF1 intact: the
  file remains the append-only trace; Nia never opens it.
- **E1 (inline escalation in-session).** Additionally, when `/pipeline`
  escalates mid-run, it displays the question and lettered options in the
  session itself; Nia may answer in natural language there; the glue
  transcribes under `## Response` and resumes immediately. The cockpit
  Questions surface (D2) and the inline path (E1) are two writers of the
  same file format — RECON must confirm both respect one shared contract.
- **E1-chaining (CA1 deviation is a bug).** In `/pipeline` mode,
  `close-step` must never stop between briefs; the chain a→b→c runs
  uninterrupted to the final verify. The stop observed on 0005 is a
  deviation from CA1 to locate and fix.
- **F1 (PR-conflict capability, bounded).** If the PR is `CONFLICTING`,
  `/pipeline` merges `origin/main` into `ticket/NNNN`, applies keep-both on
  append-only files (ARCHITECTURE_DECISIONS.md, the schema changelog),
  regenerates derived indexes, re-runs the FULL verify set including checks
  newly arrived from main, re-pushes. Any conflict touching `src/`
  escalates via D1 — mandatory, no mechanical resolution there. This
  codifies exactly the manual resolution that succeeded on 0005.
- **H1 (cockpit placement + collision audit).** The pipeline cockpit is a
  separate app at `tooling/pipeline_cockpit/`, same stack (FastAPI + HTMX,
  zero new dependencies), distinct port, launched on demand. Nia's explicit
  instruction: audit for name/file/port/module collisions with the world
  cockpit BEFORE any code is specified — separation by construction, not
  by discipline.
- **I1 (cockpit v1 scope), I2 deferred.** Exactly two surfaces: "Soumettre"
  (paste an artifact; type detected from its header/front-matter; number
  assigned via the `next_id.py` counter at deposit time; file written to
  the correct path; confirmation displays created names) and "Questions"
  (D2). No git operations, no status board, no `/pipeline` launcher.
  **Deferred, named: I2** — a read-only ticket status board derived from
  facts; add only when live usage shows the need.
- **J2 (cockpit assigns numbers).** Chat always delivers artifacts with
  `NNNN` placeholders; the cockpit assigns the number at deposit via the
  `next_id.py` counter and substitutes everywhere (filename + body), then
  displays it. Structural reason: GitHub lags the working tree; the disk at
  deposit time is the only truth for "next number" — one authority, no race
  window. Nia reports the assigned number back to chat in one word.
- **Intake fact for RECON:** `next_id.py` is currently CLI-print-only (the
  counting logic lives inline in `main()`); the cockpit needs either a
  subprocess call or an extracted importable function — RECON reports the
  shape, the brief decides.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `tooling/pipeline_cockpit/` exists, imports cleanly, and declares a
      port distinct from the world cockpit's  -> verify/checks/pipeline_cockpit.py
- [ ] Deposit logic, given a pasted `TICKET-NNNN-*.md` body in a temp tree,
      writes the file to the correct directory with the computed 4-digit
      number substituted in both filename and body  -> same check, pure-function test
- [ ] QUESTION response writer refuses to touch a file whose `## Response`
      is non-empty (append-only respected)  -> same check
- [ ] The `/pipeline` command definition contains the no-recon-spec
      derivation clause and the post-recon push clause  -> verify/checks/pipeline_state.py (extended)

### Live  ->  human gate (Nia)
- [ ] Paste this ticket + its recon spec into "Soumettre": both land at the
      correct paths, correctly numbered; the assigned number is displayed
- [ ] `/pipeline TICKET-NNNN` on a ticket with a recon spec: runs recon,
      commits + pushes the result on `ticket/NNNN`, stops; the result is
      readable from chat via its raw URL
- [ ] A multi-brief ticket chains a→b with no human gate between briefs
- [ ] A forced escalation shows the question inline; a natural-language
      answer in-session is transcribed under `## Response` and the chain
      resumes; the same open QUESTION is also visible and answerable from
      the cockpit Questions surface
- [ ] A simulated `CONFLICTING` PR on append-only docs is auto-resolved
      keep-both, full verify green, re-pushed; a simulated conflict in
      `src/` escalates instead
