---
id: TICKET-NNNN
title:
type:                 # feature | bug
status: intake        # intake|recon|brief|exec|verify|live-gate|done|paused|escalated
created:
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []      # any of: db_write, migration, destructive_data
blast_radius:         # small | medium | large
brief_ids: []
schema_version_touched:
retry_count: 0        # D1(d): 2 consecutive verify failures -> escalate
---

## Request (verbatim, as Nia stated it)

## Clarifications resolved (intake)

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] <criterion>  -> verify/checks/<name>.py

### Live  ->  human gate (Nia)
- [ ] <criterion>
