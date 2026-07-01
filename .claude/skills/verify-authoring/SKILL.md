---
name: verify-authoring
description: Turn an observable acceptance criterion into a deterministic check.
---
Each MACHINE-checkable criterion becomes one small Python file in
tooling/verify/checks/ that exits 0 (pass) or non-zero (fail) with a one-line
PASS/FAIL message. Kinds:
- DB assertion: connect to ~/.world_engine/world_engine.db, run a query, assert.
- File check: assert a path exists / contains given content.
- Command verdict: run a command, assert its exit code / output.
- Structural invariant: grep the source for a forbidden or required shape.

Rules: deterministic only. No LLM calls. No judgement words ("clean", "good").
Runs under the project runtime (venv + PYTHONPATH=src). Name after the criterion,
not the ticket, so checks are reusable (e.g. no_world_orphans.py).

LIVE criteria (things only visible in real gameplay) are NOT scripted — they are
flagged for Nia's human gate.
