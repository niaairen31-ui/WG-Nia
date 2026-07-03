---
id: TICKET-0003
title: single_canon_write deterministic check (canon/ephemeral classification)
type: feature
status: recon
created: 2026-07-02
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: [BRIEF-0003-a, BRIEF-0003-b]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"Les checks concrets, et le vrai check single_canon_write (a besoin de la
classification table-canon/éphémère produite par un RECON)." — pipeline
onboarding, deferred-work list.

## Clarifications resolved (intake)

- The doctrine to enforce: exactly two sanctioned canon-write paths —
  `_apply_mutation` (AI proposals post-approval) and creator CRUD — both
  routed through `writes.py` helpers. The check must make any THIRD path a
  deterministic verify failure, structurally (code facts), not by
  convention.
- The classification (which tables are canon vs ephemeral vs
  pipeline-internal) is a DESIGN DECISION taken by Nia in chat AFTER the
  recon reports the facts. The recon classifies nothing.
- Check design (static code scan vs DB assertion vs both) is also decided
  post-recon — the recon reports the seams that make each option viable.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] no canon write outside sanctioned sites  -> verify/checks/single_canon_write.py

### Live  ->  human gate (Nia)
- [ ] Introducing a test `session.add()` on a canon table in an unsanctioned
      module (then reverting) turns /verify red, naming file and table.
