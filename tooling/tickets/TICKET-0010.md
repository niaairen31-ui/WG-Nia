---
id: TICKET-0010
slug: claude-md-contract
title: CLAUDE.md optimization + structural freshness contract
type: maintenance
status: live-gate
created: 2026-07-04
model_lane: { intake: opus, recon: opus-chat, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: [BRIEF-0010-a]
schema_version_touched: none
retry_count: 0
---

## Request (as Nia stated it)

Optimise mon CLAUDE.md. Je veux qu'il contienne la bonne information pour
mes sessions Claude Code, et s'assurer qu'il demeure propre et à jour.

## RECON findings (chat-side, against main)

- CLAUDE.md is 1366 lines / 107 KB — ~25K tokens loaded into every Claude
  Code session.
- `### File structure` is 916 lines (67%): an annotated tree carrying
  per-file, brief-by-brief history inline — duplicating
  `ARCHITECTURE_DECISIONS.md` and the schema changelog, and going stale on
  every chantier. It is simultaneously incomplete: it omits `tooling/`,
  `.claude/`, `prompt_registry.py`, `writes.py`, `backup.py`, the second
  cockpit, and points at `verify/checks/` instead of the real
  `tooling/verify/checks/`.
- `## Invariants` is 33 entries / 242 lines; several entries carry chantier
  narrative rather than pure law.
- The existing freshness rule ("step closure keeps this file consistent")
  is disciplinary and demonstrably failed — the structural remedy is a
  verify contract on the file itself.

## Decisions locked

- **A1** — File structure becomes a bare tree: one line per file, role
  only (from the real cloned tree, not the stale one). History references
  banned from the section, structurally.
- **B1** — All 33 invariants kept, rewritten as law only; rationale and
  chantier history live in `ARCHITECTURE_DECISIONS.md`. Two additions
  reflect shipped reality: the prompt-model write-path invariant
  (TICKET-0009) and corrected verify-check paths.
- **C1** — New deterministic check `tooling/verify/checks/
  claude_md_contract.py` enforcing section whitelist, line budgets, and
  the archaeology ban in File structure.
- **D1** — The rewrite is authored chat-side (delivered as a finished
  file); Claude Code replaces the file, ships the contract check, and
  verifies content-constancy against the invariant checklist in the brief.
- **T2 (folded in)** — the pipeline-cockpit deposit-flow dormancy and the
  filename-is-law artifact convention are recorded in
  `ARCHITECTURE_DECISIONS.md` by this ticket's brief.

## Acceptance criteria

### Machine-checkable -> G1
- [ ] New CLAUDE.md in place; `claude_md_contract.py` green:
      section whitelist exact, total <= 500 lines, File structure <= 80
      lines, zero `BRIEF-`/schema-version references inside File structure
      -> verify/checks/claude_md_contract.py
- [ ] All other verify checks still green (no invariant text they grep for
      was lost)

### Live -> human gate (Nia)
- [ ] A fresh Claude Code session loads the new file and can state the
      per-NPC B1 invariant, the two canon-write paths, and the current
      verify command — without any other file open
- [ ] `ARCHITECTURE_DECISIONS.md` carries the new entry (CLAUDE.md
      contract + pipeline-cockpit dormancy + filename-is-law)
