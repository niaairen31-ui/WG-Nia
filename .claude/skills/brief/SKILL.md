---
name: brief
description: BRIEF-NN format and the execution/commit contract.
---
A brief is written AFTER its RECON. English. It contains:
- The ticket id + the RECON id it relies on.
- The exact files and `path:line` anchors to touch (from the RECON, not memory).
- Step-by-step changes, each mapping to an acceptance criterion.
- Danger class, if any — if db_write/migration/destructive_data, note that
  backup runs first (hook) and the ticket is human-gated.

Execution contract: branch `ticket/NNNN`, /review-step + /close-step per commit,
never push to main, end with /verify. If a decision is unsettled, STOP (D1).
