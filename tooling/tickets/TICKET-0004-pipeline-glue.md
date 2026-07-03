---
id: TICKET-0004
title: /pipeline orchestration glue (chain to next human gate)
type: feature
status: live-gate
created: 2026-07-02
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0004]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"L'automatisation qui enchaîne les étapes sans moi (glue, Phase 3)" —
pipeline onboarding, deferred-work list; confirmed as the next intake after
TICKET-0003 merged ("Parfait, on ouvre l'intake glue").

## Clarifications resolved (intake)

- P1: glue covers ONLY the Claude Code segment (ticket+brief present →
  exec → verify → retry → PR or escalate). Intake and brief authoring stay
  in chat; the file contract is the boundary, so future automation of the
  deposit gesture requires no glue change.
- Q1: single command `/pipeline TICKET-NNNN`, idempotent, resumable.
- R1+SM1: state lives in the ticket front-matter `status` field, using
  TEMPLATE.md's existing enum verbatim
  (intake|recon|brief|exec|verify|live-gate|done|paused|escalated).
  Transition ownership: Nia owns intake→recon, recon→brief, brief→exec
  (brief deposit = green light), live-gate→done (merge). /pipeline owns
  exec→verify, verify→live-gate (green), →escalated (D1), →paused (clean
  interruption). /pipeline NEVER performs a Nia-owned transition.
- V1: first red verify → one (1) fix attempt confined to the brief's
  Scope IN, retry_count incremented, re-verify. Second consecutive red →
  escalated + QUESTION file citing both verdicts (D1-d literal).
- QF1: tooling/questions/QUESTION-TICKET-NNNN.md, fixed sections
  (Trigger a/b/c/d, Context, Question — exactly one, Options lettered,
  ## Response left empty for Nia). On relaunch over an escalated ticket:
  Response filled → resume applying it; empty → stop and say so. File
  persists after resolution (append-only trace).
- PR1: green verify → gh pr create (body: ticket id, brief ids, verdict
  JSON), status → live-gate. Nia plays, merges on GitHub. C1 untouched
  (never push main; block-main-push hook remains the net).
- SES1: one invocation chains to the NEXT HUMAN GATE (exec then verify in
  one session if context allows); clean stop → paused, resumable.
- H1: no backup hook; destructive ops escalate via D1-b (danger_class).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] pipeline state conformity  -> verify/checks/pipeline_state.py

### Live  ->  human gate (Nia)
- [ ] A real ticket runs end-to-end: brief deposited → /pipeline TICKET-NNNN
      → exec → verify green → PR opened → status live-gate, with zero manual
      step between deposit and PR.
- [ ] Forced-failure drill: a deliberately failing check triggers exactly
      one confined retry, then escalated + a well-formed QUESTION file.
