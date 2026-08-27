# BRIEF-0049-b — Step "seed_test.py + reset_test.py"

## Context
With env resolution landed (BRIEF-0049-a), the test DB path resolves under
`~/.world_engine/test/`. This step gives it a deterministic, idempotent
population and a disposable reset cycle (C2 + D1). The seed must be *small and
deterministic* — a handful of entities with stable slug IDs — and must produce
the exact IDs that `test_context.py` will reference in BRIEF-0049-c (H1
contract). It must NOT reuse or import `seed_pilot.py` (that is the ~3000-line
pilot seed against prod; the test seed is a distinct, minimal fixture).

## Mini-RECON (execute first, REPORT ONLY, no edits)
1. `WORLD_ENGINE_ENV=test python -c "from world_engine.db import create_db_and_tables; create_db_and_tables(); print('ok')"`
   — confirm the test schema builds clean on an empty test DB. REPORT the path
   created.
2. Read the minimal entity shape needed by `assemble_npc_context`: open
   `scripts/test_context.py` and note which tables/rows its assertions require
   (Knowledge rows with `share_threshold` 50 and 65, an `is_secret` player row
   `personal_magic_incident`, an `is_secret` NPC secret). Also
   `grep -n "class Knowledge\|share_threshold\|is_secret" src/world_engine/models/*.py`
   to confirm current column names. REPORT the exact columns; the seed rows in
   Scope IN must match them. If a column name differs from this brief, follow the
   code and REPORT the discrepancy — do not invent columns.
3. `grep -n "def write_\|_apply_mutation\|create_entity" src/world_engine/writes/*.py | head`
   — determine whether the seed should insert via the sanctioned write helpers
   or via direct creator-CRUD Session adds. Per the single-canon-write doctrine,
   seeds run under **creator direct authority** (the second sanctioned path), so
   plain `session.add` on model instances is correct here. Confirm no write helper
   is *required* for the tables you touch, and REPORT.

## Scope IN
1. **Create `scripts/reset_test.py`.** Behaviour:
   - Fail-closed guard at the very top, BEFORE importing `world_engine.db`:
     if `os.environ.get("WORLD_ENGINE_ENV") != "test"` => print an explicit
     error and `sys.exit(1)`. Exact message (verbatim):
     `reset_test.py refuses to run unless WORLD_ENGINE_ENV=test (got: <value>).`
     (substitute the actual value or `unset`). This prevents an accidental
     drop against prod even if the URL override is present.
   - Then resolve the test DB path via `world_engine.db` (import after the
     guard), close/dispose the engine if needed, delete the test DB file if it
     exists, recreate via `create_db_and_tables()`, then call the seed
     (import and invoke `seed_test.main()` — do not shell out).
   - Print a one-line summary: path reset + seeded.
2. **Create `scripts/seed_test.py`.** Behaviour:
   - Same fail-closed `WORLD_ENGINE_ENV=test` guard at the top, verbatim message
     pattern:
     `seed_test.py refuses to run unless WORLD_ENGINE_ENV=test (got: <value>).`
   - Idempotent: every row uses a deterministic slug PK; check-or-create, never
     duplicate. A second run changes nothing and prints an identical summary.
   - Expose `def main() -> None:` so `reset_test.py` can call it.
   - Seed this minimal deterministic world (IDs are the H1 contract — verbatim):
     - World: `world-test`
     - Location: `loc-test-tavern`
     - NPC: `npc-test-keeper`
     - Player character: `char-test-player`
     - Knowledge rows on `npc-test-keeper` sufficient to exercise the disclosure
       policy: at least one row `share_threshold = 50` (visible at neutral
       relation), one row `share_threshold = 65` (hidden at relation 50), and one
       row `is_secret = True` (never injected).
     - One `is_secret = True` player-owned Knowledge row on `char-test-player`
       with subject `personal_magic_incident` (mirrors the prod fixture so the
       same assertion logic holds).
   - Print a summary listing created vs. existing counts.
3. **Deterministic-ID docstring block** at the top of `seed_test.py` listing the
   four entity IDs above and the knowledge-row contract, so BRIEF-0049-c and any
   future reader have a single source of truth for the fixture.

## Scope OUT
- Do NOT import, call, or copy `seed_pilot.py`. The test seed is independent.
- Do NOT seed the full pilot cast (Maelis/Reike/Senna/Bryn/Korin) — minimal
  fixture only.
- Do NOT modify `db.py` (done in -a).
- Do NOT modify `test_context.py` (that is -c; this brief only *produces* the IDs
  it will consume).
- Do NOT write verify checks (that is -d).
- Do NOT add a CLI arg parser, `--force`, or interactive prompts. The env guard
  is the only gate.
- Do NOT implement a backup/rotation scheme for the test DB — it is disposable.

## Invariants to defend
- **History is sacred** applies to prod/canon; the test DB is disposable by
  design (D1) — but the *drop* path is gated so it can NEVER run against prod
  (env guard + a -c/-d guard layer). Defend that gate.
- **Single canon-write authority**: seeds use creator direct-CRUD authority
  (`session.add`), the sanctioned second path. Do not route seed inserts through
  `_apply_mutation`.
- **No structure without a reader**: every seeded row exists to be read by
  `test_context.py`'s assertions. Do not seed rows nothing reads.

## Done means
- [ ] `WORLD_ENGINE_ENV=test python scripts/reset_test.py` => fresh test DB
      exists at `~/.world_engine/test/world_engine_test.db`, seeded; prints
      summary.
- [ ] `WORLD_ENGINE_ENV=test python scripts/seed_test.py` run twice => byte-identical
      created/existing summary the second time (0 created), no duplicate rows
      (verify with a `SELECT COUNT`).
- [ ] Running either script WITHOUT `WORLD_ENGINE_ENV=test` (e.g. `=prod`, or
      unset) => exits non-zero with the verbatim refusal message; prod file mtime
      unchanged.
- [ ] The four contract IDs are present in the test DB after seeding.
- [ ] `/review-step` and `/close-step` if any `src/` code is touched (expected:
      none — scripts only; if none, state so).

## Docs to update
- This brief's seed docstring IS the fixture-ID doc. Additionally add a short
  pointer in the launch procedure doc (from -a) to `reset_test.py` /
  `seed_test.py` as the test-DB lifecycle commands.
