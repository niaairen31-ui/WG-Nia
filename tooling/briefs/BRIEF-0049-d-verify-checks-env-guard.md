# BRIEF-0049-d — Step "verify checks: env_guard + env_fail_closed"

## Context
The ticket's promise — "Claude Code uses the test DB for its tests" — must be
structural, not a convention in CLAUDE.md. This step adds two fail-closed verify
checks so the guarantee is enforced by construction (the doctrine's whole point).
`env_fail_closed` proves `db.py` refuses to resolve without an env; `env_guard`
proves no script under `scripts/` reaches the engine without an env being set at
import time. Both are wired into TICKET-0049 so the runner (`run.py`, which only
executes checks referenced by `-> verify/checks/...` lines in the ticket .md)
picks them up.

## Mini-RECON (execute first, REPORT ONLY, no edits)
1. `sed -n '1,60p' tooling/verify/checks/import_cycle.py` — copy the established
   check idiom verbatim structure: `ROOT = ...parents[3]`, `FAILURES: list[str]`,
   `fail()`, `_report_and_exit()` with the vacuous-proof guard (zero targets =>
   FAILURE, not PASS), stdlib `ast` only, no DB, no execution of app code.
   REPORT the exact skeleton you will clone.
2. `sed -n '1,25p' tooling/verify/checks/no_print_in_src.py` — confirm the
   `scripts/` scoping precedent. `env_guard` scopes to `scripts/`, the inverse of
   this check's `src/` scope. REPORT.
3. `grep -n "machine_checks\|-> verify/checks\|CHECKS /" tooling/verify/run.py` —
   re-confirm the runner resolves each check by basename from a `->
   verify/checks/NAME.py` link in the ticket .md (RECON anchor run.py:10,52-53).
   REPORT that TICKET-0049's acceptance lines already carry these links (they do
   — env_fail_closed.py and env_guard.py).
4. `grep -rln "from world_engine.db import\|world_engine.db" scripts/*.py` —
   enumerate the scripts that import the engine/db. Expected set the guard must
   reason about: `test_context.py`, `seed_pilot.py`, `test_ddl_atomicity.py`,
   `test_rollback_quarantine.py`, and the new `seed_test.py` / `reset_test.py`.
   REPORT the full list; the guard logic below must correctly PASS the ones that
   set an env/URL before import and FAIL any that import the engine with no env
   resolvable.

## Scope IN
1. **Create `tooling/verify/checks/env_fail_closed.py`.** AST + subprocess-free
   static assertions on `src/world_engine/db.py`:
   - Assert the module does NOT contain an implicit prod default: there is no
     assignment resolving `DATABASE_URL` to a `world_engine.db` path via
     `os.getenv(..., <default>)` with a default argument. (Parse the AST; find the
     resolver; assert the "neither var set" branch raises.)
   - Assert a `raise` statement exists on the unresolved path, and that the
     refusal message substring `Refusing to start` is present in the module
     source.
   - Assert the `test` branch resolves under a `test` path segment
     (substring `"test"` in the resolved test path literal) distinct from the
     prod default filename.
   - Vacuous-proof: if `db.py` is missing or the resolver node is not found =>
     FAILURE (not pass).
2. **Create `tooling/verify/checks/env_guard.py`.** AST over every
   `scripts/*.py`:
   - For each script, determine (a) whether it imports the engine
     (`from world_engine.db import ...` naming `engine` or
     `create_db_and_tables`, or `from world_engine import db`), and (b) whether,
     lexically BEFORE that import in module top-level order, it either sets
     `os.environ["WORLD_ENGINE_ENV"]` / `os.environ["WORLD_ENGINE_DATABASE_URL"]`
     OR contains a top-level fail-closed guard reading
     `os.environ.get("WORLD_ENGINE_ENV")` and calling `sys.exit`.
   - PASS a script if it imports the engine AND (sets an env before import OR has
     the pre-import env guard). FAIL a script that imports the engine with
     neither.
   - Scripts that do not import the engine are out of scope (skip, not fail).
   - Vacuous-proof: if zero `scripts/*.py` are found, or zero engine-importing
     scripts are found => FAILURE (the check must never green on an empty set).
   - `seed_pilot.py` note: it imports the engine and does NOT currently set an
     env or carry a guard. Under this check it will FAIL. That is intended — it
     is the second latent prod-polluter. **Do not rewrite `seed_pilot.py` in this
     ticket.** Instead, add it to an explicit, commented `KNOWN_PROD_SEED_ALLOW`
     set at the top of `env_guard.py` naming `seed_pilot.py` with a one-line
     rationale (`creator-run pilot seed against prod, gated by operator, not a
     test harness — TICKET-0049 deferral`). The allow-set is the single declared
     exception; everything else fails closed. REPORT this as a flagged decision.
3. **Both checks** follow the `import_cycle.py` idiom exactly: `parents[3]` ROOT,
   `FAILURES` list, `fail()`, `_report_and_exit()`, print `PASS: <name> — ...`
   on success, `sys.exit(1)` with `FAIL:` lines otherwise. stdlib `ast` only.
4. **CLAUDE.md standing convention**: add one line under the testing/DB section:
   every test or seed script runs under `WORLD_ENGINE_ENV=test` and must set or
   guard the env before importing the engine; enforced by `env_guard.py`.

## Scope OUT
- Do NOT rewrite, re-env, or otherwise modify `seed_pilot.py` (allow-listed).
- Do NOT modify `db.py`, `seed_test.py`, `reset_test.py`, or `test_context.py`
  (landed in a/b/c).
- Do NOT make `env_guard` execute the scripts (AST only — never import or run a
  script that might touch a DB).
- Do NOT add these checks to any ticket other than TICKET-0049.
- Do NOT broaden `env_fail_closed` into a general env-var linter; it asserts only
  the db.py resolver contract.

## Invariants to defend
- **Structural over disciplinary**: these checks ARE the structural enforcement.
  They must fail-closed (vacuous-proof), or they'd give a false green — the exact
  failure mode called out in the standing lessons (function_length born-noncompliant,
  column-presence-only schema checks).
- **Report-only mini-RECON**: the RECON steps above take no action.

## Done means
- [ ] `python tooling/verify/checks/env_fail_closed.py` => `PASS` on the post-a
      `db.py`; flip-test: temporarily reintroduce a `getenv` default in a scratch
      copy => the check FAILS (do this in a throwaway file, not the real db.py;
      REPORT the flip result).
- [ ] `python tooling/verify/checks/env_guard.py` => `PASS`, with `seed_pilot.py`
      allow-listed and `test_context.py` / `seed_test.py` / `reset_test.py`
      passing via their pre-import guards, and the two scratch scripts passing via
      their explicit URL set.
- [ ] Introducing a scratch `scripts/test_bad.py` that does
      `from world_engine.db import engine` with no env => `env_guard` FAILS naming
      it. Remove the scratch file after; REPORT the result.
- [ ] `python tooling/verify/run.py` (or the project's verify entrypoint) against
      TICKET-0049 => both checks execute (proving the `->` links resolve) and
      report green.
- [ ] `/review-step` and `/close-step` (tooling code touched).

## Docs to update
- CLAUDE.md testing/DB convention line (Scope IN item 4).
- `DECISIONS_INDEX.md` / `ARCHITECTURE_DECISIONS.md`: record the `seed_pilot.py`
  allow-list exception (declared deferral, not a silent drop).
