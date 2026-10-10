---
paths:
  - "tooling/verify/checks/*.py"
---

# Writing a verify check

- One rule per observable, named in the module docstring (`R1`, `A2`, ...).
  The docstring is the law the check enforces: when an invariant ends with
  `-- enforced by <check>.py`, a reviewer reads that docstring for the full
  rule. Its first sentence is the check's line in `FILE_MAP.md`.
- Fail-closed: a missing file, a parse error, or a rule that collected zero
  items is a FAILURE, never a pass. Collect every failure in a `FAILURES`
  list through `fail()`, print each as `FAIL: ...`, exit 1; print one
  `PASS: <name> -- ...` line and exit 0 otherwise (`file_map.py`,
  `session_config.py`).
- Never touch Nia's database. A DB-backed check builds a fresh temp-file
  SQLite fixture and sets `WORLD_ENGINE_DATABASE_URL` before any
  `world_engine` import (`fact_spine.py`), and builds its rows through the
  real sanctioned writers.
- Never a second copy of a parser or renderer: import it
  (`pipeline_state.py` imports `run.py` and `escalation.py`; `file_map.py`
  imports `gen_file_map.py`).
- Every rule is proven by a named mutation in the brief's Done means: a
  one-line change that turns that rule red, then reverted.
- `corpus_gate.py` runs every check here as a subprocess with a 15-second
  timeout; an import error, a crash or a timeout is a failure.
- A check is retired by deleting it and recording `<file>|<ticket>` in
  `tooling/verify/baselines/checks.retired` in the same commit; older
  tickets keep their arrows to it.
