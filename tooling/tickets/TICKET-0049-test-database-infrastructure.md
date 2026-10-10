---
id: TICKET-0049
title: Test database infrastructure (WORLD_ENGINE_ENV, seed_test, reset_test, env_guard)
type: feature
status: live-gate
created: 2026-07-27
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []          # no migration, no canon write, no destructive prod op
blast_radius: medium      # touches db.py engine resolution (imported everywhere)
brief_ids: [BRIEF-0049-a, BRIEF-0049-b, BRIEF-0049-c, BRIEF-0049-d]
schema_version_touched:   # none — no schema change
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"J'aimerais qu'on se fasse une BD de test (actuellement des tests sont
effectués sur ma BD de production et des choses s'ajoutent dedans, je n'aime
pas cela. En plus, c'est une bonne pratique d'avoir une BD de test). [...]
Il faut s'assurer que Claude Code utilise la BD de test pour ses tests."

## Clarifications resolved (intake)

- **A1** — Isolation by construction: an environment variable resolves the DB
  path. No convention, no per-call flag.
- **B1** — Fail-closed: the primary env variable absent => refuse to start. No
  implicit default to prod (the current trap).
- **C2** — Test DB is populated by an idempotent `seed_test.py` producing a
  small deterministic world.
- **D1** — Test DB is disposable: `reset_test.py` drops + recreates + seeds.
- **E2** — Full package: path resolution + seed + reset + guard, not path only.
- **F1** — `WORLD_ENGINE_ENV` (`prod`/`test`) is the primary fail-closed
  mechanism. `WORLD_ENGINE_DATABASE_URL`, when present, is an explicit override
  that *satisfies* the fail-closed check. Resolution order:
  explicit URL > resolved ENV > refuse to start.
- **G1** — `test_context.py` is converted to consume the test DB, backed by the
  deterministic seed.
- **H1** — `seed_test.py` produces documented deterministic IDs;
  `test_context.py` references those IDs. Explicit seed <-> test contract.
- No prod cleanup of any kind (creator handles prod manually). Path resolution
  never touches prod; that is guaranteed by A1+B1.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `WORLD_ENGINE_ENV` unset AND `WORLD_ENGINE_DATABASE_URL` unset => process
      refuses to start with a non-zero exit and an explicit message
      -> verify/checks/env_fail_closed.py
- [ ] No `scripts/*.py` imports `world_engine.db.engine` (or `create_db_and_tables`)
      without an env being resolvable at import time; test/seed scripts set or
      require the env before the import  -> verify/checks/env_guard.py
- [ ] `env=test` resolves to a path distinct from the prod default path, under
      `~/.world_engine/test/`  -> verify/checks/env_fail_closed.py

### Live  ->  human gate (Nia)
- [ ] `WORLD_ENGINE_ENV=test python scripts/reset_test.py` yields a fresh test DB
      at `~/.world_engine/test/world_engine_test.db`; prod file mtime unchanged.
- [ ] `WORLD_ENGINE_ENV=test python scripts/seed_test.py` run twice => identical
      summary, no duplicate rows (idempotent).
- [ ] `WORLD_ENGINE_ENV=test python scripts/test_context.py` passes its assertion
      report against the seeded test world.
- [ ] Prod still launches after updating the launch procedure to export
      `WORLD_ENGINE_ENV=prod` (see BRIEF-0049-a "Done means" + new procedure).

## Escalations

### E-01 — archived — QUESTION-TICKET-0049.md

**Response:** archived from `tooling/questions/QUESTION-TICKET-0049.md`, which the ticket pipeline wrote before escalations moved into the ticket. The file follows verbatim, its own Response included.

~~~~markdown
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
A - allow-list all ~49 operator/migration scripts alongside seed_pilot.py.
Confirmed 2026-07-27 (Nia): these scripts are not used anymore and won't
create problems. env_guard.py allow-lists them all with the shared
rationale, enforcing fail-closed only on the 6 scripts BRIEF-0049-d
actually anticipated (test_context.py, seed_test.py, reset_test.py,
test_ddl_atomicity.py, test_rollback_quarantine.py pass via their guards;
seed_pilot.py + the ~49 operator/migration scripts allow-listed). Chain
resumes at BRIEF-0049-d.
~~~~
