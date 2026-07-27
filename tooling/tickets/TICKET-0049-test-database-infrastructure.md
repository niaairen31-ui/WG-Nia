---
id: TICKET-0049
title: Test database infrastructure (WORLD_ENGINE_ENV, seed_test, reset_test, env_guard)
type: feature
status: exec
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
