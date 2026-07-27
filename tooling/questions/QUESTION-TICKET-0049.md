# QUESTION — TICKET-0049
Trigger: D1-a (unspecified user-visible behavior change) / D1-c (scope above BRIEF-0049-d's stated blast radius)
## Context
BRIEF-0049-d's mini-RECON item 4 instructed: `grep -rln "from world_engine.db
import\|world_engine.db" scripts/*.py` — enumerate the scripts that import the
engine, expecting "test_context.py, seed_pilot.py, test_ddl_atomicity.py,
test_rollback_quarantine.py, and the new seed_test.py / reset_test.py." The
brief's Scope IN anticipates exactly ONE structural exception to `env_guard`'s
fail-closed rule: `seed_pilot.py`, via a named `KNOWN_PROD_SEED_ALLOW` set with
a one-line rationale ("creator-run pilot seed against prod, gated by operator,
not a test harness").

**The actual grep returns 55 scripts**, not 6. Beyond the expected six
(all of which correctly pass — `test_context.py`/`seed_test.py`/
`reset_test.py` via their new pre-import guards from -b/-c, the two
`test_*_atomicity/quarantine.py` scripts via their explicit
`WORLD_ENGINE_DATABASE_URL` set), the remaining ~49 import
`world_engine.db.engine` (or `create_db_and_tables`) with **no env set and
no guard**: every `migrate_v1_*.py` (all 33 of them), every
`apply_ticket_NNNN_prompt_*.py` (9 of them), plus `backup.py`, `init_db.py`,
`talk.py`, `analyze_conversation.py`, `rollback_quarantine.py`,
`seed_trait_keys.py`, and `preview_tick_context.py`. Under BRIEF-0049-a
(already landed), every one of these now raises `RuntimeError` at import
time unless the operator exports `WORLD_ENGINE_ENV` first — a real,
already-shipped behavior change these scripts don't yet document or guard
against; `env_guard.py`, run literally as specified ("AST over every
`scripts/*.py`... FAIL a script that imports the engine with neither"),
would report all ~49 as failures on top of `seed_pilot.py`.

The brief names `seed_pilot.py` as "the second latent prod-polluter" (singular,
implying it's the only other one) and its Scope OUT only forbids touching
`seed_pilot.py`, `db.py`, `seed_test.py`, `reset_test.py`, `test_context.py` —
it never anticipated retrofitting or allow-listing dozens of migration/
one-shot/operator scripts. None of A/B/C below is guessable from the brief
text; each has a materially different blast radius than what BRIEF-0049-d's
Scope IN describes.

## Question
How should `env_guard.py` treat the ~49 non-test operator scripts (migrations,
`apply_ticket_*`, `backup.py`, `init_db.py`, `talk.py`,
`analyze_conversation.py`, `rollback_quarantine.py`, `seed_trait_keys.py`,
`preview_tick_context.py`) that import the engine with no per-script env
guard?

## Options
A. Allow-list all ~49 alongside `seed_pilot.py` in `KNOWN_PROD_SEED_ALLOW`
   (rename it something broader, e.g. `KNOWN_OPERATOR_SCRIPT_ALLOW`), each
   inheriting the same one-line rationale ("operator-run, gated by env
   export at the shell, not a test harness"). `env_guard.py` goes green as
   literally specified, but the allow-list ends up covering the large
   majority of `scripts/*.py` — the check enforces almost nothing beyond the
   6 scripts BRIEF-0049-d actually anticipated.
B. Narrow `env_guard.py`'s scope to only the test/seed harness family the
   brief's Context section actually names ("no *test* script under `scripts/`
   reaches the engine without an env being set") — i.e. `test_context.py`,
   `seed_test.py`, `reset_test.py`, `test_ddl_atomicity.py`,
   `test_rollback_quarantine.py`, plus `seed_pilot.py` as the sole named
   allow-listed exception. All other operator scripts are out of scope by a
   naming/directory convention (e.g. a `test_`/`seed_`/explicit allow-list
   prefix check) documented as a deliberate boundary, not silently skipped.
   Defers the ~49-script retrofit to a future ticket.
C. Retrofit all ~49 scripts now, in this ticket, with the same fail-closed
   `WORLD_ENGINE_ENV` guard pattern landed on `seed_test.py`/`reset_test.py`/
   `test_context.py` — `env_guard.py` then enforces universally with zero
   exceptions beyond none. Correct end state, but a much larger diff than
   BRIEF-0049-d's stated Scope IN (`tooling/verify/checks/env_fail_closed.py`,
   `tooling/verify/checks/env_guard.py`, one `CLAUDE.md` line, one decisions
   entry) and touches operator scripts explicitly protected elsewhere
   (`rollback_quarantine.py` is invariant-critical, B1 rollback contract).
## Response

