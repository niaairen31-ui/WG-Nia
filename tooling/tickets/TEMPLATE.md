---
id: TICKET-NNNN
title:
type:                 # feature | bug
status: intake        # intake|recon|brief|exec|verify|live-gate|done|paused|escalated
created:
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
                      # recon is the lot RECON, run in the chat session.
                      # The per-brief Mini-RECON is the first move of exec.
danger_class: []      # any of: db_write, migration, destructive_data
blast_radius:         # small | medium | large
lot_id:               # LOT-NNNN-slug.md — authoritative on conflict with a brief
brief_ids: []         # letters in execution order, e.g. [A, B, C, D, E]
current_brief:        # letter in flight, or empty
schema_version_touched:
retry_count: 0        # 2 consecutive verify failures on the SAME brief -> escalate
                      # reset to 0 when a brief lands
slug:
---

## Request (verbatim, as Nia stated it)

## Clarifications resolved (intake)

## Decisions locked (do not re-litigate without Nia)

<!-- Settled in the planning conversation, before any brief was drafted. These
     outlive the lot: an amendment replaces contracts and RECON findings, never
     these. One line each; include the reason only where the reason is what makes
     the decision load-bearing. -->

- 

## Carried forward / open

<!-- Ordered by how much they block. Each: what is undecided, the options put to
     Nia, and whether it deserves its own ticket. An item touching an invariant
     gets a ticket rather than a line in a brief. -->

- 

## Acceptance criteria

<!-- The living gate for the whole ticket. The "Done means" of each brief are
     intermediate observables and do not replace this section; an amendment may
     change a brief's Done means without touching anything here. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] <criterion>  -> verify/checks/<name>.py

### Live  ->  human gate (Nia)
- [ ] <criterion>

## Amendment log

<!-- Index only, appended and never rewritten. The content of each amendment
     lives in AMENDMENT-NNNN-NN.md and its effect is applied to the lot header. -->

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |

<!-- ## Escalations is created at the end of the ticket by
     `python tooling/glue/escalation.py open ...` the first time /pipeline
     escalates. Never write it by hand. -->
