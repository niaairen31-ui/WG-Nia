# BRIEF-0049-a — Step "WORLD_ENGINE_ENV resolution + fail-closed"

## Context
Today `src/world_engine/db.py:34` reads `WORLD_ENGINE_DATABASE_URL` and, when
absent, silently defaults to the prod file `~/.world_engine/world_engine.db`.
That implicit default is exactly why tests currently write into prod. This step
introduces `WORLD_ENGINE_ENV` (`prod`|`test`) as the primary, fail-closed
resolver, keeps `WORLD_ENGINE_DATABASE_URL` as an explicit override, and removes
the implicit prod default. This is the load-bearing brief: b, c, d all depend on
the resolved path existing.

## Mini-RECON (execute first, REPORT ONLY, no edits)
Run and paste findings into the PR/commit description before touching code:
1. `sed -n '30,50p' src/world_engine/db.py` — confirm lines 32-46 still read as
   the RECON anchor (DEFAULT_DB_PATH, DEFAULT_DATABASE_URL, DATABASE_URL getenv,
   make_url dir-creation block, create_engine). If any line moved, re-anchor and
   report the new line numbers before editing.
2. `grep -rn "WORLD_ENGINE_DATABASE_URL" --include="*.py" .` — enumerate every
   consumer that sets this variable. Expected: `scripts/test_ddl_atomicity.py`,
   `scripts/test_rollback_quarantine.py`. Confirm they set it BEFORE importing
   `world_engine.db`. These must keep working unchanged under F1 (explicit URL
   satisfies fail-closed). Report any additional setter found.
3. `grep -rn "from world_engine.db import\|from world_engine import db\|db.engine" --include="*.py" .`
   — inventory every import of the engine singleton. This is the blast radius.
   REPORT the count; do not modify these consumers (they import a resolved
   engine; the resolution changes underneath them, transparently).

## Scope IN
1. **In `src/world_engine/db.py`, replace the resolution block** (current
   `DEFAULT_DB_PATH` / `DEFAULT_DATABASE_URL` / `DATABASE_URL` lines, RECON
   anchor db.py:32-34) with an explicit resolver function. Behaviour:
   - Read `WORLD_ENGINE_DATABASE_URL` first. If set and non-empty => use it
     verbatim as `DATABASE_URL` (explicit override; satisfies fail-closed).
   - Else read `WORLD_ENGINE_ENV`. Accept exactly `"prod"` or `"test"`
     (case-sensitive). Resolve:
       - `prod` -> `Path.home() / ".world_engine" / "world_engine.db"`
       - `test` -> `Path.home() / ".world_engine" / "test" / "world_engine_test.db"`
     as `sqlite:///{path}`.
   - Else (neither variable set, or `WORLD_ENGINE_ENV` set to any other value)
     => raise `RuntimeError` at import time with this exact message text
     (verbatim, single line):
     `WORLD_ENGINE_ENV must be 'prod' or 'test' (or set WORLD_ENGINE_DATABASE_URL explicitly). Refusing to start with no resolved database.`
   - Keep the existing directory-creation guard (`make_url` + `mkdir parents`)
     unchanged, applied to the resolved URL.
2. **Preserve** the two SQLite event listeners (`_enable_sqlite_foreign_keys`,
   `_begin_sqlite_transaction`), `create_db_and_tables`, and `get_session`
   verbatim. Only the URL-resolution lines change.
3. **Update the module docstring** (db.py:1-9) to state the new contract:
   `WORLD_ENGINE_ENV` primary (`prod`/`test`), `WORLD_ENGINE_DATABASE_URL`
   explicit override, no implicit default, fail-closed when unresolved.
4. **New launch procedure doc** — create `docs/launch-procedure.md` (or append a
   section to the existing operator doc if one exists; RECON: `ls docs/` first)
   stating that prod is now launched with `WORLD_ENGINE_ENV=prod` exported, and
   test with `WORLD_ENGINE_ENV=test`. Include the exact PowerShell lines
   (see "Docs to update").

## Scope OUT
- Do NOT create `seed_test.py` or `reset_test.py` (BRIEF-0049-b).
- Do NOT modify `test_context.py` (BRIEF-0049-c).
- Do NOT write the `env_guard` / `env_fail_closed` verify checks (BRIEF-0049-d).
- Do NOT modify `scripts/test_ddl_atomicity.py` or
  `scripts/test_rollback_quarantine.py` — they already set an explicit URL and
  must remain untouched.
- Do NOT modify `seed_pilot.py` in this brief (its env exposure is handled by
  the guard in -d; rewriting it is out of scope for the whole ticket).
- Do NOT add a `dev`/`staging` environment. Only `prod` and `test` exist.
- Do NOT touch `Activate.ps1` logic beyond the documented env export
  (no refactor of the activation script).

## Invariants to defend
- **Fail-closed over advisory** (CLAUDE.md): the unresolved case must RAISE, not
  warn-and-default. This is the whole point of the brief.
- **Structural over disciplinary**: the path is chosen by resolver code, never
  by the caller remembering to pass a flag.
- **Single engine singleton**: do not introduce a second engine or a
  reconfigure-at-runtime path. One module-level `engine`, resolved once.

## Done means
- [ ] `python -c "import world_engine.db"` with BOTH env vars unset => exits
      non-zero, prints the exact refusal message.
- [ ] `WORLD_ENGINE_ENV=prod python -c "from world_engine.db import engine; print(engine.url)"`
      => prints the prod URL (`.../.world_engine/world_engine.db`).
- [ ] `WORLD_ENGINE_ENV=test python -c "from world_engine.db import engine; print(engine.url)"`
      => prints `.../.world_engine/test/world_engine_test.db` and the
      `test/` directory now exists.
- [ ] `WORLD_ENGINE_DATABASE_URL=sqlite:////tmp/x.db python -c "from world_engine.db import engine; print(engine.url)"`
      with `WORLD_ENGINE_ENV` unset => prints the explicit URL (override wins,
      no refusal).
- [ ] `scripts/test_ddl_atomicity.py` and `scripts/test_rollback_quarantine.py`
      still run green unchanged.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update
- `db.py` module docstring (Scope IN item 3).
- New launch procedure. Exact PowerShell lines to document, verbatim:
  - Prod: `$env:WORLD_ENGINE_ENV = "prod"` then the existing activate/run.
  - Test: `$env:WORLD_ENGINE_ENV = "test"` then run seed/reset/test scripts.
- `ARCHITECTURE_DECISIONS.md`: one entry recording F1 (env primary, URL override,
  fail-closed, no implicit default) with a pointer to TICKET-0049.
